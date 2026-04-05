"""清洗流水线：编排完整的数据清洗流程"""

import json
import logging
from pathlib import Path

from src.cleaner.field_cleaner import (
    clean_education,
    clean_experience,
    clean_job_category,
    clean_job_title,
    clean_location,
)
from src.cleaner.skill_cleaner import clean_skills
from src.cleaner.validator import validate_jd

logger = logging.getLogger(__name__)


def clean_single_jd(jd: dict) -> dict:
    """清洗单条 JD 数据。"""
    result = dict(jd)

    # 字段清洗
    result["job_title"] = clean_job_title(result.get("job_title"))
    result["locations"] = clean_location(result.get("location"))
    result["education"] = clean_education(result.get("education"))
    result["experience"] = clean_experience(result.get("experience"))
    result["job_category"] = clean_job_category(result.get("job_category"))

    # 技能清洗
    req, pref = clean_skills(
        result.get("required_skills", []),
        result.get("preferred_skills", []),
    )
    result["required_skills"] = req
    result["preferred_skills"] = pref

    # 保留原始 responsibilities
    result.setdefault("responsibilities", [])

    # 删除已拆分的原始 location 字段，改用 locations 列表
    result.pop("location", None)

    return result


def run_pipeline(input_path: Path, output_dir: Path) -> list[dict]:
    """执行完整清洗流水线。

    Args:
        input_path: 输入 JSON 文件路径（_all.json）
        output_dir: 输出目录

    Returns:
        清洗后的 JD 列表
    """
    logger.info("加载输入数据: %s", input_path)
    with open(input_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict):
        raw_data = [raw_data]

    logger.info("共 %d 条 JD 待清洗", len(raw_data))

    # 校验 + 清洗
    all_warnings: list[str] = []
    cleaned: list[dict] = []

    for i, jd in enumerate(raw_data):
        # 先校验原始数据
        warnings = validate_jd(jd, index=i)
        all_warnings.extend(warnings)

        # 执行清洗
        result = clean_single_jd(jd)
        cleaned.append(result)

    # 输出清洗后数据
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "_all_cleaned.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    logger.info("清洗完成: %d 条数据 → %s", len(cleaned), output_path)
    if all_warnings:
        logger.info("共 %d 条警告", len(all_warnings))

    return cleaned
