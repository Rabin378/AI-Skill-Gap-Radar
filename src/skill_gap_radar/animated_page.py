"""Build a single animated HTML page: the radar, sliders, and learn-next list.

The page embeds the computed scores as JSON and recalculates coverage and
recommendations in the browser with the same rules as ``analytics.py``, so
the numbers on the page match the CLI and report.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .analytics import skill_reason
from .models import JobPosting, SkillScore, TrendSignal

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "animated_page.html"
DATA_PLACEHOLDER = "__SKILL_RADAR_DATA__"
PROFILE_SIZE = 12
TABLE_LIMIT = 10
MAX_LEVEL = 5.0


def _clamp_level(value: float) -> float:
    return max(0.0, min(MAX_LEVEL, value))


def build_page_data(
    jobs: list[JobPosting],
    skill_scores: list[SkillScore],
    user_skills: Mapping[str, float],
    trends: Mapping[str, TrendSignal] | None = None,
) -> dict:
    """Collect the values the page needs. Plain numbers and strings only."""
    skills = [
        {
            "skill": score.skill,
            "projected": score.projected_value_score,
            "postings": score.posting_count,
            "avgSalary": score.avg_salary,
            "change": score.change_12m_pct,
            "reason": skill_reason(score),
            "level": _clamp_level(user_skills.get(score.skill, 0.0)),
        }
        for score in skill_scores
    ]

    # The same profile rule as the dashboard: the top sliders, plus any other
    # market skill the user already has a level for.
    top_names = [score.skill for score in skill_scores[:PROFILE_SIZE]]
    extra_names = [
        score.skill
        for score in skill_scores[PROFILE_SIZE:]
        if user_skills.get(score.skill, 0.0) > 0
    ]

    synthetic = any("synthetic" in signal.source_note.lower() for signal in (trends or {}).values())

    return {
        "postings": len(jobs),
        "syntheticTrends": synthetic,
        "profile": top_names + extra_names,
        "tableLimit": TABLE_LIMIT,
        "skills": skills,
    }


def _to_script_json(data: dict) -> str:
    """Serialize for a <script> block. Escaping < > & stops a skill name from closing the tag."""
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def render_animated_page(
    jobs: list[JobPosting],
    skill_scores: list[SkillScore],
    user_skills: Mapping[str, float],
    trends: Mapping[str, TrendSignal] | None = None,
) -> str:
    data = build_page_data(jobs, skill_scores, user_skills, trends)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace(DATA_PLACEHOLDER, _to_script_json(data))


def write_animated_page(
    output_path: str | Path,
    jobs: list[JobPosting],
    skill_scores: list[SkillScore],
    user_skills: Mapping[str, float],
    trends: Mapping[str, TrendSignal] | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_animated_page(jobs, skill_scores, user_skills, trends), encoding="utf-8")
    return path.resolve()
