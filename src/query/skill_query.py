"""技能查询：热门排行 / 共现关联 / 技能树 / 按分类查询"""

from src.loader.neo4j_client import Neo4jClient


def get_top_skills(
    client: Neo4jClient,
    limit: int = 30,
) -> list[dict]:
    """统计被最多职位要求的技能（热门排行）。"""
    return client.run_query(
        """
        MATCH (j:Job)-[:REQUIRES_SKILL|PREFERS_SKILL]->(s:Skill)
        RETURN s.name AS name,
               s.category AS category,
               count(DISTINCT j) AS job_count
        ORDER BY job_count DESC
        LIMIT $limit
        """,
        {"limit": limit},
    )


def get_related_skills(
    client: Neo4jClient,
    skill_name: str,
    limit: int = 20,
) -> list[dict]:
    """查询与指定技能共现频率最高的技能。"""
    return client.run_query(
        """
        MATCH (s:Skill {name: $name})-[r:CO_OCCURS_WITH]-(other:Skill)
        RETURN other.name AS name,
               other.category AS category,
               r.job_count AS job_count,
               r.weight AS weight
        ORDER BY r.job_count DESC
        LIMIT $limit
        """,
        {"name": skill_name, "limit": limit},
    )


def get_skill_tree(
    client: Neo4jClient,
    skill_name: str,
) -> dict:
    """查询指定技能的层级关系（父技能和子技能）。"""
    # 查找子技能（当前技能作为 parent）
    children = client.run_query(
        """
        MATCH (parent:Skill {name: $name})-[:PARENT_OF]->(child:Skill)
        RETURN child.name AS name, child.category AS category
        """,
        {"name": skill_name},
    )

    # 查找父技能（当前技能作为 child）
    parents = client.run_query(
        """
        MATCH (parent:Skill)-[:PARENT_OF]->(child:Skill {name: $name})
        RETURN parent.name AS name, parent.category AS category
        """,
        {"name": skill_name},
    )

    return {
        "skill": skill_name,
        "parents": parents,
        "children": children,
    }


def get_skills_by_category(
    client: Neo4jClient,
    category: str,
    limit: int = 50,
) -> list[dict]:
    """查询某分类下的所有技能。"""
    return client.run_query(
        """
        MATCH (s:Skill {category: $category})
        OPTIONAL MATCH (j:Job)-[:REQUIRES_SKILL|PREFERS_SKILL]->(s)
        RETURN s.name AS name,
               count(DISTINCT j) AS job_count
        ORDER BY job_count DESC
        LIMIT $limit
        """,
        {"category": category, "limit": limit},
    )
