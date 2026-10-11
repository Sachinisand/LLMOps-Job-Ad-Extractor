from jobad_llmops.metrics import check_gate, field_correct, score
from jobad_llmops.monitoring import Monitor, detect_language, drift_check
from jobad_llmops.extractor import ExtractionResult
from jobad_llmops.schema import JobAd

LABEL = {"job_title": "Data Analyst", "seniority": "junior", "skills": ["python", "sql"],
         "german_level": "B2", "english_required": True, "work_mode": "hybrid",
         "salary_min": 45000, "salary_max": 50000, "location": "München"}


def test_perfect_prediction_scores_one():
    m = score([dict(LABEL)], [LABEL])
    assert m["field_accuracy"] == 1.0 and m["skills_f1"] == 1.0


def test_invalid_prediction_scores_zero():
    m = score([None], [LABEL])
    assert m["json_valid_rate"] == 0 and m["field_accuracy"] == 0 and m["skills_recall"] == 0


def test_normalisation_rules():
    assert field_correct("location", "Munich", "München")
    assert field_correct("job_title", "Data Analyst (m/w/d)", "Data Analyst")
    assert not field_correct("seniority", "mid", "junior")


def test_gate_reports_failures():
    assert check_gate({"skills_f1": 0.5}, {"skills_f1": 0.7}) == ["skills_f1: 0.5 < 0.7"]
    assert check_gate({"skills_f1": 0.9}, {"skills_f1": 0.7}) == []


def test_language_detection():
    assert detect_language("Wir suchen eine Person mit Erfahrung in SQL und Python für unser Team") == "de"
    assert detect_language("We are looking for a person with experience in SQL and Python") == "en"


def test_drift_flags_big_language_shift():
    ref = {"german_ad_share": 0.5, "avg_input_chars": 500}
    assert drift_check(0.9, 500, ref)["drift_detected"]
    assert not drift_check(0.55, 520, ref)["drift_detected"]


def test_monitor_logs_and_summarises(tmp_path):
    mon = Monitor(str(tmp_path / "m.db"))
    ok = ExtractionResult(JobAd(job_title="X"), True, 1, 120.0, "test", "v2")
    bad = ExtractionResult(None, False, 2, 300.0, "test", "v2", error="ValueError")
    rid = mon.log_request("Wir suchen einen Data Analyst mit SQL und Python", ok)
    mon.log_request("We are hiring a data analyst with SQL", bad)
    mon.log_feedback(rid, "seniority", "junior")
    s = mon.summary({"german_ad_share": 0.5, "avg_input_chars": 45})
    assert s["requests"] == 2
    assert s["valid_json_rate"] == 0.5
    assert s["retry_rate"] == 0.5
    assert s["corrections_by_field"] == {"seniority": 1}
    assert "drift" in s
