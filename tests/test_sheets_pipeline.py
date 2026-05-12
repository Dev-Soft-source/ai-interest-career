from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from config import default_question_columns
from response_validation import validate_response_answers
from sheets_client import MOCK_SAMPLE_1_ANSWERS, SheetsClient, _normalize_top_job, _parse_result_row
from config import Settings


def test_validate_response_answers_accepts_sample_1():
    answers = validate_response_answers(MOCK_SAMPLE_1_ANSWERS, default_question_columns())
    assert answers["A1"] == "1"
    assert answers["F8"] == "2"


def test_validate_response_answers_rejects_missing_item():
    incomplete = dict(MOCK_SAMPLE_1_ANSWERS)
    del incomplete["C8"]
    with pytest.raises(ValueError, match="C8"):
        validate_response_answers(incomplete, default_question_columns())


def test_validate_response_answers_rejects_out_of_range():
    invalid = dict(MOCK_SAMPLE_1_ANSWERS)
    invalid["B1"] = "9"
    with pytest.raises(ValueError, match="B1"):
        validate_response_answers(invalid, default_question_columns())


def test_parse_result_row_reads_v2_fields():
    settings = Settings()
    headers = [
        settings.results_email_column,
        settings.results_user_vector_column,
        settings.results_top_jobs_column,
        settings.results_summary_column,
    ]
    row = [
        "demo@example.com",
        '{"creation_expression": 1.0, "analysis_conceptual": 3.25, "technical_manual": 2.0, "physical_bodily": 0.38, "social_collective": 1.5, "organization_management": 2.38}',
        '[{"job_id": "DEV_WEB", "job_label": "Web Developer", "score": 90, "reason": "Fit."}]',
        "Summary text.",
    ]
    data = _parse_result_row(row, headers, settings)
    assert data["email"] == "demo@example.com"
    assert data["summary"] == "Summary text."
    assert data["top_jobs"][0]["job_label"] == "Web Developer"
    assert data["top_jobs"][0]["score"] == 90
    assert data["user_dimension_vector"]["analysis_conceptual"] == 3.25


def test_response_headers_without_processed_are_allowed():
    client = SheetsClient(Settings())
    headers = ["email", *default_question_columns()]
    client._validate_response_headers(headers)


def test_normalize_top_job_accepts_v2_shape():
    normalized = _normalize_top_job(
        {"job_id": "DEV_WEB", "job_label": "Web Developer", "score": 88, "reason": "Reason."}
    )
    assert normalized["job_label"] == "Web Developer"
    assert normalized["job_id"] == "DEV_WEB"
