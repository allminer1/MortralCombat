"""Access log that cannot contain clinical data (CLAUDE.md rule 5, spec Section 6).

One line per request: method, path, status, latency, model version, warning codes and
validation error codes. The middleware never touches the request body, the query
string, headers or the client address, so none of them can reach the log.
"""

from __future__ import annotations

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

access_logger = logging.getLogger("neomortalsurv.access")


def configure_logging(level: str) -> None:
    if not access_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        access_logger.addHandler(handler)
    access_logger.setLevel(level)


class AccessLogMiddleware:
    """Pure ASGI middleware: wraps `send` to read the status code, passes `receive` through."""

    def __init__(self, app: ASGIApp, model_version: str) -> None:
        self.app = app
        self.model_version = model_version

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        status = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            access_logger.info(
                "method=%s path=%s status=%d latency_ms=%.1f model_version=%s warnings=%s errors=%s",
                scope["method"],
                scope["path"],  # path only: scope["query_string"] is never read
                status,
                1000 * (time.perf_counter() - started),
                self.model_version,
                ",".join(state.get("warning_codes", ())) or "-",
                ",".join(state.get("error_codes", ())) or "-",
            )
