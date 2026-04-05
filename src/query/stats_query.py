"""统计查询：图谱概览 / 各类分布"""

from src.loader.neo4j_client import Neo4jClient


def get_graph_overview(client: Neo4jClient) -> dict:
    """获取图谱概览：各类节点和关系的数量。"""
    node_counts = client.run_query(
        """
        CALL {
            MATCH (n:Job) RETURN 'Job' AS label, count(n) AS count
            UNION ALL
            MATCH (n:Skill) RETURN 'Skill' AS label, count(n) AS count
            UNION ALL
            MATCH (n:Location) RETURN 'Location' AS label, count(n) AS count
            UNION ALL
            MATCH (n:Education) RETURN 'Education' AS label, count(n) AS count
            UNION ALL
            MATCH (n:Category) RETURN 'Category' AS label, count(n) AS count
        }
        RETURN label, count
        """
    )

    rel_counts = client.run_query(
        """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY count DESC
        """
    )

    return {
        "nodes": {r["label"]: r["count"] for r in node_counts},
        "relations": {r["type"]: r["count"] for r in rel_counts},
    }


def get_skill_distribution(
    client: Neo4jClient,
    limit: int = 50,
) -> list[dict]:
    """各技能被职位要求的频次统计。"""
    return client.run_query(
        """
        MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill)
        RETURN s.name AS skill,
               s.category AS category,
               count(j) AS required_count
        ORDER BY required_count DESC
        LIMIT $limit
        """,
        {"limit": limit},
    )


def get_location_distribution(client: Neo4jClient) -> list[dict]:
    """各城市的职位数量统计。"""
    return client.run_query(
        """
        MATCH (j:Job)-[:LOCATED_IN]->(l:Location)
        RETURN l.name AS location, count(j) AS job_count
        ORDER BY job_count DESC
        """
    )


def get_education_distribution(client: Neo4jClient) -> list[dict]:
    """各学历要求的职位数量统计。"""
    return client.run_query(
        """
        MATCH (j:Job)-[:REQUIRES_EDUCATION]->(e:Education)
        RETURN e.level AS education, e.rank AS rank, count(j) AS job_count
        ORDER BY e.rank
        """
    )


def get_category_distribution(client: Neo4jClient) -> list[dict]:
    """各职位类别的统计。"""
    return client.run_query(
        """
        MATCH (j:Job)-[:BELONGS_TO]->(c:Category)
        RETURN c.name AS category, count(j) AS job_count
        ORDER BY job_count DESC
        """
    )


def get_skill_category_distribution(client: Neo4jClient) -> list[dict]:
    """各技能类别的技能数量和关联职位数。"""
    return client.run_query(
        """
        MATCH (s:Skill)
        OPTIONAL MATCH (j:Job)-[:REQUIRES_SKILL|PREFERS_SKILL]->(s)
        WITH s.category AS category,
             count(DISTINCT s) AS skill_count,
             count(DISTINCT j) AS job_count
        RETURN category, skill_count, job_count
        ORDER BY job_count DESC
        """
    )
