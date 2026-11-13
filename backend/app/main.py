"""FastAPI application. `app` is created at import for uvicorn (`app.main:app`)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from swagger_ui_bundle import swagger_ui_path

from app.api.errors import error_body, make_validation_handler
from app.api.v1 import build_router
from app.core.config import Settings
from app.core.logging import AccessLogMiddleware, configure_logging
from app.core.warnings import WarningRules
from app.inference import Predictor, default_model_dir

HTTP_ERROR_CODES = {
    401: "not_signed_in",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    429: "rate_limited",
}
DOCS_ASSETS = "/api/docs/assets"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)
    model_dir = settings.model_dir or default_model_dir()
    predictor = Predictor(model_dir)  # the single ONNX session, created at startup

    app = FastAPI(
        title="NeoMortalSurv API",
        version=predictor.model_version,
        description="Survival estimates for very-low-birth-weight infants from a published DeepSurv model "
        "(doi:10.3389/fped.2026.1801840). Research use; not a substitute for clinical judgement.",
        openapi_url="/api/openapi.json",
        docs_url=None,  # served below from local files: no CDN (spec Section 4)
        redoc_url=None,
    )
    app.openapi_version = "3.0.3"  # the bundled Swagger UI 4 does not read OpenAPI 3.1
    app.state.predictor = predictor
    app.add_middleware(AccessLogMiddleware, model_version=predictor.model_version)
    app.add_exception_handler(RequestValidationError, make_validation_handler(predictor.spec))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        # Our own handlers pass a code as `detail`; anything else gets the generic code.
        known = getattr(request.state, "error_codes", None)
        code = known[0] if known else HTTP_ERROR_CODES.get(exc.status_code, "error")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body({"field": None, "code": code}),
            headers=exc.headers,
        )

    rules = WarningRules(predictor.spec)
    app.include_router(build_router(predictor, settings, model_dir, rules))

    # Accounts and saved history: nothing below exists unless the flag is on.
    if settings.enable_accounts:
        if not settings.database_url:
            raise RuntimeError("ENABLE_ACCOUNTS is on but DATABASE_URL is not set")
        from app.api.accounts import build_accounts_router
        from app.db.engine import make_engine, make_session_factory

        engine = make_engine(settings.database_url)
        app.state.db_engine = engine
        app.include_router(build_accounts_router(predictor, settings, make_session_factory(engine), rules))

    @app.get("/api/v1/features", tags=["meta"], summary="Which optional features this server has switched on")
    def features() -> dict[str, bool]:
        return {"accounts": settings.enable_accounts}

    app.mount(DOCS_ASSETS, StaticFiles(directory=str(swagger_ui_path)), name="docs-assets")

    @app.get("/api/docs", include_in_schema=False)
    def docs() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} docs",
            swagger_js_url=f"{DOCS_ASSETS}/swagger-ui-bundle.js",
            swagger_css_url=f"{DOCS_ASSETS}/swagger-ui.css",
            swagger_favicon_url=f"{DOCS_ASSETS}/favicon-32x32.png",
        )

    return app


app = create_app()
