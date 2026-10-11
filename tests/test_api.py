import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """API with the rule-based backend and a temporary database (no LLM needed)."""
    import jobad_llmops.extractor as ex
    real_load = ex.load_config

    def test_config(*args, **kwargs):
        cfg = real_load()
        cfg["llm"]["backend"] = "baseline"
        cfg["monitoring"]["db_path"] = str(tmp_path / "api.db")
        return cfg

    monkeypatch.setattr(ex, "load_config", test_config)
    import jobad_llmops.api as api
    importlib.reload(api)
    return TestClient(api.app)


AD = "Junior Data Analyst – Standort: Bremen. SQL und Excel. Deutsch C1. Vor Ort. 44.000 €."


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["model"] == "baseline:rules"


def test_extract_feedback_metrics_flow(client):
    r = client.post("/extract", json={"text": AD})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] and body["result"]["location"] == "Bremen"

    fb = client.post("/feedback", json={"request_id": body["request_id"], "field": "seniority",
                                        "correct_value": "junior"})
    assert fb.status_code == 200

    m = client.get("/metrics").json()
    assert m["requests"] == 1 and m["corrections_by_field"] == {"seniority": 1}


def test_rejects_too_short_text(client):
    assert client.post("/extract", json={"text": "short"}).status_code == 422


def test_feedback_unknown_field(client):
    rid = client.post("/extract", json={"text": AD}).json()["request_id"]
    assert client.post("/feedback", json={"request_id": rid, "field": "colour", "correct_value": 1}).status_code == 422
