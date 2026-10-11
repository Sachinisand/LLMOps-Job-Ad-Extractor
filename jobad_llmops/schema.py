"""
The structured result we want from every job ad.

Pydantic checks the LLM output: wrong types, unknown categories or missing
fields make validation fail, and the extractor then retries or reports an error
instead of passing bad data on.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Seniority = Literal["intern", "working_student", "junior", "mid", "senior", "lead", "unspecified"]
GermanLevel = Literal["none", "A1", "A2", "B1", "B2", "C1", "C2", "native", "unspecified"]
WorkMode = Literal["onsite", "hybrid", "remote", "unspecified"]

# Canonical skill names, so "PowerBI", "Power-BI" and "MS Power BI" count as one skill.
SKILL_SYNONYMS = {
    "powerbi": "power bi", "power-bi": "power bi", "ms power bi": "power bi", "microsoft power bi": "power bi",
    "ms excel": "excel", "microsoft excel": "excel", "advanced excel": "excel",
    "python3": "python", "py": "python",
    "postgresql": "sql", "mysql": "sql", "t-sql": "sql", "tsql": "sql", "ms sql": "sql", "sql server": "sql",
    "amazon web services": "aws", "microsoft azure": "azure", "google cloud": "gcp", "google cloud platform": "gcp",
    "apache spark": "spark", "pyspark": "spark", "apache airflow": "airflow",
    "ml": "machine learning", "maschinelles lernen": "machine learning",
    "statistik": "statistics", "a/b tests": "a/b testing", "ab testing": "a/b testing",
    "sap s/4hana": "sap", "sap bw": "sap", "google bigquery": "bigquery", "looker studio": "looker",
}


def normalise_skill(skill: str) -> str:
    s = " ".join(skill.lower().strip().split())
    return SKILL_SYNONYMS.get(s, s)


class JobAd(BaseModel):
    job_title: Optional[str] = Field(None, description="Job title as written in the ad")
    seniority: Seniority = "unspecified"
    skills: list[str] = Field(default_factory=list, description="Technical skills and tools, lower case")
    german_level: GermanLevel = "unspecified"
    english_required: Optional[bool] = None
    work_mode: WorkMode = "unspecified"
    salary_min: Optional[int] = Field(None, description="Yearly gross salary in EUR")
    salary_max: Optional[int] = Field(None, description="Yearly gross salary in EUR")
    location: Optional[str] = None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, skills: list[str]) -> list[str]:
        return sorted({normalise_skill(s) for s in skills if s and s.strip()})

    @field_validator("salary_max")
    @classmethod
    def max_not_below_min(cls, value, info):
        low = info.data.get("salary_min")
        if value is not None and low is not None and value < low:
            raise ValueError("salary_max is lower than salary_min")
        return value


def json_schema() -> dict:
    """JSON schema sent to Ollama so the model can only answer in this shape."""
    return JobAd.model_json_schema()
