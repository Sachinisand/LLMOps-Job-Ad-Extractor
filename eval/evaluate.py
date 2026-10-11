"""
Evaluate one model + prompt combination on the labelled job ads.

Examples
    python -m eval.evaluate --backend baseline
    python -m eval.evaluate --backend baseline --set holdout
    python -m eval.evaluate --backend ollama --model llama3.2:3b --prompt v2
    python -m eval.evaluate --backend ollama --model qwen2.5:3b --prompt v1

Each run
- prints the scores,
- saves the details to eval/results/<set>_<backend>_<model>_<prompt>.json,
- adds one row to eval/results/leaderboard.csv (so runs can be compared over time),
- fails (exit code 1) if the scores are below the quality gate in config.yaml.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from jobad_llmops.extractor import ROOT, Extractor, load_config
from jobad_llmops.llm import BaselineBackend, OllamaBackend
from jobad_llmops.metrics import check_gate, score
from jobad_llmops.monitoring import percentile

EVAL_SETS = {"main": ROOT / "eval" / "job_ads.jsonl",          # 30 ads, used while developing
             "holdout": ROOT / "eval" / "holdout_ads.jsonl"}   # 12 unseen ads, never tuned on
RESULTS = ROOT / "eval" / "results"


def load_eval_set(name: str = "main"):
    path = EVAL_SETS[name]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None):
    config = load_config()
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=["baseline", "ollama"], default=config["llm"]["backend"])
    p.add_argument("--model", default=config["llm"]["model"])
    p.add_argument("--prompt", default=config["prompt_version"])
    p.add_argument("--set", choices=list(EVAL_SETS), default="main", help="which labelled ads to use")
    p.add_argument("--limit", type=int, default=None, help="only the first N ads (quick check)")
    args = p.parse_args(argv)

    if args.backend == "baseline":
        backend, gate_name = BaselineBackend(), "baseline"
    else:
        llm = config["llm"]
        backend = OllamaBackend(args.model, llm["ollama_url"], llm["temperature"], llm["timeout_seconds"])
        gate_name = "llm"
    extractor = Extractor(backend, args.prompt)

    ads = load_eval_set(args.set)[: args.limit]
    predictions, latencies, rows = [], [], []
    for i, ad in enumerate(ads, 1):
        result = extractor.extract(ad["text"])
        pred = result.job.model_dump() if result.job else None
        predictions.append(pred)
        latencies.append(result.latency_ms)
        rows.append({"id": ad["id"], "valid": result.valid, "attempts": result.attempts,
                     "latency_ms": result.latency_ms, "prediction": pred, "label": ad["label"],
                     "error": result.error})
        print(f"  {i:>2}/{len(ads)} {ad['id']}  {'ok ' if result.valid else 'ERR'}  {result.latency_ms:>8.0f} ms",
              flush=True)

    metrics = score(predictions, [a["label"] for a in ads])
    metrics["latency_p50_ms"] = percentile(latencies, 0.5)
    metrics["latency_p95_ms"] = percentile(latencies, 0.95)
    metrics["retry_rate"] = round(sum(r["attempts"] > 1 for r in rows) / len(rows), 3)

    name = f"{args.set}_{args.backend}_{args.model if args.backend == 'ollama' else 'rules'}_{args.prompt}".replace(":", "-")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps({"metrics": metrics, "details": rows}, indent=2,
                                                     ensure_ascii=False), encoding="utf-8")
    board = RESULTS / "leaderboard.csv"
    new = not board.exists()
    with board.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "eval_set", "backend", "model", "prompt", "ads", "json_valid_rate", "field_accuracy",
                        "skills_f1", "latency_p50_ms", "latency_p95_ms"])
        w.writerow([datetime.now(timezone.utc).date().isoformat(), args.set, args.backend,
                    args.model if args.backend == "ollama" else "rules", args.prompt, len(ads),
                    metrics["json_valid_rate"], metrics["field_accuracy"], metrics["skills_f1"],
                    metrics["latency_p50_ms"], metrics["latency_p95_ms"]])

    print("\nResults")
    for k, v in metrics.items():
        if k != "field_accuracy_by_field":
            print(f"  {k:<18} {v}")
    print("  by field:", ", ".join(f"{k} {v:.0%}" for k, v in metrics["field_accuracy_by_field"].items()))

    if os.getenv("GITHUB_STEP_SUMMARY"):   # nice table on the GitHub Actions run page
        model = args.model if args.backend == "ollama" else "rules"
        lines = [f"### {args.backend} / {model} / prompt {args.prompt} / {args.set} set ({len(ads)} ads)", "",
                 "| metric | value |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in metrics.items() if k != "field_accuracy_by_field"]
        lines += [f"| accuracy: {k} | {v:.0%} |" for k, v in metrics["field_accuracy_by_field"].items()]
        # A few real model answers, so readers can see what the scores are based on.
        texts = {a["id"]: a["text"] for a in ads}
        for r in rows[:3]:
            lines += ["", f"<details><summary>Example {r['id']}</summary>", "",
                      "**Job ad**", "", "```text", texts[r["id"]].strip(), "```", "",
                      "**Model answer**", "", "```json",
                      json.dumps(r["prediction"], ensure_ascii=False, indent=2), "```", "",
                      "**Correct label**", "", "```json",
                      json.dumps(r["label"], ensure_ascii=False, indent=2), "```", "", "</details>"]
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")

    failed = check_gate(metrics, config["quality_gate"][gate_name])
    if failed:
        print("\nQUALITY GATE FAILED:\n  " + "\n  ".join(failed))
        return 1
    print(f"\nQuality gate ({gate_name}) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
