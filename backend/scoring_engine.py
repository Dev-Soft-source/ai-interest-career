"""Orchestrate: answers → LLM → persist results."""

from __future__ import annotations

import logging
from typing import Any

from backend.llm_service import call_llm
from backend.models import LLMOutput
from backend.sheets_client import ResponseRow, SheetsClient
from backend.utils import normalize_email

logger = logging.getLogger(__name__)


def process_user_response(row: ResponseRow, sheets: SheetsClient) -> LLMOutput:
    answers = extract_answers(row)
    output = call_llm(answers)
    top_jobs = [j.model_dump() for j in output.top_jobs]
    sheets.upsert_result(
        email=row.email,
        top_jobs=top_jobs,
        scores=output.scores,
        summary=output.summary,
    )
    sheets.mark_processed(row.row_number, "TRUE")
    return output


def extract_answers(row: ResponseRow) -> dict[str, str]:
    return {k: v for k, v in row.answers.items() if v}


def process_pending(
    sheets: SheetsClient,
    email: str | None = None,
) -> dict[str, Any]:
    rows = sheets.list_response_rows()
    if email:
        target = normalize_email(email)
        rows = [r for r in rows if normalize_email(r.email) == target]
        if not rows:
            return {
                "processed": [],
                "errors": [{"email": email, "error": "No response row found for this email in Google Sheets"}],
            }

    processed: list[str] = []
    errors: list[dict[str, Any]] = []

    for row in rows:
        if row.processed_raw in ("true", "1", "yes"):
            continue
        if not any(row.answers.values()):
            errors.append({"email": row.email, "error": "No answer values in configured question columns"})
            continue
        try:
            process_user_response(row, sheets)
            processed.append(row.email)
        except Exception as e:
            logger.exception("Failed to process %s", row.email)
            errors.append({"email": row.email, "error": str(e)})

    return {"processed": processed, "errors": errors}
