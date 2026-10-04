# AI Skill Gap Radar

AI Skill Gap Radar is a Python project that analyzes job postings, required skills, salaries, and technology trend signals to estimate which skills are becoming more valuable. It also compares market demand against a user's current skill profile and recommends what to learn next.

## What It Does

- Ranks skills by demand, salary signal, and trend growth.
- Calculates a personalized skill gap score.
- Recommends high-value next skills to learn.
- Runs as both a command-line tool and a Streamlit dashboard.
- Uses simple CSV inputs so you can replace the sample data with real job-posting exports.

## Project Structure

```text
.
├── data/
│   ├── sample_job_postings.csv
│   ├── technology_trends.csv
│   └── user_skills.csv
├── src/
│   └── skill_gap_radar/
│       ├── analytics.py
│       ├── app.py
│       ├── cli.py
│       ├── data_loader.py
│       └── models.py
├── tests/
│   └── test_analytics.py
├── pyproject.toml
└── requirements.txt
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Run the CLI:

```bash
skill-gap-radar analyze
```

Run the dashboard:

```bash
streamlit run src/skill_gap_radar/app.py
```

Run tests:

```bash
pytest
```

## Input CSV Format

`data/sample_job_postings.csv`

```csv
job_id,title,company,location,posted_date,salary_min,salary_max,skills
1,Data Scientist,Northstar Analytics,Remote,2026-09-10,118000,155000,"Python;SQL;Machine Learning;Statistics"
```

`data/technology_trends.csv`

```csv
skill,trend_index,change_12m_pct,source_note
GenAI,94,34,Synthetic market signal
```

`data/user_skills.csv`

```csv
skill,level
Python,4
SQL,3
```

Skill level is from `0` to `5`.

## How The Score Works

Each skill receives a value score from three market signals:

- Demand: how often the skill appears in job postings.
- Salary: average salary midpoint for postings requiring that skill.
- Growth: external trend signal and 12-month change.

The personalized gap score estimates how much high-value demand is not covered by the user's current skill levels. A higher score means a larger learning opportunity.

## Portfolio Ideas

Good next upgrades for this project:

- Add a job scraper for sources that allow scraping or provide APIs.
- Add salary normalization by location.
- Add time-series forecasting by month.
- Add embeddings to cluster related skills.
- Add resume parsing to infer the user's current skill vector automatically.
