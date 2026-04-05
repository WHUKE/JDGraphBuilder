"""CLI: 数据清洗命令"""

import argparse
import logging
import sys
from pathlib import Path

from src.config import CLEANED_DIR, INPUT_DIR


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="清洗 JDParser 输出数据")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=INPUT_DIR / "_all.json",
        help="输入 JSON 文件路径 (默认: data/input/_all.json)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=CLEANED_DIR,
        help="输出目录 (默认: data/cleaned/)",
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

    from src.cleaner.pipeline import run_pipeline

    results = run_pipeline(args.input, args.output)
    print(f"清洗完成: {len(results)} 条 JD → {args.output / '_all_cleaned.json'}")


if __name__ == "__main__":
    main()
