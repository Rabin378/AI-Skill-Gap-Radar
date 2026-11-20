from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class JobPosting:
    job_id: str
    title: str
    company: str
    location: str
    posted_date: date
    salary_min: float
    salary_max: float
    skills: tuple[str, ...]

    @property
    def salary_midpoint(self) -> float:
        return (self.salary_min + self.salary_max) / 2


@dataclass(frozen=True)
class TrendSignal:
    skill: str
    trend_index: float
    change_12m_pct: float
    source_note: str


@dataclass(frozen=True)
class SkillScore:
    skill: str
    posting_count: int
    avg_salary: float
    trend_index: float
    change_12m_pct: float
    demand_score: float
    salary_score: float
    growth_score: float
    value_score: float
    projected_value_score: float
    total_postings: int = 0


@dataclass(frozen=True)
class SkillRecommendation:
    skill: str
    current_level: float
    target_score: float
    gap_contribution: float
    reason: str
