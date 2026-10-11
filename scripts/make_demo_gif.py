"""
Builds docs/demo.gif: a short animation of one job ad going into the service and
the model's JSON answer coming out, with each field checked against the label.

The content is NOT invented: docs/demo_example.json holds one real answer from
the LLM evaluation run on GitHub Actions (job ad, model answer, correct label,
latency, run link). The model's waiting time is shown sped up.

Run:  python scripts/make_demo_gif.py      (needs Pillow; uses DejaVu/Inter fonts if present)
"""

import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jobad_llmops.metrics import SCORED_FIELDS, field_correct  # noqa: E402

W, H = 960, 540
BG, PANEL, BORDER = (13, 13, 13), (26, 26, 25), (56, 56, 53)
INK, INK2, MUTED = (255, 255, 255), (195, 194, 183), (137, 135, 129)
BLUE, GOOD, BAD = (57, 135, 229), (12, 163, 12), (230, 103, 103)


def font(names, size):
    for n in names:
        for d in ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/dejavu"]:
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


SANS = font(["Inter-Regular.otf", "DejaVuSans.ttf"], 15)
SANS_B = font(["Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"], 15)
SMALL = font(["Inter-Regular.otf", "DejaVuSans.ttf"], 13)
MONO = font(["DejaVuSansMono.ttf"], 14)
MARK = font(["DejaVuSans-Bold.ttf", "Inter-SemiBold.otf"], 18)


def json_lines(pred):
    lines = ["{"]
    keys = list(pred)
    for i, k in enumerate(keys):
        comma = "," if i < len(keys) - 1 else ""
        lines.append((k, f'  "{k}": {json.dumps(pred[k], ensure_ascii=False)}{comma}'))
    lines.append("}")
    return lines


def frame(ex, typed_words, think_s, shown_lines, final):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # header
    d.rounded_rectangle([20, 16, W - 20, 56], 10, fill=PANEL, outline=BORDER)
    d.text((38, 27), "POST /extract", font=SANS_B, fill=BLUE)
    d.text((160, 27), f"model {ex['model']}  ·  prompt {ex['prompt']}  ·  temperature 0",
           font=SANS, fill=INK2)
    # panels
    lx, rx, top, bot = 20, 492, 72, 470
    for x in (lx, rx):
        d.rounded_rectangle([x, top, x + 448, bot], 10, fill=PANEL, outline=BORDER)
    d.text((lx + 18, top + 14), "Job ad (input)", font=SANS_B, fill=INK)
    d.text((rx + 18, top + 14), "Model answer (validated JSON)", font=SANS_B, fill=INK)

    # typed job ad
    words = ex["text"].split()
    shown = " ".join(words[:typed_words])
    y = top + 46
    for para in shown.split("\n"):
        for line in textwrap.wrap(para, 46) or [""]:
            d.text((lx + 18, y), line, font=MONO, fill=INK2)
            y += 21
    if typed_words < len(words):
        d.rectangle([lx + 18, y + 2, lx + 26, y + 17], fill=BLUE)

    # thinking / answer
    if think_s is not None and shown_lines == 0:
        dots = "." * (int(think_s * 3) % 4)
        d.text((rx + 18, top + 52), f"{ex['model']} is reading the ad{dots}", font=SANS, fill=INK2)
        d.text((rx + 18, top + 78), f"{think_s:4.1f} s", font=MONO, fill=BLUE)
        d.text((rx + 18, top + 104), "(sped up in this clip)", font=SMALL, fill=MUTED)
    lines = json_lines(ex["prediction"])
    y = top + 46
    for item in lines[:shown_lines]:
        key, text = item if isinstance(item, tuple) else (None, item)
        if len(text) > 44:
            text = text[:41] + "…"
        d.text((rx + 18, y), text, font=MONO, fill=INK)
        if key in SCORED_FIELDS:
            ok = field_correct(key, ex["prediction"][key], ex["label"][key])
            d.text((rx + 418, y - 2), "✓" if ok else "✗", font=MARK, fill=GOOD if ok else BAD)
        elif key == "skills":   # skills are scored by overlap, not right/wrong
            hit = len(set(ex["prediction"]["skills"]) & set(ex["label"]["skills"]))
            d.text((rx + 404, y), f"{hit}/{len(ex['label']['skills'])}", font=MONO, fill=MUTED)
        y += 24

    # footer
    if final:
        n_ok = sum(field_correct(f, ex["prediction"][f], ex["label"][f]) for f in SCORED_FIELDS)
        d.text((20, 484), f"{n_ok} of {len(SCORED_FIELDS)} fields correct against the hand-written label   ·   "
                          f"real latency {ex['latency_s']:.1f} s on a CPU runner", font=SANS, fill=INK)
    d.text((20, 510), f"Real output from the LLM evaluation run on GitHub Actions ({ex['example_id']}, held-out set)",
           font=SMALL, fill=MUTED)
    return im


def main():
    ex = json.loads((ROOT / "docs" / "demo_example.json").read_text(encoding="utf-8"))
    frames, durations = [], []
    n_words = len(ex["text"].split())
    for w in range(0, n_words + 1, 3):                    # typing the ad
        frames.append(frame(ex, w, None, 0, False)); durations.append(70)
    frames.append(frame(ex, n_words, None, 0, False)); durations.append(500)
    steps = 12
    for i in range(steps + 1):                            # waiting for the model (sped up)
        frames.append(frame(ex, n_words, ex["latency_s"] * i / steps, 0, False)); durations.append(130)
    n_lines = len(json_lines(ex["prediction"]))
    for k in range(1, n_lines + 1):                       # answer appears line by line
        frames.append(frame(ex, n_words, ex["latency_s"], k, False)); durations.append(220)
    frames.append(frame(ex, n_words, ex["latency_s"], n_lines, True)); durations.append(4500)

    out = ROOT / "docs" / "demo.gif"
    # one shared palette (taken from the last frame, which has every colour) keeps
    # the ticks green and crosses red in all frames
    sample = Image.new("RGB", (W, H + 40), BG)
    sample.paste(frames[-1], (0, 0))
    for i, c in enumerate([GOOD, BAD, BLUE, INK, INK2, MUTED]):   # make sure key colours survive
        sample.paste(c, (i * 40, H, i * 40 + 40, H + 40))
    palette = sample.quantize(colors=128, method=Image.Quantize.MAXCOVERAGE)
    pal = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)
    print(f"written {out} ({out.stat().st_size // 1024} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
