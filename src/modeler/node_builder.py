"""节点构造器：从清洗后数据提取并去重所有节点"""

from src.modeler.schema import EDUCATION_RANK


def build_nodes(jds: list[dict]) -> dict:
    """从清洗后的 JD 数据中构造所有节点。

    Returns:
        {
            "jobs": [{"title": ..., "source_file": ..., ...}],
            "skills": [{"name": ..., "category": ...}],
            "locations": [{"name": ...}],
            "educations": [{"level": ..., "rank": ...}],
            "categories": [{"name": ...}],
        }
    """
    jobs = []
    skills_map: dict[str, dict] = {}   # name_lower → skill dict
    locations_set: set[str] = set()
    educations_set: set[str] = set()
    categories_set: set[str] = set()

    for jd in jds:
        # Job 节点
        exp = jd.get("experience", {})
        if isinstance(exp, str):
            exp = {"min": 0, "max": None}

        job = {
            "source_file": jd["source_file"],
            "title": jd.get("job_title", "未知职位"),
            "experience_min": exp.get("min", 0),
            "experience_max": exp.get("max"),
            "responsibilities": jd.get("responsibilities", []),
        }
        jobs.append(job)

        # Skill 节点（全局去重）
        for skill in jd.get("required_skills", []) + jd.get("preferred_skills", []):
            name = skill.get("name", "").strip()
            if not name:
                continue
            key = name.lower()
            if key not in skills_map:
                skills_map[key] = {
                    "name": name,
                    "category": skill.get("category", "其他"),
                }

            # 同时收集 parent 指向的技能
            parent = skill.get("parent")
            if parent:
                parent = parent.strip()
                pkey = parent.lower()
                if pkey not in skills_map:
                    skills_map[pkey] = {
                        "name": parent,
                        "category": "其他",
                    }

        # Location 节点
        for loc in jd.get("locations", []):
            locations_set.add(loc)

        # Education 节点
        edu = jd.get("education")
        if edu:
            educations_set.add(edu)

        # Category 节点
        cat = jd.get("job_category")
        if cat:
            categories_set.add(cat)

    return {
        "jobs": jobs,
        "skills": list(skills_map.values()),
        "locations": [{"name": loc} for loc in sorted(locations_set)],
        "educations": [
            {"level": edu, "rank": EDUCATION_RANK.get(edu, -1)}
            for edu in sorted(educations_set, key=lambda e: EDUCATION_RANK.get(e, -1))
        ],
        "categories": [{"name": cat} for cat in sorted(categories_set)],
    }
