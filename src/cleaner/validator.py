"""数据校验：必填项检查、格式验证、校验报告"""

import logging

from src.config import VALID_EDUCATION, VALID_PROFICIENCY

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["source_file"]
WARN_IF_MISSING = ["job_title", "location", "education", "job_category"]


def validate_jd(jd: dict, index: int = 0) -> list[str]:
    """校验单条 JD 数据，返回警告消息列表。

    不会中断清洗流程，仅记录问题。
    """
    warnings: list[str] = []
    source = jd.get("source_file", f"<index={index}>")

    # 必填字段
    for field in REQUIRED_FIELDS:
        if not jd.get(field):
            msg = f"[{source}] 缺少必填字段: {field}"
            logger.error(msg)
            warnings.append(msg)

    # 建议字段
    for field in WARN_IF_MISSING:
        if not jd.get(field):
            msg = f"[{source}] 缺少建议字段: {field}"
            logger.warning(msg)
            warnings.append(msg)

    # 学历值域
    edu = jd.get("education")
    if edu and edu not in VALID_EDUCATION:
        msg = f"[{source}] 非标准学历值: '{edu}'"
        logger.warning(msg)
        warnings.append(msg)

    # 技能 proficiency 值域
    for skill_type in ("required_skills", "preferred_skills"):
        for skill in jd.get(skill_type, []):
            prof = skill.get("proficiency")
            if prof and prof not in VALID_PROFICIENCY:
                msg = f"[{source}] 技能 '{skill.get('name')}' 的非标准熟练度: '{prof}'"
                logger.debug(msg)
                warnings.append(msg)

    return warnings
