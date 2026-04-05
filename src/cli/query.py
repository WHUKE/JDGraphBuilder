"""CLI: 交互式查询命令"""

import argparse
import json
import logging
import sys

from src.loader.neo4j_client import Neo4jClient


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="知识图谱查询")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--skill", "-s",
        nargs="+",
        help="按技能匹配职位",
    )
    group.add_argument(
        "--location", "-l",
        type=str,
        help="按地点筛选职位",
    )
    group.add_argument(
        "--education", "-e",
        type=str,
        help="按学历筛选职位",
    )
    group.add_argument(
        "--detail", "-d",
        type=str,
        metavar="SOURCE_FILE",
        help="查看职位详情",
    )
    group.add_argument(
        "--related",
        type=str,
        metavar="SKILL",
        help="查询技能的共现关联技能",
    )
    group.add_argument(
        "--tree",
        type=str,
        metavar="SKILL",
        help="查询技能层级关系",
    )
    group.add_argument(
        "--gap",
        nargs="+",
        metavar="SKILL",
        help="技能差距分析: --gap <技能1> <技能2> ... --target <职位名>",
    )
    group.add_argument(
        "--path",
        nargs=2,
        metavar="JOB",
        help="职位跳转路径分析: --path <起始职位> <目标职位>",
    )
    group.add_argument(
        "--trending",
        action="store_true",
        help="热门技能排行",
    )

    parser.add_argument("--target", type=str, help="目标职位名（配合 --gap 使用）")
    parser.add_argument("--limit", type=int, default=20, help="结果数量限制")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    with Neo4jClient() as client:
        if args.skill:
            from src.query.job_query import find_jobs_by_skills
            results = find_jobs_by_skills(client, args.skill, args.limit)
            _print_jobs(results, f"按技能匹配: {', '.join(args.skill)}")

        elif args.location:
            from src.query.job_query import find_jobs_by_location
            results = find_jobs_by_location(client, args.location, args.limit)
            _print_jobs(results, f"地点: {args.location}")

        elif args.education:
            from src.query.job_query import find_jobs_by_education
            results = find_jobs_by_education(client, args.education, args.limit)
            _print_jobs(results, f"学历: {args.education}")

        elif args.detail:
            from src.query.job_query import get_job_detail
            result = get_job_detail(client, args.detail)
            if result:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"未找到职位: {args.detail}")

        elif args.related:
            from src.query.skill_query import get_related_skills
            results = get_related_skills(client, args.related, args.limit)
            print(f"\n与 '{args.related}' 共现频率最高的技能:")
            print("-" * 50)
            for r in results:
                print(f"  {r['name']:20s} (共现 {r['job_count']} 次, 权重 {r['weight']:.2f})")

        elif args.tree:
            from src.query.skill_query import get_skill_tree
            tree = get_skill_tree(client, args.tree)
            print(f"\n技能层级: {args.tree}")
            print("-" * 50)
            if tree["parents"]:
                print("  父技能:")
                for p in tree["parents"]:
                    print(f"    ← {p['name']} ({p['category']})")
            if tree["children"]:
                print("  子技能:")
                for c in tree["children"]:
                    print(f"    → {c['name']} ({c['category']})")
            if not tree["parents"] and not tree["children"]:
                print("  (无层级关系)")

        elif args.gap:
            if not args.target:
                print("错误: --gap 需要配合 --target 指定目标职位", file=sys.stderr)
                sys.exit(1)
            from src.query.path_query import get_skill_gap
            result = get_skill_gap(client, args.gap, args.target)
            print(f"\n技能差距分析: → {result.get('target_job', args.target)}")
            print("-" * 50)
            if "error" in result:
                print(f"  {result['error']}")
            else:
                print(f"  匹配率: {result['match_rate']:.0%}")
                if result["matched_skills"]:
                    print(f"  已掌握 ({len(result['matched_skills'])}):")
                    for s in result["matched_skills"]:
                        print(f"    ✓ {s['name']}")
                if result["missing_skills"]:
                    print(f"  需学习 ({len(result['missing_skills'])}):")
                    for s in result["missing_skills"]:
                        print(f"    ✗ {s['name']} ({s.get('proficiency', '不限')})")

        elif args.path:
            from src.query.path_query import get_job_transition
            result = get_job_transition(client, args.path[0], args.path[1])
            print(f"\n职位跳转: {result.get('from_job', args.path[0])} → {result.get('to_job', args.path[1])}")
            print("-" * 50)
            if "error" in result:
                print(f"  {result['error']}")
            else:
                print(f"  技能重叠率: {result['overlap_rate']:.0%}")
                print(f"  共有技能 ({len(result['overlapping_skills'])}): {', '.join(result['overlapping_skills'][:10])}")
                print(f"  需学习 ({len(result['skills_to_learn'])}): {', '.join(result['skills_to_learn'][:10])}")

        elif args.trending:
            from src.query.skill_query import get_top_skills
            results = get_top_skills(client, args.limit)
            print(f"\n热门技能 Top {args.limit}:")
            print("-" * 50)
            for i, r in enumerate(results, 1):
                print(f"  {i:2d}. {r['name']:20s} ({r['category']:10s}) - {r['job_count']} 个职位")


def _print_jobs(results: list[dict], title: str) -> None:
    print(f"\n{title} ({len(results)} 条结果):")
    print("-" * 70)
    for r in results:
        locs = ", ".join(r.get("locations", [])) if r.get("locations") else ""
        edu = r.get("education", "")
        cat = r.get("category", "")
        matched = r.get("matched", "")
        matched_str = f" [匹配 {matched} 项]" if matched else ""
        print(f"  {r['title']:30s} | {cat:10s} | {locs:15s} | {edu}{matched_str}")


if __name__ == "__main__":
    main()
