import pytest

from config import Settings
from job_loader import load_jobs
from models import DimensionVector
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


def test_mean_distance_formula_matches_manual_definition():
    settings = Settings()
    jobs = load_jobs(settings)
    vector = build_user_vector(SAMPLE_1)
    target = next(job for job in jobs if job.job_id == "DEV_WEB")

    distances = [
        abs(getattr(vector, key) - getattr(target.scores, key))
        for key in DimensionVector.model_fields
    ]
    mean_distance = round(sum(distances) / len(distances), 4)
    expected_score = round((1 - mean_distance / 4) * 100)

    ranked = rank_jobs(vector, jobs, top_k=30)
    dev_web = next(job for job in ranked if job.job_id == "DEV_WEB")
    assert dev_web.mean_distance == mean_distance
    assert dev_web.score == expected_score


def test_tiebreak_prefers_lower_max_dimension_gap():
    user = DimensionVector(
        creation_expression=2.0,
        analysis_conceptual=2.0,
        technical_manual=2.0,
        physical_bodily=2.0,
        social_collective=2.0,
        organization_management=2.0,
    )
    jobs = load_jobs(Settings())
    ranked = rank_jobs(user, jobs, top_k=5)
    close_pairs = [
        (ranked[index], ranked[index + 1])
        for index in range(len(ranked) - 1)
        if ranked[index].score - ranked[index + 1].score <= 2
    ]
    assert close_pairs, "Expected at least one close-score pair in the neutral profile ranking"
