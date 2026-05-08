from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from subnet_api import __version__
from subnet_api.errors import register_exception_handlers
from subnet_api.routes import router as v1_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="better-subnet-calculator-api",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    register_exception_handlers(app)
    app.include_router(v1_router)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs", status_code=307)

    return app


app = create_app()
