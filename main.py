"""JDGraphBuilder 顶层入口 —— 兼容性提示。

历史版本曾在此启动 HTTP 服务；现已迁移至 JDGraphMono 仓库（FastAPI）。
本文件仅打印迁移提示，避免老脚本/快捷方式静默失败。
"""

from __future__ import annotations

import sys
import textwrap


_MIGRATION_NOTE = textwrap.dedent(
    """
    ────────────────────────────────────────────────────────────────
    JDGraphBuilder 不再托管 HTTP 服务（自 0.2 起）。
    可视化后端 / AI 问答接口已迁移至同级仓库 JDGraphMono：

        cd ../JDGraphMono
        uv sync
        # 配置 .env（NEO4J_* 与 LLM_API_KEY）
        uv run python -m backend.main --host 0.0.0.0 --port 8000

    JDGraphBuilder 现专注于以下 CLI：
        uv run python -m src.cli.build   --input data/input/_all.json [--reset]
        uv run python -m src.cli.clean   --input data/input/_all.json
        uv run python -m src.cli.query   --skill Python
        uv run python -m src.cli.stats
    ────────────────────────────────────────────────────────────────
    """
).strip()


def main() -> None:
    print(_MIGRATION_NOTE)
    sys.exit(0)


if __name__ == "__main__":
    main()
