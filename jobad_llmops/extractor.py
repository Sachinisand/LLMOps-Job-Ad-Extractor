"""
The core step: job ad text in, validated JobAd out.

1. Fill the job ad into the versioned prompt (prompts/<version>.md).
2. Ask the model backend for an answer.
3. Parse the JSON and validate it against the schema.
4. If parsing or validation fails, retry once with a stricter reminder.
Each call returns timing and error details, which the monitoring layer stores.
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from .schema import JobAd

ROOT = Path(__file__).resolve().parents[1]
PROMPT_DIR = ROOT / "prompts"
RETRY_NOTE = "\n\nYour previous answer was not valid. Reply with one JSON object that follows the rules exactly."


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    """Read config.yaml. Environment variables override it, which Docker uses
    (LLM_BACKEND, LLM_MODEL, OLLAMA_URL, PROMPT_VERSION)."""
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    llm = config["llm"]
    llm["backend"] = os.getenv("LLM_BACKEND", llm["backend"])
    llm["model"] = os.getenv("LLM_MODEL", llm["model"])
    llm["ollama_url"] = os.getenv("OLLAMA_URL", llm["ollama_url"])
    config["prompt_version"] = os.getenv("PROMPT_VERSION", config["prompt_version"])
    return config


def load_prompt(version: str) -> str:
    path = PROMPT_DIR / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt version '{version}' not found in {PROMPT_DIR}")
    return path.read_text(encoding="utf-8")


@dataclass
class ExtractionResult:
    job: Optional[JobAd]
    valid: bool
    attempts: int
    latency_ms: float
    model: str
    prompt_version: str
    error: Optional[str] = None
    raw_answers: list = field(default_factory=list)


def parse_answer(raw: str) -> JobAd:
    """Turn the raw model answer into a JobAd. Accepts JSON wrapped in ``` fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in the answer")
    return JobAd.model_validate(json.loads(text[start:end + 1]))


class Extractor:
    def __init__(self, backend, prompt_version: str, max_attempts: int = 2):
        self.backend = backend
        self.prompt_version = prompt_version
        self.template = load_prompt(prompt_version)
        self.max_attempts = max_attempts

    def extract(self, job_ad: str) -> ExtractionResult:
        prompt = self.template.replace("{job_ad}", job_ad.strip())
        started = time.perf_counter()
        raw_answers, error = [], None
        for attempt in range(1, self.max_attempts + 1):
            try:
                raw = self.backend.generate(prompt if attempt == 1 else prompt + RETRY_NOTE, job_ad)
                raw_answers.append(raw)
                job = parse_answer(raw)
                return ExtractionResult(job, True, attempt, self._ms(started), self.backend.name,
                                        self.prompt_version, raw_answers=raw_answers)
            except (ValueError, ValidationError, json.JSONDecodeError) as exc:
                error = f"{type(exc).__name__}: {str(exc)[:200]}"
        return ExtractionResult(None, False, self.max_attempts, self._ms(started), self.backend.name,
                                self.prompt_version, error=error, raw_answers=raw_answers)

    @staticmethod
    def _ms(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 1)
