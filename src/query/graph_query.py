"""图谱可视化数据查询：为前端生成 nodes / edges 结构。"""

from __future__ import annotations

from src.loader.neo4j_client import Neo4jClient
from src.query.job_query import find_jobs_by_skills
from src.query.skill_query import get_related_skills, get_top_skills


def get_visual_graph(
    client: Neo4jClient,
    skill_limit: int = 8,
    related_skill_limit: int = 3,
    jobs_per_skill: int = 2,
    focus_skill: str | None = None,
) -> dict:
    """生成适合前端 D3 渲染的子图数据。"""

    def add_node(node_id: str, label: str, node_type: str, **attrs) -> None:
        existing = nodes.get(node_id)
        payload = {
            "id": node_id,
            "label": label,
            "type": node_type,
        }
        payload.update({key: value for key, value in attrs.items() if value is not None})
        if existing is None:
            nodes[node_id] = payload
            return
        for key, value in payload.items():
            if key not in existing or existing[key] in (None, "", [], {}):
                existing[key] = value

    def add_edge(source: str, target: str, label: str, **attrs) -> None:
        key = (source, target, label, attrs.get("relation"))
        if key in edge_keys:
            return
        edge = {"source": source, "target": target, "label": label}
        edge.update({key: value for key, value in attrs.items() if value is not None})
        edges.append(edge)
        edge_keys.add(key)

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    edge_keys: set[tuple[str, str, str, str | None]] = set()

    seeds = [{"name": focus_skill}] if focus_skill else get_top_skills(client, limit=skill_limit)

    for skill in seeds:
        skill_name = skill.get("name")
        if not skill_name:
            continue

        skill_id = f"skill:{skill_name}"
        add_node(
            skill_id,
            skill_name,
            "skill",
            category=skill.get("category"),
            job_count=skill.get("job_count"),
        )

        related_skills = get_related_skills(client, skill_name, limit=related_skill_limit)
        for related in related_skills:
            related_name = related.get("name")
            if not related_name:
                continue
            related_id = f"skill:{related_name}"
            add_node(
                related_id,
                related_name,
                "skill",
                category=related.get("category"),
                job_count=related.get("job_count"),
            )
            add_edge(
                skill_id,
                related_id,
                "co_occurs",
                relation="CO_OCCURS_WITH",
                weight=related.get("weight"),
                job_count=related.get("job_count"),
            )

        jobs = find_jobs_by_skills(client, [skill_name], limit=jobs_per_skill)
        for job in jobs:
            source_file = job.get("source_file")
            title = job.get("title")
            if not source_file or not title:
                continue

            job_id = f"job:{source_file}"
            add_node(
                job_id,
                title,
                "role",
                source_file=source_file,
                category=job.get("category"),
                education=job.get("education"),
                locations=job.get("locations") or [],
                matched=job.get("matched", 0),
            )
            add_edge(
                job_id,
                skill_id,
                "requires",
                relation="REQUIRES_SKILL",
                matched=job.get("matched", 0),
            )

            for location in job.get("locations") or []:
                location_id = f"location:{location}"
                add_node(location_id, location, "meta", kind="location")
                add_edge(job_id, location_id, "located_in", relation="LOCATED_IN")

            education = job.get("education")
            if education:
                education_id = f"education:{education}"
                add_node(education_id, education, "meta", kind="education")
                add_edge(job_id, education_id, "requires_education", relation="REQUIRES_EDUCATION")

            category = job.get("category")
            if category:
                category_id = f"category:{category}"
                add_node(category_id, category, "meta", kind="category")
                add_edge(job_id, category_id, "belongs_to", relation="BELONGS_TO")

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": {
            "seed_skill": focus_skill,
            "skill_limit": skill_limit,
            "related_skill_limit": related_skill_limit,
            "jobs_per_skill": jobs_per_skill,
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }
