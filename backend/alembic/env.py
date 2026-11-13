import os

from alembic import context
from sqlalchemy import create_engine

from app.db.engine import normalise_url
from app.db.models import Base

target_metadata = Base.metadata


def run() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set")
    engine = create_engine(normalise_url(url))
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run()
