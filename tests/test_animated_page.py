import json
import re
from datetime import date

from skill_gap_radar.analytics import build_skill_scores, calculate_skill_gap_score
from skill_gap_radar.animated_page import (
    DATA_PLACEHOLDER,
    build_page_data,
    render_animated_page,
    write_animated_page,
)
from skill_gap_radar.cli import main
from skill_gap_radar.data_loader import (
    DEFAULT_JOBS_PATH,
    DEFAULT_TRENDS_PATH,
    DEFAULT_USER_PATH,
    load_job_postings,
    load_trend_signals,
    load_user_skills,
)
from skill_gap_radar.models import JobPosting, TrendSignal


def _sample():
    jobs = load_job_postings(DEFAULT_JOBS_PATH)
    trends = load_trend_signals(DEFAULT_TRENDS_PATH)
    user = load_user_skills(DEFAULT_USER_PATH)
    scores = build_skill_scores(jobs, trends)
    return jobs, scores, user, trends


def _embedded_data(html: str) -> dict:
    match = re.search(r'<script type="application/json" id="skill-data">(.*?)</script>', html, re.S)
    assert match, "data block missing"
    return json.loads(match.group(1))


def test_page_embeds_the_real_scores_and_levels():
    jobs, scores, user, trends = _sample()

    data = _embedded_data(render_animated_page(jobs, scores, user, trends))

    assert data["postings"] == 20
    assert [s["skill"] for s in data["skills"]] == [s.skill for s in scores]
    python_row = next(s for s in data["skills"] if s["skill"] == "Python")
    assert python_row["level"] == 4.0
    assert data["profile"][:3] == [s.skill for s in scores[:3]]


def test_embedded_gap_matches_the_python_engine():
    """The browser recomputes coverage with the same rules, so the starting values must agree."""
    jobs, scores, user, trends = _sample()
    data = _embedded_data(render_animated_page(jobs, scores, user, trends))

    total = sum(s["projected"] for s in data["skills"])
    missing = sum(s["projected"] * (1 - s["level"] / 5) for s in data["skills"])
    gap_in_browser_rules = round(missing / total * 100, 1)

    assert gap_in_browser_rules == calculate_skill_gap_score(scores, user)


def test_script_breakout_in_a_skill_name_is_escaped():
    jobs = [JobPosting("1", "Eng", "Co", "Remote", date(2026, 1, 1), 100000, 120000, ("</script><b>x</b>",))]
    trends = {"</script><b>x</b>": TrendSignal("</script><b>x</b>", 80, 5, "synthetic demo")}
    scores = build_skill_scores(jobs, trends)

    html = render_animated_page(jobs, scores, {}, trends)

    # The template has exactly two script blocks; a breakout would add a third closing tag.
    assert html.count("</script>") == 2
    assert "</script><b>x</b>" not in html
    assert _embedded_data(html)["skills"][0]["skill"] == "</script><b>x</b>"


def test_page_is_self_contained():
    jobs, scores, user, trends = _sample()
    html = render_animated_page(jobs, scores, user, trends)

    assert DATA_PLACEHOLDER not in html
    assert "<link " not in html
    assert not re.search(r'src="https?://', html)
    assert not re.search(r'href="https?://', html)
    assert "fetch(" not in html


def test_synthetic_notice_follows_the_trend_source_note():
    jobs, scores, user, trends = _sample()
    assert build_page_data(jobs, scores, user, trends)["syntheticTrends"] is True
    assert build_page_data(jobs, scores, user, {})["syntheticTrends"] is False


def test_reduced_motion_is_respected_in_the_page():
    jobs, scores, user, trends = _sample()
    html = render_animated_page(jobs, scores, user, trends)

    assert "prefers-reduced-motion: reduce" in html


def test_write_and_cli_produce_the_page(tmp_path, capsys):
    jobs, scores, user, trends = _sample()
    target = write_animated_page(tmp_path / "nested" / "page.html", jobs, scores, user, trends)
    assert target.read_text(encoding="utf-8").startswith("<!doctype html>")

    cli_target = tmp_path / "cli.html"
    assert main(["page", "--output", str(cli_target)]) == 0
    assert cli_target.exists()
    assert "Wrote animated page" in capsys.readouterr().out
