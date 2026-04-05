"""职位查询：按技能/地点/学历匹配职位"""

from src.loader.neo4j_client import Neo4jClient


def find_jobs_by_skills(
    client: Neo4jClient,
    skills: list[str],
    limit: int = 20,
) -> list[dict]:
    """给定技能列表，返回匹配度最高的职位（按匹配技能数排序）。"""
    return client.run_query(
        """
        MATCH (j:Job)-[r:REQUIRES_SKILL]->(s:Skill)
        WHERE s.name IN $skills
        WITH j, count(s) AS matched, collect(s.name) AS matched_skills
        OPTIONAL MATCH (j)-[:LOCATED_IN]->(l:Location)
        OPTIONAL MATCH (j)-[:REQUIRES_EDUCATION]->(e:Education)
        OPTIONAL MATCH (j)-[:BELONGS_TO]->(c:Category)
        RETURN j.title AS title,
               j.source_file AS source_file,
               matched,
               matched_skills,
               collect(DISTINCT l.name) AS locations,
               e.level AS education,
               c.name AS category
        ORDER BY matched DESC
        LIMIT $limit
        """,
        {"skills": skills, "limit": limit},
    )


def find_jobs_by_location(
    client: Neo4jClient,
    city: str,
    limit: int = 50,
) -> list[dict]:
    """查询指定城市的所有职位。"""
    return client.run_query(
        """
        MATCH (j:Job)-[:LOCATED_IN]->(l:Location {name: $city})
        OPTIONAL MATCH (j)-[:REQUIRES_EDUCATION]->(e:Education)
        OPTIONAL MATCH (j)-[:BELONGS_TO]->(c:Category)
        RETURN j.title AS title,
               j.source_file AS source_file,
               e.level AS education,
               c.name AS category
        ORDER BY j.title
        LIMIT $limit
        """,
        {"city": city, "limit": limit},
    )


def find_jobs_by_education(
    client: Neo4jClient,
    level: str,
    limit: int = 50,
) -> list[dict]:
    """查询指定学历要求及以下的职位。"""
    from src.modeler.schema import EDUCATION_RANK

    rank = EDUCATION_RANK.get(level, 1)
    return client.run_query(
        """
        MATCH (j:Job)-[:REQUIRES_EDUCATION]->(e:Education)
        WHERE e.rank <= $rank
        OPTIONAL MATCH (j)-[:LOCATED_IN]->(l:Location)
        OPTIONAL MATCH (j)-[:BELONGS_TO]->(c:Category)
        RETURN j.title AS title,
               j.source_file AS source_file,
               e.level AS education,
               collect(DISTINCT l.name) AS locations,
               c.name AS category
        ORDER BY e.rank DESC, j.title
        LIMIT $limit
        """,
        {"rank": rank, "limit": limit},
    )


def get_job_detail(client: Neo4jClient, source_file: str) -> dict | None:
    """获取职位完整详情。"""
    results = client.run_query(
        """
        MATCH (j:Job {source_file: $sf})
        OPTIONAL MATCH (j)-[rs:REQUIRES_SKILL]->(req_s:Skill)
        OPTIONAL MATCH (j)-[ps:PREFERS_SKILL]->(pref_s:Skill)
        OPTIONAL MATCH (j)-[:LOCATED_IN]->(l:Location)
        OPTIONAL MATCH (j)-[:REQUIRES_EDUCATION]->(e:Education)
        OPTIONAL MATCH (j)-[:BELONGS_TO]->(c:Category)
        RETURN j.title AS title,
               j.source_file AS source_file,
               j.experience_min AS experience_min,
               j.experience_max AS experience_max,
               j.responsibilities AS responsibilities,
               e.level AS education,
               c.name AS category,
               collect(DISTINCT l.name) AS locations,
               collect(DISTINCT {name: req_s.name, proficiency: rs.proficiency, category: req_s.category}) AS required_skills,
               collect(DISTINCT {name: pref_s.name, proficiency: ps.proficiency, category: pref_s.category}) AS preferred_skills
        """,
        {"sf": source_file},
    )
    if results:
        result = results[0]
        # 过滤掉 null 技能（来自 OPTIONAL MATCH）
        result["required_skills"] = [s for s in result["required_skills"] if s.get("name")]
        result["preferred_skills"] = [s for s in result["preferred_skills"] if s.get("name")]
        return result
    return None
