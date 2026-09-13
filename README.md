# Current portfolio source

Live measured KPIs: https://you.techguyverlabs.org/admin-analytics?tab=projects&window=24h . This authenticated view and GrokBot consume `/api/admin/projects`. The JSONL/Pages content below is legacy history, not the current measurement authority. Do not publish private API payloads here.

On Roy's Mac, the deterministic consumer is `node /Users/royhermannn_new/Desktop/Development/techguyver-you/scripts/projects/read.mjs 24h` (optional third argument: project ID). Existing credentials load internally. Daily collection is owned by the existing GrokBot Portfolio daily review via `scripts/projects/daily.mjs` in techguyver-you.

# Techguyver Portfolio KPIs

Lightweight daily portfolio glance. **No Google Sheets.**

## How it works
1. **Ledger** (source of truth): append-only JSONL in `data/`
2. **Build**: `python3 scripts/build_viewer.py` → static HTML in `docs/`
3. **URL**: GitHub Pages from `/docs` → https://royherma.github.io/techguyver-portfolio-kpis/

## Breadcrumbs
- `Portfolio` (latest)
- `Portfolio / 2026-09-13` (day folder)
- `Portfolio / Mighty Mouse` (project history)

## Daily update
```bash
# 1) append one row per project to data/project-daily.jsonl
# 2) append CoS row to data/cos-daily.jsonl (optional)
# 3) refresh data/projects-latest.json
python3 scripts/build_viewer.py
git add data docs
git commit -m "portfolio: YYYY-MM-DD"
git push
```

## Data shape
`project-daily.jsonl` line:
```json
{"date":"YYYY-MM-DD","project":"…","health":"GREEN|RED","revenue":0,"costs":"TBD","users":"…","top":"…","next":"…"}
```

Costs stay `TBD` until real spend is tracked. Never invent numbers.
