"""Chat endpoint — the primary JARVIS entry point."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ...models.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """One user turn. The orchestrator interprets intent, plans, delegates to
    agents, and returns a structured result — the caller never needs to know
    which agents were involved."""
    return request.app.state.orchestrator.run(payload)
