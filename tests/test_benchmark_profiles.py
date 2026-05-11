import json
from pathlib import Path

import pytest

from config import Settings
from job_loader import load_jobs
from scorer import build_user_vector, rank_jobs

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = json.loads((ROOT / "data" / "benchmark_samples.json").read_text(encoding="utf-8"))

PROFILE_EXPECTATIONS = {
    "sample_1_analytical_technical": (
        {
            "DEV_WEB",
            "DATA_ANALYST",
            "TECH_INFO",
            "TESTEUR_LOGICIEL",
            "CHARGE_ETUDES",
        },
        3,
    ),
    "sample_2_social_teaching": (
        {
            "FORMATEUR",
            "PROFESSEUR",
            "CIP",
            "ASSISTANT_SOCIAL",
            "EDUCATEUR_SPEC",
        },
        3,
    ),
    "sample_3_creative_communication": (
        {
            "REDACTEUR_CM",
            "GRAPHISTE",
            "UX_UI",
            "MEDIATEUR_CULT",
        },
        3,
    ),
    "sample_4_hands_on_physical": (
        {
            "TECH_MAINT",
            "ARTISAN",
            "TECH_FOREST",
            "CUISINIER",
        },
        3,
    ),
    "sample_5_management_coordination": (
        {
            "CHEF_PROJET",
            "PRODUCT_OWNER",
            "RESP_PEDAGO",
            "COORD_EQUIPE",
            "RESP_PLANNING",
            "LOGISTICIEN",
            "CONSULTANT",
            "CIP",
            "ASSISTANT_SOCIAL",
        },
        2,
    ),
    "sample_6_mixed_tiebreak": (
        {
            "CONSULTANT",
            "CHEF_PROJET",
            "UX_UI",
            "REDACTEUR_CM",
            "DATA_ANALYST",
            "PRODUCT_OWNER",
        },
        2,
    ),
}


@pytest.mark.parametrize("sample_name", PROFILE_EXPECTATIONS)
def test_benchmark_profile_top_five_matches_expected_family(sample_name: str):
    settings = Settings()
    jobs = load_jobs(settings)
    vector = build_user_vector(SAMPLES[sample_name])
    ranked = rank_jobs(vector, jobs, top_k=5)
    top_ids = {job.job_id for job in ranked}
    expected, minimum_overlap = PROFILE_EXPECTATIONS[sample_name]

    assert len(ranked) == 5
    assert len(top_ids & expected) >= minimum_overlap
    assert ranked[0].score >= ranked[-1].score
