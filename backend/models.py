"""Pydantic models for questionnaire, jobs, scoring, LLM I/O, and API responses."""

from typing import Any, Literal

JobSetName = Literal["core_30", "client_40"]

from pydantic import BaseModel, Field, field_validator

DIMENSION_KEYS: tuple[str, ...] = (
    "creation_expression",
    "analysis_conceptual",
    "technical_manual",
    "physical_bodily",
    "social_collective",
    "organization_management",
)

QUESTION_GROUPS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


class DimensionVector(BaseModel):
    """Six-dimension interest profile on a 0–4 scale."""

    creation_expression: float = Field(..., ge=0, le=4)
    analysis_conceptual: float = Field(..., ge=0, le=4)
    technical_manual: float = Field(..., ge=0, le=4)
    physical_bodily: float = Field(..., ge=0, le=4)
    social_collective: float = Field(..., ge=0, le=4)
    organization_management: float = Field(..., ge=0, le=4)


class JobRecord(BaseModel):
    """Structured job entry from jobs_30_core / jobs_40_client JSON."""

    job_id: str
    job_label: str
    scores: DimensionVector
    short_description: str


class RankedJob(BaseModel):
    """Numeric fit from Python scoring (before LLM explanations)."""

    job_id: str
    job_label: str
    score: int = Field(..., ge=0, le=100)
    mean_distance: float = Field(..., ge=0, le=4)


class TopJobResult(BaseModel):
    """One ranked job with user-facing explanation."""

    job_id: str
    job_label: str
    score: int = Field(..., ge=0, le=100)
    reason: str


class AssessmentResult(BaseModel):
    """Full v2 assessment payload for persistence and API."""

    user_dimension_vector: DimensionVector
    top_jobs: list[TopJobResult] = Field(..., min_length=1)
    summary: str

    @field_validator("top_jobs")
    @classmethod
    def validate_top_jobs_count(cls, value: list[TopJobResult]) -> list[TopJobResult]:
        if len(value) > 5:
            raise ValueError("top_jobs must contain at most 5 entries")
        return value


class TopJobExplanation(BaseModel):
    job_id: str
    reason: str


class LLMExplanationOutput(BaseModel):
    """JSON returned by the LLM for explanations only (ranks fixed by Python)."""

    top_jobs: list[TopJobExplanation]
    summary: str


# --- Legacy MVP models (used until API / Sheets migration is complete) ---


class LLMInput(BaseModel):
    answers: dict[str, str] = Field(..., description="Question id → answer text or option key")
    job_list: list[str]


class TopJob(BaseModel):
    job: str
    score: int = Field(..., ge=0, le=100)
    reason: str


class LLMOutput(BaseModel):
    scores: dict[str, int]
    top_jobs: list[TopJob]
    summary: str


class ResultsResponse(BaseModel):
    email: str
    user_dimension_vector: DimensionVector | None = None
    top_jobs: list[TopJobResult]
    summary: str
    job_set: JobSetName | None = None


class ErrorResponse(BaseModel):
    detail: str
