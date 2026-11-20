"""Load job postings, trend signals, and user skill levels from CSV files.

Every loader checks for required columns and reports the file name and line
number when a value cannot be parsed, so bad data is easy to fix.
"""

from __future__ import annotations

import csv
import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from .models import JobPosting, TrendSignal

MAX_LEVEL = 5.0

JOB_COLUMNS = frozenset(
    {"job_id", "title", "company", "location", "posted_date", "salary_min", "salary_max", "skills"}
)
TREND_COLUMNS = frozenset({"skill", "trend_index", "change_12m_pct", "source_note"})
USER_COLUMNS = frozenset({"skill", "level"})

SKILL_ALIASES = {
    "generative ai": "GenAI",
    "gen ai": "GenAI",
    "genai": "GenAI",
    "large language models": "LLM",
    "llms": "LLM",
    "bi": "BI",
    "mlops": "MLOps",
    "dbt": "dbt",
    "apis": "APIs",
}


def _resolve_data_dir() -> Path:
    """Find the data folder: $SKILL_RADAR_DATA_DIR, then the project, then ./data."""
    override = os.environ.get("SKILL_RADAR_DATA_DIR")
    if override:
        return Path(override)
    project_data = Path(__file__).resolve().parents[2] / "data"
    if project_data.is_dir():
        return project_data
    return Path.cwd() / "data"


DEFAULT_DATA_DIR = _resolve_data_dir()
DEFAULT_JOBS_PATH = DEFAULT_DATA_DIR / "sample_job_postings.csv"
DEFAULT_TRENDS_PATH = DEFAULT_DATA_DIR / "technology_trends.csv"
DEFAULT_USER_PATH = DEFAULT_DATA_DIR / "user_skills.csv"


def normalize_skill(skill: str) -> str:
    """Trim whitespace and map common spellings to one canonical name."""
    cleaned = " ".join(skill.strip().split())
    if not cleaned:
        return cleaned
    return SKILL_ALIASES.get(cleaned.lower(), cleaned)


def split_skills(raw_skills: str) -> tuple[str, ...]:
    """Split a semicolon-separated skill list, dropping blanks and duplicates."""
    seen: dict[str, None] = {}
    for part in raw_skills.split(";"):
        skill = normalize_skill(part)
        if skill:
            seen.setdefault(skill, None)
    return tuple(seen)


def _iter_rows(path: str | Path, required: frozenset[str], label: str) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield (line_number, row) pairs after checking the header.

    ``utf-8-sig`` strips the byte-order mark that Excel adds to CSV exports.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"{label} file not found: {file_path}")

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            columns = ", ".join(sorted(missing))
            raise ValueError(f"{file_path.name} is missing required column(s): {columns}")
        for line_number, row in enumerate(reader, start=2):
            yield line_number, row


def _parse_error(path: str | Path, line_number: int, problem: Exception) -> ValueError:
    return ValueError(f"{Path(path).name}, line {line_number}: {problem}")


def load_job_postings(path: str | Path = DEFAULT_JOBS_PATH) -> list[JobPosting]:
    rows: list[JobPosting] = []
    for line_number, row in _iter_rows(path, JOB_COLUMNS, "Job postings"):
        try:
            salary_min = float(row["salary_min"])
            salary_max = float(row["salary_max"])
            if salary_max < salary_min:
                raise ValueError("salary_max is lower than salary_min")
            rows.append(
                JobPosting(
                    job_id=row["job_id"].strip(),
                    title=row["title"].strip(),
                    company=row["company"].strip(),
                    location=row["location"].strip(),
                    posted_date=date.fromisoformat(row["posted_date"].strip()),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    skills=split_skills(row["skills"]),
                )
            )
        except (ValueError, KeyError) as problem:
            raise _parse_error(path, line_number, problem) from problem
    return rows


def load_trend_signals(path: str | Path = DEFAULT_TRENDS_PATH) -> dict[str, TrendSignal]:
    signals: dict[str, TrendSignal] = {}
    for line_number, row in _iter_rows(path, TREND_COLUMNS, "Trend"):
        try:
            skill = normalize_skill(row["skill"])
            signals[skill] = TrendSignal(
                skill=skill,
                trend_index=float(row["trend_index"]),
                change_12m_pct=float(row["change_12m_pct"]),
                source_note=row["source_note"].strip(),
            )
        except (ValueError, KeyError) as problem:
            raise _parse_error(path, line_number, problem) from problem
    return signals


def load_user_skills(path: str | Path = DEFAULT_USER_PATH) -> dict[str, float]:
    """Return skill levels clamped to the 0-5 range."""
    skills: dict[str, float] = {}
    for line_number, row in _iter_rows(path, USER_COLUMNS, "User skills"):
        try:
            level = float(row["level"])
        except ValueError as problem:
            raise _parse_error(path, line_number, problem) from problem
        skills[normalize_skill(row["skill"])] = max(0.0, min(MAX_LEVEL, level))
    return skills
