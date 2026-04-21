"""性能基准脚本：测量不同数据规模下的 build / 查询耗时。

用法：
    python scripts/benchmark.py --sizes 120,600,1200
    python scripts/benchmark.py --sizes 120 --skip-neo4j

说明：
- 伪数据通过复制真实 _all.json 并改写 source_file 生成。
- 不真实入库时仅度量清洗 + 建模耗时（--skip-neo4j）。
- 入库度量需 .env 正确配置且 Neo4j 可访问。
- 结果输出到 docs/benchmark.md（追加模式）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cleaner.pipeline import run_pipeline  # noqa: E402
from src.config import CLEANED_DIR, INPUT_DIR, PROJECT_ROOT  # noqa: E402
from src.modeler.co_occurrence import compute_co_occurrence  # noqa: E402
from src.modeler.node_builder import build_nodes  # noqa: E402
from src.modeler.relation_builder import build_relations  # noqa: E402


def generate_pseudo_dataset(base: list[dict], target_size: int, out_path: Path) -> int:
    """复制 base 数据至 target_size 条（改 source_file 避免冲突）。"""
    result: list[dict] = []
    i = 0
    while len(result) < target_size:
        src = base[i % len(base)]
        dup = json.loads(json.dumps(src, ensure_ascii=False))
        dup["source_file"] = f"bench_{len(result):05d}.txt"
        result.append(dup)
        i += 1
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return len(result)


def bench_build(input_file: Path, cleaned_dir: Path) -> dict:
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    cleaned = run_pipeline(input_file, cleaned_dir)
    t_clean = time.perf_counter() - t0

    t0 = time.perf_counter()
    nodes = build_nodes(cleaned)
    relations = build_relations(cleaned)
    co = compute_co_occurrence(cleaned, min_count=None)
    t_model = time.perf_counter() - t0

    return {
        "n_jds": len(cleaned),
        "clean_sec": round(t_clean, 3),
        "model_sec": round(t_model, 3),
        "n_jobs": len(nodes["jobs"]),
        "n_skills": len(nodes["skills"]),
        "n_req_skill": len(relations["requires_skill"]),
        "n_co_occurrence": len(co),
    }


def bench_queries(repeat: int = 5) -> dict:
    """连接 Neo4j 跑 5 个代表性查询，返回每个查询的中位毫秒数。"""
    from src.loader.neo4j_client import Neo4jClient  # 延迟导入
    from src.query.job_query import find_jobs_by_skills
    from src.query.skill_query import get_top_skills
    from src.query.stats_query import get_graph_overview, get_skill_distribution
    from src.utils.cache import invalidate_cache

    results: dict[str, float] = {}

    with Neo4jClient() as client:
        client.verify_connectivity()

        def _time(name: str, func, *args, **kwargs):
            invalidate_cache()  # 确保每次 cold
            times_ms: list[float] = []
            for _ in range(repeat):
                t0 = time.perf_counter()
                func(*args, **kwargs)
                times_ms.append((time.perf_counter() - t0) * 1000)
                invalidate_cache()
            results[name] = round(median(times_ms), 2)

        _time("get_graph_overview", get_graph_overview, client)
        _time("get_top_skills(30)", get_top_skills, client, 30)
        _time("get_skill_distribution(50)", get_skill_distribution, client, 50)
        _time("find_jobs_by_skills(['Python','MySQL'])", find_jobs_by_skills, client, ["Python", "MySQL"], 20)
        _time("find_jobs_by_skills(['Java','Spring','MySQL'])", find_jobs_by_skills, client, ["Java", "Spring", "MySQL"], 20)

    return results


def append_markdown(report: list[dict], query_results: dict | None, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"\n## Benchmark @ {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("### 构建耗时\n")
    lines.append("| n_jds | clean(s) | model(s) | jobs | skills | REQUIRES_SKILL | CO_OCCURS_WITH |")
    lines.append("|------:|---------:|---------:|-----:|-------:|---------------:|---------------:|")
    for r in report:
        lines.append(
            f"| {r['n_jds']} | {r['clean_sec']:.3f} | {r['model_sec']:.3f} | "
            f"{r['n_jobs']} | {r['n_skills']} | {r['n_req_skill']} | {r['n_co_occurrence']} |"
        )

    if query_results:
        lines.append("\n### 查询延迟（中位数 ms，cold / 每次前清缓存）\n")
        lines.append("| 查询 | 中位 ms |")
        lines.append("|------|--------:|")
        for name, ms in query_results.items():
            lines.append(f"| `{name}` | {ms} |")

    lines.append("\n")
    with open(out, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="120,600,1200",
                        help="逗号分隔的 JD 数据规模，默认 120,600,1200")
    parser.add_argument("--base", type=Path, default=INPUT_DIR / "_all.json",
                        help="用于复制扩展的基础 JSON（默认 data/input/_all.json）")
    parser.add_argument("--skip-neo4j", action="store_true",
                        help="跳过查询基准（不连接 Neo4j）")
    parser.add_argument("--repeat", type=int, default=5,
                        help="查询基准每个查询重复次数（默认 5）")
    args = parser.parse_args()

    if not args.base.exists():
        print(f"错误: 基础数据不存在: {args.base}", file=sys.stderr)
        sys.exit(1)

    with open(args.base, encoding="utf-8") as f:
        base = json.load(f)
    if isinstance(base, dict):
        base = [base]

    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    build_reports: list[dict] = []

    tmp_root = PROJECT_ROOT / "data" / "_bench"
    tmp_root.mkdir(parents=True, exist_ok=True)

    for n in sizes:
        print(f"\n[Benchmark] size={n}")
        fake_input = tmp_root / f"bench_{n}.json"
        fake_cleaned = tmp_root / f"cleaned_{n}"
        actual = generate_pseudo_dataset(base, n, fake_input)
        report = bench_build(fake_input, fake_cleaned)
        build_reports.append(report)
        print(f"  n={actual} clean={report['clean_sec']}s model={report['model_sec']}s "
              f"skills={report['n_skills']} co={report['n_co_occurrence']}")

    query_results: dict | None = None
    if not args.skip_neo4j:
        try:
            print("\n[Benchmark] 查询基准（需要已入库数据）")
            query_results = bench_queries(repeat=args.repeat)
            for k, v in query_results.items():
                print(f"  {k}: {v} ms")
        except Exception as e:
            print(f"[Benchmark] 查询阶段失败，跳过: {e}", file=sys.stderr)

    out = PROJECT_ROOT / "docs" / "benchmark.md"
    append_markdown(build_reports, query_results, out)
    print(f"\n结果已追加至: {out}")


if __name__ == "__main__":
    main()
