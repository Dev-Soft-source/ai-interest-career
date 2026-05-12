from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR.parent))

from config import Settings
from google_credentials import has_google_service_account_credentials, load_google_credentials


def test_has_credentials_from_env_fields():
    settings = Settings(
        google_service_account_project_id="demo-project",
        google_service_account_private_key="-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n",
        google_service_account_client_email="demo@demo-project.iam.gserviceaccount.com",
    )
    assert has_google_service_account_credentials(settings) is True


def test_private_key_normalizes_escaped_newlines():
    settings = Settings(
        google_service_account_project_id="demo-project",
        google_service_account_private_key="-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----\\n",
        google_service_account_client_email="demo@demo-project.iam.gserviceaccount.com",
    )
    assert settings.google_service_account_private_key == (
        "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n"
    )


def test_incomplete_env_fields_raise():
    settings = Settings.model_construct(
        google_service_account_project_id="demo-project",
        google_service_account_client_email="demo@demo-project.iam.gserviceaccount.com",
        google_service_account_private_key=None,
        google_service_account_json=None,
        google_service_account_file=None,
    )
    with pytest.raises(RuntimeError, match="Incomplete Google service account settings"):
        load_google_credentials(settings)


def test_default_service_account_file_is_detected():
    default_path = Path(__file__).resolve().parent.parent / "secrets" / "service-account.json"
    if not default_path.is_file():
        pytest.skip("service-account.json is not present in this environment")
    settings = Settings.model_construct(
        google_service_account_json=None,
        google_service_account_file=None,
        google_service_account_project_id=None,
        google_service_account_private_key=None,
        google_service_account_client_email=None,
    )
    assert has_google_service_account_credentials(settings) is True
