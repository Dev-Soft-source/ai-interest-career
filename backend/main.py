"""FastAPI app: career results API + static results page."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from models import DimensionVector, ProcessRequest, ProcessSummary, ResultsResponse, TopJobResult
from scoring_engine import process_pending
from sheets_client import SheetsClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
load_dotenv(ROOT / ".env")

app = FastAPI(title="Career Interest Test API", version="0.2.0")


@app.on_event("startup")
def _refresh_settings() -> None:
    get_settings.cache_clear()
    get_settings()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def to_results_response(raw: dict[str, Any]) -> ResultsResponse:
    top_jobs = [TopJobResult.model_validate(_normalize_top_job(item)) for item in raw["top_jobs"]]
    vector = None
    if raw.get("user_dimension_vector"):
        vector = DimensionVector.model_validate(raw["user_dimension_vector"])
    return ResultsResponse(
        email=raw["email"],
        user_dimension_vector=vector,
        top_jobs=top_jobs,
        summary=raw["summary"],
    )


def _normalize_top_job(item: dict[str, Any]) -> dict[str, Any]:
    if "job_label" in item:
        return {
            "job_id": item.get("job_id", ""),
            "job_label": item["job_label"],
            "score": item.get("score", 0),
            "reason": item.get("reason", ""),
        }
    if "job" in item:
        return {
            "job_id": item.get("job_id", ""),
            "job_label": item["job"],
            "score": item.get("score", 0),
            "reason": item.get("reason", ""),
        }
    raise ValueError("top_jobs entry must include job_label or job")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/results", response_model=ResultsResponse)
def get_results(email: str = Query(..., description="Respondent email (same as in Tally / Sheets)")):
    settings = get_settings()
    sheets = SheetsClient(settings)
    raw = sheets.get_result_by_email(email)
    if not raw:
        raise HTTPException(
            status_code=404,
            detail="No results yet for this email. Submit the form, then run POST /api/process or wait for processing.",
        )
    try:
        return to_results_response(raw)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Stored results are invalid: {exc}") from exc


@app.post("/api/process", response_model=ProcessSummary)
def post_process(body: ProcessRequest | None = None):
    """Process unprocessed response rows (optionally filter by email)."""
    settings = get_settings()
    sheets = SheetsClient(settings)
    email = body.email if body else None
    result = process_pending(sheets, email=email)
    return ProcessSummary(processed=result["processed"], errors=result["errors"])


def _results_page_path() -> Path | None:
    for name in ("results.html", "index.html"):
        path = FRONTEND_DIR / name
        if path.is_file():
            return path
    return None


@app.get("/results.html")
def results_page():
    path = _results_page_path()
    if path is None:
        raise HTTPException(status_code=404, detail="results page not found")
    return FileResponse(path, media_type="text/html")


@app.get("/")
def index():
    path = _results_page_path()
    if path is not None:
        return FileResponse(path, media_type="text/html")
    return {"message": "Career API — see GET /results.html?email=..."}
