"""Orchestrate: answers → assessment → persist results."""

from __future__ import annotations

import logging

from llm_service import call_assessment
from models import AssessmentResult
from response_validation import validate_response_answers
from sheets_client import SheetsClient

logger = logging.getLogger(__name__)


def assess_for_email(sheets: SheetsClient, email: str) -> AssessmentResult:
    row = sheets.get_response_by_email(email)
    if row is None:
        raise ValueError("No response row found for this email in Google Sheets")

    answers = validate_response_answers(row.answers, sheets.settings.question_columns)
    result = call_assessment(answers, settings=sheets.settings)
#    if sheets.settings.write_results_sheet:
#        sheets.upsert_result(email=row.email, result=result)
    return result
