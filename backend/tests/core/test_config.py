import json
import logging

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.core.logging import configure_logging, redact_secrets


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


@pytest.mark.parametrize("token", ["", "   "])
def test_settings_reject_blank_gitlab_token(token: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE_SETTINGS, gitlab_token=token)


def test_logging_redacts_sensitive_values_recursively() -> None:
    redacted = redact_secrets(
        None,
        "info",
        {
            "token": "top-secret",
            "headers": {"Authorization": "Bearer nested-secret"},
            "credential": SecretStr("secret-object"),
        },
    )

    encoded = json.dumps(redacted, default=str)
    assert redacted["token"] == "[REDACTED]"
    assert redacted["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["credential"] == "[REDACTED]"
    assert "top-secret" not in encoded
    assert "nested-secret" not in encoded
    assert "secret-object" not in encoded


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Authorization: Bearer bearer-secret", "Authorization: Bearer [REDACTED]"),
        ("PRIVATE-TOKEN: private-secret", "PRIVATE-TOKEN: [REDACTED]"),
    ],
)
def test_logging_redacts_header_values_in_message(message: str, expected: str) -> None:
    redacted = redact_secrets(None, "info", {"event": message})

    assert redacted["event"] == expected


def test_configure_logging_structures_and_redacts_uvicorn_output(capsys) -> None:
    configure_logging()

    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:12345",
        "GET",
        "/api/health?token=runtime-secret",
        "1.1",
        200,
    )

    output = capsys.readouterr().out.strip()
    record = json.loads(output)
    assert record["event"] == (
        '127.0.0.1:12345 - "GET /api/health?token=[REDACTED] HTTP/1.1" 200'
    )
    assert record["level"] == "info"
    assert "runtime-secret" not in output
