"""Admin command line for accounts (invite-only: there is no sign-up page).

    python -m app.cli migrate
    python -m app.cli create-user EMAIL [--admin]
    python -m app.cli reset-password EMAIL
    python -m app.cli deactivate EMAIL | activate EMAIL
    python -m app.cli list-users
    python -m app.cli purge-sessions

Passwords are typed at a prompt (or piped with --password-stdin); they are never given
as command-line arguments, where they would land in the shell history.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.accounts import service
from app.core.config import Settings
from app.db.engine import make_engine, make_session_factory
from app.db.models import Calculation, User


def read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass("Password: ")
    if first != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords differ.")
    return first


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    create = sub.add_parser("create-user")
    create.add_argument("email")
    create.add_argument("--admin", action="store_true")
    create.add_argument("--password-stdin", action="store_true")
    reset = sub.add_parser("reset-password")
    reset.add_argument("email")
    reset.add_argument("--password-stdin", action="store_true")
    for name in ("deactivate", "activate"):
        sub.add_parser(name).add_argument("email")
    sub.add_parser("list-users")
    sub.add_parser("purge-sessions")
    args = parser.parse_args(argv)

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set.")
    if args.command == "migrate":
        migrate()
        print("Database is at the latest revision.")
        return 0

    settings = Settings.from_env()
    with make_session_factory(make_engine(url))() as db:
        try:
            if args.command == "create-user":
                role = "admin" if args.admin else "user"
                user = service.create_user(db, args.email, read_password(args.password_stdin), role)
                print(f"Created {user.role} {user.email}.")
            elif args.command == "list-users":
                counts = dict(
                    db.execute(select(Calculation.user_id, func.count()).group_by(Calculation.user_id)).all()
                )
                for user in db.scalars(select(User).order_by(User.email)):
                    state = "active" if user.is_active else "inactive"
                    print(f"{user.email}\t{user.role}\t{state}\t{counts.get(user.id, 0)} saved")
            elif args.command == "purge-sessions":
                removed = service.purge_expired_sessions(db, settings.session_idle_minutes)
                print(f"Removed {removed} expired sessions.")
            else:
                user = service.find_user(db, args.email)
                if user is None:
                    raise SystemExit("No such user.")
                if args.command == "reset-password":
                    service.set_password(db, user, read_password(args.password_stdin))
                    print(f"Password changed for {user.email}; all their sessions are ended.")
                else:
                    service.set_active(db, user, args.command == "activate")
                    print(f"{user.email} is now {'active' if user.is_active else 'inactive'}.")
        except service.AccountError as exc:
            raise SystemExit(f"Not done: {exc.args[0]}") from None
        db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
