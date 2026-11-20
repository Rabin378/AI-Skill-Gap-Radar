# Methodology

This page explains how Skill Radar turns postings and trend data into the numbers you see. It is written so you can check the logic, change the weights, or decide whether the approach fits your question.

## 1. Inputs

- **Postings**: each posting contributes its skills and a salary midpoint, `(salary_min + salary_max) / 2`.
- **Trends**: each skill may have a `trend_index` (0 to 100) and a `change_12m_pct`. Missing skills use a trend index of 50 and a change of 0.
- **Your levels**: each skill is a number from 0 to 5. Values outside that range are clamped.

Duplicate skills within one posting count once.

## 2. Three signals per skill

Let `N` be the number of postings, `n` the postings that list a skill, and `maxₙ` the largest `n` across all skills.

**Demand** = `n / maxₙ × 100`. The most common skill scores 100.

**Salary** = the average salary midpoint `m` of postings listing the skill, scaled between the lowest and highest such averages across all skills. The lowest-paid skill scores 0, the highest 100. If every skill has the same average, every skill scores 100.

**Growth** = `0.55 × trend_index + 0.45 × scale(change_12m_pct, −10, 40)`, where `scale` maps the range −10 to 40 onto 0 to 100 and clamps the result.

## 3. Market value

```
value      = 0.45 × demand + 0.35 × salary + 0.20 × growth
projected  = clamp(value × (1 + change_12m_pct / 100), 0, 100)
```

The weights are the defaults in `analytics.build_skill_scores`. They must be non-negative and add up to 1.0. Anything else raises an error.

`projected` is the **market value** used for ranking, the radar chart, and the gap.

## 4. Coverage and gap

Each skill's missing share is `1 − level / 5`.

```
gap       = Σ projected × (1 − level / 5)  /  Σ projected × 100
coverage  = 100 − gap
```

A gap of 0 means your levels reach every skill at full strength. A gap near 100 means almost none of the market value is covered.

## 5. Recommendations

For each skill you have not fully reached:

```
opportunity = projected × (1 − level / 5)
```

Skills are ranked by opportunity. The dashboard and report show each opportunity relative to the top pick. Skills at level 5 are left out.

## 6. Worked example

Take two skills with market values 80 (SQL) and 60 (GenAI). You are at level 4 in SQL and level 1 in GenAI.

- SQL missing share: `1 − 4/5 = 0.2`, so it contributes `80 × 0.2 = 16`.
- GenAI missing share: `1 − 1/5 = 0.8`, so it contributes `60 × 0.8 = 48`.
- Gap: `(16 + 48) / (80 + 60) × 100 = 45.7%`. Coverage is 54.3%.
- GenAI ranks first to learn, with an opportunity of 48 against SQL's 16.

## 7. Known limits and decisions to review

These are deliberate choices or open questions. They are documented so you can change them with full information.

- **Growth may count twice.** The growth signal already includes the 12-month change, and `projected` multiplies by the change again. That favours fast-growing skills more than the weights alone imply. To remove the second effect, use `value` instead of `projected` in the ranking.
- **Posting dates are not used.** They are validated but do not affect any score. Adding a recency weight is the most useful next change to the methodology.
- **Salary is relative.** The salary signal stretches the gap between the lowest and highest skill, so one outlier can compress everyone else. Median-based scaling would be more robust.
- **The sample trend file is synthetic.** Treat its growth numbers as placeholders.
- **Scores are relative to your data.** Adding or removing postings changes every skill's demand and salary scaling.
