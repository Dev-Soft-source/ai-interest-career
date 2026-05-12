"""Score with Python, then call OpenAI or Gemini for explanations."""

from __future__ import annotations

import logging

from config import Settings, get_settings, resolve_llm_provider
from job_loader import load_jobs
from models import (
    AssessmentResult,
    LLMExplanationOutput,
    LLMOutput,
    RankedJob,
    TopJob,
    TopJobResult,
)
from prompt_templates import EXPLANATION_SYSTEM_PROMPT, build_explanation_user_prompt
from scorer import build_user_vector, rank_jobs
from utils import extract_json_object, sanitize_user_facing_text

logger = logging.getLogger(__name__)


def call_assessment(answers: dict[str, str], settings: Settings | None = None) -> AssessmentResult:
    settings = settings or get_settings()
    jobs = load_jobs(settings)
    jobs_by_id = {job.job_id: job for job in jobs}

    user_vector = build_user_vector(answers)
    ranked = rank_jobs(user_vector, jobs, top_k=settings.top_k)
    user_content = build_explanation_user_prompt(answers, user_vector, ranked, jobs_by_id)

    provider = resolve_llm_provider(settings)
    if provider == "gemini":
        raw = _call_gemini(user_content, settings)
    else:
        raw = _call_openai(user_content, settings)

    explained = LLMExplanationOutput.model_validate(extract_json_object(raw))
    top_jobs = _merge_explanations(ranked, explained)
    return AssessmentResult(
        user_dimension_vector=user_vector,
        top_jobs=top_jobs,
        summary=sanitize_user_facing_text(explained.summary.strip()),
    )


def call_llm(answers: dict[str, str], settings: Settings | None = None) -> LLMOutput:
    """Legacy adapter for callers that still expect the MVP LLMOutput shape."""
    return assessment_to_legacy(call_assessment(answers, settings))


def assessment_to_legacy(result: AssessmentResult) -> LLMOutput:
    top_jobs = [
        TopJob(job=job.job_label, score=job.score, reason=job.reason)
        for job in result.top_jobs
    ]
    scores = {job.job: job.score for job in top_jobs}
    return LLMOutput(scores=scores, top_jobs=top_jobs, summary=result.summary)


def _merge_explanations(
    ranked: list[RankedJob],
    explained: LLMExplanationOutput,
) -> list[TopJobResult]:
    reasons = {item.job_id: item.reason.strip() for item in explained.top_jobs}
    merged: list[TopJobResult] = []

    for job in ranked:
        reason = sanitize_user_facing_text(reasons.get(job.job_id, "").strip())
        if not reason:
            raise ValueError(f'Missing explanation for job_id "{job.job_id}"')
        merged.append(
            TopJobResult(
                job_id=job.job_id,
                job_label=job.job_label,
                score=job.score,
                reason=reason,
            )
        )
    return merged


def _call_openai(user_content: str, settings: Settings) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=settings.llm_temperature,
        response_format={"type": "json_object"},
    )
    choice = resp.choices[0].message.content
    if not choice:
        raise RuntimeError("Empty OpenAI response")
    return choice


def _call_gemini(user_content: str, settings: Settings) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model_name = settings.gemini_model.removeprefix("models/")
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=EXPLANATION_SYSTEM_PROMPT,
    )
    resp = model.generate_content(
        user_content,
        generation_config={
            "temperature": settings.llm_temperature,
            "response_mime_type": "application/json",
        },
    )
    text = resp.text
    if not text:
        raise RuntimeError("Empty Gemini response")
    return text
