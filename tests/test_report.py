from skill_gap_radar.analytics import build_skill_scores, calculate_skill_gap_score, recommend_skills
from skill_gap_radar.data_loader import load_job_postings, load_trend_signals, load_user_skills
from skill_gap_radar.data_loader import DEFAULT_JOBS_PATH, DEFAULT_TRENDS_PATH, DEFAULT_USER_PATH
from skill_gap_radar.models import JobPosting, TrendSignal
from skill_gap_radar.report import build_html_report, write_html_report
from datetime import date


def _sample_context():
    jobs = load_job_postings(DEFAULT_JOBS_PATH)
    trends = load_trend_signals(DEFAULT_TRENDS_PATH)
    user = load_user_skills(DEFAULT_USER_PATH)
    scores = build_skill_scores(jobs, trends)
    gap = calculate_skill_gap_score(scores, user)
    recs = recommend_skills(scores, user, limit=5)
    return jobs, scores, gap, recs, user


def test_report_contains_the_core_sections_and_a_radar():
    jobs, scores, gap, recs, user = _sample_context()

    html = build_html_report(jobs, scores, gap, recs, limit=10, user_skills=user)

    assert "<!doctype html>" in html
    assert "Learn next" in html
    assert "How to read this" in html
    assert "<svg" in html and "</svg>" in html
    assert "synthetic demo values" in html


def test_report_is_self_contained_with_no_external_requests():
    jobs, scores, gap, recs, user = _sample_context()

    html = build_html_report(jobs, scores, gap, recs, user_skills=user)

    assert "<script" not in html
    assert "http://" not in html and "https://" not in html.replace(
        'xmlns="http://www.w3.org/2000/svg"', ""
    )


def test_skill_names_are_escaped():
    jobs = [
        JobPosting("1", "Eng", "Co", "Remote", date(2026, 1, 1), 100000, 120000, ("<script>alert(1)</script>",)),
    ]
    trends = {"<script>alert(1)</script>": TrendSignal("<script>alert(1)</script>", 80, 5, "x")}
    scores = build_skill_scores(jobs, trends)
    gap = calculate_skill_gap_score(scores, {})
    recs = recommend_skills(scores, {}, limit=3)

    html = build_html_report(jobs, scores, gap, recs)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_report_handles_empty_market_without_crashing():
    html = build_html_report([], [], 0.0, [])

    assert "No skill data was loaded yet." in html


def test_write_html_report_creates_parent_folders(tmp_path):
    jobs, scores, gap, recs, user = _sample_context()
    target = tmp_path / "nested" / "report.html"

    written = write_html_report(target, jobs, scores, gap, recs, user_skills=user)

    assert written.exists()
    assert written.read_text(encoding="utf-8").startswith("<!doctype html>")
