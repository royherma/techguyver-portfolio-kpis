#!/usr/bin/env python3
"""Build static portfolio KPI viewer from append-only JSONL ledgers."""
from __future__ import annotations
import csv, json, re, html
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS = ROOT / "docs"

def esc(s):
    return html.escape(str(s if s is not None else ""))

def bare(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE).strip()

def slug(name: str) -> str:
    b = bare(name).lower().replace(" ", "-")
    return re.sub(r"-+", "-", b) or "project"

def health_class(h: str) -> str:
    u = str(h).upper()
    if "RED" in u:
        return "red"
    if "YELLOW" in u or "AMBER" in u:
        return "yellow"
    return "green"

CSS = """
:root{--bg:#0b0d10;--ink:#e8edf5;--muted:#9aa7b8;--line:#243041;--green:#3dd68c;--red:#ff6b6b;--yellow:#f5c84c;--card:#161b24}
*{box-sizing:border-box}body{margin:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:radial-gradient(1200px 600px at 10% -10%,#1a2740 0%,transparent 55%),var(--bg);color:var(--ink);line-height:1.45}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
.crumbs{font-size:13px;color:var(--muted);margin-bottom:14px}.crumbs a{color:#9ec1ff;text-decoration:none}.crumbs a:hover{text-decoration:underline}
h1{margin:0 0 6px;font-size:24px;letter-spacing:-.02em}.meta{color:var(--muted);font-size:13px}
.lead{background:#141a24;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:16px 0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.card header{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:8px}
.card h2{margin:0;font-size:15px}.dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px;background:var(--muted)}
.card.green .dot{background:var(--green)}.card.red .dot{background:var(--red)}.card.yellow .dot{background:var(--yellow)}
.pill{font-size:11px;border-radius:999px;padding:2px 8px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.pill.green{color:#9af0c4;border-color:#24553d;background:#12251c}.pill.red{color:#ffb4b4;border-color:#5a2a2a;background:#2a1515}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0;font-size:13px}.lbl{color:var(--muted);font-size:11px}.val{font-weight:600}
.issue,.next{font-size:13px;color:#c9d4e5;margin:6px 0}h3{margin:26px 0 10px;font-size:14px;color:#cfe0ff}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:820px}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#141a24;color:#a9bdd8;position:sticky;top:0}footer{margin-top:28px;color:var(--muted);font-size:12px}
code{background:#0f131a;border:1px solid var(--line);padding:1px 5px;border-radius:5px}a.cardlink{color:inherit;text-decoration:none}a.cardlink:hover .card{border-color:#3a5070}
.daynav{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 0}.daynav a{color:#9ec1ff;font-size:13px}
"""

def load_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def page(title, crumbs, body):
    crumb_html = " / ".join(
        (f'<a href="{href}">{esc(label)}</a>' if href else esc(label))
        for label, href in crumbs
    )
    return f"""<!DOCTYPE html>
<html lang=\"en\"><head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><main class=\"wrap\"><nav class=\"crumbs\">{crumb_html}</nav>
{body}
<footer>Source: append-only <code>data/*.jsonl</code>. Rebuild with <code>python3 scripts/build_viewer.py</code>. Costs TBD (never invent). Google Sheets is not the daily source of truth.</footer>
</main></body></html>"""

def main():
    hist = load_jsonl(DATA / "project-daily.jsonl")
    cos = load_jsonl(DATA / "cos-daily.jsonl")
    latest_path = DATA / "projects-latest.json"
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else []

    dates = sorted({r["date"] for r in hist}, reverse=True)
    if not dates:
        raise SystemExit("no dates in project-daily.jsonl")
    newest = dates[0]

    by_date = defaultdict(list)
    by_proj = defaultdict(list)
    for r in hist:
        by_date[r["date"]].append(r)
        by_proj[bare(r["project"])].append(r)

    # normalize project order from newest day
    order = [bare(r["project"]) for r in by_date[newest]]
    for d in by_date:
        by_date[d].sort(key=lambda r: order.index(bare(r["project"])) if bare(r["project"]) in order else 99)

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "days").mkdir(exist_ok=True)
    (DOCS / "projects").mkdir(exist_ok=True)
    (DOCS / "data").mkdir(exist_ok=True)

    # raw exports
    payload = {
        "latest_date": newest,
        "projects": latest or by_date[newest],
        "history": hist,
        "cos_history": cos,
    }
    (DOCS / "data" / "latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    with (DOCS / "data" / "dashboard.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Project", "Health", "Revenue", "Costs", "Users", "Top issue", "Next move"])
        for d in dates:
            for r in by_date[d]:
                w.writerow([r.get("date"), r.get("project"), r.get("health"), r.get("revenue", 0), r.get("costs"), r.get("users"), r.get("top"), r.get("next")])

    def cos_for(day):
        for c in cos:
            if c.get("date") == day:
                return c
        return {}

    def cards_html(rows):
        out = []
        for r in rows:
            hc = health_class(r.get("health", ""))
            s = slug(r.get("project", ""))
            out.append(f"""<a class=\"cardlink\" href=\"../../projects/{s}/index.html\"><article class=\"card {hc}\">
<header><h2><span class=\"dot\"></span>{esc(r.get('project'))}</h2><span class=\"pill {hc}\">{esc(r.get('health'))}</span></header>
<div class=\"kpis\"><div><div class=\"lbl\">Revenue</div><div class=\"val\">${esc(r.get('revenue',0))}</div></div>
<div><div class=\"lbl\">Costs</div><div class=\"val\">{esc(r.get('costs','TBD'))}</div></div>
<div><div class=\"lbl\">Users</div><div class=\"val\">{esc(r.get('users'))}</div></div></div>
<p class=\"issue\"><strong>Top</strong> {esc(r.get('top'))}</p>
<p class=\"next\"><strong>Next</strong> {esc(r.get('next'))}</p>
</article></a>""")
        return "\n".join(out)

    def table_rows(rows):
        trs = []
        for r in rows:
            hc = health_class(r.get("health", ""))
            trs.append(f"<tr><td>{esc(r.get('date'))}</td><td>{esc(r.get('project'))}</td><td><span class='pill {hc}'>{esc(r.get('health'))}</span></td><td>{esc(r.get('revenue',0))}</td><td>{esc(r.get('costs'))}</td><td>{esc(r.get('users'))}</td><td>{esc(r.get('top'))}</td><td>{esc(r.get('next'))}</td></tr>")
        return "\n".join(trs)

    # day pages
    for i, d in enumerate(dates):
        c = cos_for(d)
        m = c.get("metrics", {})
        prev_link = f"<a href=\"../{dates[i+1]}/index.html\">← {dates[i+1]}</a>" if i + 1 < len(dates) else ""
        next_link = f"<a href=\"../{dates[i-1]}/index.html\">{dates[i-1]} →</a>" if i - 1 >= 0 else ""
        # card links from day page are ../../projects relative from days/YYYY/ - wait days/YYYY-MM-DD/ so projects is ../../projects - correct for cards_html which uses ../../projects - but cards_html is shared. From day page path docs/days/D/ index, projects is ../../projects. Good.
        # From index at docs/, need different relative paths - build cards separately for index.

        body = f"""<h1>Portfolio · {esc(d)}</h1>
<div class=\"meta\">Asia/Bangkok · JSONL-backed daily glance</div>
<section class=\"lead\"><strong>CoS score {esc(c.get('cos_score','—'))}</strong>
 · Open {esc(m.get('open_count','—'))}
 · Waiting {esc(m.get('waiting_count','—'))}
 · Done {esc(m.get('done_count','—'))}
 · Skipped {esc(m.get('skipped_count','—'))}
 · Pending Roy {esc(m.get('pending_roy_decision','—'))}
<div class=\"daynav\">{prev_link} {next_link} <a href=\"../../index.html\">Latest</a></div>
</section>
<section class=\"grid\">{cards_html(by_date[d])}</section>
<h3>Dashboard · {esc(d)}</h3>
<div class=\"table-wrap\"><table><thead><tr><th>Date</th><th>Project</th><th>Health</th><th>Rev</th><th>Costs</th><th>Users</th><th>Top</th><th>Next</th></tr></thead>
<tbody>{table_rows(by_date[d])}</tbody></table></div>
<h3>All history</h3>
<div class=\"table-wrap\"><table><thead><tr><th>Date</th><th>Project</th><th>Health</th><th>Rev</th><th>Costs</th><th>Users</th><th>Top</th><th>Next</th></tr></thead>
<tbody>{table_rows([r for dd in dates for r in by_date[dd]])}</tbody></table></div>
"""
        day_dir = DOCS / "days" / d
        day_dir.mkdir(parents=True, exist_ok=True)
        (day_dir / "index.html").write_text(page(
            f"Portfolio · {d}",
            [("Portfolio", "../../index.html"), (d, None)],
            body,
        ))

    # project pages
    for pname, rows in by_proj.items():
        rows = sorted(rows, key=lambda r: r.get("date", ""), reverse=True)
        s = slug(rows[0]["project"])
        latest_row = rows[0]
        hc = health_class(latest_row.get("health", ""))
        body = f"""<h1>{esc(latest_row.get('project'))}</h1>
<div class=\"meta\">Latest {esc(latest_row.get('date'))}</div>
<section class=\"lead\"><span class=\"pill {hc}\">{esc(latest_row.get('health'))}</span>
 · Rev ${esc(latest_row.get('revenue',0))} · Costs {esc(latest_row.get('costs'))} · {esc(latest_row.get('users'))}
<p class=\"issue\"><strong>Top</strong> {esc(latest_row.get('top'))}</p>
<p class=\"next\"><strong>Next</strong> {esc(latest_row.get('next'))}</p>
</section>
<h3>History</h3>
<div class=\"table-wrap\"><table><thead><tr><th>Date</th><th>Health</th><th>Rev</th><th>Users</th><th>Top</th><th>Next</th></tr></thead><tbody>
{''.join(f"<tr><td>{esc(r.get('date'))}</td><td><span class='pill {health_class(r.get('health'))}'>{esc(r.get('health'))}</span></td><td>{esc(r.get('revenue',0))}</td><td>{esc(r.get('users'))}</td><td>{esc(r.get('top'))}</td><td>{esc(r.get('next'))}</td></tr>" for r in rows)}
</tbody></table></div>
"""
        pdir = DOCS / "projects" / s
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "index.html").write_text(page(
            bare(latest_row.get("project")),
            [("Portfolio", "../../index.html"), (bare(latest_row.get("project")), None)],
            body,
        ))

    # index = latest, with paths relative to docs/
    def cards_index(rows):
        out = []
        for r in rows:
            hc = health_class(r.get("health", ""))
            s = slug(r.get("project", ""))
            out.append(f"""<a class=\"cardlink\" href=\"projects/{s}/index.html\"><article class=\"card {hc}\">
<header><h2><span class=\"dot\"></span>{esc(r.get('project'))}</h2><span class=\"pill {hc}\">{esc(r.get('health'))}</span></header>
<div class=\"kpis\"><div><div class=\"lbl\">Revenue</div><div class=\"val\">${esc(r.get('revenue',0))}</div></div>
<div><div class=\"lbl\">Costs</div><div class=\"val\">{esc(r.get('costs','TBD'))}</div></div>
<div><div class=\"lbl\">Users</div><div class=\"val\">{esc(r.get('users'))}</div></div></div>
<p class=\"issue\"><strong>Top</strong> {esc(r.get('top'))}</p>
<p class=\"next\"><strong>Next</strong> {esc(r.get('next'))}</p>
</article></a>""")
        return "\n".join(out)

    c = cos_for(newest)
    m = c.get("metrics", {})
    day_links = " · ".join(f"<a href=\"days/{d}/index.html\">{d}</a>" for d in dates)
    body = f"""<h1>Techguyver Portfolio KPIs</h1>
<div class=\"meta\">Latest {esc(newest)} · Asia/Bangkok · JSONL → static site</div>
<section class=\"lead\"><strong>CoS score {esc(c.get('cos_score','—'))}</strong>
 · Open {esc(m.get('open_count','—'))}
 · Waiting {esc(m.get('waiting_count','—'))}
 · Done {esc(m.get('done_count','—'))}
 · Skipped {esc(m.get('skipped_count','—'))}
 · Pending Roy {esc(m.get('pending_roy_decision','—'))}
<div class=\"daynav\">Days: {day_links}</div>
</section>
<section class=\"grid\">{cards_index(by_date[newest])}</section>
<h3>Dashboard history</h3>
<div class=\"table-wrap\"><table><thead><tr><th>Date</th><th>Project</th><th>Health</th><th>Rev</th><th>Costs</th><th>Users</th><th>Top</th><th>Next</th></tr></thead>
<tbody>{table_rows([r for dd in dates for r in by_date[dd]])}</tbody></table></div>
"""
    (DOCS / "index.html").write_text(page(
        "Techguyver Portfolio KPIs",
        [("Portfolio", None)],
        body,
    ))
    print(f"built docs for {len(dates)} days, latest={newest}")

if __name__ == "__main__":
    main()
