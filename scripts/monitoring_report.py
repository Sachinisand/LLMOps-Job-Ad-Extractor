"""
Builds a one-page HTML monitoring report from data/monitoring.db.

Shows: request volume, valid-JSON rate, latency (p50/p95 and per request),
user corrections per field, and the input-drift check against the evaluation set.

Run:  python scripts/monitoring_report.py [--out outputs/monitoring_report.html]
"""

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobad_llmops.extractor import load_config                    # noqa: E402
from jobad_llmops.monitoring import Monitor, reference_stats       # noqa: E402

CSS = """
:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--s1:#2a78d6;--border:rgba(11,11,11,.1);--good:#006300;--bad:#d03b3b;}
@media (prefers-color-scheme:dark){:root{--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--border:rgba(255,255,255,.1);--good:#0ca30c;--bad:#e66767;}}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);
font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:24px 16px 40px}h1{font-size:22px;margin:0 0 4px}
.meta{color:var(--ink2);font-size:13px}.note{color:var(--muted);font-size:12px;margin-top:4px}
.tiles{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:18px 0}
.tile,.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px 16px}
.tile .l{font-size:12px;color:var(--ink2)}.tile .v{font-size:24px;font-weight:600;margin-top:2px}
.tile .s{font-size:12px;color:var(--muted)}.ok{color:var(--good)}.alert{color:var(--bad)}
.grid{display:grid;grid-template-columns:3fr 2fr;gap:12px}h2{font-size:15px;margin:0 0 2px}
.sub{font-size:12px;color:var(--ink2);margin-bottom:8px}svg{width:100%;height:auto;display:block}
svg text{fill:var(--muted);font-size:11px}svg .v{fill:var(--ink2)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:4px}
td,th{padding:5px 8px;border-bottom:1px solid var(--grid);text-align:right}td:first-child,th:first-child{text-align:left}
th{color:var(--ink2);font-weight:600}
@media(max-width:760px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}}
"""


def latency_chart(series, w=600, h=220):
    if not series:
        return "<p class='sub'>No requests yet.</p>"
    values = [v for _, v in series]
    top = max(values) * 1.1 or 1
    m = dict(l=48, r=10, t=10, b=26)
    x = lambda i: m["l"] + (w - m["l"] - m["r"]) * (i / max(1, len(values) - 1))
    y = lambda v: m["t"] + (h - m["t"] - m["b"]) * (1 - v / top)
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Latency per request">']
    for k in range(5):
        v = top * k / 4
        parts.append(f'<line x1="{m["l"]}" x2="{w - m["r"]}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
                     f'stroke="var(--{"axis" if k == 0 else "grid"})"/>'
                     f'<text x="{m["l"] - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v:,.0f}</text>')
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="var(--s1)" stroke-width="2" stroke-linejoin="round"/>')
    parts.append(f'<text x="{m["l"]}" y="{h - 6}">request 1</text>'
                 f'<text x="{w - m["r"]}" y="{h - 6}" text-anchor="end">request {len(values)}</text></svg>')
    return "".join(parts)


def corrections_chart(counts: dict, w=380):
    if not counts:
        return "<p class='sub'>No corrections received.</p>"
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    row, label_w = 26, 120
    h = row * len(items) + 8
    top = max(counts.values())
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Corrections by field">']
    for i, (field, n) in enumerate(items):
        y0 = 4 + i * row
        bw = (w - label_w - 40) * n / top
        parts.append(f'<text x="{label_w - 8}" y="{y0 + 15}" text-anchor="end">{html.escape(field)}</text>'
                     f'<rect x="{label_w}" y="{y0 + 4}" width="{bw:.1f}" height="16" rx="4" fill="var(--s1)"/>'
                     f'<text class="v" x="{label_w + bw + 6:.1f}" y="{y0 + 16}">{n}</text>')
    parts.append("</svg>")
    return "".join(parts)


def tile(label, value, sub="", cls=""):
    return (f'<div class="tile"><div class="l">{label}</div><div class="v {cls}">{value}</div>'
            f'<div class="s">{sub}</div></div>')


def build(summary: dict, series, note: str) -> str:
    if summary.get("requests", 0) == 0:
        body = "<p>No requests logged yet. Run scripts/simulate_traffic.py or call the API first.</p>"
    else:
        d = summary["drift"]
        drift_txt = "⚠ Drift" if d["drift_detected"] else "✓ No drift"
        tiles = "".join([
            tile("Requests", f'{summary["requests"]:,}', f'{summary["first_request"][:10]} to {summary["last_request"][:10]}'),
            tile("Valid JSON", f'{summary["valid_json_rate"]:.0%}', f'retries {summary["retry_rate"]:.0%}',
                 "ok" if summary["valid_json_rate"] >= 0.95 else "alert"),
            tile("Latency p50 / p95", f'{summary["latency_p50_ms"]:,.0f} ms', f'p95 {summary["latency_p95_ms"]:,.0f} ms'),
            tile("Corrections per request", f'{summary["correction_rate"]:.2f}', "user feedback"),
            tile("Input drift", drift_txt, f'German share {d["german_share_change_pts"]:+.0f} pts, '
                                           f'length {d["length_change_pct"]:+.0f} %',
                 "alert" if d["drift_detected"] else "ok"),
        ])
        drift_rows = (f'<tr><td>Share of German ads</td><td>{summary["reference"]["german_ad_share"]:.0%}</td>'
                      f'<td>{d["german_ad_share"]:.0%}</td><td>{d["german_share_change_pts"]:+.1f} pts</td></tr>'
                      f'<tr><td>Average ad length (characters)</td><td>{summary["reference"]["avg_input_chars"]:,.0f}</td>'
                      f'<td>{d["avg_input_chars"]:,}</td><td>{d["length_change_pct"]:+.1f} %</td></tr>')
        body = f"""<div class="tiles">{tiles}</div>
<div class="grid">
 <div class="card"><h2>Latency per request</h2><div class="sub">milliseconds, in order of arrival</div>{latency_chart(series)}</div>
 <div class="card"><h2>User corrections by field</h2><div class="sub">where real users found the answer wrong</div>
 {corrections_chart(summary["corrections_by_field"])}</div>
</div>
<div class="card" style="margin-top:12px"><h2>Input drift check</h2>
<div class="sub">The most recent requests compared with the evaluation set. Alert when the German share moves by more than 20 points or the average length by more than 30 %.</div>
<table><tr><th>Measure</th><th>Evaluation set</th><th>Last {d["window"]} requests</th><th>Change</th></tr>{drift_rows}</table></div>"""
    versions = ", ".join(summary.get("versions", [])) or "–"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Job-Ad Extractor Monitoring</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>Job-Ad Extractor – Monitoring</h1><div class="meta">Model / prompt: {html.escape(versions)}</div>
<div class="note">{html.escape(note)}</div>{body}</div></body></html>"""


def main():
    config = load_config()
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(ROOT / "outputs" / "monitoring_report.html"))
    p.add_argument("--note", default="Generated from data/monitoring.db.")
    args = p.parse_args()

    ads = [json.loads(l)["text"] for l in (ROOT / "eval" / "job_ads.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    reference = reference_stats(ads)
    monitor = Monitor(str(ROOT / config["monitoring"]["db_path"]))
    summary = monitor.summary(reference, config["monitoring"].get("drift_window", 30))
    summary["reference"] = reference
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(summary, monitor.latency_series(), args.note), encoding="utf-8")
    print(f"Report written to {out}")


if __name__ == "__main__":
    main()
