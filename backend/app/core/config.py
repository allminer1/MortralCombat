"""Runtime settings, read from environment variables. No secrets in Phase 2."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model_dir: Path | None = None  # None = repository model/ directory
    rate_limit_per_minute: int = 60  # per client IP on /predict; 0 disables the limit
    trusted_proxy: bool = False  # True only behind our own reverse proxy (Caddy)
    log_level: str = "INFO"
    # Accounts and saved history (spec Section 8). Off unless explicitly enabled; with
    # it off no database is contacted and the account endpoints do not exist.
    enable_accounts: bool = False
    database_url: str | None = None
    cookie_secure: bool = True  # False only for plain-HTTP local tests
    session_idle_minutes: int = 30
    session_max_hours: int = 12
    login_attempts_per_15_min: int = 10  # per client address and e-mail; 0 disables

    @classmethod
    def from_env(cls) -> Settings:
        model_dir = os.environ.get("MODEL_DIR")
        return cls(
            model_dir=Path(model_dir) if model_dir else None,
            rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
            trusted_proxy=_flag("TRUSTED_PROXY", False),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            enable_accounts=_flag("ENABLE_ACCOUNTS", False),
            database_url=os.environ.get("DATABASE_URL") or None,
            cookie_secure=_flag("COOKIE_SECURE", True),
            session_idle_minutes=int(os.environ.get("SESSION_IDLE_MINUTES", "30")),
            session_max_hours=int(os.environ.get("SESSION_MAX_HOURS", "12")),
            login_attempts_per_15_min=int(os.environ.get("LOGIN_ATTEMPTS_PER_15_MIN", "10")),
        )
