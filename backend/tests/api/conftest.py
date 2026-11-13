import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

PREDICT = "/api/v1/predict"


@pytest.fixture(scope="session")
def client() -> TestClient:
    """App without a rate limit, for tests that send many requests."""
    return TestClient(create_app(Settings(rate_limit_per_minute=0)))


@pytest.fixture(scope="session")
def api_features(client) -> list[dict]:
    """Feature list as the API publishes it; tests read names and ranges from here."""
    return client.get("/api/v1/model").json()["feature_spec"]["features"]


@pytest.fixture(scope="session")
def to_body(api_features):
    """Golden inputs store booleans as 0 / 1; the API takes JSON true / false."""
    bool_fields = {f["api_field"] for f in api_features if f["type"] == "bool"}

    def convert(inputs: dict) -> dict:
        return {k: bool(v) if k in bool_fields else v for k, v in inputs.items()}

    return convert


@pytest.fixture()
def valid_body(figure_8, to_body) -> dict:
    return to_body(figure_8)
