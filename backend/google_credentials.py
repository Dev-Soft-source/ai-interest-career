"""Load Google service account credentials from env vars or a JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import REPO_ROOT, Settings

GOOGLE_SHEETS_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
)


def has_google_service_account_credentials(settings: Settings) -> bool:
    if settings.google_service_account_json:
        return True
    if _env_service_account_fields(settings):
        return True
    return _credential_file_path(settings) is not None


def load_google_credentials(settings: Settings):
    from google.oauth2.service_account import Credentials

    info = _service_account_info(settings)
    if info is not None:
        return Credentials.from_service_account_info(info, scopes=GOOGLE_SHEETS_SCOPES)

    cred_path = _credential_file_path(settings)
    if cred_path is not None:
        return Credentials.from_service_account_file(str(cred_path), scopes=GOOGLE_SHEETS_SCOPES)

    raise RuntimeError(_missing_credentials_message(settings))


def _env_service_account_fields(settings: Settings) -> bool:
    return bool(
        settings.google_service_account_client_email
        or settings.google_service_account_private_key
        or settings.google_service_account_project_id
    )


def _service_account_info(settings: Settings) -> dict[str, Any] | None:
    if settings.google_service_account_json:
        return json.loads(settings.google_service_account_json)

    if not _env_service_account_fields(settings):
        return None

    missing = [
        name
        for name, value in (
            ("GOOGLE_SERVICE_ACCOUNT_PROJECT_ID", settings.google_service_account_project_id),
            ("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY", settings.google_service_account_private_key),
            ("GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL", settings.google_service_account_client_email),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Incomplete Google service account settings in .env. Set all of: "
            + ", ".join(missing)
            + ", or set GOOGLE_SERVICE_ACCOUNT_JSON, or provide a JSON key file."
        )

    return {
        "type": settings.google_service_account_type or "service_account",
        "project_id": settings.google_service_account_project_id,
        "private_key_id": settings.google_service_account_private_key_id or "",
        "private_key": settings.google_service_account_private_key,
        "client_email": settings.google_service_account_client_email,
        "client_id": settings.google_service_account_client_id or "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "",
        "universe_domain": "googleapis.com",
    }


def _credential_file_path(settings: Settings) -> Path | None:
    if settings.google_service_account_file:
        cred_path = Path(settings.google_service_account_file)
        if cred_path.is_file():
            return cred_path

    default_path = REPO_ROOT / "secrets" / "service-account.json"
    if default_path.is_file():
        return default_path
    return None


def _missing_credentials_message(settings: Settings) -> str:
    if settings.google_service_account_file:
        return (
            f"Google service account file not found: {settings.google_service_account_file}. "
            "Set GOOGLE_SERVICE_ACCOUNT_* values in .env, point GOOGLE_SERVICE_ACCOUNT_FILE "
            "to a readable JSON key file, or set USE_MOCK_SHEETS=true for local demo without Google Sheets."
        )
    return (
        "Google Sheets credentials are not configured. Set GOOGLE_SERVICE_ACCOUNT_* values in .env, "
        "set GOOGLE_SERVICE_ACCOUNT_FILE to a JSON key file, or set USE_MOCK_SHEETS=true for local demo "
        "without Google Sheets."
    )
