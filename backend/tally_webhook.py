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
    received_labels: list[str] = []

    for field in fields:
        if not isinstance(field, dict):
            continue
        raw_label = _field_label(field)
        if raw_label:
            received_labels.append(raw_label)
        label = _normalize_label(raw_label)
        value = extract_field_value(field)
        if value is None:
            continue

        if _labels_match(label, email_label):
            email = value
            continue

        if field.get("type") in EMAIL_FIELD_TYPES and email_fallback is None:
            email_fallback = value

        matched_column = _match_question_column(label, question_labels)
        if matched_column:
            answers[matched_column] = value

    if not email:
        email = email_fallback
    if not email:
        raise ValueError(
            f'No email field found (expected label "{settings.email_column}"). '
            f"Received labels: {_format_label_sample(received_labels)}"
        )

    missing = [column for column in settings.question_columns if column not in answers]
    if missing:
        raise ValueError(
            "Missing questionnaire answers for: "
            + ", ".join(missing[:8])
            + ("..." if len(missing) > 8 else "")
            + ". Set QUESTION_COLUMNS in Render to match Tally field labels exactly, "
            "or rename Tally questions / calculated fields to A1..F8. "
            f"Received labels: {_format_label_sample(received_labels)}"
        )

    return {
        "email": email.strip(),
        "answers": answers,
        "submission_id": data.get("submissionId") or data.get("responseId"),
        "form_id": data.get("formId"),
    }


def _field_label(field: dict[str, Any]) -> str:
    for key in ("label", "title", "name"):
        value = field.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _labels_match(normalized_label: str, normalized_target: str) -> bool:
    if not normalized_label or not normalized_target:
        return False
    if normalized_label == normalized_target:
        return True
    return normalized_label.startswith(normalized_target + " ") or normalized_label.startswith(
        normalized_target + "."
    )


def _match_question_column(
    normalized_label: str,
    question_labels: dict[str, str],
) -> str | None:
    if normalized_label in question_labels:
        return question_labels[normalized_label]
    for key, column in question_labels.items():
        if _labels_match(normalized_label, key):
            return column
    return None


def _format_label_sample(labels: list[str], limit: int = 12) -> str:
    unique = list(dict.fromkeys(label for label in labels if label))
    if not unique:
        return "(none)"
    sample = unique[:limit]
    text = ", ".join(sample)
    if len(unique) > limit:
        text += f", ... ({len(unique)} total)"
    return text


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
            return _normalize_score_text(text)
        if selected is not None and str(selected).strip():
            return _normalize_score_text(str(selected).strip())
    return None


def _normalize_score_text(text: str) -> str:
    """Map Tally option text like '3' or 'Plutôt (3)' to a score string."""
    stripped = text.strip()
    if stripped.isdigit() and len(stripped) == 1:
        return stripped
    for char in stripped:
        if char.isdigit():
            return char
    return stripped


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().casefold().split())
