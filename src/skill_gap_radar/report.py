"""Build a standalone HTML report. It needs no server and no internet connection."""

from __future__ import annotations

import math
from collections.abc import Mapping
from html import escape
from pathlib import Path

from .analytics import coverage_score
from .insights import (
    LEVEL_GUIDE,
    coverage_sentence,
    headline_for,
    level_label,
    opportunity_ratio,
)
from .models import JobPosting, SkillRecommendation, SkillScore

RADAR_AXES = 8
MARKET_COLOR = "#1d6b67"
YOU_COLOR = "#b9802a"

CSS = """
:root {
  --paper: #eef1ec;
  --panel: #f7f9f6;
  --ink: #1c2630;
  --muted: #56646c;
  --rule: #c5cdc8;
  --market: #1d6b67;
  --market-soft: #d4e6e3;
  --you: #b9802a;
  --you-soft: #efe0c6;
  --down: #a4492f;
  --serif: "Charter", "Bitstream Charter", "Iowan Old Style", "Sitka Text", Cambria, Georgia, serif;
  --sans: "Avenir Next", "Helvetica Neue", "Segoe UI", system-ui, -apple-system, sans-serif;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 17px/1.6 var(--sans);
}
.page { max-width: 1120px; margin: 0 auto; padding: 56px 24px 72px; }
a { color: var(--market); }
:focus-visible { outline: 2px solid var(--market); outline-offset: 3px; border-radius: 2px; }

.hero {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 40px;
  align-items: center;
}
.hero h1 {
  font: 700 clamp(36px, 5vw, 56px)/1.08 var(--serif);
  letter-spacing: -0.015em;
  margin: 0 0 20px;
}
.lede { font-size: 19px; color: var(--muted); max-width: 34em; margin: 0 0 16px; }
.answer { font-size: 19px; margin: 0 0 12px; max-width: 34em; }
.answer strong { font-weight: 700; color: var(--market); }

.radar { margin: 0; }
.radar svg { width: 100%; height: auto; display: block; }
.radar figcaption { font-size: 14px; color: var(--muted); margin-top: 8px; }
.radar-label { font: 500 20px var(--sans); fill: var(--ink); }
.key { display: inline-flex; align-items: center; gap: 8px; margin-right: 18px; }
.swatch { width: 18px; height: 4px; border-radius: 2px; display: inline-block; }

section { margin-top: 72px; padding-top: 28px; border-top: 1px solid var(--rule); }
h2 { font: 600 30px/1.2 var(--serif); margin: 0 0 8px; letter-spacing: -0.01em; }
.section-intro { color: var(--muted); max-width: 40em; margin: 0 0 28px; }

.picks { list-style: none; margin: 0; padding: 0; }
.picks li {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 8px 16px;
  padding: 26px 0;
  border-top: 1px solid var(--rule);
}
.picks li:first-child { border-top: 0; padding-top: 0; }
.rank { font: 500 34px/1 var(--serif); color: var(--muted); }
.pick-name { font: 600 24px/1.2 var(--serif); margin: 0 0 6px; }
.pick-reason { margin: 0 0 14px; color: var(--muted); font-size: 16px; }
.meter { display: block; height: 6px; border-radius: 999px; background: var(--market-soft); overflow: hidden; max-width: 360px; }
.meter span { display: block; height: 100%; background: var(--market); }
.meter-label { font-size: 14px; color: var(--muted); margin-top: 6px; }
.level-note { font-size: 14px; color: var(--muted); margin: 6px 0 0; }

.table-wrap { overflow-x: auto; border-top: 1px solid var(--rule); }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; min-width: 680px; }
caption { text-align: left; color: var(--muted); padding: 14px 0 10px; font-size: 14px; }
th, td { padding: 14px 12px 14px 0; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: middle; }
th { font-size: 14px; font-weight: 600; color: var(--muted); }
th.num, td.num { text-align: right; padding-right: 16px; }
.value { display: flex; align-items: center; gap: 12px; }
.value .meter { width: 150px; flex: 0 0 150px; }
.value b { font-weight: 600; min-width: 3.2em; }
.trend-up { color: var(--market); font-weight: 600; }
.trend-down { color: var(--down); font-weight: 600; }
.dots { display: inline-flex; gap: 4px; vertical-align: middle; }
.dots i { width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid var(--you); display: inline-block; }
.dots i.on { background: var(--you); }

.reading { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 40px 56px; }
.reading h3 { font: 600 19px/1.3 var(--serif); margin: 0 0 8px; }
.reading p { margin: 0; color: var(--muted); font-size: 16px; }
.levels { margin: 14px 0 0; padding: 0; list-style: none; font-size: 16px; color: var(--muted); }
.levels li { padding: 6px 0; border-top: 1px solid var(--rule); display: flex; gap: 12px; }
.levels li b { min-width: 1.2em; color: var(--ink); font-weight: 600; }

.footnote { margin-top: 64px; padding-top: 22px; border-top: 1px solid var(--rule); font-size: 14px; color: var(--muted); }

@media (max-width: 860px) {
  .hero { grid-template-columns: 1fr; gap: 36px; }
  .reading { grid-template-columns: 1fr; }
}
@media (max-width: 520px) {
  .page { padding: 36px 18px 56px; }
  .radar-label { font-size: 24px; }
  .hero h1 { font-size: 34px; }
  .rank { font-size: 26px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""


def _polar(index: int, count: int) -> float:
    return -math.pi / 2 + (2 * math.pi * index / count)


def _radar_svg(skill_scores: list[SkillScore], user_skills: Mapping[str, float]) -> str:
    axes = skill_scores[:RADAR_AXES]
    count = len(axes)
    width, height = 760, 560
    center_x, center_y = width / 2, height / 2
    radius = 146

    def point(value_pct: float, index: int) -> tuple[float, float]:
        angle = _polar(index, count)
        distance = radius * (value_pct / 100)
        return center_x + distance * math.cos(angle), center_y + distance * math.sin(angle)

    def polygon(values: list[float]) -> str:
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(v, i) for i, v in enumerate(values)))

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="radar-title radar-desc">',
        '<title id="radar-title">Market value compared with your skill levels</title>',
        f'<desc id="radar-desc">Radar chart of the top {count} skills by market value. '
        "The teal shape is market value. The amber shape is your level.</desc>",
    ]

    for ring in (25, 50, 75, 100):
        parts.append(
            f'<polygon points="{polygon([ring] * count)}" fill="none" stroke="#c5cdc8" stroke-width="1"/>'
        )

    for index in range(count):
        end_x, end_y = point(100, index)
        parts.append(
            f'<line x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" '
            'stroke="#c5cdc8" stroke-width="1"/>'
        )

    market_values = [score.projected_value_score for score in axes]
    your_values = [max(0.0, min(5.0, user_skills.get(score.skill, 0.0))) / 5 * 100 for score in axes]

    parts.append(
        f'<polygon points="{polygon(market_values)}" fill="{MARKET_COLOR}" fill-opacity="0.16" '
        f'stroke="{MARKET_COLOR}" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    parts.append(
        f'<polygon points="{polygon(your_values)}" fill="{YOU_COLOR}" fill-opacity="0.18" '
        f'stroke="{YOU_COLOR}" stroke-width="2" stroke-dasharray="6 5" stroke-linejoin="round"/>'
    )

    for index, score in enumerate(axes):
        angle = _polar(index, count)
        label_x = center_x + (radius + 22) * math.cos(angle)
        label_y = center_y + (radius + 22) * math.sin(angle)
        if math.cos(angle) > 0.2:
            anchor = "start"
        elif math.cos(angle) < -0.2:
            anchor = "end"
        else:
            anchor = "middle"
        baseline = "middle"
        if math.sin(angle) > 0.5:
            baseline = "hanging"
        elif math.sin(angle) < -0.5:
            baseline = "auto"
        parts.append(
            f'<text class="radar-label" x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="{baseline}">{escape(score.skill)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _meter(value_pct: float) -> str:
    clamped = max(0.0, min(100.0, value_pct))
    return f'<span class="meter" aria-hidden="true"><span style="width: {clamped:.1f}%"></span></span>'


def _level_dots(level: float) -> str:
    filled = round(max(0.0, min(5.0, level)))
    dots = "".join(f'<i class="{"on" if i < filled else ""}"></i>' for i in range(5))
    return f'<span class="dots" role="img" aria-label="Level {level:g} of 5, {level_label(level)}">{dots}</span>'


def _pick_list(recommendations: list[SkillRecommendation], user_skills: Mapping[str, float]) -> str:
    items = []
    for index, rec in enumerate(recommendations, start=1):
        ratio = opportunity_ratio(rec, recommendations)
        current = user_skills.get(rec.skill, 0.0)
        if current <= 0:
            level_text = "Not on your profile yet."
        else:
            level_text = f"You are at {current:g} of 5 ({level_label(current).lower()})."
        items.append(
            "<li>"
            f'<span class="rank">{index}</span>'
            "<div>"
            f'<h3 class="pick-name">{escape(rec.skill)}</h3>'
            f'<p class="pick-reason">{escape(rec.reason)}</p>'
            f"{_meter(ratio * 100)}"
            f'<p class="meter-label">Opportunity, relative to the top pick. {level_text}</p>'
            "</div>"
            "</li>"
        )
    if not items:
        return '<p class="section-intro">Your current skills already cover the strongest opportunities.</p>'
    return f'<ol class="picks">{"".join(items)}</ol>'


def _market_table(skill_scores: list[SkillScore], limit: int, user_skills: Mapping[str, float]) -> str:
    rows = []
    for score in skill_scores[:limit]:
        trend_class = "trend-up" if score.change_12m_pct >= 0 else "trend-down"
        sign = "+" if score.change_12m_pct >= 0 else ""
        level = user_skills.get(score.skill, 0.0)
        rows.append(
            "<tr>"
            f'<th scope="row">{escape(score.skill)}</th>'
            f'<td><div class="value">{_meter(score.projected_value_score)}'
            f"<b>{score.projected_value_score:.1f}</b></div></td>"
            f'<td class="num">{score.posting_count}</td>'
            f'<td class="num">${score.avg_salary:,.0f}</td>'
            f'<td class="num"><span class="{trend_class}">{sign}{score.change_12m_pct:.0f}%</span></td>'
            f"<td>{_level_dots(level)}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap" tabindex="0">'
        "<table>"
        f"<caption>Top {min(limit, len(skill_scores))} skills by projected market value</caption>"
        "<thead><tr>"
        '<th scope="col">Skill</th>'
        '<th scope="col">Market value</th>'
        '<th scope="col" class="num">Postings</th>'
        '<th scope="col" class="num">Average salary</th>'
        '<th scope="col" class="num">Past 12 months</th>'
        '<th scope="col">Your level</th>'
        "</tr></thead>"
        f'<tbody>{"".join(rows)}</tbody>'
        "</table></div>"
    )


def _level_guide() -> str:
    items = "".join(f"<li><b>{number}</b><span>{escape(text)}</span></li>" for number, text in LEVEL_GUIDE)
    return f'<ul class="levels">{items}</ul>'


def build_html_report(
    jobs: list[JobPosting],
    skill_scores: list[SkillScore],
    gap_score: float,
    recommendations: list[SkillRecommendation],
    limit: int = 10,
    user_skills: Mapping[str, float] | None = None,
) -> str:
    user_skills = dict(user_skills or {})
    coverage = coverage_score(gap_score)
    headline = escape(headline_for(skill_scores, recommendations))
    top_names = ", ".join(escape(score.skill) for score in skill_scores[:3])
    sentence = escape(coverage_sentence(coverage, len(jobs)))
    radar = _radar_svg(skill_scores, user_skills) if skill_scores else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Which data and AI skills the job market rewards, and how your profile compares.">
  <title>Skill Radar</title>
  <style>{CSS}</style>
</head>
<body>
  <main class="page">
    <header class="hero">
      <div>
        <h1>{headline}</h1>
        <p class="answer">{sentence}</p>
        <p class="lede">This report ranks skills by how much the postings pay for them, and points to the gaps worth closing first.</p>
      </div>
      <figure class="radar">
        {radar}
        <figcaption>
          <span class="key"><span class="swatch" style="background:{MARKET_COLOR}"></span>Market value</span>
          <span class="key"><span class="swatch" style="background:{YOU_COLOR}"></span>Your level</span>
        </figcaption>
      </figure>
    </header>

    <section aria-labelledby="picks-heading">
      <h2 id="picks-heading">Learn next</h2>
      <p class="section-intro">The skills that would unlock the most market value for your current profile, in order.</p>
      {_pick_list(recommendations, user_skills)}
    </section>

    <section aria-labelledby="market-heading">
      <h2 id="market-heading">Where the market value is</h2>
      <p class="section-intro">Leaders include {top_names}. Scroll sideways on small screens to see every column.</p>
      {_market_table(skill_scores, limit, user_skills)}
    </section>

    <section aria-labelledby="reading-heading">
      <h2 id="reading-heading">How to read this</h2>
      <p class="section-intro">The numbers come from three signals. Each one is explained below.</p>
      <div class="reading">
        <div>
          <h3>Market value</h3>
          <p>A 0 to 100 score. It blends demand, salary, and growth, then adjusts for the 12-month change. Higher means the market pays more for the skill right now.</p>
        </div>
        <div>
          <h3>Your level</h3>
          <p>Your own rating from 0 to 5, taken from your skill file. The dots show the level and the amber outline marks what you have not reached yet.</p>
          {_level_guide()}
        </div>
        <div>
          <h3>Coverage and gap</h3>
          <p>Coverage is the share of market value your levels already reach. The gap is the rest. A gap of {gap_score:.1f}% means {gap_score:.1f} of every 100 points of market value are still open to you.</p>
        </div>
        <div>
          <h3>What drives the score</h3>
          <p>Demand counts how often a skill appears. Salary uses the midpoint of posted ranges. Growth uses the trend index and the 12-month change. Each signal is scaled to 0 to 100 before it is combined.</p>
        </div>
      </div>
    </section>

    <footer class="footnote">
      Built from {len(jobs)} job postings, a trend signal file, and your skill levels. The trend figures in the sample data are synthetic demo values. Replace <code>data/technology_trends.csv</code> with real data before you make decisions based on this report.
    </footer>
  </main>
</body>
</html>
"""


def write_html_report(
    output_path: str | Path,
    jobs: list[JobPosting],
    skill_scores: list[SkillScore],
    gap_score: float,
    recommendations: list[SkillRecommendation],
    limit: int = 10,
    user_skills: Mapping[str, float] | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        build_html_report(
            jobs,
            skill_scores,
            gap_score,
            recommendations,
            limit=limit,
            user_skills=user_skills,
        ),
        encoding="utf-8",
    )
    return path.resolve()
