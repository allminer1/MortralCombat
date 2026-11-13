"""Accounts and saved calculations (spec Section 8). Mounted only when ENABLE_ACCOUNTS is on.

No `from __future__ import annotations`: FastAPI must see the generated request model
as a real class (same reason as in v1.py).
"""

import csv
import io
import secrets
import uuid
from collections.abc import Iterator
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as Db
from sqlalchemy.orm import sessionmaker

from app.accounts import service
from app.accounts.security import PASSWORD_MAX, hash_password, needs_rehash, verify_password
from app.api.v1 import warning_codes
from app.core.client import client_ip
from app.core.config import Settings
from app.core.ratelimit import RateLimiter
from app.db.models import CASE_CODE_MAX, Calculation, Session
from app.inference import Predictor
from app.schemas.predict import ErrorResponse, build_request_model

CSRF_HEADER = "x-csrf-token"
CASE_CODE_PATTERN = rf"^[A-Za-z0-9][A-Za-z0-9_-]{{0,{CASE_CODE_MAX - 1}}}$"
MAX_LIST = 500


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    password: str = Field(max_length=PASSWORD_MAX)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(max_length=PASSWORD_MAX)
    new_password: str = Field(max_length=PASSWORD_MAX)


class Me(BaseModel):
    email: str
    role: str
    csrf_token: str


def fail(status: int, code: str, request: Request, headers: dict | None = None) -> HTTPException:
    request.state.error_codes = [code]
    return HTTPException(status_code=status, detail=code, headers=headers)


def item_json(row: Calculation, with_curve: bool) -> dict:
    outputs = dict(row.outputs)
    if not with_curve:
        outputs.pop("curve", None)
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat(),
        "case_code": row.case_code,
        "model_version": row.model_version,
        "inputs": row.inputs,
        "outputs": outputs,
    }


def build_accounts_router(
    predictor: Predictor, settings: Settings, session_factory: sessionmaker[Db]
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["accounts"])
    cookie_name = "__Host-nms_session" if settings.cookie_secure else "nms_session"
    login_limiter = RateLimiter(settings.login_attempts_per_15_min, window_seconds=900)
    PredictRequest = build_request_model(predictor.spec)
    SaveRequest = create_model(
        "SaveRequest",
        __config__=ConfigDict(extra="forbid"),
        inputs=(PredictRequest, ...),
        case_code=(Annotated[str | None, Field(pattern=CASE_CODE_PATTERN, max_length=CASE_CODE_MAX)], None),
    )
    api_fields = list(predictor.spec.api_fields)
    errors = {
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    }

    def get_db() -> Iterator[Db]:
        with session_factory() as db:
            yield db

    def same_origin(request: Request) -> None:
        """Browsers send Origin on cross-site state-changing requests; it must be ours."""
        origin = request.headers.get("origin")
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            raise fail(403, "csrf_failed", request)

    def current_session(request: Request, db: Db = Depends(get_db)) -> Session:
        token = request.cookies.get(cookie_name)
        row = service.load_session(db, token, settings.session_idle_minutes) if token else None
        if row is None:
            raise fail(401, "not_signed_in", request)
        return row

    def csrf(request: Request, session: Session = Depends(current_session)) -> Session:
        same_origin(request)
        sent = request.headers.get(CSRF_HEADER, "")
        if not secrets.compare_digest(sent, session.csrf_token):
            raise fail(403, "csrf_failed", request)
        return session

    def set_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            cookie_name,
            token,
            max_age=settings.session_max_hours * 3600,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )

    def own(db: Db, session: Session, item_id: uuid.UUID, request: Request) -> Calculation:
        """The item if it belongs to the signed-in user; otherwise 404, never 403, so that
        nobody can find out which ids exist."""
        row = db.scalar(
            select(Calculation).where(Calculation.id == item_id, Calculation.user_id == session.user_id)
        )
        if row is None:
            raise fail(404, "not_found", request)
        return row

    @router.post("/auth/login", response_model=Me, responses=errors, dependencies=[Depends(same_origin)])
    def login(body: Credentials, request: Request, response: Response, db: Db = Depends(get_db)) -> Me:
        email = body.email.strip().lower()
        key = f"{client_ip(request, settings.trusted_proxy)}|{email}"
        retry_after = login_limiter.check(key)
        if retry_after:
            raise fail(429, "rate_limited", request, {"Retry-After": str(retry_after)})
        user = service.find_user(db, email)
        ok = verify_password(user.password_hash if user else None, body.password)
        if not ok or user is None or not user.is_active:
            raise fail(401, "invalid_credentials", request)  # same answer for every cause
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(body.password)
        session, token = service.open_session(db, user, settings.session_max_hours)
        db.commit()
        set_cookie(response, token)
        return Me(email=user.email, role=user.role, csrf_token=session.csrf_token)

    @router.post("/auth/logout", status_code=204, responses=errors)
    def logout(response: Response, session: Session = Depends(csrf), db: Db = Depends(get_db)) -> None:
        db.execute(delete(Session).where(Session.id == session.id))
        db.commit()
        response.delete_cookie(
            cookie_name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax"
        )

    @router.get("/auth/me", response_model=Me, responses=errors)
    def me(session: Session = Depends(current_session)) -> Me:
        return Me(email=session.user.email, role=session.user.role, csrf_token=session.csrf_token)

    @router.post("/auth/password", status_code=204, responses=errors)
    def change_password(
        body: PasswordChange, request: Request, session: Session = Depends(csrf), db: Db = Depends(get_db)
    ) -> None:
        user = db.merge(session.user)
        if not verify_password(user.password_hash, body.current_password):
            raise fail(401, "invalid_credentials", request)
        try:
            service.set_password(db, user, body.new_password, keep_session=session.id)
        except service.AccountError as exc:
            raise fail(422, exc.args[0], request) from None
        db.commit()

    @router.post("/calculations", status_code=201, responses=errors)
    def save(
        body: SaveRequest, request: Request, session: Session = Depends(csrf), db: Db = Depends(get_db)
    ) -> dict:  # type: ignore[valid-type]
        # The result is computed here from the inputs; a client cannot store its own numbers.
        inputs = body.inputs.model_dump()
        warnings = warning_codes(inputs)
        request.state.warning_codes = warnings
        result = predictor.predict(inputs)
        points = result.survival_points
        row = Calculation(
            id=uuid.uuid4(),
            user_id=session.user_id,
            created_at=service.now(),
            case_code=body.case_code,
            inputs=inputs,
            outputs={
                "log_risk": result.log_risk,
                "survival": {f"day_{day}": value for day, value in points.items()},
                "curve": list(result.curve),
                "warnings": warnings,
            },
            model_version=result.model_version,
        )
        db.add(row)
        db.commit()
        return item_json(row, with_curve=True)

    def own_items(db: Db, session: Session, case_code: str | None = None) -> list[Calculation]:
        query = select(Calculation).where(Calculation.user_id == session.user_id)
        if case_code is not None:
            query = query.where(Calculation.case_code == case_code)
        return list(db.scalars(query.order_by(Calculation.created_at.desc()).limit(MAX_LIST)))

    @router.get("/calculations", responses=errors)
    def list_items(
        case_code: str | None = None, session: Session = Depends(current_session), db: Db = Depends(get_db)
    ) -> dict:
        return {"items": [item_json(row, with_curve=False) for row in own_items(db, session, case_code)]}

    @router.get("/calculations/export.csv", responses=errors)
    def export(session: Session = Depends(current_session), db: Db = Depends(get_db)) -> Response:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "created_at",
                "case_code",
                "model_version",
                *api_fields,
                "log_risk",
                "day_7",
                "day_28",
                "day_100",
                "warnings",
            ]
        )
        for row in own_items(db, session):
            survival = row.outputs["survival"]
            writer.writerow(
                [
                    row.id,
                    row.created_at.isoformat(),
                    row.case_code or "",
                    row.model_version,
                    *[row.inputs.get(name) for name in api_fields],
                    row.outputs["log_risk"],
                    survival["day_7"],
                    survival["day_28"],
                    survival["day_100"],
                    " ".join(row.outputs.get("warnings", [])),
                ]
            )
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="neomortalsurv-calculations.csv"',
                "Cache-Control": "no-store",
            },
        )

    @router.get("/calculations/{item_id}", responses=errors)
    def get_item(
        item_id: uuid.UUID,
        request: Request,
        session: Session = Depends(current_session),
        db: Db = Depends(get_db),
    ) -> dict:
        return item_json(own(db, session, item_id, request), with_curve=True)

    @router.delete("/calculations/{item_id}", status_code=204, responses=errors)
    def delete_item(
        item_id: uuid.UUID, request: Request, session: Session = Depends(csrf), db: Db = Depends(get_db)
    ) -> None:
        db.delete(own(db, session, item_id, request))
        db.commit()

    return router
