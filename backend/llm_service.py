"""Call OpenAI or Gemini and return structured LLMOutput."""

from __future__ import annotations

import logging

from backend.config import Settings, get_settings, load_job_list
from backend.models import LLMOutput
from backend.prompt_templates import SYSTEM_PROMPT, build_user_prompt
from backend.utils import extract_json_object

logger = logging.getLogger(__name__)


def call_llm(answers: dict[str, str], settings: Settings | None = None) -> LLMOutput:
    settings = settings or get_settings()
    jobs = load_job_list(settings)
    user_content = build_user_prompt(answers, jobs)
    provider = (settings.llm_provider or "openai").lower()

    if provider == "gemini":
        raw = _call_gemini(user_content, settings)
    else:
        raw = _call_openai(user_content, settings)

    data = extract_json_object(raw)
    return LLMOutput.model_validate(data)


def _call_openai(user_content: str, settings: Settings) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
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
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=SYSTEM_PROMPT,
    )
    resp = model.generate_content(
        user_content,
        generation_config={
            "temperature": 0.4,
            "response_mime_type": "application/json",
        },
    )
    text = resp.text
    if not text:
        raise RuntimeError("Empty Gemini response")
    return text
