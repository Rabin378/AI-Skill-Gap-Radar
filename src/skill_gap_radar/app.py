"""Streamlit dashboard for Skill Radar.

Run from the project root with:  streamlit run src/skill_gap_radar/app.py
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

# Let Streamlit find the package even when the project has not been pip-installed.
_SRC_DIR = str(Path(__file__).resolve().parents[1])
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from skill_gap_radar.analytics import (  # noqa: E402
    build_skill_scores,
    calculate_skill_gap_score,
    coverage_score,
    recommend_skills,
)
from skill_gap_radar.data_loader import (  # noqa: E402
    load_job_postings,
    load_trend_signals,
    load_user_skills,
    normalize_skill,
)
from skill_gap_radar.insights import (  # noqa: E402
    LEVEL_GUIDE,
    coverage_sentence,
    headline_for,
    level_label,
    opportunity_ratio,
)

MARKET_COLOR = "#1d6b67"
YOU_COLOR = "#b9802a"
PROFILE_SIZE = 12
CHART_LIMIT = 8

PAGE_STYLE = """
<style>
  .stApp h1, .stApp h2, .stApp h3, .stApp [data-testid="stMetricValue"] {
    font-family: Charter, "Bitstream Charter", "Iowan Old Style", "Sitka Text", Cambria, Georgia, serif;
    letter-spacing: -0.01em;
  }
  .stApp h1 { font-weight: 700; }
  .stApp h2, .stApp h3 { font-weight: 600; }
  .answer { font-size: 1.05rem; line-height: 1.6; max-width: 46em; }
  .muted { color: #56646c; }
</style>
"""


@st.cache_data
def load_demo_data():
    return load_job_postings(), load_trend_signals(), load_user_skills()


def normalize_skill_map(skills: dict[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for skill, level in skills.items():
        normalized[normalize_skill(str(skill))] = max(0.0, min(5.0, float(level)))
    return normalized


def build_table_rows(skill_scores, limit: int) -> list[dict]:
    return [
        {
            "Skill": score.skill,
            "Market value": round(score.projected_value_score, 1),
            "Postings": score.posting_count,
            "Average salary": round(score.avg_salary),
            "Past 12 months (%)": round(score.change_12m_pct, 1),
            "Demand": round(score.demand_score, 1),
            "Salary": round(score.salary_score, 1),
            "Growth": round(score.growth_score, 1),
        }
        for score in skill_scores[:limit]
    ]


def build_radar_figure(skill_scores, user_skills: dict[str, float], limit: int) -> go.Figure:
    axes = skill_scores[:limit]
    names = [score.skill for score in axes]
    market = [round(score.projected_value_score, 1) for score in axes]
    yours = [round(user_skills.get(score.skill, 0.0) / 5 * 100, 1) for score in axes]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=market + market[:1],
            theta=names + names[:1],
            name="Market value",
            fill="toself",
            line=dict(color=MARKET_COLOR, width=2.5),
            fillcolor="rgba(29, 107, 103, 0.16)",
            hovertemplate="%{theta}: %{r:.1f} market value<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=yours + yours[:1],
            theta=names + names[:1],
            name="Your level",
            fill="toself",
            line=dict(color=YOU_COLOR, width=2, dash="dot"),
            fillcolor="rgba(185, 128, 42, 0.14)",
            hovertemplate="%{theta}: level %{customdata:.1f} of 5<extra></extra>",
            customdata=[user_skills.get(name, 0.0) for name in names + names[:1]],
        )
    )
    fig.update_layout(
        polar=dict(
            domain=dict(x=[0.14, 0.86], y=[0.12, 0.88]),
            radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="#c5cdc8", linecolor="#c5cdc8"),
            angularaxis=dict(gridcolor="#c5cdc8", linecolor="#c5cdc8", tickfont=dict(size=14)),
            bgcolor="rgba(0,0,0,0)",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=20, b=20),
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Avenir Next, Helvetica Neue, Segoe UI, sans-serif", color="#1c2630"),
    )
    return fig


def render_sidebar(skill_scores, defaults: dict[str, float]) -> tuple[dict[str, float], int]:
    st.sidebar.header("Your skill levels")
    st.sidebar.caption("0 means not started. 5 means you can teach it or lead decisions about it.")
    with st.sidebar.expander("What each level means", expanded=False):
        for number, text in LEVEL_GUIDE:
            st.markdown(f"**{number}**  {text}")

    # Every level from your file counts toward coverage, even for skills that are
    # not in the top sliders. The sliders adjust the most valuable skills, plus any
    # other market skill you already have a level for.
    user_skills: dict[str, float] = dict(defaults)
    top_names = [score.skill for score in skill_scores[:PROFILE_SIZE]]
    extra_names = [
        score.skill
        for score in skill_scores[PROFILE_SIZE:]
        if defaults.get(score.skill, 0.0) > 0
    ]
    for skill in top_names + extra_names:
        user_skills[skill] = st.sidebar.slider(
            skill,
            min_value=0.0,
            max_value=5.0,
            value=float(defaults.get(skill, 0.0)),
            step=0.5,
            key=f"level_{skill}",
        )

    st.sidebar.divider()
    max_top = min(15, len(skill_scores))
    top_n = st.sidebar.slider(
        "Skills in the table",
        min_value=min(5, max_top),
        max_value=max_top,
        value=min(10, max_top),
    )
    return user_skills, top_n


def render_dashboard() -> None:
    st.set_page_config(page_title="Skill Radar", layout="wide")
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)

    jobs, trends, default_user_skills = load_demo_data()
    skill_scores = build_skill_scores(jobs, trends)
    defaults = normalize_skill_map(default_user_skills)

    st.title("Skill Radar")
    st.markdown(
        '<p class="muted">Which skills the job market pays for, compared with the skills you already have.</p>',
        unsafe_allow_html=True,
    )

    if not jobs or not skill_scores:
        st.warning("No market data was loaded. Add job postings and trend signals to the data folder.")
        return

    user_skills, top_n = render_sidebar(skill_scores, defaults)

    gap_score = calculate_skill_gap_score(skill_scores, user_skills)
    coverage = coverage_score(gap_score)
    recommendations = recommend_skills(skill_scores, user_skills, limit=5)

    st.markdown(
        f'<p class="answer">{escape(coverage_sentence(coverage, len(jobs)))}</p>',
        unsafe_allow_html=True,
    )
    st.subheader(headline_for(skill_scores, recommendations))

    metric_cols = st.columns(3)
    metric_cols[0].metric(
        "Market value you cover",
        f"{coverage:.0f}%",
        help="Share of the market value that your current skill levels already reach.",
    )
    metric_cols[1].metric("Job postings analysed", len(jobs))
    metric_cols[2].metric(
        "Best next skill",
        recommendations[0].skill if recommendations else "None needed",
    )

    left, right = st.columns([1.3, 1], gap="large")
    with left:
        st.subheader("Market value and your level")
        st.plotly_chart(
            build_radar_figure(skill_scores, user_skills, CHART_LIMIT),
            alt="Radar chart comparing market value with your skill levels for the top skills.",
        )

    with right:
        st.subheader("Learn next")
        if not recommendations:
            st.info("Your current skills already cover the strongest market opportunities.")
        for index, rec in enumerate(recommendations, start=1):
            level_text = (
                f"You are at {rec.current_level:g} of 5 ({level_label(rec.current_level).lower()})."
                if rec.current_level > 0
                else "Not on your profile yet."
            )
            st.markdown(f"**{index}. {rec.skill}**")
            st.caption(rec.reason)
            st.progress(
                opportunity_ratio(rec, recommendations),
                text=f"Opportunity compared with the top pick. {level_text}",
            )

    st.subheader("All skills")
    st.dataframe(
        build_table_rows(skill_scores, top_n),
        hide_index=True,
        column_config={
            "Market value": st.column_config.ProgressColumn(
                "Market value", min_value=0, max_value=100, format="%.1f"
            ),
            "Average salary": st.column_config.NumberColumn("Average salary", format="$%d"),
            "Past 12 months (%)": st.column_config.NumberColumn("Past 12 months", format="%.1f%%"),
            "Demand": st.column_config.NumberColumn(format="%.1f"),
            "Salary": st.column_config.NumberColumn(format="%.1f"),
            "Growth": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    with st.expander("How the scores are calculated"):
        st.markdown(
            """
**Market value** blends three signals, each scaled from 0 to 100:

- **Demand** (45%): how often postings list the skill.
- **Salary** (35%): the average midpoint of posted salary ranges for that skill.
- **Growth** (20%): the trend index and the 12-month change from the trend file.

The blend is then adjusted by the 12-month change.

**Gap** is the share of that market value your levels do not yet reach. A gap of 0% means your profile covers everything in the market view. Each recommendation's opportunity is the value it would add, measured against the top pick.

The sample trend figures are synthetic demo values. Replace `data/technology_trends.csv` with real data before you rely on the results.
"""
        )


if __name__ == "__main__":
    render_dashboard()
