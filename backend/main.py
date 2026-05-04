"""FastAPI app: career results API + static results page."""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.models import ProcessRequest, ProcessSummary, ResultsResponse, TopJob
from backend.scoring_engine import process_pending
from backend.sheets_client import SheetsClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
load_dotenv(ROOT / ".env")

app = FastAPI(title="Career Interest Test API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


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
    top = [TopJob.model_validate(j) for j in raw["top_jobs"]]
    return ResultsResponse(
        email=raw["email"],
        scores=raw["scores"],
        top_jobs=top,
        summary=raw["summary"],
    )


@app.post("/api/process", response_model=ProcessSummary)
def post_process(body: ProcessRequest | None = None):
    """Process unprocessed response rows (optionally filter by email)."""
    settings = get_settings()
    sheets = SheetsClient(settings)
    email = body.email if body else None
    result = process_pending(sheets, email=email)
    return ProcessSummary(processed=result["processed"], errors=result["errors"])


@app.get("/results.html")
def results_page():
    path = FRONTEND_DIR / "results.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="results.html not found")
    return FileResponse(path, media_type="text/html")


@app.get("/")
def index():
    path = FRONTEND_DIR / "results.html"
    if path.is_file():
        return FileResponse(path, media_type="text/html")
    return {"message": "Career API — see GET /results.html?email=..."}
