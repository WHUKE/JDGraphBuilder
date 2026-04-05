"""CLI: 一站式图谱构建命令（清洗 → 建模 → 入库）"""

import argparse
import json
import logging
import sys
from pathlib import Path

from src.config import CLEANED_DIR, INPUT_DIR


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="一站式构建知识图谱（清洗→建模→入库）")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=INPUT_DIR / "_all.json",
        help="输入 JSON 文件路径 (默认: data/input/_all.json)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空数据库后重新导入",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="跳过 Neo4j 导入（仅执行清洗和建模）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not args.input.exists():
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    # ── Step 1: 清洗 ──────────────────────────────────
    from src.cleaner.pipeline import run_pipeline

    print("=" * 50)
    print("Step 1: 数据清洗")
    print("=" * 50)
    cleaned = run_pipeline(args.input, CLEANED_DIR)
    print(f"  清洗完成: {len(cleaned)} 条 JD\n")

    # ── Step 2: 建模 ──────────────────────────────────
    from src.modeler.co_occurrence import compute_co_occurrence
    from src.modeler.node_builder import build_nodes
    from src.modeler.relation_builder import build_relations

    print("=" * 50)
    print("Step 2: 图谱建模")
    print("=" * 50)
    nodes = build_nodes(cleaned)
    relations = build_relations(cleaned)
    co_occurrences = compute_co_occurrence(cleaned)

    print(f"  节点: Job={len(nodes['jobs'])}, Skill={len(nodes['skills'])}, "
          f"Location={len(nodes['locations'])}, Education={len(nodes['educations'])}, "
          f"Category={len(nodes['categories'])}")
    print(f"  关系: REQUIRES_SKILL={len(relations['requires_skill'])}, "
          f"PREFERS_SKILL={len(relations['prefers_skill'])}, "
          f"PARENT_OF={len(relations['parent_of'])}, "
          f"CO_OCCURS_WITH={len(co_occurrences)}")
    print()

    # 保存建模结果为 JSON（便于调试）
    model_output = CLEANED_DIR / "_model_summary.json"
    summary = {
        "node_counts": {k: len(v) for k, v in nodes.items()},
        "relation_counts": {k: len(v) for k, v in relations.items()},
        "co_occurrence_count": len(co_occurrences),
    }
    with open(model_output, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if args.skip_import:
        print("已跳过 Neo4j 导入 (--skip-import)")
        return

    # ── Step 3: 入库 ──────────────────────────────────
    from src.loader.batch_importer import BatchImporter
    from src.loader.neo4j_client import Neo4jClient
    from src.loader.schema_initializer import init_schema, reset_database

    print("=" * 50)
    print("Step 3: Neo4j 入库")
    print("=" * 50)

    with Neo4jClient() as client:
        client.verify_connectivity()

        if args.reset:
            reset_database(client)

        init_schema(client)

        importer = BatchImporter(client)
        stats = importer.import_all(nodes, relations, co_occurrences)

    print("\n导入统计:")
    for key, count in stats.items():
        print(f"  {key:20s}: {count}")
    print("\n构建完成!")


if __name__ == "__main__":
    main()
