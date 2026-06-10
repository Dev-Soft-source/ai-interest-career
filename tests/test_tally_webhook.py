from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import sheets_client
from config import Settings, default_question_columns, get_settings
from main import app
from tally_webhook import parse_tally_submission, verify_tally_signature


@pytest.fixture(autouse=True)
def reset_mock_state(monkeypatch: pytest.MonkeyPatch):
    sheets_client._MOCK_STORE.clear()
    sheets_client._MOCK_ROWS_STATE = None
    monkeypatch.setenv("USE_MOCK_SHEETS", "true")
    monkeypatch.setenv("EMAIL_COLUMN", "Votre email")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _sign_payload(payload: dict, secret: str) -> str:
    canonical = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")


def _sample_tally_payload(email: str = "tester@example.com") -> dict:
    fields: list[dict] = [
        {
            "key": "question_email",
            "label": "Votre email",
            "type": "INPUT_EMAIL",
            "value": email,
        }
    ]
    for column in default_question_columns():
        fields.append(
            {
                "key": f"question_{column}",
                "label": column,
                "type": "LINEAR_SCALE",
                "value": 2,
            }
        )
    return {
        "eventId": "evt-1",
        "eventType": "FORM_RESPONSE",
        "createdAt": "2026-05-22T12:00:00.000Z",
        "data": {
            "responseId": "resp-1",
            "submissionId": "resp-1",
            "formId": "form-1",
            "formName": "Career test",
            "fields": fields,
        },
    }


def test_parse_tally_submission_maps_email_and_answers():
    settings = Settings(email_column="Votre email")
    parsed = parse_tally_submission(_sample_tally_payload(), settings)
    assert parsed["email"] == "tester@example.com"
    assert parsed["answers"]["A1"] == "2"
    assert len(parsed["answers"]) == 48


def test_verify_tally_signature():
    payload = _sample_tally_payload()
    secret = "test-secret"
    signature = _sign_payload(payload, secret)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    assert verify_tally_signature(body, signature, secret)
    assert not verify_tally_signature(body, "bad-signature", secret)


def test_tally_webhook_appends_row(client: TestClient):
    payload = _sample_tally_payload("webhook@example.com")
    response = client.post("/api/tally-webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["email"] == "webhook@example.com"

    sheets = sheets_client.SheetsClient(get_settings())
    row = sheets.get_response_by_email("webhook@example.com")
    assert row is not None
    assert row.answers["B3"] == "2"


def test_tally_webhook_requires_signature_when_secret_set(client: TestClient, monkeypatch):
    monkeypatch.setenv("TALLY_WEBHOOK_SECRET", "prod-secret")
    get_settings.cache_clear()

    payload = _sample_tally_payload("secure@example.com")
    unsigned = client.post("/api/tally-webhook", json=payload)
    assert unsigned.status_code == 401

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    signed = client.post(
        "/api/tally-webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "Tally-Signature": _sign_payload(payload, "prod-secret"),
        },
    )
    assert signed.status_code == 200
