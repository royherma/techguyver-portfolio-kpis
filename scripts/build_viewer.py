#!/usr/bin/env python3
"""Build a dense, Sheets-like static portfolio KPI viewer from JSONL ledgers."""
from __future__ import annotations
import csv, json, re, html
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA, DOCS = ROOT / "data", ROOT / "docs"

PROJECTS_ORDER = [
    "Mighty Mouse",
    "Creators of Today",
    "Cut Jam",
    "Robots HQ",
    "Techno Optimists",
]
SHORT = {
    "Mighty Mouse": "MM",
    "Creators of Today": "COT",
    "Cut Jam": "CJ",
    "Robots HQ": "RHQ",
    "Techno Optimists": "TO",
}

def esc(s):
    return html.escape(str(s if s is not None else ""))

def bare(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", str(name), flags=re.UNICODE).strip()
    for p in PROJECTS_ORDER:
        if p.lower() in s.lower() or s.lower() in p.lower():
            return p
    return s

def slug(name: str) -> str:
    return re.sub(r"-+", "-", bare(name).lower().replace(" ", "-")) or "project"

def health_key(h: str) -> str:
    u = str(h).upper()
    if "RED" in u: return "RED"
    if "YELLOW" in u or "AMBER" in u: return "YELLOW"
    return "GREEN"

def health_class(h: str) -> str:
    return health_key(h).lower()

def load_jsonl(path: Path):
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows

CSS = r"""
:root{
  --bg:#0f1115; --panel:#161a22; --ink:#eef2f8; --muted:#8b98a8;
  --line:#2a3342; --green:#22c55e; --red:#ef4444; --yellow:#eab308;
  --blue:#3b82f6; --chip:#1c2330; --head:#12161e;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background:var(--bg); color:var(--ink); font-size:13px; line-height:1.35;
}
.wrap{max-width:1280px;margin:0 auto;padding:14px 16px 20px;min-height:100vh;display:flex;flex-direction:column;gap:10px}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap}
h1{margin:0;font-size:18px;font-weight:700;letter-spacing:-.02em}
.meta{color:var(--muted);font-size:11px;margin-top:2px}
.crumbs{font-size:11px;color:var(--muted)} .crumbs a{color:#93c5fd;text-decoration:none}
.cos{
  display:flex;gap:10px;align-items:center;flex-wrap:wrap;
  background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px;
}
.cos .score{font-size:20px;font-weight:800;color:#fff}
.cos .stat{display:flex;flex-direction:column;min-width:52px}
.cos .stat b{font-size:14px} .cos .stat span{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.tabs{display:flex;gap:4px;flex-wrap:wrap}
.tab{
  border:1px solid var(--line);background:var(--chip);color:var(--muted);
  border-radius:8px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer;
}
.tab.active,.tab:hover{color:var(--ink);border-color:#3b4a63;background:#1a2230}
.tab a{color:inherit;text-decoration:none}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.panel h2{
  margin:0;padding:7px 10px;font-size:11px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:#a8b7ca;background:var(--head);border-bottom:1px solid var(--line);
}
.grid-main{display:grid;grid-template-columns:1.1fr .9fr;gap:10px}
@media (max-width:980px){.grid-main{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse}
th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:#9aabbf;background:#141922;font-weight:700}
td{font-size:12px}
tr:last-child td{border-bottom:0}
tr:hover td{background:rgba(255,255,255,.02)}
.pill{
  display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;
  border-radius:999px;padding:2px 7px;border:1px solid var(--line);
}
.pill .d{width:6px;height:6px;border-radius:50%}
.pill.green{color:#86efac;background:#052e1a;border-color:#14532d} .pill.green .d{background:var(--green)}
.pill.red{color:#fca5a5;background:#3f0d0d;border-color:#7f1d1d} .pill.red .d{background:var(--red)}
.pill.yellow{color:#fde68a;background:#3f2e05;border-color:#854d0e} .pill.yellow .d{background:var(--yellow)}
.cell-g{color:#86efac;font-weight:700} .cell-r{color:#fca5a5;font-weight:700} .cell-y{color:#fde68a;font-weight:700}
.muted{color:var(--muted)} .tight td,.tight th{padding:5px 7px}
.matrix td:not(:first-child){text-align:center}
.kpi-num{font-variant-numeric:tabular-nums;font-weight:600}
.detail-top{font-size:11px;color:#cbd5e1;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.footer{color:var(--muted);font-size:10px;margin-top:auto}
.footer code{background:#12161e;border:1px solid var(--line);padding:1px 4px;border-radius:4px}
a.p{color:#93c5fd;text-decoration:none} a.p:hover{text-decoration:underline}
.note{padding:6px 10px;font-size:11px;color:var(--muted);border-top:1px solid var(--line)}
"""

def pill(h: str) -> str:
    c = health_class(h)
    label = health_key(h)
    return f'<span class="pill {c}"><span class="d"></span>{label}</span>'

def cell_health(h: str) -> str:
    c = health_class(h)
    return f'<span class="cell-{c[0]}">{health_key(h)}</span>'

def page(title: str, crumbs, body: str) -> str:
    crumb = " / ".join(
        (f'<a href="{href}">{esc(lab)}</a>' if href else esc(lab))
        for lab, href in crumbs
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(title)}</title><style>{CSS}</style>
</head><body><div class="wrap">
<nav class="crumbs">{crumb}</nav>
<div class="cos"><strong>Live KPI reports</strong> <a class="p" href="https://you.techguyverlabs.org/admin-analytics?tab=projects&amp;window=24h">Open authenticated portfolio</a><span class="muted">Shared API measurements · this page is a legacy snapshot, not current KPI evidence.</span></div>
{body}
<div class="footer">Source: append-only <code>data/*.jsonl</code> · rebuild <code>python3 scripts/build_viewer.py</code> · push · Pages updates. Costs TBD (never invent).</div>
</div></body></html>"""

def main():
    hist = load_jsonl(DATA / "project-daily.jsonl")
    cos = load_jsonl(DATA / "cos-daily.jsonl")
    latest = json.loads((DATA / "projects-latest.json").read_text()) if (DATA / "projects-latest.json").exists() else []

    dates = sorted({r["date"] for r in hist}, reverse=True)
    if not dates:
        raise SystemExit("no dates")
    newest = dates[0]

    by_date = defaultdict(dict)  # date -> bare -> row
    for r in hist:
        by_date[r["date"]][bare(r["project"])] = r

    cos_by = {c["date"]: c for c in cos}

    # project order
    order = []
    for p in PROJECTS_ORDER:
        if any(p in by_date[d] for d in dates):
            order.append(p)
    for d in dates:
        for p in by_date[d]:
            if p not in order:
                order.append(p)

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "days").mkdir(exist_ok=True)
    (DOCS / "projects").mkdir(exist_ok=True)
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("")

    # exports
    payload = {"latest_date": newest, "projects": latest, "history": hist, "cos_history": cos}
    (DOCS / "data" / "latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    with (DOCS / "data" / "dashboard.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Project", "Health", "Revenue", "Costs", "Users", "Top issue", "Next move"])
        for d in dates:
            for p in order:
                r = by_date[d].get(p)
                if not r: continue
                w.writerow([d, r.get("project"), health_key(r.get("health")), r.get("revenue", 0), r.get("costs"), r.get("users"), r.get("top"), r.get("next")])

    def cos_strip(day: str) -> str:
        c = cos_by.get(day, {})
        m = c.get("metrics", {})
        return f"""<div class="cos">
  <div><div class="muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.05em">CoS</div><div class="score">{esc(c.get('cos_score','—'))}</div></div>
  <div class="stat"><span>Open</span><b>{esc(m.get('open_count','—'))}</b></div>
  <div class="stat"><span>Wait</span><b>{esc(m.get('waiting_count','—'))}</b></div>
  <div class="stat"><span>Done</span><b>{esc(m.get('done_count','—'))}</b></div>
  <div class="stat"><span>Skip</span><b>{esc(m.get('skipped_count','—'))}</b></div>
  <div class="stat"><span>Roy</span><b>{esc(m.get('pending_roy_decision','—'))}</b></div>
  <div class="stat"><span>Δ</span><b>{esc(c.get('delta_vs_yesterday',0))}</b></div>
</div>"""

    def day_tabs(active: str, prefix: str = "") -> str:
        bits = []
        for d in dates:
            cls = "tab active" if d == active else "tab"
            href = f"{prefix}days/{d}/index.html" if d != newest or prefix == "" else f"{prefix}index.html"
            # always link day pages for consistency except newest also = index
            if d == newest and prefix == "":
                href = "index.html"
            elif prefix == "":
                href = f"days/{d}/index.html"
            else:
                href = f"../days/{d}/index.html" if "projects" in prefix else f"{d}/index.html"
            bits.append(f'<span class="{cls}"><a href="{href}">{d}</a></span>')
        return '<div class="tabs">' + "".join(bits) + "</div>"

    def matrix_html(link_prefix: str = "") -> str:
        head = "".join(f"<th title=\"{esc(p)}\"><a class=\"p\" href=\"{link_prefix}projects/{slug(p)}/index.html\">{esc(SHORT.get(p,p[:3]))}</a></th>" for p in order)
        head += "<th>CoS</th>"
        rows = []
        for d in dates:
            cells = [f'<td><a class="p" href="{link_prefix}days/{d}/index.html">{d}</a></td>']
            for p in order:
                r = by_date[d].get(p)
                cells.append(f"<td>{cell_health(r.get('health')) if r else '—'}</td>")
            c = cos_by.get(d, {})
            cells.append(f'<td class="kpi-num">{esc(c.get("cos_score","—"))}</td>')
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return f"""<div class="panel"><h2>Health over time</h2>
<table class="tight matrix"><thead><tr><th>Date</th>{head}</tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<div class="note">GREEN/RED by day · click project code for history · click date for that day’s sheet</div></div>"""

    def detail_table(day: str, link_prefix: str = "") -> str:
        rows = []
        for p in order:
            r = by_date[day].get(p)
            if not r: continue
            top = esc(r.get("top"))
            nxt = esc(r.get("next"))
            rows.append(
                "<tr>"
                f'<td><a class="p" href="{link_prefix}projects/{slug(p)}/index.html">{esc(r.get("project"))}</a></td>'
                f"<td>{pill(r.get('health'))}</td>"
                f'<td class="kpi-num">${esc(r.get("revenue",0))}</td>'
                f"<td>{esc(r.get('costs','TBD'))}</td>"
                f"<td>{esc(r.get('users'))}</td>"
                f'<td><div class="detail-top" title="{top}">{top}</div></td>'
                f'<td><div class="detail-top" title="{nxt}">{nxt}</div></td>'
                "</tr>"
            )
        return f"""<div class="panel"><h2>Day detail · {esc(day)}</h2>
<table class="tight"><thead><tr>
<th>Project</th><th>Health</th><th>Rev</th><th>Costs</th><th>Users / metric</th><th>Top issue</th><th>Next move</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""

    # ---- index (latest, one-pager) ----
    body = f"""
<div class="top">
  <div>
    <h1>Techguyver Portfolio KPIs</h1>
    <div class="meta">Latest {esc(newest)} · Asia/Bangkok · JSONL ledger → static sheet</div>
  </div>
  {cos_strip(newest)}
</div>
{day_tabs(newest)}
<div class="grid-main">
  {matrix_html()}
  {detail_table(newest)}
</div>
"""
    (DOCS / "index.html").write_text(page(
        "Techguyver Portfolio KPIs",
        [("Portfolio", None)],
        body,
    ))

    # ---- day pages ----
    for d in dates:
        day_dir = DOCS / "days" / d
        day_dir.mkdir(parents=True, exist_ok=True)
        # tabs from days/YYYY
        tabs = []
        for dd in dates:
            cls = "tab active" if dd == d else "tab"
            href = "index.html" if dd == d else f"../{dd}/index.html"
            if dd == newest:
                href_home = "../../index.html"
            else:
                href_home = None
            tabs.append(f'<span class="{cls}"><a href="{href}">{dd}</a></span>')
        tabs_html = '<div class="tabs">' + "".join(tabs) + f'<span class="tab"><a href="../../index.html">Latest</a></span></div>'
        body = f"""
<div class="top">
  <div>
    <h1>Portfolio · {esc(d)}</h1>
    <div class="meta">Day folder · same sheet layout</div>
  </div>
  {cos_strip(d)}
</div>
{tabs_html}
<div class="grid-main">
  {matrix_html('../../')}
  {detail_table(d, '../../')}
</div>
"""
        (day_dir / "index.html").write_text(page(
            f"Portfolio · {d}",
            [("Portfolio", "../../index.html"), (d, None)],
            body,
        ))

    # ---- project pages ----
    by_proj = defaultdict(list)
    for r in hist:
        by_proj[bare(r["project"])].append(r)
    for p, rows in by_proj.items():
        rows = sorted(rows, key=lambda x: x.get("date", ""), reverse=True)
        s = slug(p)
        latest_row = rows[0]
        tr = "".join(
            f"<tr><td>{esc(r.get('date'))}</td><td>{pill(r.get('health'))}</td>"
            f"<td class='kpi-num'>${esc(r.get('revenue',0))}</td><td>{esc(r.get('users'))}</td>"
            f"<td>{esc(r.get('top'))}</td><td>{esc(r.get('next'))}</td></tr>"
            for r in rows
        )
        body = f"""
<div class="top">
  <div>
    <h1>{esc(latest_row.get('project'))}</h1>
    <div class="meta">Project history · latest {esc(latest_row.get('date'))}</div>
  </div>
  {pill(latest_row.get('health'))}
</div>
<div class="panel"><h2>KPI history</h2>
<table class="tight"><thead><tr><th>Date</th><th>Health</th><th>Rev</th><th>Users</th><th>Top issue</th><th>Next</th></tr></thead>
<tbody>{tr}</tbody></table></div>
"""
        pdir = DOCS / "projects" / s
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "index.html").write_text(page(
            p,
            [("Portfolio", "../../index.html"), (p, None)],
            body,
        ))

    print(f"built one-pager · latest={newest} · days={len(dates)} · projects={len(order)}")

if __name__ == "__main__":
    main()
