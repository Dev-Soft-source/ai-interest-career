import json
from unittest.mock import patch

import pytest

from config import Settings, get_settings
from job_loader import load_jobs
from llm_service import call_assessment
from scorer import build_user_vector, rank_jobs

SAMPLE_1 = {
    "A1": "1",
    "A2": "2",
    "A3": "0",
    "A4": "0",
    "A5": "2",
    "A6": "3",
    "A7": "0",
    "A8": "0",
    "B1": "4",
    "B2": "4",
    "B3": "4",
    "B4": "4",
    "B5": "3",
    "B6": "3",
    "B7": "2",
    "B8": "2",
    "C1": "2",
    "C2": "2",
    "C3": "4",
    "C4": "4",
    "C5": "1",
    "C6": "1",
    "C7": "1",
    "C8": "1",
    "D1": "0",
    "D2": "0",
    "D3": "1",
    "D4": "1",
    "D5": "1",
    "D6": "0",
    "D7": "0",
    "D8": "0",
    "E1": "2",
    "E2": "2",
    "E3": "1",
    "E4": "2",
    "E5": "1",
    "E6": "2",
    "E7": "1",
    "E8": "1",
    "F1": "2",
    "F2": "3",
    "F3": "3",
    "F4": "3",
    "F5": "2",
    "F6": "2",
    "F7": "2",
    "F8": "2",
}


def _explanation_payload(job_ids: list[str]) -> str:
    return json.dumps(
        {
            "top_jobs": [
                {"job_id": job_id, "reason": f"Explanation for {job_id}."}
                for job_id in job_ids
            ],
            "summary": "Summary text.",
        }
    )


def _mock_explanation_response(user_content: str, settings: Settings) -> str:
    del user_content
    vector = build_user_vector(SAMPLE_1)
    ranked = rank_jobs(vector, load_jobs(settings), top_k=settings.top_k)
    return _explanation_payload([job.job_id for job in ranked])


@pytest.mark.parametrize(
    ("provider", "llm_attr"),
    [
        ("gemini", "_call_gemini"),
        ("openai", "_call_openai"),
    ],
)
def test_provider_uses_python_ranking_and_returns_v2_shape(provider: str, llm_attr: str):
    get_settings.cache_clear()
    settings = Settings(llm_provider=provider, gemini_api_key="gemini-test", openai_api_key="openai-test")

    with patch(f"llm_service.{llm_attr}", side_effect=_mock_explanation_response):
        result = call_assessment(SAMPLE_1, settings=settings)

    assert result.summary == "Summary text."
    assert len(result.top_jobs) == 5
    assert result.top_jobs[0].job_id in {
        "DEV_WEB",
        "DATA_ANALYST",
        "TECH_INFO",
        "TESTEUR_LOGICIEL",
        "CHARGE_ETUDES",
    }
    assert result.top_jobs[0].reason.startswith("Explanation for ")


def test_same_ranking_when_switching_provider_with_mocked_explanations():
    get_settings.cache_clear()
    gemini_settings = Settings(llm_provider="gemini", gemini_api_key="gemini-test")
    openai_settings = Settings(llm_provider="openai", openai_api_key="openai-test")

    with patch("llm_service._call_gemini", side_effect=_mock_explanation_response), patch(
        "llm_service._call_openai",
        side_effect=_mock_explanation_response,
    ):
        gemini_result = call_assessment(SAMPLE_1, settings=gemini_settings)
        openai_result = call_assessment(SAMPLE_1, settings=openai_settings)

    assert [job.job_id for job in gemini_result.top_jobs] == [job.job_id for job in openai_result.top_jobs]
    assert [job.score for job in gemini_result.top_jobs] == [job.score for job in openai_result.top_jobs]
