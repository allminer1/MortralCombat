from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.ratelimit import RateLimiter
from app.main import create_app
from tests.api.conftest import PREDICT


def test_default_limit_is_60_per_minute():
    assert Settings().rate_limit_per_minute == 60


def test_limiter_window():
    now = [0.0]
    limiter = RateLimiter(limit=3, window_seconds=60, clock=lambda: now[0])
    assert [limiter.check("a") for _ in range(3)] == [0, 0, 0]
    assert limiter.check("a") == 60
    assert limiter.check("b") == 0  # other clients are not affected
    now[0] = 59.5
    assert limiter.check("a") == 1
    now[0] = 60.0
    assert limiter.check("a") == 0  # the oldest request left the window


def test_limiter_forgets_idle_clients():
    now = [0.0]
    limiter = RateLimiter(limit=3, window_seconds=60, clock=lambda: now[0])
    limiter.check("a")
    now[0] = 200.0
    limiter.check("b")
    assert set(limiter._hits) == {"b"}


def test_predict_returns_429_with_retry_after(valid_body):
    client = TestClient(create_app(Settings(rate_limit_per_minute=3)))
    assert [client.post(PREDICT, json=valid_body).status_code for _ in range(3)] == [200, 200, 200]
    blocked = client.post(PREDICT, json=valid_body)
    assert blocked.status_code == 429
    assert blocked.json() == {"errors": [{"field": None, "code": "rate_limited"}]}
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60
    # invalid requests count as well, and other endpoints are not limited
    assert client.post(PREDICT, json={}).status_code == 429
    assert client.get("/api/v1/health").status_code == 200


def test_forwarded_header_ignored_unless_proxy_is_trusted(valid_body):
    untrusted = TestClient(create_app(Settings(rate_limit_per_minute=1)))
    codes = [
        untrusted.post(PREDICT, json=valid_body, headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code
        for i in range(2)
    ]
    assert codes == [200, 429]  # a client cannot dodge the limit by inventing the header

    trusted = TestClient(create_app(Settings(rate_limit_per_minute=1, trusted_proxy=True)))
    codes = [
        trusted.post(
            PREDICT, json=valid_body, headers={"X-Forwarded-For": f"6.6.6.6, 10.0.0.{i}"}
        ).status_code
        for i in (1, 2, 1)
    ]
    assert codes == [200, 200, 429]  # keyed on the entry our proxy appended (the last one)
