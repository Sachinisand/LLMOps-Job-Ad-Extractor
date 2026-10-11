"""
Builds docs/demo.svg: a short animated clip of job ads going into the service and
the model's JSON answer coming out, each field checked against the label.
Pure SVG + SMIL animation, so it plays on GitHub like a video and stays sharp.

The content is NOT invented: docs/demo_example.json holds real answers copied
from the LLM evaluation run on GitHub Actions (job ad, model answer, correct
label, run link). The waiting time is that run's median latency, shown sped up.

Run:  python scripts/make_demo_svg.py
"""

import json
import sys
import textwrap
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jobad_llmops.metrics import SCORED_FIELDS, field_correct  # noqa: E402

W, H = 960, 540
SCENE = 11.0  # seconds per job ad
CSS = """
.bg{fill:#0d0d0d}.panel{fill:#1a1a19;stroke:#383835}
.h{font:600 15px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#fff}
.sub{font:15px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#c3c2b7}
.blue{font:600 15px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#3987e5}
.small{font:13px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#898781}
.mono{font:14px ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;fill:#c3c2b7}
.json{font:14px ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;fill:#fff}
.clock{font:600 14px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#3987e5}
.ok{font:700 17px system-ui,sans-serif;fill:#0ca30c}.bad{font:700 17px system-ui,sans-serif;fill:#e66767}
.ratio{font:13px ui-monospace,Menlo,Consolas,monospace;fill:#898781}
"""


def show(start, end, total, fade=0.12):
    """Opacity 0 → 1 at `start`, back to 0 at `end` (seconds within a loop of `total`)."""
    k = [0, max(start - fade, 0), start, end, min(end + fade, total), total]
    v = [0, 0, 1, 1, 0, 0]
    if start <= 0:
        k, v = [0, end, min(end + fade, total), total], [1, 1, 0, 0]
    keys = ";".join(f"{x / total:.4f}" for x in k)
    return (f'<animate attributeName="opacity" dur="{total}s" repeatCount="indefinite" '
            f'keyTimes="{keys}" values="{";".join(map(str, v))}"/>')


def json_lines(pred):
    keys = list(pred)
    out = [(None, "{")]
    for i, k in enumerate(keys):
        text = f'  "{k}": {json.dumps(pred[k], ensure_ascii=False)}{"," if i < len(keys) - 1 else ""}'
        out.append((k, text if len(text) <= 44 else text[:41] + "…"))
    return out + [(None, "}")]


def scene(ex, t0, total, idx):
    """All elements for one job ad, visible between t0 and t0 + SCENE."""
    end = t0 + SCENE - 0.2
    p = [f'<g opacity="0">{show(t0, end, total)}']
    lx, rx, top = 20, 492, 72

    # job ad typed line by line (each line revealed left to right)
    lines = []
    for para in ex["text"].strip().split("\n"):
        lines += textwrap.wrap(para, 46) or [""]
    per_line = 2.6 / max(len(lines), 1)
    for i, line in enumerate(lines):
        s, e = t0 + i * per_line, t0 + (i + 1) * per_line
        cid = f"c{idx}_{i}"
        y = top + 60 + i * 21
        p.append(f'<clipPath id="{cid}"><rect x="{lx + 16}" y="{y - 15}" height="20" width="0">'
                 f'<animate attributeName="width" dur="{total}s" repeatCount="indefinite" '
                 f'keyTimes="0;{s / total:.4f};{e / total:.4f};1" values="0;0;420;420"/></rect></clipPath>'
                 f'<text class="mono" x="{lx + 18}" y="{y}" clip-path="url(#{cid})">{escape(line)}</text>')

    # waiting for the model: a sped-up clock
    w0, w1 = t0 + 2.9, t0 + 4.6
    p.append(f'<g opacity="0">{show(w0, w1, total, 0.05)}'
             f'<text class="sub" x="{rx + 18}" y="{top + 66}">{ex["model"]} is reading the ad …</text>'
             f'<text class="small" x="{rx + 18}" y="{top + 118}">(sped up in this clip)</text></g>')
    steps = 8
    for i in range(steps + 1):
        s = w0 + (w1 - w0) * i / (steps + 1)
        e = w0 + (w1 - w0) * (i + 1) / (steps + 1)
        p.append(f'<text class="clock" x="{rx + 18}" y="{top + 94}" opacity="0">'
                 f'{show(s, e if i < steps else w1, total, 0.01)}{ex["latency_s"] * i / steps:4.1f} s</text>')

    # answer appears line by line, with ✓ / ✗ against the label
    a0 = w1 + 0.1
    for i, (key, text) in enumerate(json_lines(ex["prediction"])):
        y = top + 60 + i * 24
        s = a0 + i * 0.22
        mark = ""
        if key in SCORED_FIELDS:
            ok = field_correct(key, ex["prediction"][key], ex["label"][key])
            mark = f'<text class="{"ok" if ok else "bad"}" x="{rx + 420}" y="{y + 1}">{"✓" if ok else "✗"}</text>'
        elif key == "skills":   # skills are scored by overlap, not right/wrong
            hit = len(set(ex["prediction"]["skills"]) & set(ex["label"]["skills"]))
            mark = f'<text class="ratio" x="{rx + 404}" y="{y}">{hit}/{len(ex["label"]["skills"])}</text>'
        p.append(f'<g opacity="0">{show(s, end, total, 0.08)}'
                 f'<text class="json" x="{rx + 18}" y="{y}" xml:space="preserve">{escape(text)}</text>{mark}</g>')

    # result line
    n_ok = sum(field_correct(f, ex["prediction"][f], ex["label"][f]) for f in SCORED_FIELDS)
    f0 = a0 + len(json_lines(ex["prediction"])) * 0.22 + 0.2
    p.append(f'<g opacity="0">{show(f0, end, total)}'
             f'<text class="h" x="20" y="496">{n_ok} of {len(SCORED_FIELDS)} fields correct against the '
             f'hand-written label  ·  median latency {ex["latency_s"]:.1f} s on a CPU runner</text></g>')
    p.append(f'<text class="small" x="20" y="522">Real output from the LLM evaluation run on GitHub Actions '
             f'({ex["example_id"]}, held-out set)  ·  ad {idx + 1} of 2</text>')
    p.append("</g>")
    return "".join(p)


def main():
    data = json.loads((ROOT / "docs" / "demo_example.json").read_text(encoding="utf-8"))
    shown = [next(e for e in data["examples"] if e["example_id"] == i) for i in data["show"]]
    total = SCENE * len(shown)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="Demo: job ads are sent to the service and the model answer appears field by field, '
         f'each field marked right or wrong against the label"><style>{CSS}</style>',
         f'<rect class="bg" width="{W}" height="{H}" rx="14"/>',
         '<rect class="panel" x="20" y="16" width="920" height="40" rx="10"/>',
         '<text class="blue" x="38" y="41">POST /extract</text>',
         f'<text class="sub" x="160" y="41">model {data["model"]}  ·  prompt {data["prompt"]}  ·  temperature 0</text>',
         '<rect class="panel" x="20" y="72" width="448" height="398" rx="10"/>',
         '<rect class="panel" x="492" y="72" width="448" height="398" rx="10"/>',
         '<text class="h" x="38" y="100">Job ad (input)</text>',
         '<text class="h" x="510" y="100">Model answer (validated JSON)</text>']
    for idx, ex in enumerate(shown):
        ex = {**ex, "model": data["model"], "latency_s": data["latency_p50_s"]}
        p.append(scene(ex, idx * SCENE, total, idx))
    p.append("</svg>")
    out = ROOT / "docs" / "demo.svg"
    out.write_text("\n".join(p), encoding="utf-8")
    print(f"written {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
