"""
Draws docs/pipeline.svg: an animated diagram of one job ad moving through the
system (used at the top of the README). Pure SVG + SMIL animation, so it plays
directly on GitHub without JavaScript.

Run:  python scripts/make_pipeline_svg.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = 12.0  # seconds for one full cycle

W, H = 960, 380
BOX_W, BOX_H, TOP = 150, 78, 92
XS = [30 + i * 186 for i in range(5)]  # left edge of the five main boxes

STAGES = [
    ("Job ad", "German or English text", 0.0, 1.0),
    ("Prompt v2", "versioned file", 1.5, 2.5),
    ("Llama 3.2 3B", "via Ollama, temp 0", 3.0, 4.6),
    ("Validate", "Pydantic schema", 5.1, 6.1),
    ("Structured JSON", "8 fields", 6.6, 10.0),
]
# moving dot between box i and i+1: (start, end)
LINKS = [(1.0, 1.5), (2.5, 3.0), (4.6, 5.1), (6.1, 6.6)]
BADGES = {  # small label that appears above a box while it is active
    0: "POST /extract",
    2: "≈ 10 s on CPU",
    3: "✓ valid",
    4: "logged",
}

CSS = """
.bg{fill:#f9f9f7}.box{fill:#fcfcfb;stroke:#c3c2b7;stroke-width:1.2}
.hi{fill:none;stroke:#2a78d6;stroke-width:2.6}.hifill{fill:#2a78d6;fill-opacity:.07}
.t1{font:600 15px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#0b0b0b}
.t2{font:12px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#52514e}
.t3{font:11px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#898781}
.title{font:600 13px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#52514e;letter-spacing:.04em}
.line{stroke:#c3c2b7;stroke-width:1.5;fill:none}.dash{stroke-dasharray:4 4}
.arrow{fill:#c3c2b7}.dot{fill:#2a78d6}
.badge{fill:#2a78d6}.badgetxt{font:600 11px system-ui,-apple-system,'Segoe UI',sans-serif;fill:#fff}
.ok{fill:#006300}.chip{fill:#2a78d6;fill-opacity:.1;stroke:#2a78d6;stroke-opacity:.35}
.chiptxt{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;fill:#0b0b0b}
@media (prefers-color-scheme:dark){
.bg{fill:#0d0d0d}.box{fill:#1a1a19;stroke:#383835}.hi{stroke:#3987e5}.hifill{fill:#3987e5;fill-opacity:.12}
.t1{fill:#fff}.t2{fill:#c3c2b7}.t3,.title{fill:#898781}.line{stroke:#4a4a46}.arrow{fill:#4a4a46}
.dot,.badge{fill:#3987e5}.ok{fill:#0ca30c}.chip{fill:#3987e5;stroke:#3987e5}.chiptxt{fill:#fff}}
"""


def window(start: float, end: float, fade: float = 0.15) -> str:
    """SMIL opacity animation that is 1 between start and end, else 0."""
    k = [0, max(start - fade, 0) / T, start / T, end / T, min(end + fade, T) / T, 1]
    v = [0, 0, 1, 1, 0, 0]
    if start == 0:
        k, v = [0, end / T, min(end + fade, T) / T, 1], [1, 1, 0, 0]
    keys = ";".join(f"{x:.4f}" for x in k)
    vals = ";".join(str(x) for x in v)
    return (f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
            f'keyTimes="{keys}" values="{vals}" calcMode="linear"/>')


def move(x1, y1, x2, y2, start, end) -> str:
    """Dot that travels from (x1,y1) to (x2,y2) between start and end."""
    k = f"0;{start / T:.4f};{end / T:.4f};1"
    return (f'<circle class="dot" r="5" cx="0" cy="0" opacity="0">'
            f'<animateMotion dur="{T}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{k}" keyPoints="0;0;1;1" path="M{x1},{y1} L{x2},{y2}"/>'
            f'{window(start, end, 0.05)}</circle>')


def badge(cx, y, text, start, end, cls="badge") -> str:
    w = 8 + 6.6 * len(text)
    return (f'<g opacity="0">{window(start, end)}'
            f'<rect class="{cls}" x="{cx - w / 2:.1f}" y="{y}" width="{w:.1f}" height="20" rx="10"/>'
            f'<text class="badgetxt" x="{cx}" y="{y + 14}" text-anchor="middle">{text}</text></g>')


def main():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'role="img" aria-label="Animated pipeline: job ad, prompt, LLM, schema validation, JSON result, '
         f'with monitoring and evaluation"><style>{CSS}</style>',
         f'<rect class="bg" width="{W}" height="{H}" rx="14"/>',
         '<text class="title" x="30" y="40">ONE REQUEST, STEP BY STEP</text>',
         '<text class="t3" x="30" y="60">FastAPI service in Docker · every request is validated, timed and logged</text>']
    mid = TOP + BOX_H / 2

    # connectors with arrow heads
    for i in range(4):
        x1, x2 = XS[i] + BOX_W, XS[i + 1]
        p.append(f'<line class="line" x1="{x1}" y1="{mid}" x2="{x2 - 6}" y2="{mid}"/>'
                 f'<path class="arrow" d="M{x2},{mid} l-7,-4 v8 z"/>')

    # retry loop: from Validate back to the LLM
    lx1, lx2 = XS[3] + BOX_W / 2, XS[2] + BOX_W / 2
    p.append(f'<path class="line dash" d="M{lx1},{TOP} C{lx1},{TOP - 30} {lx2},{TOP - 30} {lx2},{TOP - 6}"/>'
             f'<path class="arrow" d="M{lx2},{TOP} l-4,-7 h8 z"/>'
             f'<text class="t3" x="{(lx1 + lx2) / 2}" y="{TOP - 26}" text-anchor="middle">invalid → retry once</text>')

    # main boxes with highlight overlay
    for i, (name, sub, s, e) in enumerate(STAGES):
        x = XS[i]
        p.append(f'<rect class="box" x="{x}" y="{TOP}" width="{BOX_W}" height="{BOX_H}" rx="10"/>'
                 f'<g opacity="0">{window(s, e)}'
                 f'<rect class="hifill" x="{x}" y="{TOP}" width="{BOX_W}" height="{BOX_H}" rx="10"/>'
                 f'<rect class="hi" x="{x}" y="{TOP}" width="{BOX_W}" height="{BOX_H}" rx="10"/></g>'
                 f'<text class="t1" x="{x + BOX_W / 2}" y="{TOP + 34}" text-anchor="middle">{name}</text>'
                 f'<text class="t2" x="{x + BOX_W / 2}" y="{TOP + 54}" text-anchor="middle">{sub}</text>')
        if i in BADGES and i != 4:
            p.append(badge(x + BOX_W / 2, TOP + BOX_H + 10, BADGES[i], s, e, "ok" if i == 3 else "badge"))

    for i, (s, e) in enumerate(LINKS):
        p.append(move(XS[i] + BOX_W, mid, XS[i + 1] - 4, mid, s, e))

    # field chips appearing below the result box one after another
    chips = ["job_title", "seniority", "skills", "german_level"]
    cx = XS[4] + BOX_W / 2
    for j, chip in enumerate(chips):
        s = 6.8 + j * 0.25
        y = TOP + BOX_H + 10 + j * 22
        w = 7.2 * len(chip) + 16
        p.append(f'<g opacity="0">{window(s, 10.0)}'
                 f'<rect class="chip" x="{cx - w / 2:.1f}" y="{y}" width="{w:.1f}" height="19" rx="5"/>'
                 f'<text class="chiptxt" x="{cx}" y="{y + 13.5}" text-anchor="middle">{chip}</text></g>')

    # bottom row: evaluation (offline) and monitoring (live)
    by, bh = 282, 78
    ex, ew = XS[1], XS[2] + BOX_W - XS[1]
    p.append(f'<rect class="box" x="{ex}" y="{by}" width="{ew}" height="{bh}" rx="10"/>'
             f'<text class="t1" x="{ex + 18}" y="{by + 30}">Evaluation before release</text>'
             f'<text class="t2" x="{ex + 18}" y="{by + 52}">42 labelled ads · accuracy, skills F1, latency</text>'
             f'<text class="t3" x="{ex + 18}" y="{by + 68}">quality gate decides which model + prompt may run</text>')
    for xx in (XS[1] + BOX_W / 2, XS[2] + BOX_W / 2):
        p.append(f'<line class="line dash" x1="{xx}" y1="{by}" x2="{xx}" y2="{TOP + BOX_H + 6}"/>'
                 f'<path class="arrow" d="M{xx},{TOP + BOX_H} l-4,7 h8 z"/>')

    mx, mw = XS[3], XS[4] + BOX_W - XS[3]
    p.append(f'<rect class="box" x="{mx}" y="{by}" width="{mw}" height="{bh}" rx="10"/>'
             f'<g opacity="0">{window(10.0, 11.6)}'
             f'<rect class="hifill" x="{mx}" y="{by}" width="{mw}" height="{bh}" rx="10"/>'
             f'<rect class="hi" x="{mx}" y="{by}" width="{mw}" height="{bh}" rx="10"/></g>'
             f'<text class="t1" x="{mx + 18}" y="{by + 30}">Monitoring (SQLite)</text>'
             f'<text class="t2" x="{mx + 18}" y="{by + 52}">latency · valid JSON · input drift</text>'
             f'<text class="t3" x="{mx + 18}" y="{by + 68}">+ user corrections via /feedback</text>')
    # path from Validate down to monitoring (every request is logged, valid or not)
    vx = XS[3] + 40
    p.append(f'<line class="line" x1="{vx}" y1="{TOP + BOX_H}" x2="{vx}" y2="{by - 6}"/>'
             f'<path class="arrow" d="M{vx},{by} l-4,-7 h8 z"/>')
    p.append(move(vx, TOP + BOX_H + 4, vx, by - 4, 9.5, 10.0))
    p.append(badge(mx + mw - 50, by - 12, "logged", 10.0, 11.6))

    p.append("</svg>")
    out = ROOT / "docs" / "pipeline.svg"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(p), encoding="utf-8")
    print(f"written {out}")


if __name__ == "__main__":
    main()
