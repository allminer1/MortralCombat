"""Client address, used only as the rate-limit key. It is never logged."""

from __future__ import annotations

from starlette.requests import HTTPConnection


def client_ip(conn: HTTPConnection, trusted_proxy: bool) -> str:
    """Socket address, or the address our reverse proxy saw when `trusted_proxy` is on.

    Only the last X-Forwarded-For entry is used: it is the one appended by our own
    proxy. Earlier entries are sent by the client and can be forged.
    """
    if trusted_proxy:
        forwarded = conn.headers.get("x-forwarded-for", "")
        last = forwarded.split(",")[-1].strip()
        if last:
            return last
    return conn.client.host if conn.client else "unknown"
