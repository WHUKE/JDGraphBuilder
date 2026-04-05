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
