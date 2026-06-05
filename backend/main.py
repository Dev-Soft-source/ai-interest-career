"""FastAPI app: career results API + static results page."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from config import REPO_ROOT, get_settings, resolve_job_set, settings_for_job_set
from models import AssessmentResult, DimensionVector, JobSetName, ResultsResponse, TopJobResult
from scoring_engine import assess_for_email
from sheets_client import SheetsClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = REPO_ROOT
FRONTEND_DIR = ROOT / "frontend"
load_dotenv(ROOT / ".env")

app = FastAPI(title="Career Interest Test API", version="0.2.0")


@app.on_event("startup")
def _refresh_settings() -> None:
    get_settings.cache_clear()
    get_settings()

origins = [
   "https://ai-interest-career.onrender.com",  # frontend ngrok URL
   #"http://localhost:8000",  # frontend ngrok URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or only your ngrok frontend URL
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
    job_set = raw.get("job_set")
    return ResultsResponse(
        email=raw["email"],
        user_dimension_vector=vector,
        top_jobs=top_jobs,
        summary=raw["summary"],
        job_set=job_set,
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


def _assessment_to_raw(email: str, result: AssessmentResult, job_set: JobSetName) -> dict[str, Any]:
    return {
        "email": email,
        "user_dimension_vector": result.user_dimension_vector.model_dump(),
        "top_jobs": [job.model_dump() for job in result.top_jobs],
        "summary": result.summary,
        "job_set": job_set,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    path = FRONTEND_DIR / "favicon.ico"
    if path.is_file():
        return FileResponse(path, media_type="image/x-icon")
    return Response(status_code=404)


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon():
    path = FRONTEND_DIR / "apple-touch-icon.png"
    if path.is_file():
        return FileResponse(path, media_type="image/png")
    return Response(status_code=404)


def _frontend_file(name: str, media_type: str) -> FileResponse | Response:
    path = FRONTEND_DIR / name
    if path.is_file():
        return FileResponse(path, media_type=media_type)
    return Response(status_code=404)


@app.get("/styles.css", include_in_schema=False)
def styles_css():
    return _frontend_file("styles.css", "text/css; charset=utf-8")


@app.get("/app.js", include_in_schema=False)
def app_js():
    return _frontend_file("app.js", "application/javascript; charset=utf-8")


@app.get("/favicon.svg", include_in_schema=False)
def favicon_svg():
    return _frontend_file("favicon.svg", "image/svg+xml")


@app.get("/api/results", response_model=ResultsResponse)
def get_results(
    email: str = Query(..., description="Respondent email (same as in Tally / Sheets)"),
    job_set: JobSetName | None = Query(
        None,
        description="Job catalog: core_30 (jobs_30_core.json) or client_40 (jobs_40_client.json)",
    ),
):
    resolved_job_set = resolve_job_set(job_set)
    settings = settings_for_job_set(get_settings(), resolved_job_set)
    sheets = SheetsClient(settings)
    try:
        result = assess_for_email(sheets, email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to assess %s", email)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    raw = _assessment_to_raw(email, result, resolved_job_set)
    try:
        return to_results_response(raw)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid assessment payload: {exc}") from exc


def _results_page_path() -> Path | None:
    path = FRONTEND_DIR / "results.html"
    return path if path.is_file() else None


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
