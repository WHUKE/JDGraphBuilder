"""关系构造器：从清洗后数据生成显式关系"""


def build_relations(jds: list[dict]) -> dict:
    """从清洗后的 JD 数据中构造所有显式关系。

    Returns:
        {
            "requires_skill": [{"source_file": ..., "skill_name": ..., "proficiency": ...}],
            "prefers_skill":  [{"source_file": ..., "skill_name": ..., "proficiency": ...}],
            "requires_education": [{"source_file": ..., "education": ...}],
            "located_in": [{"source_file": ..., "location": ...}],
            "belongs_to": [{"source_file": ..., "category": ...}],
            "parent_of": [{"parent": ..., "child": ...}],
        }
    """
    requires_skill = []
    prefers_skill = []
    requires_education = []
    located_in = []
    belongs_to = []
    parent_of_set: set[tuple[str, str]] = set()

    for jd in jds:
        sf = jd["source_file"]

        # REQUIRES_SKILL
        for skill in jd.get("required_skills", []):
            name = skill.get("name", "").strip()
            if name:
                requires_skill.append({
                    "source_file": sf,
                    "skill_name": name,
                    "proficiency": skill.get("proficiency", "不限"),
                })
            # parent 关系
            parent = skill.get("parent")
            if parent and name:
                parent = parent.strip()
                key = (parent.lower(), name.lower())
                if key not in parent_of_set:
                    parent_of_set.add(key)

        # PREFERS_SKILL
        for skill in jd.get("preferred_skills", []):
            name = skill.get("name", "").strip()
            if name:
                prefers_skill.append({
                    "source_file": sf,
                    "skill_name": name,
                    "proficiency": skill.get("proficiency", "不限"),
                })
            parent = skill.get("parent")
            if parent and name:
                parent = parent.strip()
                key = (parent.lower(), name.lower())
                if key not in parent_of_set:
                    parent_of_set.add(key)

        # REQUIRES_EDUCATION
        edu = jd.get("education")
        if edu:
            requires_education.append({
                "source_file": sf,
                "education": edu,
            })

        # LOCATED_IN (多地点 → 多条关系)
        for loc in jd.get("locations", []):
            located_in.append({
                "source_file": sf,
                "location": loc,
            })

        # BELONGS_TO
        cat = jd.get("job_category")
        if cat:
            belongs_to.append({
                "source_file": sf,
                "category": cat,
            })

    # PARENT_OF: 将 set 转为 list[dict]，保持原始大小写
    # 需要从原始数据中获取正确大小写的名称
    parent_of = _build_parent_of_list(jds, parent_of_set)

    return {
        "requires_skill": requires_skill,
        "prefers_skill": prefers_skill,
        "requires_education": requires_education,
        "located_in": located_in,
        "belongs_to": belongs_to,
        "parent_of": parent_of,
    }


def _build_parent_of_list(
    jds: list[dict], parent_of_set: set[tuple[str, str]]
) -> list[dict]:
    """从去重集合中构建 parent_of 关系列表，保留原始大小写。"""
    # 构建 lower → original 名称映射
    name_map: dict[str, str] = {}
    for jd in jds:
        for skill in jd.get("required_skills", []) + jd.get("preferred_skills", []):
            n = skill.get("name", "").strip()
            if n:
                name_map.setdefault(n.lower(), n)
            p = skill.get("parent")
            if p:
                p = p.strip()
                name_map.setdefault(p.lower(), p)

    result = []
    for parent_lower, child_lower in parent_of_set:
        parent_name = name_map.get(parent_lower, parent_lower)
        child_name = name_map.get(child_lower, child_lower)
        result.append({"parent": parent_name, "child": child_name})
    return result
