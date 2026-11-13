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

    @classmethod
    def from_env(cls) -> Settings:
        model_dir = os.environ.get("MODEL_DIR")
        return cls(
            model_dir=Path(model_dir) if model_dir else None,
            rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
            trusted_proxy=_flag("TRUSTED_PROXY", False),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
