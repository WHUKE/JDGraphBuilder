"""CLI: 图谱统计命令"""

import argparse
import logging

from src.loader.neo4j_client import Neo4jClient


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="图谱统计信息")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--limit", type=int, default=20, help="各统计项的数量限制")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from src.query.stats_query import (
        get_category_distribution,
        get_education_distribution,
        get_graph_overview,
        get_location_distribution,
        get_skill_category_distribution,
        get_skill_distribution,
    )

    with Neo4jClient() as client:
        # 概览
        overview = get_graph_overview(client)
        print("=" * 60)
        print("图谱概览")
        print("=" * 60)
        print("\n节点:")
        for label, count in overview["nodes"].items():
            print(f"  {label:15s}: {count}")
        print("\n关系:")
        for rtype, count in overview["relations"].items():
            print(f"  {rtype:20s}: {count}")

        # 技能需求 Top N
        print(f"\n{'=' * 60}")
        print(f"技能需求 Top {args.limit}")
        print("=" * 60)
        for r in get_skill_distribution(client, args.limit):
            print(f"  {r['skill']:25s} ({r['category']:10s}) - {r['required_count']} 个职位")

        # 地域分布
        print(f"\n{'=' * 60}")
        print("地域分布")
        print("=" * 60)
        for r in get_location_distribution(client):
            print(f"  {r['location']:10s}: {r['job_count']} 个职位")

        # 学历分布
        print(f"\n{'=' * 60}")
        print("学历要求分布")
        print("=" * 60)
        for r in get_education_distribution(client):
            print(f"  {r['education']:6s}: {r['job_count']} 个职位")

        # 职位类别分布
        print(f"\n{'=' * 60}")
        print("职位类别分布")
        print("=" * 60)
        for r in get_category_distribution(client):
            print(f"  {r['category']:15s}: {r['job_count']} 个职位")

        # 技能类别分布
        print(f"\n{'=' * 60}")
        print("技能类别分布")
        print("=" * 60)
        for r in get_skill_category_distribution(client):
            print(f"  {r['category']:15s}: {r['skill_count']} 个技能, {r['job_count']} 个关联职位")


if __name__ == "__main__":
    main()
