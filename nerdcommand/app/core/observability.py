"""
Lightweight observability for JARVIS (Phase 1).

Every agent call and tool call is associated with a shared trace_id so a
wrong answer can be traced back to the agent/tool that produced it — a hard
requirement from the Multi-Agent Systems Architect persona.
"""
from __future__ import annotations

import contextvars
import logging
import uuid
from typing import Dict, Any

_trace_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_logger = logging.getLogger("jarvis")


def new_trace_id() -> str:
    return "tr-" + uuid.uuid4().hex[:12]


def set_trace(trace_id: str) -> contextvars.Token:
    return _trace_var.set(trace_id)


def reset_trace(token: contextvars.Token) -> None:
    _trace_var.reset(token)


def get_trace_id() -> str:
    return _trace_var.get()


def log(event: str, **fields: Any) -> None:
    """Emit a structured log line carrying the current trace_id."""
    payload = {"event": event, "trace_id": get_trace_id()}
    payload.update(fields)
    _logger.info(payload)


# Simple in-process span sink so tests/observability can inspect spans.
SPANS: list = []


def span(kind: str, **fields: Any) -> Dict[str, Any]:
    entry = {"trace_id": get_trace_id(), "kind": kind}
    entry.update(fields)
    SPANS.append(entry)
    return entry
