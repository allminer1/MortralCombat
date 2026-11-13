from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def normalise_url(url: str) -> str:
    """Use the psycopg 3 driver whatever form the URL was given in."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def make_engine(url: str) -> Engine:
    # hide_parameters: statement parameters (e-mails, inputs) never appear in error text or logs.
    return create_engine(
        normalise_url(url), pool_pre_ping=True, pool_size=5, max_overflow=5, hide_parameters=True
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)
