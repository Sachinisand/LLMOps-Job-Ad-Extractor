"""
Monitoring: every extraction is logged to a small SQLite database, and users can
send corrections (feedback). From these two tables we calculate:

- volume, valid-JSON rate and retries      -> is the model answering in the right format?
- latency p50 / p95                        -> is it fast enough?
- correction rate per field                -> where is it wrong in real use?
- input drift (last N requests)            -> do recent ads look different from the ads we tested on?
"""

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

GERMAN_WORDS = {"und", "der", "die", "das", "mit", "für", "wir", "sie", "du", "deine", "ihre",
                "kenntnisse", "erfahrung", "aufgaben", "bei", "eine", "ein", "zu", "im", "von",
                "gute", "gutes", "sehr", "oder", "nicht", "suchen", "standort", "profil", "bieten",
                "pro", "woche", "jahr", "englisch", "deutsch", "büro", "vor", "ort", "gehalt"}
MIN_REQUESTS_FOR_DRIFT = 10


def detect_language(text: str) -> str:
    words = re.findall(r"[a-zäöüß]+", text.lower())
    if not words:
        return "unknown"
    share = sum(w in GERMAN_WORDS for w in words) / len(words)
    return "de" if share > 0.06 else "en"


def percentile(values: list[float], p: float):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (k - lo), 1)


class Monitor:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        with self._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT, model TEXT, prompt_version TEXT,
                    latency_ms REAL, valid INTEGER, attempts INTEGER, error TEXT,
                    input_chars INTEGER, input_lang TEXT, output TEXT);
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER, ts TEXT, field TEXT, correct_value TEXT);
            """)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def log_request(self, job_ad: str, result) -> int:
        output = result.job.model_dump_json() if result.job else None
        with self._connect() as con:
            cur = con.execute(
                "INSERT INTO requests (ts, model, prompt_version, latency_ms, valid, attempts, error, "
                "input_chars, input_lang, output) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (self._now(), result.model, result.prompt_version, result.latency_ms, int(result.valid),
                 result.attempts, result.error, len(job_ad), detect_language(job_ad), output))
            return cur.lastrowid

    def log_feedback(self, request_id: int, field: str, correct_value) -> None:
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM requests WHERE id = ?", (request_id,)).fetchone():
                raise KeyError(f"request {request_id} not found")
            con.execute("INSERT INTO feedback (request_id, ts, field, correct_value) VALUES (?,?,?,?)",
                        (request_id, self._now(), field, json.dumps(correct_value)))

    def summary(self, reference: dict | None = None, drift_window: int = 30) -> dict:
        with self._connect() as con:
            rows = con.execute("SELECT latency_ms, valid, attempts, input_chars, input_lang, model, "
                               "prompt_version, ts FROM requests").fetchall()
            feedback = con.execute("SELECT field, COUNT(*) FROM feedback GROUP BY field").fetchall()
        if not rows:
            return {"requests": 0}
        latencies = [r[0] for r in rows]
        n = len(rows)
        de_share = sum(r[4] == "de" for r in rows) / n
        avg_chars = sum(r[3] for r in rows) / n
        result = {
            "requests": n,
            "valid_json_rate": round(sum(r[1] for r in rows) / n, 3),
            "retry_rate": round(sum(r[2] > 1 for r in rows) / n, 3),
            "latency_p50_ms": percentile(latencies, 0.5),
            "latency_p95_ms": percentile(latencies, 0.95),
            "german_ad_share": round(de_share, 3),
            "avg_input_chars": round(avg_chars),
            "corrections_by_field": dict(feedback),
            "correction_rate": round(sum(c for _, c in feedback) / n, 3),
            "versions": sorted({f"{r[5]} / prompt {r[6]}" for r in rows}),
            "first_request": min(r[7] for r in rows),
            "last_request": max(r[7] for r in rows),
        }
        if reference:
            # Drift looks at the most recent requests only, so a recent change is not
            # hidden by older traffic.
            recent = rows[-drift_window:]
            recent_de = sum(r[4] == "de" for r in recent) / len(recent)
            recent_chars = sum(r[3] for r in recent) / len(recent)
            result["drift"] = drift_check(recent_de, recent_chars, reference)
            if len(recent) < MIN_REQUESTS_FOR_DRIFT:   # too few requests to judge
                result["drift"]["drift_detected"] = False
            result["drift"].update(window=len(recent), german_ad_share=round(recent_de, 3),
                                   avg_input_chars=round(recent_chars))
        return result

    def latency_series(self) -> list[tuple[str, float]]:
        with self._connect() as con:
            return con.execute("SELECT ts, latency_ms FROM requests ORDER BY id").fetchall()


def reference_stats(ads: list[str]) -> dict:
    """Input profile of the evaluation set: what 'normal' ads look like."""
    return {"german_ad_share": sum(detect_language(a) == "de" for a in ads) / len(ads),
            "avg_input_chars": sum(len(a) for a in ads) / len(ads)}


def drift_check(de_share: float, avg_chars: float, reference: dict) -> dict:
    """Flag drift when the language mix moves by > 20 points or ad length by > 30 %."""
    lang_shift = de_share - reference["german_ad_share"]
    length_shift = avg_chars / reference["avg_input_chars"] - 1
    return {
        "german_share_change_pts": round(lang_shift * 100, 1),
        "length_change_pct": round(length_shift * 100, 1),
        "drift_detected": abs(lang_shift) > 0.20 or abs(length_shift) > 0.30,
    }
