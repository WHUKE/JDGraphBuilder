"""技能数据清洗与增强"""


def clean_skills(required: list[dict], preferred: list[dict]) -> tuple[list[dict], list[dict]]:
    """清洗技能数据：补全缺失字段、去重。

    Returns:
        (cleaned_required, cleaned_preferred)
    """
    required = [_clean_single_skill(s) for s in required]
    preferred = [_clean_single_skill(s) for s in preferred]

    # required 内部去重
    required = _dedup_skills(required)

    # preferred 内部去重
    preferred = _dedup_skills(preferred)

    # preferred 中移除已在 required 中出现的技能
    required_names = {s["name"].lower() for s in required}
    preferred = [s for s in preferred if s["name"].lower() not in required_names]

    return required, preferred


def _clean_single_skill(skill: dict) -> dict:
    """清洗单个技能 dict：补全缺失字段。"""
    from src.cleaner.field_cleaner import clean_proficiency

    result = dict(skill)

    # name 必须存在
    result["name"] = result.get("name", "").strip()

    # proficiency 缺失补全
    result["proficiency"] = clean_proficiency(result.get("proficiency"))

    # category 缺失补全
    if not result.get("category") or not result["category"].strip():
        result["category"] = "其他"

    # parent 保留（可为 None）
    result.setdefault("parent", None)

    return result


def _dedup_skills(skills: list[dict]) -> list[dict]:
    """按技能名称去重（大小写不敏感），保留第一次出现的。"""
    seen: set[str] = set()
    result = []
    for s in skills:
        key = s["name"].lower()
        if key and key not in seen:
            seen.add(key)
            result.append(s)
    return result
