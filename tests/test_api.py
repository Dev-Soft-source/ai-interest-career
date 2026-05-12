from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import sheets_client
from config import get_settings
from main import app
from models import AssessmentResult, DimensionVector, TopJobResult


@pytest.fixture(autouse=True)
def reset_mock_state(monkeypatch: pytest.MonkeyPatch):
    sheets_client._MOCK_STORE.clear()
    sheets_client._MOCK_ROWS_STATE = None
    monkeypatch.setenv("USE_MOCK_SHEETS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _sample_assessment() -> AssessmentResult:
    vector = DimensionVector(
        creation_expression=1.0,
        analysis_conceptual=3.25,
        technical_manual=2.0,
        physical_bodily=0.38,
        social_collective=1.5,
        organization_management=2.38,
    )
    return AssessmentResult(
        user_dimension_vector=vector,
        top_jobs=[
            TopJobResult(
                job_id="DEV_WEB",
                job_label="Web Developer",
                score=90,
                reason="Strong analytical and technical fit.",
            )
        ],
        summary="Analytical profile.",
    )


def test_get_results_404_when_missing(client: TestClient):
    response = client.get("/api/results", params={"email": "missing@example.com"})
    assert response.status_code == 404


@patch("scoring_engine.call_assessment", return_value=_sample_assessment())
def test_get_results_assesses_on_each_request(mock_call, client: TestClient):
    results = client.get("/api/results", params={"email": "demo@example.com"})
    assert results.status_code == 200
    mock_call.assert_called_once()

    payload = results.json()
    assert payload["email"] == "demo@example.com"
    assert payload["summary"] == "Analytical profile."
    assert payload["top_jobs"][0]["job_label"] == "Web Developer"
    assert payload["user_dimension_vector"]["analysis_conceptual"] == 3.25
    assert payload["job_set"] == "core_30"

    client.get("/api/results", params={"email": "demo@example.com"})
    assert mock_call.call_count == 2


@patch("scoring_engine.call_assessment", return_value=_sample_assessment())
def test_get_results_uses_requested_job_set(mock_call, client: TestClient):
    response = client.get(
        "/api/results",
        params={"email": "demo@example.com", "job_set": "client_40"},
    )
    assert response.status_code == 200
    called_settings = mock_call.call_args.kwargs["settings"]
    assert called_settings.job_set == "client_40"
