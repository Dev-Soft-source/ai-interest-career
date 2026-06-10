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
from tally_webhook import normalize_score_text, parse_tally_submission, verify_tally_signature


@pytest.fixture(autouse=True)
def reset_mock_state(monkeypatch: pytest.MonkeyPatch):
    sheets_client._MOCK_STORE.clear()
    sheets_client._MOCK_ROWS_STATE = None
    monkeypatch.setenv("USE_MOCK_SHEETS", "true")
    monkeypatch.setenv("EMAIL_COLUMN", "Votre email")
    monkeypatch.setenv("TALLY_WEBHOOK_SECRET", "")
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
    assert verify_tally_signature(body, "bad-signature", secret) is False
    # Tally may sign the raw request bytes on the wire.
    raw_body = b'{"eventType":"FORM_RESPONSE","data":{"fields":[]}}'
    raw_sig = base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("ascii")
    assert verify_tally_signature(raw_body, raw_sig, secret)


def test_tally_webhook_appends_row(client: TestClient):
    payload = _sample_tally_payload("webhook@example.com")
    response = client.post("/api/tally-webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["email"] == "webhook@example.com"

    sheets = sheets_client.SheetsClient(get_settings())
    row = sheets.get_response_by_email("webhook@example.com")
    assert row is not None
    assert row.answers["B3"] == "2"


def _raw_french_payload(email: str = "raw@example.com") -> dict:
    fields: list[dict] = [
        {
            "key": "question_email",
            "label": "Votre email",
            "type": "INPUT_EMAIL",
            "value": email,
        }
    ]
    for index in range(1, 49):
        fields.append(
            {
                "key": f"question_q{index}",
                "label": f"Intérêt professionnel {index}",
                "type": "MULTIPLE_CHOICE",
                "value": ["opt-3"],
                "options": [
                    {"id": "opt-0", "text": "Pas du tout (0)"},
                    {"id": "opt-1", "text": "Un peu (1)"},
                    {"id": "opt-2", "text": "Moyennement (2)"},
                    {"id": "opt-3", "text": "Plutôt (3)"},
                    {"id": "opt-4", "text": "Tout à fait (4)"},
                ],
            }
        )
    return {
        "eventId": "evt-raw",
        "eventType": "FORM_RESPONSE",
        "createdAt": "2026-05-22T12:00:00.000Z",
        "data": {
            "responseId": "resp-raw",
            "submissionId": "resp-raw",
            "formId": "form-raw",
            "formName": "Career test",
            "fields": fields,
        },
    }


def test_map_raw_tally_fields_by_order():
    settings = Settings(email_column="Votre email", tally_map_raw_by_order=True)
    parsed = parse_tally_submission(_raw_french_payload(), settings)
    assert parsed["email"] == "raw@example.com"
    assert parsed["answers"]["A1"] == "3"
    assert parsed["answers"]["F8"] == "3"
    assert len(parsed["answers"]) == 48


def test_normalize_score_text_handles_french_options():
    assert normalize_score_text("Plutôt (3)") == "3"
    assert normalize_score_text("Pas du tout (0)") == "0"
    assert normalize_score_text("Tout à fait (4)") == "4"


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
