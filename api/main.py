"""FastAPI app factory for the admin API (C3).

Per ARCH-001@0.1.1 §3 C3:
  - Creates the FastAPI app.
  - Includes routers: auth, health, users, links, stats.
  - Configures CORS for the admin panel origin.
  - Registers exception handlers (502 for telemt unreachable — AC7).

Invariants:
  - INV-ASYNC: all endpoints are async.
  - INV-SECRETS: no secrets hardcoded; all from env vars.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.links import router as links_router
from api.routes.stats import router as stats_router
from api.routes.users import router as users_router
from telemt_proxy.exceptions import TelemtConnectionError

# CORS origins: the admin panel domain (INV-SECRETS: from env var).
CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "http://localhost:5173")


def create_app() -> FastAPI:
    """Create and configure the FastAPI admin API application.

    Returns:
        A configured FastAPI instance with all routers included,
        CORS middleware, and exception handlers.
    """
    app = FastAPI(
        title="telemt-mgmt Admin API",
        description="Admin API for Telemt MTProxy management layer (C3).",
        version="0.1.0",
    )

    # CORS: allow the admin panel origin.
    origins: list[str] = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Include routers.
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(links_router)
    app.include_router(stats_router)

    # Exception handler: TelemtConnectionError -> 502 (AC7).
    @app.exception_handler(TelemtConnectionError)
    async def telemt_connection_error_handler(
        request: Request, exc: TelemtConnectionError
    ) -> JSONResponse:
        """Handle telemt API connection errors by returning 502.

        This catches any uncaught TelemtConnectionError that escapes
        route handlers and converts it to a 502 Bad Gateway response,
        rather than letting FastAPI return a 500.
        """
        return JSONResponse(
            status_code=502,
            content={"detail": f"Telemt API unreachable: {exc}"},
        )

    return app


# Module-level app instance for uvicorn: ``uvicorn api.main:app``.
app = create_app()
