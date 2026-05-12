"""Load structured job catalogs from JSON files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from config import REPO_ROOT, Settings
from models import JobRecord

DEFAULT_JOBS_RELATIVE = Path("data") / "jobs_30_core.json"
CLIENT_JOBS_RELATIVE = Path("data") / "jobs_40_client.json"

DEFAULT_CORE_JOB_WHITELIST: tuple[str, ...] = (
    "ARTISAN",
    "INFIRMIER",
    "DEV_WEB",
    "CHEF_PROJET",
    "PROFESSEUR",
    "AIDE_SOIGNANT",
    "EDUCATEUR_SPEC",
    "ASSISTANT_SOCIAL",
    "PSYCHOLOGUE",
    "CIP",
    "FORMATEUR",
    "COACH_SPORTIF",
    "ANIMATEUR_SC",
    "RESP_PEDAGO",
    "COORD_EQUIPE",
    "RESP_PLANNING",
    "LOGISTICIEN",
    "CONSULTANT",
    "DATA_ANALYST",
    "CHARGE_ETUDES",
    "TECH_MAINT",
    "CUISINIER",
    "TECH_INFO",
    "GRAPHISTE",
    "UX_UI",
    "REDACTEUR_CM",
    "PRODUCT_OWNER",
    "TESTEUR_LOGICIEL",
    "MEDIATEUR_CULT",
    "TECH_FOREST",
)


def resolve_jobs_path(settings: Settings) -> Path:
    if settings.jobs_file:
        path = Path(settings.jobs_file)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path
    if settings.job_set == "client_40":
        return REPO_ROOT / CLIENT_JOBS_RELATIVE
    return REPO_ROOT / DEFAULT_JOBS_RELATIVE


def _parse_jobs_payload(data: object, source: Path) -> list[JobRecord]:
    if isinstance(data, dict):
        if "jobs" in data:
            jobs = data["jobs"]
        elif "top_5" in data and "user_dimension_vector" in data:
            raise ValueError(
                f"{source} looks like an assessment result, not a job catalog "
                "(expected a JSON array of jobs or an object with a jobs array)"
            )
        else:
            jobs = data
    else:
        jobs = data
    if not isinstance(jobs, list):
        raise ValueError(f"{source} must contain a JSON array of jobs")
    return [JobRecord.model_validate(item) for item in jobs]


def _apply_whitelist(jobs: list[JobRecord], whitelist: frozenset[str]) -> list[JobRecord]:
    filtered = [job for job in jobs if job.job_id in whitelist]
    if not filtered:
        raise ValueError("Job whitelist removed every job from the catalog")
    return filtered


def resolved_core_job_whitelist(settings: Settings) -> list[str] | None:
    if settings.core_job_whitelist:
        values = [part.strip() for part in settings.core_job_whitelist.split(",") if part.strip()]
        return values or None
    if settings.enforce_core_job_whitelist:
        return list(DEFAULT_CORE_JOB_WHITELIST)
    return None


@lru_cache
def _load_jobs_cached(path_str: str, whitelist_key: str | None) -> tuple[JobRecord, ...]:
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Jobs file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    jobs = _parse_jobs_payload(data, path)
    if whitelist_key:
        whitelist = frozenset(whitelist_key.split(","))
        jobs = _apply_whitelist(jobs, whitelist)
    return tuple(jobs)


def load_jobs(settings: Settings) -> list[JobRecord]:
    path = resolve_jobs_path(settings)
    whitelist = resolved_core_job_whitelist(settings)
    whitelist_key = ",".join(sorted(whitelist)) if whitelist else None
    return list(_load_jobs_cached(str(path.resolve()), whitelist_key))


def load_job_labels(settings: Settings) -> list[str]:
    return [job.job_label for job in load_jobs(settings)]
