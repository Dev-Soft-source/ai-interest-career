"""Shared helpers."""

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse first JSON object from model output (strips accidental fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise


def normalize_email(value: str) -> str:
    return value.strip().lower()


_ITEM_CODE = r"[A-F][1-8]"
_ITEM_CODE_RANGE = re.compile(
    rf"\b{_ITEM_CODE}\s*[-\u2013]\s*{_ITEM_CODE}\b",
    re.IGNORECASE,
)
_ITEM_CODE_PAREN = re.compile(
    rf"\(\s*{_ITEM_CODE}(?:\s*[-\u2013]\s*{_ITEM_CODE})?\s*\)",
    re.IGNORECASE,
)
_ITEM_CODE_SINGLE = re.compile(rf"\b{_ITEM_CODE}\b", re.IGNORECASE)


def sanitize_user_facing_text(text: str) -> str:
    """Remove questionnaire item codes such as E1 or (E1-E8) from user-facing prose."""
    cleaned = _ITEM_CODE_PAREN.sub("", text)
    cleaned = _ITEM_CODE_RANGE.sub("", cleaned)
    cleaned = _ITEM_CODE_SINGLE.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,;:.)])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    return cleaned.strip()
