"""Health check endpoint (C3).

GET /api/health — no authentication required (AC2).
Returns a simple status check.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    No authentication required (AC2). Returns ``{"status": "ok"}``.
    """
    return HealthResponse(status="ok")
