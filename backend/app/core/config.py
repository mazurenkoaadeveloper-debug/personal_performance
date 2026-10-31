from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gitlab_base_url: AnyHttpUrl
    gitlab_token: SecretStr
    database_url: str
    report_timezone: str = "Europe/Moscow"
    retention_days: int = Field(default=365, gt=0)
    gitlab_project_ids: tuple[int, ...]

    @field_validator("gitlab_token")
    @classmethod
    def reject_blank_gitlab_token(cls, token: SecretStr) -> SecretStr:
        if not token.get_secret_value().strip():
            raise ValueError("GitLab token must not be blank")
        return token

    @field_validator("gitlab_project_ids")
    @classmethod
    def require_project_allowlist(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if not value:
            raise ValueError("at least one GitLab project ID is required")
        if any(project_id <= 0 for project_id in value):
            raise ValueError("GitLab project IDs must be positive")
        return value

    @field_validator("report_timezone")
    @classmethod
    def require_iana_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("report_timezone must be a valid IANA timezone") from error
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
