"""薪资数据清洗与标准化"""

import re
import logging

logger = logging.getLogger(__name__)

# 正则表达式定义
# 匹配 "15-30K" / "15k-30k" / "15-30K·15薪"
_SALARY_K_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~～至]\s*(\d+(?:\.\d+)?)\s*[kK]\s*(?:[·•]\s*\d+\s*薪)?")

# 匹配 "月薪 15000-30000 元"
_SALARY_YUAN_MONTH_RE = re.compile(r"(?:月薪|工资)\s*(\d{4,})\s*[-~～至]\s*(\d{4,})\s*元?")

# 匹配 "年薪 20-40 万"
_SALARY_WAN_YEAR_RE = re.compile(r"年薪\s*(\d+(?:\.\d+)?)\s*[-~～至]\s*(\d+(?:\.\d+)?)\s*万")

# 匹配 "15-30K/月" / "15-30K/月·15薪"
_SALARY_K_PER_MONTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~～至]\s*(\d+(?:\.\d+)?)\s*[kK]\s*/\s*月")

# 匹配 "15-30万/年"
_SALARY_WAN_PER_YEAR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-~～至]\s*(\d+(?:\.\d+)?)\s*万\s*/\s*年")


def clean_salary(
    salary_min: int | float | None = None,
    salary_max: int | float | None = None,
    salary_unit: str | None = None,
    raw_text: str | None = None,
) -> dict | None:
    """将薪资信息统一为标准格式。
    
    Args:
        salary_min: 薪资下限（数值）
        salary_max: 薪资上限（数值）
        salary_unit: 薪资单位（如 "K/月", "万/年", "元/月"）
        raw_text: 原始薪资文本（可选，用于兜底解析）
    
    Returns:
        标准化后的薪资字典 {"min": float, "max": float, "unit": str} 或 None
        
        unit 取值：
        - "月"：月薪（单位可能是 K/月 或 元/月，已统一转换为 K）
        - "年"：年薪（单位是 万/年）
        
    Examples:
        >>> clean_salary(15, 30, "K/月")
        {"min": 15.0, "max": 30.0, "unit": "月"}
        
        >>> clean_salary(20, 40, "万/年")
        {"min": 20.0, "max": 40.0, "unit": "年"}
        
        >>> clean_salary(raw_text="15-30K/月")
        {"min": 15.0, "max": 30.0, "unit": "月"}
    """
    # 策略1：如果已有结构化数据，直接转换
    if salary_min is not None and salary_max is not None and salary_unit:
        return _normalize_structured_salary(salary_min, salary_max, salary_unit)
    
    # 策略2：从原始文本解析
    if raw_text and raw_text.strip():
        parsed = _parse_raw_salary_text(raw_text)
        if parsed:
            return parsed
    
    # 无法解析
    logger.debug("无法解析薪资信息: min=%s, max=%s, unit=%s, raw=%s", 
                 salary_min, salary_max, salary_unit, raw_text)
    return None


def _normalize_structured_salary(
    salary_min: int | float,
    salary_max: int | float,
    salary_unit: str,
) -> dict:
    """将结构化的薪资数据转换为标准格式。
    
    支持的 unit 格式：
    - "K/月", "k/月", "K" → {"min": x, "max": y, "unit": "月"}
    - "万/年", "W/年" → {"min": x, "max": y, "unit": "年"}
    - "元/月" → 转换为 K/月
    """
    unit_lower = salary_unit.lower().strip()
    
    # 月薪 - K 为单位
    if "k" in unit_lower or ("月" in unit_lower and "万" not in unit_lower and "元" not in unit_lower):
        return {
            "min": float(salary_min),
            "max": float(salary_max),
            "unit": "月"
        }
    
    # 月薪 - 元 为单位，转换为 K
    if "元" in unit_lower and "月" in unit_lower:
        return {
            "min": round(float(salary_min) / 1000, 2),
            "max": round(float(salary_max) / 1000, 2),
            "unit": "月"
        }
    
    # 年薪 - 万 为单位
    if "万" in unit_lower or "w" in unit_lower:
        return {
            "min": float(salary_min),
            "max": float(salary_max),
            "unit": "年"
        }
    
    # 默认按原值返回，单位为"月"
    logger.warning("未知的薪资单位: %s，默认按月薪处理", salary_unit)
    return {
        "min": float(salary_min),
        "max": float(salary_max),
        "unit": "月"
    }


def _parse_raw_salary_text(raw_text: str) -> dict | None:
    """从原始文本中解析薪资信息。
    
    尝试多种正则模式，按优先级匹配。
    """
    text = raw_text.strip()
    
    # 优先级1：明确标注单位的格式
    # "15-30K/月"
    m = _SALARY_K_PER_MONTH_RE.search(text)
    if m:
        return {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
            "unit": "月"
        }
    
    # "15-30万/年"
    m = _SALARY_WAN_PER_YEAR_RE.search(text)
    if m:
        return {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
            "unit": "年"
        }
    
    # 优先级2：常见简写格式
    # "15-30K" (默认为月薪K)
    m = _SALARY_K_RE.search(text)
    if m:
        return {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
            "unit": "月"
        }
    
    # "月薪 15000-30000 元"
    m = _SALARY_YUAN_MONTH_RE.search(text)
    if m:
        return {
            "min": round(float(m.group(1)) / 1000, 2),
            "max": round(float(m.group(2)) / 1000, 2),
            "unit": "月"
        }
    
    # "年薪 20-40 万"
    m = _SALARY_WAN_YEAR_RE.search(text)
    if m:
        return {
            "min": float(m.group(1)),
            "max": float(m.group(2)),
            "unit": "年"
        }
    
    return None
