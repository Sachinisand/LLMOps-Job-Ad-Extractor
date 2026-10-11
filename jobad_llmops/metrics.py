"""
Scoring an extraction against the correct label.

- Field accuracy: share of ads where a field is exactly right (after light
  normalisation, for example "München" = "Munich" and "(m/w/d)" removed from titles).
- Skills: precision (how many found skills are real), recall (how many real skills
  were found) and F1, counted over all ads together (micro average).
- An invalid answer counts as wrong on every field.
"""

import re

from .schema import normalise_skill

SCORED_FIELDS = ["job_title", "seniority", "german_level", "english_required",
                 "work_mode", "salary_min", "salary_max", "location"]
CITY_ALIASES = {"munich": "münchen", "cologne": "köln", "frankfurt": "frankfurt am main",
                "nuremberg": "nürnberg", "hanover": "hannover"}


def _norm_text(value):
    if value is None:
        return None
    text = re.sub(r"\((?:m|w|d|f)(?:/(?:m|w|d|f))*\)", "", str(value), flags=re.I)
    return " ".join(text.lower().replace("–", "-").split()).strip(" -|")


def _norm_city(value):
    city = _norm_text(value)
    return CITY_ALIASES.get(city, city) if city else None


def field_correct(field: str, predicted, expected) -> bool:
    if field == "job_title":
        p, e = _norm_text(predicted), _norm_text(expected)
        return bool(p) and bool(e) and (p == e or p in e or e in p)
    if field == "location":
        return _norm_city(predicted) == _norm_city(expected)
    return predicted == expected


def score(predictions: list, labels: list[dict]) -> dict:
    """predictions: list of dicts (or None for invalid answers), same order as labels."""
    n = len(labels)
    per_field = {f: 0 for f in SCORED_FIELDS}
    tp = fp = fn = 0
    for pred, label in zip(predictions, labels):
        expected_skills = {normalise_skill(s) for s in label["skills"]}
        if pred is None:
            fn += len(expected_skills)
            continue
        for f in SCORED_FIELDS:
            per_field[f] += field_correct(f, pred.get(f), label[f])
        found = {normalise_skill(s) for s in pred.get("skills", [])}
        tp += len(found & expected_skills)
        fp += len(found - expected_skills)
        fn += len(expected_skills - found)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    field_acc = {f: round(c / n, 3) for f, c in per_field.items()}
    return {
        "json_valid_rate": round(sum(p is not None for p in predictions) / n, 3),
        "field_accuracy": round(sum(field_acc.values()) / len(field_acc), 3),
        "field_accuracy_by_field": field_acc,
        "skills_precision": round(precision, 3),
        "skills_recall": round(recall, 3),
        "skills_f1": round(f1, 3),
    }


def check_gate(metrics: dict, gate: dict) -> list[str]:
    """Return the list of failed checks (empty list = passed)."""
    return [f"{k}: {metrics[k]} < {v}" for k, v in gate.items() if metrics[k] < v]
