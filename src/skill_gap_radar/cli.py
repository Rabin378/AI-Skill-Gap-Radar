"""Command-line interface: ``skill-gap-radar analyze`` and ``skill-gap-radar report``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analytics import build_skill_scores, calculate_skill_gap_score, coverage_score, recommend_skills, render_bar
from .data_loader import (
    DEFAULT_JOBS_PATH,
    DEFAULT_TRENDS_PATH,
    DEFAULT_USER_PATH,
    load_job_postings,
    load_trend_signals,
    load_user_skills,
)
from .insights import coverage_sentence, headline_for, level_label
from .animated_page import write_animated_page
from .report import write_html_report

DEFAULT_REPORT_PATH = Path("outputs") / "skill_gap_radar_report.html"
DEFAULT_PAGE_PATH = Path("outputs") / "skill_radar.html"


def _add_data_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--jobs", type=Path, default=DEFAULT_JOBS_PATH, help="Job postings CSV.")
    parser.add_argument("--trends", type=Path, default=DEFAULT_TRENDS_PATH, help="Trend signals CSV.")
    parser.add_argument("--user", type=Path, default=DEFAULT_USER_PATH, help="Your skill levels CSV.")


def _load_all(args: argparse.Namespace):
    jobs = load_job_postings(args.jobs)
    trends = load_trend_signals(args.trends)
    user_skills = load_user_skills(args.user)
    skill_scores = build_skill_scores(jobs, trends)
    gap_score = calculate_skill_gap_score(skill_scores, user_skills)
    recommendations = recommend_skills(skill_scores, user_skills, limit=args.top)
    return jobs, user_skills, skill_scores, gap_score, recommendations


def _print_analysis(args: argparse.Namespace) -> None:
    jobs, user_skills, skill_scores, gap_score, recommendations = _load_all(args)
    coverage = coverage_score(gap_score)

    print("\nSKILL RADAR")
    print("=" * 40)
    print(headline_for(skill_scores, recommendations))
    print(coverage_sentence(coverage, len(jobs)))

    print("\nTop skills by market value")
    print("-" * 40)
    for score in skill_scores[: args.top]:
        print(f"{score.skill:<18} {render_bar(score.projected_value_score)} {score.projected_value_score:5.1f}")

    print("\nPast 12 months")
    print("-" * 40)
    for score in skill_scores[: args.top]:
        arrow = "up" if score.change_12m_pct >= 0 else "down"
        print(f"{score.skill:<18} {arrow} {abs(score.change_12m_pct):.0f}%")

    print(f"\nSkill gap: {gap_score:.1f}% of market value is not yet covered")
    print("\nLearn next")
    print("-" * 40)
    if not recommendations:
        print("Your current skills already cover the strongest opportunities.")
    for index, recommendation in enumerate(recommendations, start=1):
        if recommendation.current_level > 0:
            level_text = f"you are at {recommendation.current_level:g}/5, {level_label(recommendation.current_level).lower()}"
        else:
            level_text = "not on your profile yet"
        print(f"{index}. {recommendation.skill} ({level_text}, opportunity {recommendation.gap_contribution:.1f})")
        print(f"   {recommendation.reason}")


def _write_report(args: argparse.Namespace) -> None:
    jobs, user_skills, skill_scores, gap_score, recommendations = _load_all(args)
    output_path = write_html_report(
        args.output,
        jobs,
        skill_scores,
        gap_score,
        recommendations,
        limit=args.top,
        user_skills=user_skills,
    )
    print(f"Wrote report: {output_path}")


def _write_page(args: argparse.Namespace) -> None:
    jobs = load_job_postings(args.jobs)
    trends = load_trend_signals(args.trends)
    user_skills = load_user_skills(args.user)
    skill_scores = build_skill_scores(jobs, trends)
    output_path = write_animated_page(args.output, jobs, skill_scores, user_skills, trends)
    print(f"Wrote animated page: {output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-gap-radar",
        description="Find the skills the job market rewards and see how your profile compares.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze = subparsers.add_parser("analyze", help="Print the skill analysis to the terminal.")
    _add_data_arguments(analyze)
    analyze.add_argument("--top", type=int, default=8, help="How many skills to list (default: 8).")
    analyze.set_defaults(func=_print_analysis)

    report = subparsers.add_parser("report", help="Write a standalone HTML report.")
    _add_data_arguments(report)
    report.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Where to write the report (default: outputs/skill_gap_radar_report.html).",
    )
    report.add_argument("--top", type=int, default=10, help="How many skills to include (default: 10).")
    report.set_defaults(func=_write_report)

    page = subparsers.add_parser("page", help="Write an animated, interactive HTML page.")
    _add_data_arguments(page)
    page.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PAGE_PATH,
        help="Where to write the page (default: outputs/skill_radar.html).",
    )
    page.set_defaults(func=_write_page)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        args = parser.parse_args(["analyze", *(argv or [])])

    try:
        args.func(args)
    except (FileNotFoundError, ValueError) as problem:
        print(f"Error: {problem}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Output was piped into a command such as `head` that stopped reading early.
        sys.stderr.close()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
