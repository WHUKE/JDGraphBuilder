"""字段级清洗：地点 / 学历 / 经验 / 职位类别 / 职位名称"""

import json
import logging
import re
from pathlib import Path

from src.config import MAPPINGS_DIR

logger = logging.getLogger(__name__)

# 本轮清洗流程中出现过的非标准 proficiency 值（原始词 → 出现次数），
# 由 pipeline 在流程结束后读取并写入清洗报告。
_unknown_proficiency_counter: dict[str, int] = {}


def _load_mapping(filename: str) -> dict:
    path = MAPPINGS_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── 地点归一化 ─────────────────────────────────────────

_location_cfg: dict | None = None


def _get_location_cfg() -> dict:
    global _location_cfg
    if _location_cfg is None:
        _location_cfg = _load_mapping("location_mapping.json")
    return _location_cfg


def clean_location(location: str | None) -> list[str]:
    """将原始地点字符串归一化为城市名列表。

    - "广州市" → ["广州"]
    - "北京、上海、深圳" → ["北京", "上海", "深圳"]
    - "北京/上海" → ["北京", "上海"]
    - None → ["未知"]
    """
    if not location or not location.strip():
        return ["未知"]

    cfg = _get_location_cfg()
    separators = cfg["分隔符"]
    city_map = cfg["城市映射"]

    # 按分隔符拆分
    parts = [location]
    for sep in separators:
        new_parts = []
        for p in parts:
            new_parts.extend(p.split(sep))
        parts = new_parts

    cities = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 查映射表
        if part in city_map:
            part = city_map[part]
        else:
            # 去除"市""区"后缀
            for suffix in cfg["城市后缀"]:
                if part.endswith(suffix) and len(part) > len(suffix) + 1:
                    part = part[: -len(suffix)]
                    break
        if part and part not in cities:
            cities.append(part)

    return cities if cities else ["未知"]


# ── 学历归一化 ─────────────────────────────────────────

_education_cfg: dict | None = None


def _get_education_cfg() -> dict:
    global _education_cfg
    if _education_cfg is None:
        _education_cfg = _load_mapping("education_mapping.json")
    return _education_cfg


def clean_education(education: str | None) -> str:
    """将学历表述归一化为标准枚举值。

    - "本科及以上" → "本科"
    - "Bachelor" → "本科"
    - None → "不限"
    """
    if not education or not education.strip():
        return "不限"

    cfg = _get_education_cfg()
    edu = education.strip()

    # 直接匹配有效值
    if edu in cfg["有效值"]:
        return edu

    # 查映射表（大小写不敏感）
    edu_lower = edu.lower()
    for key, val in cfg["映射"].items():
        if edu_lower == key.lower():
            return val

    # 尝试包含匹配（如"本科及以上"未在映射表中但包含"本科"）
    for valid in cfg["有效值"]:
        if valid != "不限" and valid in edu:
            return valid

    return cfg["默认值"]


# ── 经验结构化 ─────────────────────────────────────────

_EXP_RANGE_RE = re.compile(r"(\d+)\s*[-–~]\s*(\d+)\s*年")
_EXP_MIN_RE = re.compile(r"(\d+)\s*年")


def clean_experience(experience: str | None) -> dict:
    """将经验字符串结构化为 {"min": int, "max": int|None}。

    - "3-5年" → {"min": 3, "max": 5}
    - "3年以上" → {"min": 3, "max": None}
    - "不限" / None → {"min": 0, "max": None}
    """
    if not experience or not experience.strip():
        return {"min": 0, "max": None}

    exp = experience.strip()

    if exp == "不限":
        return {"min": 0, "max": None}

    # "3-5年" / "5-10年"
    m = _EXP_RANGE_RE.search(exp)
    if m:
        return {"min": int(m.group(1)), "max": int(m.group(2))}

    # "3年以上" / "3年及以上" / "3年左右"
    m = _EXP_MIN_RE.search(exp)
    if m:
        val = int(m.group(1))
        if "左右" in exp:
            return {"min": max(0, val - 1), "max": val + 1}
        return {"min": val, "max": None}

    # 无法解析的噪声（如包含冗长描述的无效字段）
    return {"min": 0, "max": None}


# ── 职位类别归一化 ─────────────────────────────────────

_category_cfg: dict | None = None


def _get_category_cfg() -> dict:
    global _category_cfg
    if _category_cfg is None:
        _category_cfg = _load_mapping("category_mapping.json")
    return _category_cfg


def clean_job_category(category: str | None) -> str:
    """将职位类别归一化为标准值。

    - "后端" → "后端开发"
    - "技术-服务端开发-服务端开发" → "后端开发"
    - None → "其他"
    """
    if not category or not category.strip():
        return "其他"

    cfg = _get_category_cfg()
    cat = category.strip()

    # 精确匹配有效值
    if cat in cfg["有效值"]:
        return cat

    # 查映射表
    if cat in cfg["映射"]:
        return cfg["映射"][cat]

    return cfg["默认值"]


# ── 职位名称清洗 ───────────────────────────────────────

_TITLE_PREFIX_RE = re.compile(r"^【[^】]*】\s*")


def clean_job_title(title: str | None) -> str:
    """清洗职位名称：去除标记前缀。

    - "【急招】高级Java开发" → "高级Java开发"
    - "【平台】全栈开发工程师（AI赋能开发方向）" → "全栈开发工程师（AI赋能开发方向）"
    """
    if not title or not title.strip():
        return "未知职位"

    title = title.strip()
    title = _TITLE_PREFIX_RE.sub("", title)
    return title


# ── Proficiency 归一化 ─────────────────────────────────

_PROFICIENCY_MAP = {
    "精通": "精通",
    "熟练": "熟练",
    "熟悉": "熟悉",
    "了解": "了解",
    "不限": "不限",
    # 非标准值映射
    "掌握": "熟悉",
    "扎实": "熟练",
    "深入": "精通",
    "深入了解": "熟悉",
    "深入理解": "精通",
    "深刻理解": "精通",
    "理解": "了解",
    "清晰": "熟悉",
    "良好": "熟悉",
    "优秀": "精通",
    "出色": "精通",
    "丰富": "熟练",
    "较强": "熟练",
    "较高": "熟练",
    "强": "熟练",
    "极强": "精通",
    "强烈": "熟悉",
    "突出": "精通",
    "善于": "熟练",
    "一定": "了解",
    # P0.1 扩充：LLM 常见变体
    "基础": "了解",
    "初级": "了解",
    "初步": "了解",
    "中级": "熟悉",
    "高级": "熟练",
    "专家": "精通",
    "有经验": "熟练",
    "有相关经验": "熟练",
    "有一定经验": "熟悉",
    "实战经验": "熟练",
    "精熟": "精通",
    "精湛": "精通",
    "深刻": "精通",
    "娴熟": "熟练",
    "使用过": "了解",
    "用过": "了解",
    "会": "了解",
    "能够": "熟悉",
    "能熟练": "熟练",
    "能熟练使用": "熟练",
    "熟练掌握": "熟练",
    "熟练使用": "熟练",
    "熟练运用": "熟练",
    "熟悉掌握": "熟悉",
    "精通掌握": "精通",
}


def clean_proficiency(proficiency: str | None) -> str:
    """将熟练度归一化为标准五级枚举值。

    非命中 _PROFICIENCY_MAP 的原始词会写入 debug 日志，并被 pipeline 的
    清洗报告统计。最终仍归一为 "不限"。
    """
    if not proficiency or not proficiency.strip():
        return "不限"

    p = proficiency.strip()
    if p in _PROFICIENCY_MAP:
        return _PROFICIENCY_MAP[p]

    # 未命中：记录以便后续报告与映射表扩充
    _unknown_proficiency_counter[p] = _unknown_proficiency_counter.get(p, 0) + 1
    logger.debug("未识别的 proficiency 值: %r，已归一为 '不限'", p)
    return "不限"


def pop_unknown_proficiencies() -> dict[str, int]:
    """取出并清空本轮清洗中累积的未识别 proficiency 计数（供 pipeline 使用）。"""
    global _unknown_proficiency_counter
    result = _unknown_proficiency_counter
    _unknown_proficiency_counter = {}
    return result
