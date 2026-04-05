"""技能共现关系计算"""

from itertools import combinations


def compute_co_occurrence(
    jds: list[dict], min_count: int = 2
) -> list[dict]:
    """计算技能共现关系。

    对于同一 JD 中同时出现的技能对 (A, B)，统计：
    - job_count: 共同出现在多少个 JD 中
    - weight: 归一化后的共现强度 (0-1)

    仅保留 job_count >= min_count 的共现关系。

    Returns:
        [{"skill_a": "Python", "skill_b": "Django", "job_count": 15, "weight": 0.83}, ...]
    """
    pair_counts: dict[tuple[str, str], int] = {}  # (a, b) → count, a < b
    # 用于保留原始名称大小写
    name_map: dict[str, str] = {}  # lower → original

    for jd in jds:
        all_skills = jd.get("required_skills", []) + jd.get("preferred_skills", [])
        skill_names: list[str] = []
        for s in all_skills:
            n = s.get("name", "").strip()
            if n:
                name_map.setdefault(n.lower(), n)
                skill_names.append(n.lower())

        # 去重（同一 JD 内）
        skill_names = list(dict.fromkeys(skill_names))

        # 两两配对
        for a, b in combinations(sorted(skill_names), 2):
            pair = (a, b)
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    # 过滤低频对
    filtered = {k: v for k, v in pair_counts.items() if v >= min_count}

    if not filtered:
        return []

    # 归一化权重
    max_count = max(filtered.values())

    result = []
    for (a, b), count in sorted(filtered.items(), key=lambda x: -x[1]):
        result.append({
            "skill_a": name_map.get(a, a),
            "skill_b": name_map.get(b, b),
            "job_count": count,
            "weight": round(count / max_count, 4),
        })

    return result
