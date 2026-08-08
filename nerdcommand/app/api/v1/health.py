"""Health + capability endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])


@router.get("/health")
def health(request: Request) -> dict:
    return {
        "status": "ok",
        "app": request.app.state.settings.app_name,
        "version": request.app.state.settings.app_version,
        "provider": request.app.state.settings.model_provider,
        "agents": len(request.app.state.registry.list()),
    }
