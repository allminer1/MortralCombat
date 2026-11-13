"""Default configuration: accounts are off. Nothing account-related exists, and no
database driver is even imported."""

import subprocess
import sys
from pathlib import Path

from app.core.config import Settings


def test_flag_is_off_by_default():
    assert Settings().enable_accounts is False
    assert Settings.from_env().enable_accounts is False


def test_features_endpoint_says_off(client):
    assert client.get("/api/v1/features").json() == {"accounts": False}


def test_account_endpoints_do_not_exist(client):
    for method, path in [
        ("post", "/api/v1/auth/login"),
        ("post", "/api/v1/auth/logout"),
        ("get", "/api/v1/auth/me"),
        ("get", "/api/v1/calculations"),
        ("post", "/api/v1/calculations"),
        ("get", "/api/v1/calculations/export.csv"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 404, path
    paths = client.get("/api/openapi.json").json()["paths"]
    assert not [p for p in paths if "auth" in p or "calculations" in p]


def test_no_database_code_is_loaded_when_off():
    code = (
        "import sys; from app.main import create_app; from app.core.config import Settings; "
        "create_app(Settings()); "
        "names = ('sqlalchemy', 'psycopg', 'alembic', 'argon2'); "
        "bad = [m for m in sys.modules if m.split('.')[0] in names]; "
        "print(bad); sys.exit(1 if bad else 0)"
    )
    backend = Path(__file__).parents[2]
    result = subprocess.run([sys.executable, "-c", code], cwd=backend, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_enabling_without_a_database_url_fails_loudly():
    import pytest

    from app.main import create_app

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app(Settings(enable_accounts=True))
