import json

import httpx

from jobad_llmops.extractor import Extractor
from jobad_llmops.llm import OllamaBackend


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_ollama_request_uses_schema_and_temperature(monkeypatch):
    sent = {}

    def fake_post(url, json=None, timeout=None):
        sent.update(url=url, body=json)
        answer = {"job_title": "Data Analyst", "seniority": "junior", "skills": ["SQL"]}
        return FakeResponse({"response": __import__("json").dumps(answer)})

    monkeypatch.setattr(httpx, "post", fake_post)
    result = Extractor(OllamaBackend("llama3.2:3b"), "v2").extract("Junior Data Analyst, SQL, Berlin, hybrid.")

    assert sent["url"].endswith("/api/generate")
    assert sent["body"]["model"] == "llama3.2:3b"
    assert sent["body"]["options"]["temperature"] == 0
    assert sent["body"]["format"]["type"] == "object"      # structured-output schema is sent
    assert result.valid and result.job.skills == ["sql"]
