from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from config import Settings
from job_loader import load_jobs
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


def test_build_user_vector_sample_1():
    vector = build_user_vector(SAMPLE_1)
    assert vector.analysis_conceptual == 3.25
    assert vector.technical_manual == 2.0
    assert vector.creation_expression == 1.0


def test_rank_jobs_sample_1_prefers_technical_roles():
    settings = Settings()
    jobs = load_jobs(settings)
    vector = build_user_vector(SAMPLE_1)
    ranked = rank_jobs(vector, jobs, top_k=5)

    assert len(ranked) == 5
    assert ranked[0].job_id in {
        "DEV_WEB",
        "DATA_ANALYST",
        "TECH_INFO",
        "TESTEUR_LOGICIEL",
        "CHARGE_ETUDES",
    }
    assert ranked[0].score >= ranked[-1].score


def test_build_user_vector_rejects_missing_item():
    incomplete = dict(SAMPLE_1)
    del incomplete["A8"]
    with pytest.raises(ValueError, match="A8"):
        build_user_vector(incomplete)
