"""Request and response models for /predict.

The request model is generated from the feature spec: field names, types and ranges
are read from model/feature_spec.json and typed nowhere in the backend.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, create_model
from pydantic_core import PydanticCustomError

from app.inference import Feature, FeatureSpec


def _one_of(allowed: tuple[int, ...]):
    def check(value: int) -> int:
        if value not in allowed:
            raise PydanticCustomError("not_allowed", "value is not one of the allowed values")
        return value

    return check


def _field_type(feature: Feature) -> Any:
    unit = f" ({feature.unit})" if feature.unit else ""
    if feature.type == "bool":
        return Annotated[StrictBool, Field(description="true or false")]
    if feature.type == "int":
        return Annotated[
            int,
            Field(strict=True, ge=feature.min, le=feature.max, description=f"integer{unit}"),
        ]
    if feature.type == "enum":
        return Annotated[
            int,
            Field(
                strict=True,
                description=f"one of {list(feature.values)}",
                json_schema_extra={"enum": list(feature.values)},
            ),
            AfterValidator(_one_of(feature.values)),
        ]
    raise ValueError(f"unknown feature type {feature.type!r} for {feature.api_field}")


def build_request_model(spec: FeatureSpec) -> type[BaseModel]:
    """All fields required, unknown fields rejected, integers and real booleans only."""
    fields = {f.api_field: (_field_type(f), ...) for f in spec.features}
    return create_model("PredictRequest", __config__=ConfigDict(extra="forbid"), **fields)


class SurvivalPoints(BaseModel):
    day_7: float
    day_28: float
    day_100: float


class CurvePoint(BaseModel):
    day: int
    survival: float


class PredictResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    log_risk: float
    survival: SurvivalPoints = Field(description="Survival probability as a fraction 0-1")
    curve: list[CurvePoint] = Field(description="S(t) for integer days 0..100")
    warnings: list[str] = Field(description="Warning codes, e.g. WEIGHT_ABOVE_COHORT")
    intended_use: Literal["research"]


class HealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: Literal["ok"]
    model_version: str
    artifacts_sha256: dict[str, str]


class ErrorItem(BaseModel):
    field: str | None = Field(description="Request field the error refers to, if any")
    code: str = Field(description="Machine-readable code for the client to translate")
    min: int | None = None
    max: int | None = None
    allowed: list[int] | None = None


class ErrorResponse(BaseModel):
    errors: list[ErrorItem]
