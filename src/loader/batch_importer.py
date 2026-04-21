"""批量导入器：将建模数据高效写入 Neo4j"""

import logging
import time

from src.loader.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class BatchImporter:
    """按顺序批量导入节点和关系到 Neo4j。"""

    def __init__(self, client: Neo4jClient):
        self._client = client

    def import_all(
        self,
        nodes: dict,
        relations: dict,
        co_occurrences: list[dict],
    ) -> dict:
        """执行完整导入流程，返回各步骤的导入数量。

        导入顺序（保证引用完整性）：
        1. Skill 节点
        2. Location 节点
        3. Education 节点
        4. Category 节点
        5. Job 节点
        6. Job → Skill 关系 (REQUIRES_SKILL / PREFERS_SKILL)
        7. Job → Location / Education / Category 关系
        8. Skill → Skill (PARENT_OF)
        9. Skill → Skill (CO_OCCURS_WITH)
        """
        stats = {}
        t0 = time.time()

        # 1. Skill 节点
        stats["skills"] = self._import_skills(nodes["skills"])

        # 2. Location 节点
        stats["locations"] = self._import_locations(nodes["locations"])

        # 3. Education 节点
        stats["educations"] = self._import_educations(nodes["educations"])

        # 4. Category 节点
        stats["categories"] = self._import_categories(nodes["categories"])

        # 5. Job 节点
        stats["jobs"] = self._import_jobs(nodes["jobs"])

        # 6. REQUIRES_SKILL / PREFERS_SKILL
        stats["requires_skill"] = self._import_job_skill_relations(
            relations["requires_skill"], "REQUIRES_SKILL"
        )
        stats["prefers_skill"] = self._import_job_skill_relations(
            relations["prefers_skill"], "PREFERS_SKILL"
        )

        # 7. REQUIRES_EDUCATION / LOCATED_IN / BELONGS_TO
        stats["requires_education"] = self._import_job_education(
            relations["requires_education"]
        )
        stats["located_in"] = self._import_job_location(relations["located_in"])
        stats["belongs_to"] = self._import_job_category(relations["belongs_to"])

        # 8. PARENT_OF
        stats["parent_of"] = self._import_parent_of(relations["parent_of"])

        # 9. CO_OCCURS_WITH
        stats["co_occurs_with"] = self._import_co_occurrence(co_occurrences)

        elapsed = time.time() - t0
        logger.info("全部导入完成，耗时 %.1f 秒", elapsed)
        for key, count in stats.items():
            logger.info("  %-20s: %d", key, count)

        return stats

    # ── 增量导入（P1.1） ────────────────────────────────

    def import_all_incremental(
        self,
        nodes: dict,
        relations: dict,
        co_occurrences: list[dict],
        touched_source_files: list[str],
    ) -> dict:
        """增量导入：仅更新 touched_source_files 涉及的 Job 及其关系。

        策略：
          a) 先 DELETE 这些 Job 的 5 类出边（REQUIRES_SKILL / PREFERS_SKILL /
             REQUIRES_EDUCATION / LOCATED_IN / BELONGS_TO），避免脏边残留。
          b) MERGE 字典节点（Skill / Location / Education / Category，全量，
             不会破坏既有；因规模小，这里依然走全量 MERGE 保证新数据可用）。
          c) MERGE 这些 Job 节点（升级 title 等属性）。
          d) 重新建立这些 Job 的 5 类出边（只导入子集）。
          e) PARENT_OF 全量重算（规模 < 1k，简单稳定）。
          f) CO_OCCURS_WITH 全量重算（整图 DELETE 后重新 MERGE）。
        """
        stats: dict[str, int] = {}
        t0 = time.time()
        touched = list(dict.fromkeys(touched_source_files))  # 去重保序
        logger.info("增量导入 %d 个 Job（source_file 集合）", len(touched))

        # a) 清理这些 Job 的旧出边
        stats["purged_edges"] = self._purge_job_edges(touched)

        # b) 字典节点 MERGE（小规模，全量即可）
        stats["skills"] = self._import_skills(nodes["skills"])
        stats["locations"] = self._import_locations(nodes["locations"])
        stats["educations"] = self._import_educations(nodes["educations"])
        stats["categories"] = self._import_categories(nodes["categories"])

        # c) Job 节点 MERGE（仅 touched 子集）
        touched_set = set(touched)
        jobs_subset = [j for j in nodes["jobs"] if j["source_file"] in touched_set]
        stats["jobs"] = self._import_jobs(jobs_subset)

        # d) 重建 Job 的 5 类出边（仅 touched 子集）
        req_subset = [r for r in relations["requires_skill"] if r["source_file"] in touched_set]
        pref_subset = [r for r in relations["prefers_skill"] if r["source_file"] in touched_set]
        edu_subset = [r for r in relations["requires_education"] if r["source_file"] in touched_set]
        loc_subset = [r for r in relations["located_in"] if r["source_file"] in touched_set]
        cat_subset = [r for r in relations["belongs_to"] if r["source_file"] in touched_set]

        stats["requires_skill"] = self._import_job_skill_relations(req_subset, "REQUIRES_SKILL")
        stats["prefers_skill"] = self._import_job_skill_relations(pref_subset, "PREFERS_SKILL")
        stats["requires_education"] = self._import_job_education(edu_subset)
        stats["located_in"] = self._import_job_location(loc_subset)
        stats["belongs_to"] = self._import_job_category(cat_subset)

        # e) PARENT_OF 全量重算
        self._client.run_write("MATCH ()-[r:PARENT_OF]->() DELETE r")
        stats["parent_of"] = self._import_parent_of(relations["parent_of"])

        # f) CO_OCCURS_WITH 全量重算
        self._client.run_write("MATCH ()-[r:CO_OCCURS_WITH]-() DELETE r")
        stats["co_occurs_with"] = self._import_co_occurrence(co_occurrences)

        elapsed = time.time() - t0
        logger.info("增量导入完成，耗时 %.1f 秒", elapsed)
        for key, count in stats.items():
            logger.info("  %-20s: %d", key, count)

        return stats

    def _purge_job_edges(self, source_files: list[str]) -> int:
        """删除给定 source_file 对应 Job 的 5 类出边，返回删除的边总数。"""
        if not source_files:
            return 0
        result = self._client.run_query(
            """
            UNWIND $sfs AS sf
            MATCH (j:Job {source_file: sf})
            OPTIONAL MATCH (j)-[r:REQUIRES_SKILL|PREFERS_SKILL|REQUIRES_EDUCATION|LOCATED_IN|BELONGS_TO]->()
            WITH r WHERE r IS NOT NULL
            DELETE r
            RETURN count(*) AS deleted
            """,
            {"sfs": source_files},
        )
        deleted = result[0]["deleted"] if result else 0
        logger.info("已清理 %d 条旧出边（来自 %d 个 Job）", deleted, len(source_files))
        return deleted

    # ── 节点导入 ───────────────────────────────────────

    def _import_skills(self, skills: list[dict]) -> int:
        logger.info("导入 Skill 节点: %d", len(skills))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MERGE (s:Skill {name: item.name})
            SET s.category = item.category
            """,
            skills,
        )

    def _import_locations(self, locations: list[dict]) -> int:
        logger.info("导入 Location 节点: %d", len(locations))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MERGE (l:Location {name: item.name})
            """,
            locations,
        )

    def _import_educations(self, educations: list[dict]) -> int:
        logger.info("导入 Education 节点: %d", len(educations))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MERGE (e:Education {level: item.level})
            SET e.rank = item.rank
            """,
            educations,
        )

    def _import_categories(self, categories: list[dict]) -> int:
        logger.info("导入 Category 节点: %d", len(categories))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MERGE (c:Category {name: item.name})
            """,
            categories,
        )

    def _import_jobs(self, jobs: list[dict]) -> int:
        logger.info("导入 Job 节点: %d", len(jobs))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MERGE (j:Job {source_file: item.source_file})
            SET j.title = item.title,
                j.experience_min = item.experience_min,
                j.experience_max = item.experience_max,
                j.responsibilities = item.responsibilities
            """,
            jobs,
        )

    # ── 关系导入 ───────────────────────────────────────

    def _import_job_skill_relations(
        self, relations: list[dict], rel_type: str
    ) -> int:
        logger.info("导入 %s 关系: %d", rel_type, len(relations))
        cypher = f"""
            UNWIND $batch AS item
            MATCH (j:Job {{source_file: item.source_file}})
            MATCH (s:Skill {{name: item.skill_name}})
            MERGE (j)-[r:{rel_type}]->(s)
            SET r.proficiency = item.proficiency
        """
        return self._client.run_batch(cypher, relations)

    def _import_job_education(self, relations: list[dict]) -> int:
        logger.info("导入 REQUIRES_EDUCATION 关系: %d", len(relations))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MATCH (j:Job {source_file: item.source_file})
            MATCH (e:Education {level: item.education})
            MERGE (j)-[:REQUIRES_EDUCATION]->(e)
            """,
            relations,
        )

    def _import_job_location(self, relations: list[dict]) -> int:
        logger.info("导入 LOCATED_IN 关系: %d", len(relations))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MATCH (j:Job {source_file: item.source_file})
            MATCH (l:Location {name: item.location})
            MERGE (j)-[:LOCATED_IN]->(l)
            """,
            relations,
        )

    def _import_job_category(self, relations: list[dict]) -> int:
        logger.info("导入 BELONGS_TO 关系: %d", len(relations))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MATCH (j:Job {source_file: item.source_file})
            MATCH (c:Category {name: item.category})
            MERGE (j)-[:BELONGS_TO]->(c)
            """,
            relations,
        )

    def _import_parent_of(self, relations: list[dict]) -> int:
        logger.info("导入 PARENT_OF 关系: %d", len(relations))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MATCH (parent:Skill {name: item.parent})
            MATCH (child:Skill {name: item.child})
            MERGE (parent)-[:PARENT_OF]->(child)
            """,
            relations,
        )

    def _import_co_occurrence(self, co_occurrences: list[dict]) -> int:
        logger.info("导入 CO_OCCURS_WITH 关系: %d", len(co_occurrences))
        return self._client.run_batch(
            """
            UNWIND $batch AS item
            MATCH (a:Skill {name: item.skill_a})
            MATCH (b:Skill {name: item.skill_b})
            MERGE (a)-[r:CO_OCCURS_WITH]-(b)
            SET r.job_count = item.job_count,
                r.weight = item.weight
            """,
            co_occurrences,
        )
