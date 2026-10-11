import json

from jobad_llmops.extractor import Extractor
from jobad_llmops.llm import BaselineBackend


class FlakyBackend:
    """Returns invalid JSON first, then a valid answer: tests the retry."""
    name = "test:flaky"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt, job_ad):
        self.calls += 1
        return "not json" if self.calls == 1 else json.dumps({"job_title": "BI Analyst"})


class BrokenBackend:
    name = "test:broken"

    def generate(self, prompt, job_ad):
        return "{ this is not valid"


AD = """Junior Data Analyst (m/w/d) – Example GmbH
Standort: Hannover
SQL, Power BI und Excel. Deutsch B2, Englisch gut. Hybrid. 45.000 – 50.000 €."""


def test_baseline_extracts_main_fields():
    result = Extractor(BaselineBackend(), "v2").extract(AD)
    assert result.valid
    job = result.job
    assert job.seniority == "junior"
    assert job.german_level == "B2"
    assert job.work_mode == "hybrid"
    assert (job.salary_min, job.salary_max) == (45000, 50000)
    assert {"sql", "power bi", "excel"} <= set(job.skills)
    assert job.location == "Hannover"


def test_retry_after_invalid_answer():
    backend = FlakyBackend()
    result = Extractor(backend, "v2").extract(AD)
    assert result.valid and result.attempts == 2 and backend.calls == 2


def test_gives_up_after_max_attempts():
    result = Extractor(BrokenBackend(), "v2").extract(AD)
    assert not result.valid and result.job is None and result.error


def test_prompt_contains_the_job_ad():
    captured = {}

    class Spy:
        name = "test:spy"

        def generate(self, prompt, job_ad):
            captured["prompt"] = prompt
            return "{}"

    Extractor(Spy(), "v2").extract(AD)
    assert "Example GmbH" in captured["prompt"] and "{job_ad}" not in captured["prompt"]
