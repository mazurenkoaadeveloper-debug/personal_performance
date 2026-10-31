import pytest
from pydantic import ValidationError

from app.core.config import Settings


BASE_SETTINGS = {
    "gitlab_base_url": "https://gitlab.corp.example",
    "database_url": "postgresql+asyncpg://activity:password@postgres/activity",
    "gitlab_project_ids": (101, 202),
}


def test_settings_reject_missing_gitlab_token() -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE_SETTINGS)


def test_settings_reject_empty_project_allowlist() -> None:
    with pytest.raises(ValidationError):
        Settings(
            **(BASE_SETTINGS | {"gitlab_project_ids": ()}),
            gitlab_token="secret-value",
        )


def test_settings_use_moscow_timezone_and_hide_token() -> None:
    settings = Settings(**BASE_SETTINGS, gitlab_token="secret-value")

    assert settings.report_timezone == "Europe/Moscow"
    assert settings.retention_days == 365
    assert str(settings.gitlab_token) == "**********"
    assert settings.gitlab_token.get_secret_value() == "secret-value"
    assert "secret-value" not in repr(settings)
