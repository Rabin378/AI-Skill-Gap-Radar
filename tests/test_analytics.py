from datetime import date

import pytest

from skill_gap_radar.analytics import (
    build_skill_scores,
    calculate_skill_gap_score,
    coverage_score,
    recommend_skills,
    validate_weights,
)
from skill_gap_radar.models import JobPosting, TrendSignal


def _job(job_id, salary_min, salary_max, skills):
    return JobPosting(job_id, "Role", "Co", "Remote", date(2026, 1, int(job_id)), salary_min, salary_max, skills)


def test_skill_scores_rank_high_growth_high_salary_skill():
    jobs = [
        JobPosting("1", "AI Engineer", "A", "Remote", date(2026, 1, 1), 150000, 210000, ("Python", "GenAI")),
        JobPosting("2", "Analyst", "B", "Remote", date(2026, 1, 2), 70000, 90000, ("Excel", "SQL")),
        JobPosting("3", "AI Analyst", "C", "Remote", date(2026, 1, 3), 120000, 170000, ("GenAI", "SQL")),
    ]
    trends = {
        "GenAI": TrendSignal("GenAI", 95, 35, "test"),
        "Excel": TrendSignal("Excel", 45, -4, "test"),
        "SQL": TrendSignal("SQL", 80, 10, "test"),
        "Python": TrendSignal("Python", 88, 14, "test"),
    }

    scores = build_skill_scores(jobs, trends)

    assert scores[0].skill == "GenAI"
    assert scores[0].projected_value_score > scores[-1].projected_value_score


def test_gap_score_drops_when_user_has_more_skills():
    jobs = [
        JobPosting("1", "Data Scientist", "A", "Remote", date(2026, 1, 1), 100000, 140000, ("Python", "SQL")),
        JobPosting("2", "ML Engineer", "B", "Remote", date(2026, 1, 2), 150000, 190000, ("Python", "MLOps")),
    ]
    trends = {"Python": TrendSignal("Python", 88, 14, "test")}
    scores = build_skill_scores(jobs, trends)

    beginner_gap = calculate_skill_gap_score(scores, {"Python": 0, "SQL": 0, "MLOps": 0})
    advanced_gap = calculate_skill_gap_score(scores, {"Python": 5, "SQL": 5, "MLOps": 5})

    assert beginner_gap > advanced_gap
    assert advanced_gap == 0


def test_recommendations_prioritize_missing_high_value_skills():
    jobs = [
        JobPosting("1", "AI Engineer", "A", "Remote", date(2026, 1, 1), 150000, 210000, ("GenAI", "Python")),
        JobPosting("2", "AI Engineer", "B", "Remote", date(2026, 1, 2), 150000, 210000, ("GenAI", "SQL")),
    ]
    trends = {"GenAI": TrendSignal("GenAI", 95, 35, "test")}
    scores = build_skill_scores(jobs, trends)

    recommendations = recommend_skills(scores, {"Python": 5, "SQL": 5, "GenAI": 0}, limit=1)

    assert recommendations[0].skill == "GenAI"


def test_jobs_without_any_listed_skill_return_no_scores_instead_of_crashing():
    jobs = [_job("1", 90000, 110000, ()), _job("2", 80000, 100000, ())]

    assert build_skill_scores(jobs, {}) == []


def test_no_jobs_returns_no_scores():
    assert build_skill_scores([], {}) == []


def test_single_salary_point_does_not_divide_by_zero():
    scores = build_skill_scores([_job("1", 100, 100, ("Python",))], {})

    assert scores[0].salary_score == 100.0


def test_gap_is_between_zero_and_hundred():
    jobs = [_job("1", 100000, 120000, ("Python", "SQL")), _job("2", 90000, 130000, ("SQL",))]
    scores = build_skill_scores(jobs, {})

    gap = calculate_skill_gap_score(scores, {"Python": 2, "SQL": 1})

    assert 0 <= gap <= 100
    assert coverage_score(gap) == pytest.approx(100 - gap)


def test_skill_levels_are_clamped_to_the_scale():
    jobs = [_job("1", 100000, 120000, ("Python",))]
    scores = build_skill_scores(jobs, {})

    assert calculate_skill_gap_score(scores, {"Python": 99}) == 0.0
    assert calculate_skill_gap_score(scores, {"Python": -4}) == 100.0


def test_recommendation_reason_is_plain_language_and_states_counts():
    jobs = [_job("1", 100000, 120000, ("LLM",)), _job("2", 100000, 120000, ("SQL",))]
    trends = {"LLM": TrendSignal("LLM", 92, 31, "test")}
    scores = build_skill_scores(jobs, trends)

    rec = recommend_skills(scores, {}, limit=1)[0]

    assert rec.skill == "LLM"
    assert "Listed in 1 of 2 postings." in rec.reason
    assert "Trend is +31% over the past 12 months." in rec.reason


@pytest.mark.parametrize(
    "weights",
    [(0.5, 0.5, 0.5), (0.9, 0.2, -0.1), (0.3, 0.3, 0.3)],
)
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        validate_weights(*weights)


def test_default_weights_are_valid():
    validate_weights(0.45, 0.35, 0.20)
