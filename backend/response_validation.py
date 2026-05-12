"""Validate questionnaire answers read from Google Sheets."""

from __future__ import annotations

from backend.scorer import parse_item_score


def validate_response_answers(
    answers: dict[str, str],
    required_keys: list[str],
) -> dict[str, str]:
    """Return normalized string answers or raise ValueError with a clear message."""
    normalized: dict[str, str] = {}
    for key in required_keys:
        raw = answers.get(key)
        if raw is None or not str(raw).strip():
            raise ValueError(f'Missing questionnaire answer for "{key}"')
        normalized[key] = str(parse_item_score(str(raw), key))
    return normalized
