"""
REST API (deployment step).

  GET  /health    model and prompt version currently running
  POST /extract   job ad text in, structured fields out (every call is logged)
  POST /feedback  a user corrects one field of an earlier answer
  GET  /metrics   monitoring summary: quality, latency, corrections, drift

Run locally:  uvicorn jobad_llmops.api:app --reload
"""

import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .extractor import ROOT, Extractor, load_config
from .llm import make_backend
from .monitoring import Monitor, reference_stats
from .schema import JobAd

config = load_config()
extractor = Extractor(make_backend(config), config["prompt_version"])
monitor = Monitor(str(ROOT / config["monitoring"]["db_path"]))
EVAL_FILE = ROOT / "eval" / "job_ads.jsonl"
REFERENCE = reference_stats([json.loads(l)["text"] for l in EVAL_FILE.read_text(encoding="utf-8").splitlines() if l.strip()])

app = FastAPI(title="Job-Ad Extractor", version="1.0")


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=30, description="Full job ad text")


class ExtractResponse(BaseModel):
    request_id: int
    valid: bool
    result: JobAd | None
    model: str
    prompt_version: str
    latency_ms: float
    error: str | None = None


class FeedbackRequest(BaseModel):
    request_id: int
    field: str
    correct_value: Any


@app.get("/health")
def health():
    return {"status": "ok", "model": extractor.backend.name, "prompt_version": extractor.prompt_version}


@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest):
    try:
        result = extractor.extract(request.text)
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"Model backend not reachable: {exc}") from exc
    request_id = monitor.log_request(request.text, result)
    return ExtractResponse(request_id=request_id, valid=result.valid, result=result.job, model=result.model,
                           prompt_version=result.prompt_version, latency_ms=result.latency_ms, error=result.error)


@app.post("/feedback")
def feedback(request: FeedbackRequest):
    if request.field not in JobAd.model_fields:
        raise HTTPException(422, f"Unknown field '{request.field}'")
    try:
        monitor.log_feedback(request.request_id, request.field, request.correct_value)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"status": "saved"}


@app.get("/metrics")
def metrics():
    return monitor.summary(REFERENCE, config["monitoring"].get("drift_window", 30))
