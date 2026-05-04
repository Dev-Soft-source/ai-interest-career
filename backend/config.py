"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = Field(default="openai", description="openai | gemini")
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    # Google Sheets (service account JSON path)
    google_service_account_file: str | None = None
    spreadsheet_id: str | None = None
    responses_sheet_name: str = "Responses"
    results_sheet_name: str = "Results"

    # Column names (must match Tally → Sheets export headers)
    email_column: str = "email"
    question_columns: list[str] = Field(default_factory=lambda: ["Q1", "Q2", "Q3"])
    processed_column: str = "processed"

    # Results sheet columns
    results_email_column: str = "email"
    results_top_jobs_column: str = "top_jobs"
    results_scores_column: str = "scores_json"
    results_summary_column: str = "summary"

    # Optional: path to JSON file with {"jobs": ["Job A", ...]} — overrides built-in defaults if set
    jobs_file: str | None = None

    # Dev: skip Sheets and use sample data (see README)
    use_mock_sheets: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


def default_jobs() -> list[str]:
    return [
        "Software Engineer",
        "Data Analyst",
        "UX Designer",
        "Product Manager",
        "Marketing Specialist",
        "HR / People Operations",
        "Sales Representative",
        "Project Manager",
    ]


def load_job_list(settings: Settings) -> list[str]:
    if settings.jobs_file:
        path = Path(settings.jobs_file)
        if path.is_file():
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            jobs = data.get("jobs") if isinstance(data, dict) else data
            if isinstance(jobs, list) and all(isinstance(j, str) for j in jobs):
                return jobs
    return default_jobs()
