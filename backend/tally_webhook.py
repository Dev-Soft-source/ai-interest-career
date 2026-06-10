"""Parse and verify Tally form submission webhooks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
from typing import Any

from config import Settings

logger = logging.getLogger(__name__)

EMAIL_FIELD_TYPES = frozenset({"INPUT_EMAIL"})
SCORABLE_FIELD_TYPES = frozenset(
    {"LINEAR_SCALE", "RATING", "MULTIPLE_CHOICE", "DROPDOWN", "MULTI_SELECT"}
)
SKIP_FIELD_TYPES = frozenset(
    {
        "HIDDEN_FIELDS",
        "CALCULATED_FIELDS",
        "CHECKBOXES",
        "FILE_UPLOAD",
        "PAYMENT",
        "SIGNATURE",
        "MATRIX",
        "RANKING",
        "INPUT_TEXT",
        "TEXTAREA",
        "INPUT_LINK",
        "INPUT_PHONE_NUMBER",
        "INPUT_DATE",
        "INPUT_TIME",
        "INPUT_NUMBER",
    }
)


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

    Answers are stored as A1..F8 for Google Sheets. Mapping order:
    1) Sheet column labels (EMAIL_COLUMN, QUESTION_COLUMNS / A1..F8)
    2) TALLY_FIELD_LABELS (48 Tally labels in A1..F8 order)
    3) Raw Tally scale questions mapped by form field order (TALLY_MAP_RAW_BY_ORDER)
    """
    if payload.get("eventType") != "FORM_RESPONSE":
        raise ValueError(f'Unsupported event type: {payload.get("eventType")!r}')

    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Missing data object in webhook payload")

    fields = data.get("fields")
    if not isinstance(fields, list):
        raise ValueError("Missing fields array in webhook payload")

    received_labels = [_field_label(field) for field in fields if isinstance(field, dict)]
    received_labels = [label for label in received_labels if label]

    email = _extract_email(fields, settings)
    answers = _map_answers_by_column_labels(fields, settings)
    answers = _fill_answers_from_tally_field_labels(fields, settings, answers)

    missing = [column for column in settings.question_columns if column not in answers]
    if missing and settings.tally_map_raw_by_order:
        raw_answers = _map_answers_by_field_order(fields, settings)
        if raw_answers:
            logger.info(
                "Mapped %d raw Tally scale fields to A1..F8 by form order",
                len(raw_answers),
            )
            answers = raw_answers
            missing = [column for column in settings.question_columns if column not in answers]

    if missing:
        scorable = _collect_scorable_fields(fields, settings)
        raise ValueError(
            "Missing questionnaire answers for: "
            + ", ".join(missing[:8])
            + ("..." if len(missing) > 8 else "")
            + ". Remove A1..F8 calculated fields from Tally and use raw scale questions, "
            "or set TALLY_FIELD_LABELS to your 48 question labels in order. "
            f"Scorable fields found: {len(scorable)} (need {len(settings.question_columns)}). "
            f"Received labels: {_format_label_sample(received_labels)}"
        )

    normalized_answers = {
        column: _coerce_score(answers[column], column) for column in settings.question_columns
    }

    return {
        "email": email.strip(),
        "answers": normalized_answers,
        "submission_id": data.get("submissionId") or data.get("responseId"),
        "form_id": data.get("formId"),
    }


def _extract_email(fields: list[Any], settings: Settings) -> str:
    email_label = _normalize_label(settings.email_column)
    email: str | None = None
    email_fallback: str | None = None

    for field in fields:
        if not isinstance(field, dict):
            continue
        label = _normalize_label(_field_label(field))
        value = extract_field_value(field)
        if value is None:
            continue
        if _labels_match(label, email_label):
            email = value
            break
        if field.get("type") in EMAIL_FIELD_TYPES and email_fallback is None:
            email_fallback = value

    if not email:
        email = email_fallback
    if not email:
        labels = [_field_label(field) for field in fields if isinstance(field, dict)]
        raise ValueError(
            f'No email field found (expected label "{settings.email_column}"). '
            f"Received labels: {_format_label_sample(labels)}"
        )
    return email


def _map_answers_by_column_labels(fields: list[Any], settings: Settings) -> dict[str, str]:
    question_labels = {_normalize_label(column): column for column in settings.question_columns}
    answers: dict[str, str] = {}

    for field in fields:
        if not isinstance(field, dict):
            continue
        label = _normalize_label(_field_label(field))
        value = extract_field_value(field)
        if value is None:
            continue
        matched_column = _match_question_column(label, question_labels)
        if matched_column:
            answers[matched_column] = value

    return answers


def _fill_answers_from_tally_field_labels(
    fields: list[Any],
    settings: Settings,
    answers: dict[str, str],
) -> dict[str, str]:
    if not settings.tally_field_labels:
        return answers

    if len(settings.tally_field_labels) != len(settings.question_columns):
        raise ValueError(
            "TALLY_FIELD_LABELS must contain exactly "
            f"{len(settings.question_columns)} comma-separated labels (one per A1..F8)."
        )

    label_to_column = {
        _normalize_label(label): column
        for label, column in zip(settings.tally_field_labels, settings.question_columns, strict=True)
    }
    merged = dict(answers)

    for field in fields:
        if not isinstance(field, dict):
            continue
        label = _normalize_label(_field_label(field))
        column = label_to_column.get(label)
        if column is None:
            continue
        value = extract_field_value(field)
        if value is not None:
            merged[column] = value

    return merged


def _map_answers_by_field_order(fields: list[Any], settings: Settings) -> dict[str, str] | None:
    scorable = _collect_scorable_fields(fields, settings)
    expected = len(settings.question_columns)
    if len(scorable) != expected:
        return None

    answers: dict[str, str] = {}
    for column, field in zip(settings.question_columns, scorable, strict=True):
        value = extract_field_value(field)
        if value is None:
            return None
        answers[column] = value
    return answers


def _collect_scorable_fields(fields: list[Any], settings: Settings) -> list[dict[str, Any]]:
    email_label = _normalize_label(settings.email_column)
    scorable: list[dict[str, Any]] = []

    for field in fields:
        if not isinstance(field, dict):
            continue
        field_type = field.get("type")
        if field_type in SKIP_FIELD_TYPES or field_type in EMAIL_FIELD_TYPES:
            continue
        if field_type not in SCORABLE_FIELD_TYPES:
            continue
        label = _normalize_label(_field_label(field))
        if _labels_match(label, email_label):
            continue
        if extract_field_value(field) is None:
            continue
        scorable.append(field)

    return scorable


def _coerce_score(raw: str, column: str) -> str:
    score = normalize_score_text(raw)
    if score is None:
        raise ValueError(f'Could not parse score 0-4 for "{column}" from value "{raw}"')
    return score


def normalize_score_text(text: str) -> str | None:
    """Map Tally option/scale text to a score string 0-4."""
    stripped = text.strip()
    if stripped in {"0", "1", "2", "3", "4"}:
        return stripped

    paren_match = re.search(r"\(([0-4])\)\s*$", stripped)
    if paren_match:
        return paren_match.group(1)

    leading_match = re.match(r"^([0-4])\s*[\.\)\:\-–]", stripped)
    if leading_match:
        return leading_match.group(1)

    for char in reversed(stripped):
        if char in "01234":
            return char

    lowered = stripped.casefold()
    french_keywords = {
        "pas du tout": "0",
        "tout à fait": "4",
        "tout a fait": "4",
        "beaucoup": "3",
        "plutôt": "3",
        "plutot": "3",
        "moyennement": "2",
        "un peu": "1",
        "jamais": "0",
        "toujours": "4",
    }
    for phrase, score in french_keywords.items():
        if phrase in lowered:
            return score
    return None


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
        text = str(raw).strip()
        if field_type in {"LINEAR_SCALE", "RATING", "INPUT_NUMBER"}:
            return normalize_score_text(text) or text
        return text

    if field_type == "CALCULATED_FIELDS":
        text = str(raw).strip()
        return normalize_score_text(text) or text

    if field_type in {"MULTIPLE_CHOICE", "DROPDOWN", "MULTI_SELECT"}:
        return _choice_value(field, raw)

    if isinstance(raw, (int, float, bool)):
        return normalize_score_text(str(raw)) or str(raw)

    if isinstance(raw, str):
        return normalize_score_text(raw) or raw.strip()

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
            return normalize_score_text(text) or text
        if selected is not None and str(selected).strip():
            return normalize_score_text(str(selected).strip()) or str(selected).strip()
    return None


def _normalize_label(label: str) -> str:
    return " ".join(label.strip().casefold().split())
