"""Plain-language wording shared by the CLI, the HTML report, and the dashboard."""

from __future__ import annotations

from .models import SkillRecommendation, SkillScore

LEVEL_LABELS = (
    "Not started",
    "Aware",
    "Learning",
    "Can apply",
    "Proficient",
    "Expert",
)

LEVEL_GUIDE = (
    ("0", "Not started"),
    ("1", "Aware of it and what it is for"),
    ("2", "Learning through courses or small projects"),
    ("3", "Can apply it to real work with some help"),
    ("4", "Works with it independently"),
    ("5", "Teaches it or leads decisions about it"),
)


def level_label(level: float) -> str:
    """Name the 0-5 level, rounding to the nearest whole step."""
    index = max(0, min(len(LEVEL_LABELS) - 1, round(level)))
    return LEVEL_LABELS[index]


def coverage_band(coverage_pct: float) -> str:
    if coverage_pct >= 60:
        return "Your skills match most of what the market pays for."
    if coverage_pct >= 30:
        return "Your skills match part of what the market pays for."
    return "Most of the market value here is still ahead of you."


def headline_for(skill_scores: list[SkillScore], recommendations: list[SkillRecommendation]) -> str:
    """One sentence that names the strongest skill and the best next move."""
    if not skill_scores:
        return "No skill data was loaded yet."
    top = skill_scores[0].skill
    if not recommendations:
        return f"{top} carries the most market value, and your current skills already cover the top opportunities."
    return f"{top} carries the most market value. {recommendations[0].skill} is your biggest opening."


def coverage_sentence(coverage_pct: float, total_postings: int) -> str:
    return (
        f"Your current skills cover about {coverage_pct:.0f}% of the market value "
        f"in these {total_postings} postings. {coverage_band(coverage_pct)}"
    )


def opportunity_ratio(recommendation: SkillRecommendation, recommendations: list[SkillRecommendation]) -> float:
    """Compare a recommendation with the top pick, from 0 to 1."""
    if not recommendations:
        return 0.0
    top = recommendations[0].gap_contribution
    return 0.0 if top <= 0 else min(1.0, recommendation.gap_contribution / top)


METHOD_STEPS = (
    (
        "Demand",
        "How many postings list the skill, scaled so the most common skill scores 100.",
    ),
    (
        "Salary",
        "The average salary midpoint of postings that list the skill, scaled between the lowest and highest skill.",
    ),
    (
        "Growth",
        "The trend index and the 12-month change from the trend file.",
    ),
)
