"""Account operations shared by the API and the admin command line."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as Db

from app.accounts.security import PASSWORD_MAX, PASSWORD_MIN, hash_password, new_token, token_hash
from app.db.models import Session, User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccountError(ValueError):
    """`args[0]` is an error code."""


def now() -> datetime:
    return datetime.now(UTC)


def normalise_email(email: str) -> str:
    email = email.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise AccountError("bad_email")
    return email


def check_password(password: str) -> None:
    if len(password) < PASSWORD_MIN:
        raise AccountError("password_too_short")
    if len(password) > PASSWORD_MAX:
        raise AccountError("password_too_long")


def find_user(db: Db, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(db: Db, email: str, password: str, role: str = "user") -> User:
    if role not in ("user", "admin"):
        raise AccountError("bad_role")
    email = normalise_email(email)
    check_password(password)
    if find_user(db, email):
        raise AccountError("email_exists")
    user = User(
        id=uuid.uuid4(), email=email, password_hash=hash_password(password), role=role, is_active=True
    )
    db.add(user)
    db.flush()
    return user


def set_password(db: Db, user: User, password: str, keep_session: uuid.UUID | None = None) -> None:
    """New password; every other session of the user is ended."""
    check_password(password)
    user.password_hash = hash_password(password)
    statement = delete(Session).where(Session.user_id == user.id)
    if keep_session is not None:
        statement = statement.where(Session.id != keep_session)
    db.execute(statement)


def set_active(db: Db, user: User, active: bool) -> None:
    user.is_active = active
    if not active:
        db.execute(delete(Session).where(Session.user_id == user.id))


def open_session(db: Db, user: User, max_hours: int) -> tuple[Session, str]:
    """Returns the row and the cookie value (which is not stored)."""
    token = new_token()
    moment = now()
    row = Session(
        id=uuid.uuid4(),
        token_hash=token_hash(token),
        csrf_token=new_token(),
        user_id=user.id,
        created_at=moment,
        last_seen_at=moment,
        expires_at=moment + timedelta(hours=max_hours),
    )
    db.add(row)
    db.flush()
    return row, token


def load_session(db: Db, token: str, idle_minutes: int) -> Session | None:
    """The live session for a cookie value, or None. Expired sessions are deleted."""
    row = db.scalar(select(Session).where(Session.token_hash == token_hash(token)))
    if row is None:
        return None
    moment = now()
    idle_out = moment - row.last_seen_at > timedelta(minutes=idle_minutes)
    if idle_out or moment >= row.expires_at or not row.user.is_active:
        db.delete(row)
        db.commit()
        return None
    if moment - row.last_seen_at > timedelta(seconds=60):  # at most one write a minute
        row.last_seen_at = moment
        db.commit()
    return row


def purge_expired_sessions(db: Db, idle_minutes: int) -> int:
    moment = now()
    result = db.execute(
        delete(Session).where(
            (Session.expires_at <= moment) | (Session.last_seen_at < moment - timedelta(minutes=idle_minutes))
        )
    )
    return result.rowcount or 0
