"""Deterministic questionnaire scoring and job ranking."""

from __future__ import annotations

from models import DIMENSION_KEYS, QUESTION_GROUPS, DimensionVector, JobRecord, RankedJob


def expected_question_keys() -> list[str]:
    return [f"{group}{index}" for group in QUESTION_GROUPS for index in range(1, 9)]


def parse_item_score(raw: str, key: str) -> int:
    try:
        value = int(float(raw.strip()))
    except (TypeError, ValueError) as exc:
        raise ValueError(f'Invalid score for "{key}": expected integer 0-4') from exc
    if value < 0 or value > 4:
        raise ValueError(f'Invalid score for "{key}": expected integer 0-4')
    return value


def build_user_vector(answers: dict[str, str]) -> DimensionVector:
    dimension_values: dict[str, list[int]] = {key: [] for key in DIMENSION_KEYS}

    for group, dimension in zip(QUESTION_GROUPS, DIMENSION_KEYS, strict=True):
        for index in range(1, 9):
            key = f"{group}{index}"
            raw = answers.get(key)
            if raw is None or not str(raw).strip():
                raise ValueError(f'Missing questionnaire answer for "{key}"')
            dimension_values[dimension].append(parse_item_score(str(raw), key))

    rounded = {
        dimension: round(sum(values) / len(values), 2)
        for dimension, values in dimension_values.items()
    }
    return DimensionVector.model_validate(rounded)


def _mean_distance(user: DimensionVector, job: JobRecord) -> float:
    distances = [abs(getattr(user, key) - getattr(job.scores, key)) for key in DIMENSION_KEYS]
    return round(sum(distances) / len(distances), 4)


def _final_score(mean_distance: float) -> int:
    return round((1 - mean_distance / 4) * 100)


def _max_dimension_gap(user: DimensionVector, job: JobRecord) -> float:
    return max(abs(getattr(user, key) - getattr(job.scores, key)) for key in DIMENSION_KEYS)


def _top_dimension_gap_sum(user: DimensionVector, job: JobRecord) -> float:
    top_dimensions = sorted(DIMENSION_KEYS, key=lambda key: getattr(user, key), reverse=True)[:2]
    return sum(abs(getattr(user, key) - getattr(job.scores, key)) for key in top_dimensions)


def _ranking_key(user: DimensionVector, job: JobRecord) -> tuple[int, float, float, int, str]:
    mean_distance = _mean_distance(user, job)
    score = _final_score(mean_distance)
    return (
        -score,
        _max_dimension_gap(user, job),
        _top_dimension_gap_sum(user, job),
        len(job.short_description),
        job.job_id,
    )


def rank_jobs(user: DimensionVector, jobs: list[JobRecord], top_k: int) -> list[RankedJob]:
    if not jobs:
        raise ValueError("Job catalog is empty")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    ordered = sorted(jobs, key=lambda job: _ranking_key(user, job))
    limit = min(top_k, len(ordered))
    ranked: list[RankedJob] = []
    for job in ordered[:limit]:
        mean_distance = _mean_distance(user, job)
        ranked.append(
            RankedJob(
                job_id=job.job_id,
                job_label=job.job_label,
                score=_final_score(mean_distance),
                mean_distance=mean_distance,
            )
        )
    return ranked
