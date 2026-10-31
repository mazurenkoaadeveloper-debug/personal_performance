import asyncio

import httpx

from app.main import create_app


def test_health_returns_only_public_status(monkeypatch) -> None:
    monkeypatch.setenv("GITLAB_TOKEN", "must-not-leak")
    monkeypatch.setenv("GITLAB_BASE_URL", "https://gitlab.corp.example")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://activity:password@postgres/activity",
    )
    monkeypatch.setenv("GITLAB_PROJECT_IDS", "[101,202]")

    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/api/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "must-not-leak" not in response.text
