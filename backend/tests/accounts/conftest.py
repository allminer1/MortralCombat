"""Accounts tests need a real PostgreSQL (JSONB, constraints, the migration itself).

They run when TEST_DATABASE_URL points at a throwaway database (`make test-accounts`
starts one in Docker) and are skipped otherwise. All data in them is synthetic.
"""

import os
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import Settings

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")


def pytest_collection_modifyitems(items):
    for item in items:
        if "/accounts/" in str(item.fspath) and not URL:
            item.add_marker(
                pytest.mark.skip(reason="TEST_DATABASE_URL is not set (run `make test-accounts`)")
            )


@pytest.fixture(scope="session")
def engine():
    from app import cli
    from app.db.engine import make_engine

    os.environ["DATABASE_URL"] = URL
    engine = make_engine(URL)
    with engine.begin() as connection:  # start from nothing, then run the real migration
        connection.execute(
            text("drop table if exists calculations, sessions, users, alembic_version cascade")
        )
    cli.migrate()
    return engine


@pytest.fixture()
def db(engine):
    from app.db.engine import make_session_factory

    with engine.begin() as connection:
        connection.execute(text("truncate calculations, sessions, users cascade"))
    with make_session_factory(engine)() as session:
        yield session


def accounts_settings(**overrides) -> Settings:
    values = dict(
        enable_accounts=True,
        database_url=URL,
        cookie_secure=False,  # the test client talks plain HTTP
        rate_limit_per_minute=0,
        login_attempts_per_15_min=0,
    )
    return Settings(**(values | overrides))


@pytest.fixture()
def make_client(db):
    """Factory for independent browser-like clients (each with its own cookie jar)."""
    from app.main import create_app

    app = create_app(accounts_settings())

    def factory() -> TestClient:
        return TestClient(app, base_url="http://testserver")

    return factory


@pytest.fixture()
def make_user(db):
    """Creates a user with a random password; returns (email, password)."""
    from app.accounts import service

    def factory(email: str, role: str = "user") -> tuple[str, str]:
        password = secrets.token_urlsafe(16)
        service.create_user(db, email, password, role)
        db.commit()
        return email, password

    return factory


class SignedIn:
    """A client plus the CSRF token of its session."""

    def __init__(self, client: TestClient, email: str, password: str):
        self.client = client
        self.email = email
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        self.csrf = response.json()["csrf_token"]

    @property
    def headers(self) -> dict:
        return {"X-CSRF-Token": self.csrf}

    def save(self, inputs: dict, case_code: str | None = None):
        body = {"inputs": inputs} | ({"case_code": case_code} if case_code is not None else {})
        return self.client.post("/api/v1/calculations", json=body, headers=self.headers)


@pytest.fixture()
def sign_in(make_client, make_user):
    def factory(email: str, role: str = "user") -> SignedIn:
        address, password = make_user(email, role)
        return SignedIn(make_client(), address, password)

    return factory


@pytest.fixture()
def inputs(figure_8, spec) -> dict:
    """Figure 8 inputs with JSON booleans, as the API expects them."""
    bools = {f.api_field for f in spec.features if f.type == "bool"}
    return {k: bool(v) if k in bools else v for k, v in figure_8.items()}
