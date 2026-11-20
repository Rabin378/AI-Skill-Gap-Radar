"""Scoring logic for Skill Radar.

Scoring in one pass:

1. Demand  - share of postings that list the skill (scaled to the most common skill).
2. Salary  - average salary midpoint, scaled between the lowest and highest skill.
3. Growth  - trend index plus the 12-month change from the trend signal file.

``value_score`` is the weighted blend of the three. ``projected_value_score``
adjusts it by the 12-month change. The personal gap is the share of that
market value your current levels do not yet cover.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .models import JobPosting, SkillRecommendation, SkillScore, TrendSignal

MAX_LEVEL = 5.0
DEFAULT_TREND_INDEX = 50.0
DEFAULT_WEIGHTS = (0.45, 0.35, 0.20)  # demand, salary, growth


def _scale(value: float, minimum: float, maximum: float) -> float:
    if maximum == minimum:
        return 100.0
    return max(0.0, min(100.0, ((value - minimum) / (maximum - minimum)) * 100))


def _growth_score(trend_index: float, change_12m_pct: float) -> float:
    trend_component = max(0.0, min(100.0, trend_index))
    change_component = _scale(change_12m_pct, -10.0, 40.0)
    return (trend_component * 0.55) + (change_component * 0.45)


def _level(user_skills: dict[str, float], skill: str) -> float:
    return max(0.0, min(MAX_LEVEL, user_skills.get(skill, 0.0)))


def validate_weights(demand_weight: float, salary_weight: float, growth_weight: float) -> None:
    weights = (demand_weight, salary_weight, growth_weight)
    if any(weight < 0 for weight in weights):
        raise ValueError("Scoring weights cannot be negative.")
    total = sum(weights)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Scoring weights must add up to 1.0 (got {total:.3f}).")


def build_skill_scores(
    jobs: list[JobPosting],
    trends: dict[str, TrendSignal],
    demand_weight: float = DEFAULT_WEIGHTS[0],
    salary_weight: float = DEFAULT_WEIGHTS[1],
    growth_weight: float = DEFAULT_WEIGHTS[2],
) -> list[SkillScore]:
    """Score every skill that appears in at least one posting, best first."""
    validate_weights(demand_weight, salary_weight, growth_weight)
    if not jobs:
        return []

    skill_to_salaries: dict[str, list[float]] = defaultdict(list)
    for job in jobs:
        for skill in set(job.skills):
            skill_to_salaries[skill].append(job.salary_midpoint)

    # Jobs can exist without any listed skill. With no skills there is nothing to score.
    if not skill_to_salaries:
        return []

    counts = {skill: len(salaries) for skill, salaries in skill_to_salaries.items()}
    avg_salaries = {skill: mean(salaries) for skill, salaries in skill_to_salaries.items()}
    max_count = max(counts.values())
    min_salary = min(avg_salaries.values())
    max_salary = max(avg_salaries.values())
    total_postings = len(jobs)

    scores: list[SkillScore] = []
    for skill, posting_count in counts.items():
        avg_salary = avg_salaries[skill]
        trend = trends.get(skill)
        trend_index = trend.trend_index if trend else DEFAULT_TREND_INDEX
        change_12m_pct = trend.change_12m_pct if trend else 0.0
        demand_score = (posting_count / max_count) * 100
        salary_score = _scale(avg_salary, min_salary, max_salary)
        growth_score = _growth_score(trend_index, change_12m_pct)
        value_score = (
            (demand_score * demand_weight)
            + (salary_score * salary_weight)
            + (growth_score * growth_weight)
        )
        projected_value_score = max(0.0, min(100.0, value_score * (1 + (change_12m_pct / 100))))
        scores.append(
            SkillScore(
                skill=skill,
                posting_count=posting_count,
                avg_salary=avg_salary,
                trend_index=trend_index,
                change_12m_pct=change_12m_pct,
                demand_score=demand_score,
                salary_score=salary_score,
                growth_score=growth_score,
                value_score=value_score,
                projected_value_score=projected_value_score,
                total_postings=total_postings,
            )
        )

    return sorted(scores, key=lambda score: score.projected_value_score, reverse=True)


def calculate_skill_gap_score(skill_scores: list[SkillScore], user_skills: dict[str, float]) -> float:
    """Percent of market value not yet covered by the user's skills (0 = fully covered)."""
    total_market_value = sum(score.projected_value_score for score in skill_scores)
    if total_market_value == 0:
        return 0.0

    missing_value = 0.0
    for score in skill_scores:
        missing_ratio = 1 - (_level(user_skills, score.skill) / MAX_LEVEL)
        missing_value += score.projected_value_score * missing_ratio

    return round((missing_value / total_market_value) * 100, 1)


def coverage_score(gap_score: float) -> float:
    """The inverse of the gap: percent of market value the user already covers."""
    return round(100.0 - gap_score, 1)


def skill_reason(score: SkillScore) -> str:
    """One plain-language sentence set describing why a skill matters."""
    return (
        f"Listed in {score.posting_count} of {score.total_postings} postings. "
        f"Average salary midpoint is ${score.avg_salary:,.0f}. "
        f"Trend is {score.change_12m_pct:+.0f}% over the past 12 months."
    )


def recommend_skills(
    skill_scores: list[SkillScore],
    user_skills: dict[str, float],
    limit: int = 5,
) -> list[SkillRecommendation]:
    """Rank skills the user is missing by how much market value they would unlock."""
    recommendations: list[SkillRecommendation] = []
    for score in skill_scores:
        current_level = _level(user_skills, score.skill)
        gap_contribution = score.projected_value_score * (1 - current_level / MAX_LEVEL)
        if gap_contribution <= 0:
            continue

        recommendations.append(
            SkillRecommendation(
                skill=score.skill,
                current_level=current_level,
                target_score=score.projected_value_score,
                gap_contribution=gap_contribution,
                reason=skill_reason(score),
            )
        )

    return sorted(recommendations, key=lambda rec: rec.gap_contribution, reverse=True)[:limit]


def render_bar(value: float, width: int = 18) -> str:
    filled = round((value / 100) * width)
    return "█" * filled + "░" * (width - filled)
