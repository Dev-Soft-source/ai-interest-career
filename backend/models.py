"""Pydantic models for LLM I/O and API responses."""

from typing import Any

from pydantic import BaseModel, Field


class LLMInput(BaseModel):
    """Payload sent to the LLM (matches MVP spec)."""

    answers: dict[str, str] = Field(..., description="Question id → answer text or option key")
    job_list: list[str]


class TopJob(BaseModel):
    job: str
    score: int = Field(..., ge=0, le=100)
    reason: str


class LLMOutput(BaseModel):
    """Expected JSON shape from the model."""

    scores: dict[str, int]
    top_jobs: list[TopJob]
    summary: str


class ProcessRequest(BaseModel):
    email: str | None = None


class ResultsResponse(BaseModel):
    email: str
    scores: dict[str, int]
    top_jobs: list[TopJob]
    summary: str


class ErrorResponse(BaseModel):
    detail: str


class ProcessSummary(BaseModel):
    processed: list[str]
    errors: list[dict[str, Any]]
