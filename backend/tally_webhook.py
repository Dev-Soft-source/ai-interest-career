"""Parse and verify Tally form submission webhooks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from typing import Any

from config import Settings

logger = logging.getLogger(__name__)

EMAIL_FIELD_TYPES = frozenset({"INPUT_EMAIL"})


def verify_tally_signature(body: bytes, signature: str | None, secret: str) -> bool:
    """Verify Tally-Signature header (SHA256 HMAC, base64)."""
    if not signature or not secret:
        return False

    secret_bytes = secret.encode("utf-8")
    candidates: list[bytes] = [body]

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        candidates.extend(
            [
                json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
                json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"),
            ]
        )

    for material in candidates:
        calculated = base64.b64encode(
            hmac.new(secret_bytes, material, hashlib.sha256).digest()
        ).decode("ascii")
        if hmac.compare_digest(calculated, signature):
            return True
    return False


def parse_tally_submission(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """
    Extract email and questionnaire answers from a Tally FORM_RESPONSE webhook.

    Fields are matched to sheet columns by label (case-insensitive), using
    settings.email_column and settings.question_columns.
    """
    if payload.get("eventType") != "FORM_RESPONSE":
        raise ValueError(f'Unsupported event type: {payload.get("eventType")!r}')

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Missing data object in webhook payload")

    fields = data.get("fields")
    if not isinstance(fields, list):
        raise ValueError("Missing fields array in webhook payload")

    email_label = _normalize_label(settings.email_column)
    question_labels = {_normalize_label(column): column for column in settings.question_columns}

    email: str | None = None
    email_fallback: str | None = None
    answers: dict[str, str] = {}

    for field in fields:
        if not isinstance(field, dict):
            continue
        label = _normalize_label(str(field.get("label") or ""))
        value = extract_field_value(field)
        if value is None:
            continue

        if label == email_label:
            email = value
            continue

        if field.get("type") in EMAIL_FIELD_TYPES and email_fallback is None:
            email_fallback = value

        if label in question_labels:
            answers[question_labels[label]] = value

    if not email:
        email = email_fallback
    if not email:
        raise ValueError(f'No email field found (expected label "{settings.email_column}")')

    missing = [column for column in settings.question_columns if column not in answers]
    if missing:
        raise ValueError(
            "Missing questionnaire answers for: "
            + ", ".join(missing[:8])
            + ("..." if len(missing) > 8 else "")
            + ". Match Tally question labels to QUESTION_COLUMNS or name fields A1..F8."
        )

    return {
        "email": email.strip(),
        "answers": answers,
        "submission_id": data.get("submissionId") or data.get("responseId"),
        "form_id": data.get("formId"),
    }


def extract_field_value(field: dict[str, Any]) -> str | None:
    """Normalize a Tally field value to a string suitable for Sheets."""
    raw = field.get("value")
    if raw is None or raw == "":
        return None

    field_type = field.get("type")

    if field_type in {"INPUT_EMAIL", "INPUT_TEXT", "INPUT_NUMBER", "LINEAR_SCALE", "RATING"}:
        return str(raw).strip()

    if field_type == "CALCULATED_FIELDS":
        return str(raw).strip()

    if field_type in {"MULTIPLE_CHOICE", "DROPDOWN", "MULTI_SELECT"}:
        return _choice_value(field, raw)

    if isinstance(raw, (int, float, bool)):
        return str(raw)

    if isinstance(raw, str):
        return raw.strip()

    return None


def _choice_value(field: dict[str, Any], raw: Any) -> str | None:
    options = field.get("options") or []
    id_to_text = {
        str(option.get("id")): str(option.get("text", "")).strip()
        for option in options
        if isinstance(option, dict) and option.get("id") is not None
    }
    selected_ids = raw if isinstance(raw, list) else [raw]
    for selected in selected_ids:
        text = id_to_text.get(str(selected), "").strip()
        if text:
            return text
        if selected is not None and str(selected).strip():
            return str(selected).strip()
    return None


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().casefold().split())
