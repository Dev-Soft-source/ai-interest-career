"""LLM prompts for explanation-only generation after Python ranking."""

from __future__ import annotations

import json
from typing import Any

from models import DimensionVector, JobRecord, RankedJob

EXPLANATION_SYSTEM_PROMPT = """You are a career-interest explanation writer.

Ranking and numeric scores are already fixed by the application. Your job is to write clear,
user-facing explanations only.

Rules:
- Do not change job order, job_id values, or scores.
- Use questionnaire item meaning and job short_description to explain fit.
- Each reason must mention at least two dimension themes and one meaningful preference pattern
  from the questionnaire (grouped wording is fine; item codes are optional).
- Keep each reason to 2-3 concise sentences.
- Write summary in 2-4 short sentences for the respondent.
- Return valid JSON only, with no markdown or extra text.

Output shape:
{"top_jobs": [{"job_id": "", "reason": ""}], "summary": ""}

The top_jobs array must include exactly the provided job_id values, in the same order."""


def build_explanation_user_prompt(
    answers: dict[str, str],
    user_vector: DimensionVector,
    ranked_jobs: list[RankedJob],
    jobs_by_id: dict[str, JobRecord],
) -> str:
    ranked_payload: list[dict[str, Any]] = []
    for ranked in ranked_jobs:
        job = jobs_by_id[ranked.job_id]
        ranked_payload.append(
            {
                "job_id": ranked.job_id,
                "job_label": ranked.job_label,
                "score": ranked.score,
                "short_description": job.short_description,
            }
        )

    payload = {
        "language": "English",
        "response_mode": "strict_json",
        "scoring_lock": "numeric_ranking_only",
        "user_dimension_vector": user_vector.model_dump(),
        "item_level_answers": answers,
        "ranked_top_jobs": ranked_payload,
    }
    return (
        "Write explanations for the ranked jobs below. Do not re-rank or rescore.\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Return JSON only in the schema defined by the system prompt."
    )
