from datetime import timedelta

from sqlalchemy import select, update

from app.accounts import service
from app.db.models import Session, User
from tests.accounts.conftest import SignedIn, accounts_settings

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
BASE = "/api/v1/calculations"


def test_login_sets_a_protected_cookie(make_client, make_user):
    email, password = make_user("carol@example.test")
    client = make_client()
    response = client.post(LOGIN, json={"email": "  Carol@Example.TEST ", "password": password})
    assert response.status_code == 200
    assert response.json()["email"] == email and response.json()["role"] == "user"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert client.get(ME).json()["email"] == email


def test_production_cookie_is_secure_and_host_bound(db, make_user):
    from fastapi.testclient import TestClient

    from app.main import create_app

    email, password = make_user("carol@example.test")
    client = TestClient(create_app(accounts_settings(cookie_secure=True)), base_url="https://testserver")
    cookie = client.post(LOGIN, json={"email": email, "password": password}).headers["set-cookie"]
    assert cookie.startswith("__Host-nms_session=")
    assert "Secure" in cookie and "HttpOnly" in cookie


def test_wrong_password_unknown_user_and_inactive_user_look_the_same(make_client, make_user, db):
    email, password = make_user("carol@example.test")
    inactive, inactive_password = make_user("dave@example.test")
    service.set_active(db, service.find_user(db, inactive), False)
    db.commit()
    client = make_client()
    answers = [
        client.post(LOGIN, json={"email": email, "password": "wrong-password-123"}),
        client.post(LOGIN, json={"email": "nobody@example.test", "password": password}),
        client.post(LOGIN, json={"email": inactive, "password": inactive_password}),
    ]
    for answer in answers:
        assert answer.status_code == 401
        assert answer.json() == {"errors": [{"field": None, "code": "invalid_credentials"}]}
        assert "set-cookie" not in answer.headers


def test_passwords_are_stored_as_argon2id_and_tokens_as_hashes(make_client, make_user, db):
    email, password = make_user("carol@example.test")
    client = make_client()
    client.post(LOGIN, json={"email": email, "password": password})
    user = db.scalar(select(User))
    session = db.scalar(select(Session))
    assert user.password_hash.startswith("$argon2id$") and password not in user.password_hash
    cookie_value = next(iter(client.cookies.values()))
    assert session.token_hash != cookie_value and len(session.token_hash) == 64


def test_logout_ends_the_session(sign_in):
    carol = sign_in("carol@example.test")
    assert carol.client.post("/api/v1/auth/logout", headers=carol.headers).status_code == 204
    assert carol.client.get(ME).status_code == 401


def test_csrf_token_required_for_every_state_change(sign_in, inputs):
    carol = sign_in("carol@example.test")
    item = carol.save(inputs).json()["id"]
    attempts = [
        carol.client.post(BASE, json={"inputs": inputs}),
        carol.client.post(BASE, json={"inputs": inputs}, headers={"X-CSRF-Token": "guess"}),
        carol.client.delete(f"{BASE}/{item}"),
        carol.client.post("/api/v1/auth/logout"),
        carol.client.post("/api/v1/auth/password", json={"current_password": "x", "new_password": "y" * 12}),
    ]
    for attempt in attempts:
        assert attempt.status_code == 403
        assert attempt.json() == {"errors": [{"field": None, "code": "csrf_failed"}]}
    assert len(carol.client.get(BASE).json()["items"]) == 1  # nothing was created or deleted


def test_cross_site_origin_is_refused_even_with_a_token(sign_in, inputs, make_client, make_user):
    carol = sign_in("carol@example.test")
    evil = {"Origin": "https://evil.example"}
    assert carol.client.post(BASE, json={"inputs": inputs}, headers=carol.headers | evil).status_code == 403
    email, password = make_user("erin@example.test")
    assert (
        make_client().post(LOGIN, json={"email": email, "password": password}, headers=evil).status_code
        == 403
    )
    same = {"Origin": "http://testserver"}
    assert carol.client.post(BASE, json={"inputs": inputs}, headers=carol.headers | same).status_code == 201


def test_idle_timeout_and_absolute_limit(sign_in, db):
    carol = sign_in("carol@example.test")
    assert carol.client.get(ME).status_code == 200
    db.execute(update(Session).values(last_seen_at=service.now() - timedelta(minutes=31)))
    db.commit()
    assert carol.client.get(ME).status_code == 401
    assert db.scalar(select(Session)) is None  # the expired session row is removed

    dan = sign_in("dan@example.test")
    db.execute(update(Session).values(expires_at=service.now() - timedelta(seconds=1)))
    db.commit()
    assert dan.client.get(ME).status_code == 401


def test_activity_keeps_a_session_alive(sign_in, db):
    carol = sign_in("carol@example.test")
    db.execute(update(Session).values(last_seen_at=service.now() - timedelta(minutes=20)))
    db.commit()
    assert carol.client.get(ME).status_code == 200
    db.expire_all()
    assert service.now() - db.scalar(select(Session)).last_seen_at < timedelta(minutes=1)


def test_deactivated_user_is_signed_out(sign_in, db):
    carol = sign_in("carol@example.test")
    service.set_active(db, service.find_user(db, carol.email), False)
    db.commit()
    assert carol.client.get(ME).status_code == 401


def test_password_change_ends_other_sessions(make_client, make_user):
    email, password = make_user("carol@example.test")
    here = SignedIn(make_client(), email, password)
    elsewhere = SignedIn(make_client(), email, password)
    new_password = "a-new-long-password"
    body = {"current_password": password, "new_password": new_password}
    assert here.client.post("/api/v1/auth/password", json=body, headers=here.headers).status_code == 204
    assert here.client.get(ME).status_code == 200
    assert elsewhere.client.get(ME).status_code == 401
    assert make_client().post(LOGIN, json={"email": email, "password": password}).status_code == 401
    assert make_client().post(LOGIN, json={"email": email, "password": new_password}).status_code == 200


def test_password_rules(sign_in, make_client, make_user):
    email, password = make_user("carol@example.test")
    carol = SignedIn(make_client(), email, password)
    short = {"current_password": password, "new_password": "short"}
    answer = carol.client.post("/api/v1/auth/password", json=short, headers=carol.headers)
    assert answer.status_code == 422
    assert answer.json() == {"errors": [{"field": None, "code": "password_too_short"}]}
    wrong = {"current_password": "not-the-password", "new_password": "long-enough-password"}
    assert carol.client.post("/api/v1/auth/password", json=wrong, headers=carol.headers).status_code == 401


def test_login_rate_limit(db, make_user):
    from fastapi.testclient import TestClient

    from app.main import create_app

    email, password = make_user("carol@example.test")
    client = TestClient(create_app(accounts_settings(login_attempts_per_15_min=3)))
    codes = [
        client.post(LOGIN, json={"email": email, "password": "wrong-password-123"}).status_code
        for _ in range(4)
    ]
    assert codes == [401, 401, 401, 429]
    blocked = client.post(LOGIN, json={"email": email, "password": password})
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) >= 1
    assert blocked.json() == {"errors": [{"field": None, "code": "rate_limited"}]}
    # another address is not affected
    other, other_password = make_user("dan@example.test")
    assert client.post(LOGIN, json={"email": other, "password": other_password}).status_code == 200
