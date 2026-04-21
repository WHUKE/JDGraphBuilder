"""Proficiency 值审计脚本：扫描真实 _all.json，统计未命中 _PROFICIENCY_MAP 的原始词。

用法：
    python scripts/audit_proficiency.py [path/to/_all.json]

默认路径：data/input/_all.json
输出：stdout 打印统计表；同时把"频次 >= 2"的未命中词作为建议追加到 stdout，便于手工回填到 field_cleaner._PROFICIENCY_MAP。
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# 允许从项目根运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.field_cleaner import _PROFICIENCY_MAP  # noqa: E402
from src.config import INPUT_DIR  # noqa: E402


def audit(input_path: Path) -> None:
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    all_counter: Counter[str] = Counter()
    unknown_counter: Counter[str] = Counter()

    for jd in data:
        for skill_type in ("required_skills", "preferred_skills"):
            for s in jd.get(skill_type, []):
                p = s.get("proficiency")
                if not p or not p.strip():
                    continue
                p = p.strip()
                all_counter[p] += 1
                if p not in _PROFICIENCY_MAP:
                    unknown_counter[p] += 1

    print(f"扫描文件: {input_path}")
    print(f"共 {len(data)} 条 JD，合计 {sum(all_counter.values())} 个技能项带 proficiency")
    print(f"不同 proficiency 值总数: {len(all_counter)}")
    print(f"其中未命中映射表: {len(unknown_counter)} 种")
    print()

    if unknown_counter:
        print("=" * 60)
        print("未识别 proficiency 值（按频次降序）")
        print("=" * 60)
        for val, count in unknown_counter.most_common():
            print(f"  {val!r:30s}  × {count}")

        print()
        print("=" * 60)
        print("建议追加到 field_cleaner._PROFICIENCY_MAP（频次 >= 2）")
        print("=" * 60)
        for val, count in unknown_counter.most_common():
            if count >= 2:
                print(f'    "{val}": "TODO",   # 出现 {count} 次')
    else:
        print("所有 proficiency 值均已覆盖。")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = INPUT_DIR / "_all.json"

    if not path.exists():
        print(f"错误: 文件不存在 {path}", file=sys.stderr)
        sys.exit(1)

    audit(path)
