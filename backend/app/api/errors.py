"""Validation errors as codes (spec Section 6): no English sentences for the user and
no echo of the submitted values."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.inference import FeatureSpec

# pydantic error type -> API error code
CODES = {
    "missing": "missing",
    "extra_forbidden": "unknown_field",
    "int_type": "not_integer",
    "int_parsing": "not_integer",
    "int_from_float": "not_integer",
    "bool_type": "not_boolean",
    "bool_parsing": "not_boolean",
    "greater_than_equal": "out_of_range",
    "less_than_equal": "out_of_range",
    "not_allowed": "not_allowed",
    "json_invalid": "invalid_json",
    "model_attributes_type": "invalid_body",
    "dict_type": "invalid_body",
}


def error_body(*items: dict) -> dict:
    return {"errors": list(items)}


def make_validation_handler(spec: FeatureSpec):
    by_field = {f.api_field: f for f in spec.features}

    async def handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        items = []
        for err in exc.errors():
            loc = err.get("loc", ())
            name = loc[1] if len(loc) > 1 and loc[0] == "body" and isinstance(loc[1], str) else None
            code = CODES.get(err.get("type", ""), "invalid")
            item: dict = {"field": name, "code": code}
            feature = by_field.get(name)
            if feature is not None and code == "out_of_range":
                item |= {"min": feature.min, "max": feature.max}
            if feature is not None and code == "not_allowed":
                item["allowed"] = list(feature.values or ())
            items.append(item)
        # Codes only: field names of unknown fields are client-supplied text and stay out of the log.
        request.state.error_codes = sorted({i["code"] for i in items})
        return JSONResponse(status_code=422, content=error_body(*items))

    return handler
