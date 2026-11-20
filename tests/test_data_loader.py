import pytest

from skill_gap_radar.data_loader import (
    DEFAULT_JOBS_PATH,
    DEFAULT_TRENDS_PATH,
    DEFAULT_USER_PATH,
    load_job_postings,
    load_trend_signals,
    load_user_skills,
    normalize_skill,
    split_skills,
)


def test_sample_data_loads_with_expected_shape():
    jobs = load_job_postings(DEFAULT_JOBS_PATH)
    trends = load_trend_signals(DEFAULT_TRENDS_PATH)
    user = load_user_skills(DEFAULT_USER_PATH)

    assert len(jobs) == 20
    assert "GenAI" in trends
    assert user["Python"] == 4.0


def test_skill_aliases_are_normalized():
    assert normalize_skill("  generative   AI ") == "GenAI"
    assert normalize_skill("LLMs") == "LLM"
    assert normalize_skill("mlops") == "MLOps"


def test_split_skills_drops_blanks_and_duplicates():
    assert split_skills("Python; ;SQL;python;SQL") == ("Python", "SQL", "python")
    assert split_skills("") == ()


def test_bom_from_excel_export_is_handled(tmp_path):
    path = tmp_path / "user_skills.csv"
    path.write_text("\ufeffskill,level\nPython,3\n", encoding="utf-8")

    assert load_user_skills(path) == {"Python": 3.0}


def test_levels_are_clamped_when_loaded(tmp_path):
    path = tmp_path / "user_skills.csv"
    path.write_text("skill,level\nPython,9\nSQL,-2\n", encoding="utf-8")

    assert load_user_skills(path) == {"Python": 5.0, "SQL": 0.0}


def test_missing_column_names_the_file_and_column(tmp_path):
    path = tmp_path / "user_skills.csv"
    path.write_text("skill,score\nPython,3\n", encoding="utf-8")

    with pytest.raises(ValueError, match="user_skills.csv is missing required column"):
        load_user_skills(path)


def test_bad_number_reports_the_line(tmp_path):
    path = tmp_path / "user_skills.csv"
    path.write_text("skill,level\nPython,3\nSQL,advanced\n", encoding="utf-8")

    with pytest.raises(ValueError, match="user_skills.csv, line 3"):
        load_user_skills(path)


def test_inverted_salary_range_is_rejected(tmp_path):
    path = tmp_path / "jobs.csv"
    path.write_text(
        "job_id,title,company,location,posted_date,salary_min,salary_max,skills\n"
        "1,Analyst,Acme,Remote,2026-01-05,150000,120000,SQL\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="salary_max is lower than salary_min"):
        load_job_postings(path)


def test_missing_file_gives_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_user_skills(tmp_path / "nope.csv")
