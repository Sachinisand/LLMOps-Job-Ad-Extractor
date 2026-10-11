import pytest
from pydantic import ValidationError

from jobad_llmops.extractor import parse_answer
from jobad_llmops.schema import JobAd


def test_skills_are_normalised_and_deduplicated():
    job = JobAd(skills=["PowerBI", "Power BI", "Python3", " SQL "])
    assert job.skills == ["power bi", "python", "sql"]


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        JobAd(german_level="fluent")


def test_salary_max_below_min_is_rejected():
    with pytest.raises(ValidationError):
        JobAd(salary_min=60000, salary_max=50000)


def test_parse_answer_accepts_code_fences_and_extra_text():
    raw = 'Here is the result:\n```json\n{"job_title": "Data Analyst", "seniority": "junior"}\n```'
    job = parse_answer(raw)
    assert job.job_title == "Data Analyst" and job.seniority == "junior"


def test_parse_answer_without_json_raises():
    with pytest.raises(ValueError):
        parse_answer("Sorry, I cannot help with that.")
