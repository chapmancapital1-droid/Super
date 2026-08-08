"""Senses endpoints — JARVIS' ears and eyes.

The browser captures mic audio and camera frames (getUserMedia) and posts
them here. Audio arrives as a transcript + ambient level; video arrives as a
base64 image frame. The engine stores an auditable record and can analyze it.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ...core.observability import (
    get_trace_id, new_trace_id, reset_trace, set_trace,
)
from ...core.senses import senses

router = APIRouter(prefix="/senses", tags=["senses"])


def _trace_context():
    """Ensure a trace_id exists for this request (used by ingest handlers)."""
    if get_trace_id():
        return None
    token = set_trace(new_trace_id())
    return token


class AudioIngest(BaseModel):
    level: float = Field(0.0, ge=0.0, le=1.0)
    transcript: str = ""
    duration_ms: int = 0
    source: str = "mic"


class VisionIngest(BaseModel):
    mime: str = "image/jpeg"
    data_b64: str = ""
    width: int = 0
    height: int = 0
    description: str = ""


@router.post("/audio")
def ingest_audio(payload: AudioIngest, request: Request) -> dict:
    token = _trace_context()
    try:
        sample = senses.ingest_audio(
            level=payload.level,
            transcript=payload.transcript,
            duration_ms=payload.duration_ms,
            source=payload.source,
        )
    finally:
        if token is not None:
            reset_trace(token)
    return {
        "ok": True,
        "trace_id": sample.trace_id,
        "level": sample.level,
        "speech": bool(sample.transcript),
    }


@router.get("/status")
def senses_status(request: Request) -> dict:
    return senses.status()


@router.post("/vision")
def ingest_vision(payload: VisionIngest, request: Request) -> dict:
    # Reject empty payloads early.
    if not payload.data_b64:
        return {"ok": False, "error": "no frame data provided"}
    token = _trace_context()
    try:
        frame = senses.ingest_frame(
            mime=payload.mime,
            data_b64=payload.data_b64,
            width=payload.width,
            height=payload.height,
            description=payload.description,
        )
    finally:
        if token is not None:
            reset_trace(token)
    return {
        "ok": True,
        "trace_id": frame.trace_id,
        "width": frame.width,
        "height": frame.height,
    }
