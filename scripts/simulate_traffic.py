"""
Sends job ads through the extractor as if real users were calling the API, and
logs every request to the monitoring database. Where the answer differs from the
correct label, a "user correction" is stored, like a user fixing a wrong field.

This fills data/monitoring.db so the monitoring report has something to show.

Examples
    python scripts/simulate_traffic.py                     # model from config.yaml
    python scripts/simulate_traffic.py --backend baseline  # no LLM needed
    python scripts/simulate_traffic.py --english-only      # simulate input drift
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jobad_llmops.extractor import Extractor, load_config      # noqa: E402
from jobad_llmops.llm import BaselineBackend, make_backend      # noqa: E402
from jobad_llmops.metrics import SCORED_FIELDS, field_correct  # noqa: E402
from jobad_llmops.monitoring import Monitor, detect_language   # noqa: E402


def main():
    config = load_config()
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=["baseline", "ollama"], default=config["llm"]["backend"])
    p.add_argument("--requests", type=int, default=60)
    p.add_argument("--english-only", action="store_true", help="only English ads, to trigger the drift alert")
    p.add_argument("--feedback-share", type=float, default=0.5, help="share of wrong answers that users correct")
    args = p.parse_args()

    backend = BaselineBackend() if args.backend == "baseline" else make_backend(config)
    extractor = Extractor(backend, config["prompt_version"])
    monitor = Monitor(str(ROOT / config["monitoring"]["db_path"]))

    ads = []
    for name in ["job_ads.jsonl", "holdout_ads.jsonl"]:
        ads += [json.loads(l) for l in (ROOT / "eval" / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.english_only:
        ads = [a for a in ads if detect_language(a["text"]) == "en"]

    random.seed(42)
    corrections = 0
    for i in range(args.requests):
        ad = random.choice(ads)
        result = extractor.extract(ad["text"])
        request_id = monitor.log_request(ad["text"], result)
        if result.job:
            pred = result.job.model_dump()
            for field in SCORED_FIELDS:
                if not field_correct(field, pred[field], ad["label"][field]) and random.random() < args.feedback_share:
                    monitor.log_feedback(request_id, field, ad["label"][field])
                    corrections += 1
        if (i + 1) % 10 == 0:
            print(f"{i + 1}/{args.requests} requests logged", flush=True)
    print(f"Done. {corrections} user corrections stored in {config['monitoring']['db_path']}")


if __name__ == "__main__":
    main()
