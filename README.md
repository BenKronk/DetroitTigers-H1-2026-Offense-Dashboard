# Detroit Tigers Hitting Dashboard â€” 2026 (First Half)

A Power BI dashboard presenting key hitting statistics for the Detroit Tigers through the first half of the 2026 MLB season, benchmarked against the AL Central Division and MLB as a whole. Built end-to-end: data extraction in Python, transformation and modeling in Power Query and DAX, and visualization in Power BI Desktop.

![Dashboard screenshot](DetTigersDashboard_H1_2026.png)

## Overview

The goal was a single-page analytical view that answers one question at a glance â€” *how are the Tigers hitting relative to their division and the league, and how has that changed month to month* â€” without relying on advanced metrics that depend on external, unstable data sources.

Every statistic on the dashboard is either pulled directly from the MLB Stats API or computed from its raw components, so the numbers are reproducible and don't depend on any third-party leaderboard that could change or disappear.

## Features

- **Benchmarked KPI cards** â€” Runs per Game, Home Runs, OPS, and K%, each showing the Tigers' value alongside the MLB and Central Division figures for context. Directionality is handled correctly: K% is colored inversely (lower is better), unlike the counting and rate stats where higher is better.
- **Slash-line comparison** â€” A clustered bar chart comparing AVG / OBP / SLG across the Tigers, the Central Division, and MLB.
- **Month-over-month heatmaps** â€” Two conditional-formatted matrices showing the Tigers' AVG / OBP / SLG performance *relative to* MLB and to the Central Division, by month, with a diverging red-to-green scale that makes hot and cold stretches immediately visible.
- **Standings context** â€” Monthly Win/Loss record, providing a narrative link between offensive production and results.
- **Month slicer** â€” Filters the KPI cards, slash-line chart, and heatmaps to a selected month or the full season.
- **Player detail table** â€” Full-roster season batting stats (see *Known Limitations* regarding month interactivity).

## Data Pipeline

**Source:** [MLB Stats API](https://statsapi.mlb.com), accessed via the [`MLB-StatsAPI`](https://github.com/toddrob99/MLB-StatsAPI) Python library.

The project originally attempted extraction via `pybaseball` (FanGraphs / Baseball Reference), but FanGraphs' leaderboard endpoints returned persistent `403` errors due to anti-bot measures, and Baseball Reference's team-page scraper broke on HTML-structure changes. The pipeline was rebuilt on the official MLB Stats API, which returns clean JSON and requires no scraping.

**Extraction (Python):**
- Team season aggregates for hitting, pitching, and fielding (KPI source).
- Team game logs, grouped by month to build the monthly trend tables.
- Full-roster player season stats.
- League and division benchmarks, pooled from individual team game logs (the API has no division-level scope, and league-level game logs are not exposed, so division and league figures are aggregated from their member teams).
- Standings, filtered to the AL Central.

**Transformation (Power Query):**
- Three scope tables (Tigers / Central / MLB) tagged with a `Category` column and appended into a single comparison table.
- Slash-line stats unpivoted into a long (stat name, value) structure to drive the clustered bar chart and heatmaps.

**Modeling (DAX):**
- Rate statistics (AVG / OBP / SLG / OPS) are **recomputed from summed components** rather than averaged, so multi-game and multi-month figures are statistically correct.
- Per-scope measures (`CALCULATE` filtered on `Category`) and delta measures for the benchmark comparisons.
- A shared month dimension so a single slicer filters all visuals consistently.

## Methodology Note

A deliberate design choice throughout: **rates are never computed by averaging rates.** OPS, OBP, SLG, and similar are rebuilt from their underlying counting components (at-bats, hits, walks, total bases, etc.) across whatever games or months are in scope. Averaging per-game or per-month rate values gives statistically wrong results because it ignores differences in plate appearances / innings between games. The pooled-component approach is used everywhere a rate spans more than one game.

## Tech Stack

- **Python** â€” data extraction (`MLB-StatsAPI`, `pandas`)
- **Power BI Desktop** â€” Power Query (M) for transformation, DAX for modeling and measures, visualization
- **MLB Stats API** â€” data source

## Known Limitations

- **Player table is season-grain.** It shows full-season totals per player and does **not** react to the month slicer, because the player extraction pulls season aggregates rather than per-player monthly splits. Making it month-reactive would require per-player game logs (one API call per player). This is intentionally out of scope for the current version and labeled on the dashboard.
- **KPI card behavior across multiple months.** The KPI-style visuals display the most recent selected month's value, not a sum across a multi-month selection â€” this is how the Power BI KPI visual works by design. Cards intended to total across a selection use the standard Card visual instead.
- **Advanced defensive metrics excluded.** OAA and DRS live on sources outside the MLB Stats API (Baseball Savant / Baseball Info Solutions); the fielding data here uses traditional metrics (fielding %, errors, assists, putouts, double plays).
- **wRC+ / FIP not included.** These depend on FanGraphs' season-specific constants (and, for wRC+, park factors), which are not available from the reachable data sources. OPS and OPS-based comparisons stand in for park/league-adjusted offensive indices.

## Repository Contents

- `tigers_dashboard_pull_v2.py` â€” main extraction script (season aggregates, monthly tables, players, benchmarks)
- `*.csv` â€” extracted data files consumed by Power BI
- `DetTigersDashboard_H1_2026.pbix` â€” the Power BI report
- `DetTigersDashboard_H1_2026.png` â€” dashboard screenshot

---

*Data Â© MLB Advanced Media, retrieved via the MLB Stats API. This project is for educational and portfolio purposes and is not affiliated with or endorsed by MLB or the Detroit Tigers.*

