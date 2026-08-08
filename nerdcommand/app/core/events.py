"""
Controlled message bus for JARVIS (Phase 1).

Agents and the orchestrator communicate by emitting typed events rather than
sending free-form messages to each other. This is an in-memory bus for v1;
the interface is designed so a Redis-backed bus can replace it later without
changing callers.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List

from ..models.schemas import EventType
from .observability import get_trace_id, span

Subscriber = Callable[[str, Dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Subscriber]] = defaultdict(list)

    def subscribe(self, event_type: str, fn: Subscriber) -> None:
        self._subs[event_type].append(fn)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        span("event", event=event_type, **payload)
        payload = dict(payload)
        payload.setdefault("trace_id", get_trace_id())
        for fn in list(self._subs.get(event_type, [])):
            fn(event_type, payload)

    # --- Typed conveniences -------------------------------------------------
    def sense_audio(self, level: float, transcript: str = "") -> None:
        self.emit("sense.audio", {"level": level, "transcript": transcript})

    def sense_vision(self, mime: str = "") -> None:
        self.emit("sense.vision", {"mime": mime})

    def task_created(self, task_id: str, agent_id: str) -> None:
        self.emit(EventType.TASK_CREATED.value,
                  {"task_id": task_id, "agent_id": agent_id})

    def task_started(self, task_id: str, agent_id: str) -> None:
        self.emit(EventType.TASK_STARTED.value,
                  {"task_id": task_id, "agent_id": agent_id})

    def task_completed(self, task_id: str, agent_id: str) -> None:
        self.emit(EventType.TASK_COMPLETED.value,
                  {"task_id": task_id, "agent_id": agent_id})

    def approval_requested(self, task_id: str, agent_id: str, action: str) -> None:
        self.emit(EventType.APPROVAL_REQUESTED.value,
                  {"task_id": task_id, "agent_id": agent_id, "action": action})


# Singleton bus for the process (Phase 1).
bus = EventBus()
