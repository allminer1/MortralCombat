"""/api/v1 endpoints (spec Section 6).

No `from __future__ import annotations` here: FastAPI must see the generated request
model as a real class, not as a string, to read it from the JSON body.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.client import client_ip
from app.core.config import Settings
from app.core.ratelimit import RateLimiter
from app.core.warnings import WarningRules
from app.inference import Predictor
from app.inference.hazard import CURVE_DAYS
from app.schemas.predict import (
    CurvePoint,
    ErrorResponse,
    HealthResponse,
    PredictResponse,
    SurvivalPoints,
    build_request_model,
)


def build_router(predictor: Predictor, settings: Settings, model_dir: Path, rules: WarningRules) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    PredictRequest = build_request_model(predictor.spec)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    model_info = {
        "model_version": predictor.model_version,
        "model_card": json.loads((model_dir / "model_card.json").read_text(encoding="utf-8")),
        "feature_spec": json.loads((model_dir / "feature_spec.json").read_text(encoding="utf-8")),
    }
    model_info["citation"] = model_info["model_card"]["citation"]
    # Smallest and largest value of each continuous input in the training set.
    model_info["training_ranges"] = rules.training_ranges

    def rate_limit(request: Request) -> None:
        retry_after = limiter.check(client_ip(request, settings.trusted_proxy))
        if retry_after:
            request.state.error_codes = ["rate_limited"]
            raise HTTPException(status_code=429, headers={"Retry-After": str(retry_after)})

    @router.get("/health", response_model=HealthResponse, summary="Liveness and loaded model")
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok", model_version=predictor.model_version, artifacts_sha256=predictor.artifact_sha256
        )

    @router.get("/model", summary="Model card, feature spec (names, ranges, units), citation")
    def model() -> dict:
        return model_info

    @router.post(
        "/predict",
        response_model=PredictResponse,
        summary="One prediction",
        dependencies=[Depends(rate_limit)],
        responses={
            422: {"model": ErrorResponse, "description": "Validation errors as codes"},
            429: {"model": ErrorResponse, "description": "Rate limit exceeded; see Retry-After"},
        },
    )
    def predict(body: PredictRequest, request: Request) -> PredictResponse:  # type: ignore[valid-type]
        inputs = body.model_dump()
        warnings = rules.check(inputs)
        request.state.warning_codes = warnings.codes
        result = predictor.predict(inputs)
        points = result.survival_points
        return PredictResponse(
            model_version=result.model_version,
            log_risk=result.log_risk,
            survival=SurvivalPoints(**{f"day_{day}": value for day, value in points.items()}),
            curve=[CurvePoint(day=d, survival=s) for d, s in zip(CURVE_DAYS, result.curve, strict=True)],
            warnings=warnings.codes,
            outside_training_range=warnings.outside_training_range,
            intended_use="research",
        )

    return router
