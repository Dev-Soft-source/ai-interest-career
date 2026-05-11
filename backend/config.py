"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from models import QUESTION_GROUPS

REPO_ROOT = Path(__file__).resolve().parent.parent


def default_question_columns() -> list[str]:
    """Tally / Sheets headers for the 48-item questionnaire (A1..F8)."""
    columns: list[str] = []
    for group in QUESTION_GROUPS:
        columns.extend(f"{group}{index}" for index in range(1, 9))
    return columns


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = Field(default="gemini", description="openai | gemini")
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    llm_temperature: float = Field(default=0.3, ge=0.0, le=1.0)

    # Google Sheets (service account JSON path)
    google_service_account_file: str | None = None
    spreadsheet_id: str | None = None
    responses_sheet_name: str = "Responses"
    results_sheet_name: str = "Results"

    # Column names (must match Tally → Sheets export headers)
    email_column: str = "email"
    question_columns: list[str] = Field(default_factory=default_question_columns)
    processed_column: str = "processed"

    # Results sheet columns
    results_email_column: str = "email"
    results_top_jobs_column: str = "top_jobs"
    results_scores_column: str = "scores_json"
    results_summary_column: str = "summary"
    results_user_vector_column: str = "user_dimension_vector"

    # Jobs catalog (structured JSON with 6D vectors)
    jobs_file: str | None = None
    job_set: Literal["core_30", "client_40"] = "core_30"
    top_k: int = Field(default=5, ge=1, le=5)
    enforce_core_job_whitelist: bool = False
    core_job_whitelist: str | None = Field(
        default=None,
        description="Comma-separated job_id values; used when enforce_core_job_whitelist is true",
    )

    # Dev: skip Sheets and use sample data (see README)
    use_mock_sheets: bool = False

    @field_validator("google_service_account_file", "jobs_file", mode="before")
    @classmethod
    def resolve_repo_relative_path(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        path = Path(str(value))
        if not path.is_absolute():
            path = REPO_ROOT / path
        return str(path)

    @field_validator("question_columns", mode="before")
    @classmethod
    def parse_question_columns(cls, value: object) -> list[str]:
        if value is None or value == "":
            return default_question_columns()
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value  # type: ignore[return-value]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_llm_provider(settings: Settings) -> str:
    """Pick the configured provider, or the provider that has an API key set."""
    preferred = (settings.llm_provider or "gemini").strip().lower()
    if preferred == "gemini" and settings.gemini_api_key:
        return "gemini"
    if preferred == "openai" and settings.openai_api_key:
        return "openai"
    if settings.gemini_api_key:
        return "gemini"
    if settings.openai_api_key:
        return "openai"
    raise RuntimeError(
        "No LLM API key configured. Set GEMINI_API_KEY or OPENAI_API_KEY in .env."
    )


def load_job_list(settings: Settings | None = None) -> list[str]:
    """Legacy helper: job labels for the pre-migration LLM prompt path."""
    from job_loader import load_job_labels

    return load_job_labels(settings or get_settings())
