"""路径查询：技能差距分析 / 职位跳转路径"""

from src.loader.neo4j_client import Neo4jClient


def get_skill_gap(
    client: Neo4jClient,
    user_skills: list[str],
    target_job_title: str,
) -> dict:
    """分析用户技能集与目标职位的差距。

    Returns:
        {
            "target_job": ...,
            "matched_skills": [...],
            "missing_skills": [...],
            "match_rate": float,
        }
    """
    result = client.run_query(
        """
        MATCH (j:Job)
        WHERE j.title CONTAINS $title
        WITH j LIMIT 1
        OPTIONAL MATCH (j)-[r:REQUIRES_SKILL]->(s:Skill)
        RETURN j.title AS title,
               j.source_file AS source_file,
               collect({name: s.name, proficiency: r.proficiency, category: s.category}) AS required_skills
        """,
        {"title": target_job_title},
    )

    if not result:
        return {"target_job": target_job_title, "error": "未找到匹配职位"}

    job = result[0]
    required = [s for s in job["required_skills"] if s.get("name")]
    required_names = {s["name"] for s in required}
    user_set = {s.lower() for s in user_skills}

    matched = [s for s in required if s["name"].lower() in user_set]
    missing = [s for s in required if s["name"].lower() not in user_set]

    return {
        "target_job": job["title"],
        "source_file": job["source_file"],
        "matched_skills": matched,
        "missing_skills": missing,
        "match_rate": round(len(matched) / len(required), 2) if required else 0,
    }


def get_job_transition(
    client: Neo4jClient,
    from_job_title: str,
    to_job_title: str,
) -> dict:
    """分析两个职位之间的技能重叠度和需要补充的技能。"""
    result = client.run_query(
        """
        MATCH (j1:Job) WHERE j1.title CONTAINS $from_title
        WITH j1 LIMIT 1
        MATCH (j2:Job) WHERE j2.title CONTAINS $to_title
        WITH j1, j2 LIMIT 1
        OPTIONAL MATCH (j1)-[:REQUIRES_SKILL]->(s1:Skill)
        OPTIONAL MATCH (j2)-[:REQUIRES_SKILL]->(s2:Skill)
        WITH j1, j2,
             collect(DISTINCT s1.name) AS skills_from,
             collect(DISTINCT s2.name) AS skills_to
        RETURN j1.title AS from_title,
               j2.title AS to_title,
               skills_from,
               skills_to,
               [s IN skills_to WHERE s IN skills_from] AS overlapping,
               [s IN skills_to WHERE NOT s IN skills_from] AS to_learn,
               [s IN skills_from WHERE NOT s IN skills_to] AS no_longer_needed
        """,
        {"from_title": from_job_title, "to_title": to_job_title},
    )

    if not result:
        return {"error": "未找到匹配职位"}

    r = result[0]
    total_target = len(r["skills_to"]) if r["skills_to"] else 1
    return {
        "from_job": r["from_title"],
        "to_job": r["to_title"],
        "overlapping_skills": r["overlapping"] or [],
        "skills_to_learn": r["to_learn"] or [],
        "skills_no_longer_needed": r["no_longer_needed"] or [],
        "overlap_rate": round(len(r["overlapping"] or []) / total_target, 2),
    }
