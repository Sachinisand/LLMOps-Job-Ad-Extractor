"""
Model backends. Every backend has the same method, generate(prompt, job_ad) -> str,
which returns the raw text answer (expected to be JSON).

OllamaBackend   a real open-source LLM running locally with Ollama (free, no API key)
BaselineBackend simple rules and keywords, no LLM. Used as the benchmark the LLM
                has to beat, and in CI and tests where no LLM is available.
"""

import json
import re

import httpx

from .schema import json_schema


class OllamaBackend:
    def __init__(self, model: str, url: str = "http://localhost:11434",
                 temperature: float = 0, timeout: float = 120):
        self.model = model
        self.url = url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def generate(self, prompt: str, job_ad: str) -> str:
        response = httpx.post(
            f"{self.url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "format": json_schema(),   # structured output: the answer must fit the schema
                "stream": False,
                "options": {"temperature": self.temperature},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["response"]


# ---------------------------------------------------------------- baseline ---

KNOWN_SKILLS = [
    "python", "sql", "power bi", "tableau", "excel", "r", "aws", "azure", "gcp", "spark",
    "databricks", "airflow", "dbt", "docker", "git", "sap", "looker", "snowflake", "pandas",
    "machine learning", "statistics", "etl", "kubernetes", "java", "javascript", "scrum",
    "google analytics", "a/b testing", "vba", "qlik", "sas", "jira", "bigquery", "power query",
]
SKILL_ALIASES = {"powerbi": "power bi", "ms excel": "excel", "pyspark": "spark",
                 "statistik": "statistics", "maschinelles lernen": "machine learning",
                 "postgresql": "sql", "mysql": "sql", "a/b tests": "a/b testing"}


class BaselineBackend:
    """Keyword and regex rules. Fast and predictable, but easily fooled by wording."""

    name = "baseline:rules"

    def generate(self, prompt: str, job_ad: str) -> str:
        text = job_ad.lower()
        return json.dumps({
            "job_title": self._title(job_ad),
            "seniority": self._seniority(text),
            "skills": self._skills(text),
            "german_level": self._german(text),
            "english_required": self._english(text),
            "work_mode": self._work_mode(text),
            "salary_min": self._salary(text)[0],
            "salary_max": self._salary(text)[1],
            "location": self._location(job_ad),
        })

    @staticmethod
    def _title(ad: str):
        first = ad.strip().splitlines()[0]
        return re.split(r"\s+[–-]\s+|\s+\|\s+|\s+bei\s+|\s+at\s+", first)[0].strip() or None

    @staticmethod
    def _seniority(t: str) -> str:
        rules = [("working_student", r"werkstudent|working student"), ("intern", r"praktik|intern\b|internship"),
                 ("lead", r"\blead\b|head of|teamleit"), ("senior", r"\bsenior\b"),
                 ("junior", r"\bjunior\b|berufseinsteig|entry.level|graduate"), ("mid", r"\bmid\b|professional")]
        for label, pattern in rules:
            if re.search(pattern, t):
                return label
        return "unspecified"

    @staticmethod
    def _skills(t: str) -> list[str]:
        found = set()
        for skill in KNOWN_SKILLS:
            if re.search(r"(?<![a-z])" + re.escape(skill) + r"(?![a-z])", t):
                found.add(skill)
        for alias, skill in SKILL_ALIASES.items():
            if alias in t:
                found.add(skill)
        return sorted(found)

    @staticmethod
    def _german(t: str) -> str:
        m = re.search(r"(?:deutsch|german)[^.\n]{0,40}?\b([abc][12])\b|\b([abc][12])\b[^.\n]{0,25}?(?:deutsch|german)", t)
        if m:
            return (m.group(1) or m.group(2)).upper()
        if re.search(r"(muttersprach|native)[^.\n]{0,20}(deutsch|german)|(deutsch|german)[^.\n]{0,20}(muttersprach|native)", t):
            return "native"
        if re.search(r"verhandlungssicher|fließend[^.\n]{0,15}deutsch|fluent german|sehr gute deutsch", t):
            return "C1"
        if re.search(r"no german|german (is )?not required|keine deutschkenntnisse", t):
            return "none"
        return "unspecified"

    @staticmethod
    def _english(t: str):
        if re.search(r"englisch|english", t):
            return not re.search(r"english (is )?not required|kein englisch", t)
        return None

    @staticmethod
    def _work_mode(t: str) -> str:
        if re.search(r"hybrid|teilweise remote|\d tage?(?:n)? (?:pro woche )?(?:im )?(?:büro|office)|days? (?:a|per) week in the office", t):
            return "hybrid"
        if re.search(r"100\s?% remote|fully remote|full remote|remote-first|vollständig remote|komplett remote", t):
            return "remote"
        if re.search(r"vor ort|on.?site|in unserem büro in", t):
            return "onsite"
        return "unspecified"

    @staticmethod
    def _salary(t: str):
        nums = []
        for line in t.splitlines():
            if not re.search(r"€|eur|gehalt|salary|vergütung", line):
                continue
            monthly = re.search(r"monat|month|/\s*mo", line)
            for raw, k in re.findall(r"(\d{1,3}(?:[.,]\d{3})+|\d{2,6})\s*(k|tsd)?\b", line):
                value = int(raw.replace(".", "").replace(",", ""))
                if k:
                    value *= 1000
                if monthly and value < 15000:
                    value *= 12
                if 15000 <= value <= 250000:
                    nums.append(value)
        if not nums:
            return None, None
        return min(nums), max(nums)

    @staticmethod
    def _location(ad: str):
        m = re.search(r"(?:standort|location|ort|einsatzort)\s*:\s*([^\n.,|(]+)", ad, re.I)
        return m.group(1).strip() if m else None


def make_backend(config: dict):
    llm = config["llm"]
    if llm["backend"] == "baseline":
        return BaselineBackend()
    return OllamaBackend(llm["model"], llm.get("ollama_url", "http://localhost:11434"),
                         llm.get("temperature", 0), llm.get("timeout_seconds", 120))
