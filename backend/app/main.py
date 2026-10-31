from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    get_settings()
    configure_logging()

    application = FastAPI(title="GitLab Developer Activity Analytics")

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application
