"""清洗流水线：编排完整的数据清洗流程"""

import json
import logging
from collections import Counter
from pathlib import Path

from src.cleaner.field_cleaner import (
    clean_education,
    clean_experience,
    clean_job_category,
    clean_job_title,
    clean_location,
    pop_unknown_proficiencies,
)
from src.cleaner.salary_cleaner import clean_salary
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

    # 薪资清洗（CL-4）
    result["salary"] = clean_salary(
        salary_min=result.get("salary_min"),
        salary_max=result.get("salary_max"),
        salary_unit=result.get("salary_unit"),
    )

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


def _classify_warning(msg: str) -> str:
    """将 warning 消息粗分类（用于报告的分布统计）。"""
    if "必填字段" in msg:
        return "missing_required_field"
    if "建议字段" in msg:
        return "missing_optional_field"
    if "学历值" in msg or "非标准学历" in msg:
        return "invalid_education"
    if "熟练度" in msg or "proficiency" in msg.lower():
        return "invalid_proficiency"
    return "other"


def run_pipeline(input_path: Path, output_dir: Path) -> list[dict]:
    """执行完整清洗流水线。

    Args:
        input_path: 输入 JSON 文件路径（_all.json）
        output_dir: 输出目录

    Returns:
        清洗后的 JD 列表
    """
    # 清空上一轮残留的未识别 proficiency 计数（防止多次运行污染）
    pop_unknown_proficiencies()

    logger.info("加载输入数据: %s", input_path)
    with open(input_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict):
        raw_data = [raw_data]

    logger.info("共 %d 条 JD 待清洗", len(raw_data))

    # 校验 + 清洗
    all_warnings: list[str] = []
    warnings_by_source: dict[str, list[str]] = {}
    cleaned: list[dict] = []

    for i, jd in enumerate(raw_data):
        # 先校验原始数据
        warnings = validate_jd(jd, index=i)
        all_warnings.extend(warnings)

        source = jd.get("source_file", f"<index={i}>")
        if warnings:
            warnings_by_source.setdefault(source, []).extend(warnings)

        # 执行清洗
        result = clean_single_jd(jd)
        cleaned.append(result)

    # 输出清洗后数据
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "_all_cleaned.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    logger.info("清洗完成: %d 条数据 → %s", len(cleaned), output_path)

    # ── 生成清洗报告（P0.2） ───────────────────────────
    unknown_prof = pop_unknown_proficiencies()
    type_counter = Counter(_classify_warning(w) for w in all_warnings)

    report = {
        "total_jds": len(raw_data),
        "jds_with_warnings": len(warnings_by_source),
        "total_warnings": len(all_warnings),
        "warnings_by_type": dict(type_counter),
        "unknown_proficiency_terms": dict(
            sorted(unknown_prof.items(), key=lambda x: -x[1])
        ),
        "warnings_by_source": warnings_by_source,
    }
    report_path = output_dir / "_cleaning_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("清洗报告已生成: %s", report_path)
    if all_warnings:
        top_types = type_counter.most_common(5)
        logger.info(
            "共 %d 条警告（Top 类型: %s）",
            len(all_warnings),
            ", ".join(f"{k}={v}" for k, v in top_types),
        )
    if unknown_prof:
        logger.info(
            "发现 %d 种未识别 proficiency 值（Top 5: %s）",
            len(unknown_prof),
            ", ".join(
                f"{k}×{v}"
                for k, v in sorted(unknown_prof.items(), key=lambda x: -x[1])[:5]
            ),
        )

    return cleaned
