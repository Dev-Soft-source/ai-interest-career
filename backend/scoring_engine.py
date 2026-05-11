"""Orchestrate: answers → LLM → persist results."""

from __future__ import annotations

import logging
from typing import Any

from llm_service import call_assessment
from models import AssessmentResult
from response_validation import validate_response_answers
from sheets_client import ResponseRow, SheetsClient
from utils import normalize_email

logger = logging.getLogger(__name__)


def process_user_response(row: ResponseRow, sheets: SheetsClient) -> AssessmentResult:
    settings = sheets.settings
    answers = validate_response_answers(row.answers, settings.question_columns)
    result = call_assessment(answers, settings=settings)
    sheets.upsert_result(email=row.email, result=result)
    sheets.mark_processed(row.row_number, "TRUE")
    return result


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
        try:
            process_user_response(row, sheets)
            processed.append(row.email)
        except Exception as e:
            logger.exception("Failed to process %s", row.email)
            errors.append({"email": row.email, "error": str(e)})

    return {"processed": processed, "errors": errors}
