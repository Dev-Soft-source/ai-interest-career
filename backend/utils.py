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
