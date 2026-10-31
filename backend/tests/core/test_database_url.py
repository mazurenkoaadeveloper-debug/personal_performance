import os
import subprocess
import sys

import pytest
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("password", ["word@host", "p:/#?% word"])
def test_compose_database_url_preserves_reserved_password_characters(password: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.core.database_url"],
        env=os.environ | {"POSTGRES_PASSWORD": password},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    url = make_url(result.stdout.strip())
    assert url.drivername == "postgresql+asyncpg"
    assert url.username == "activity"
    assert url.password == password
    assert url.host == "postgres"
    assert url.port == 5432
    assert url.database == "activity"
