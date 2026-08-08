"""Agent registry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...models.schemas import AgentManifest

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentManifest])
def list_agents(request: Request) -> list[AgentManifest]:
    return request.app.state.registry.list()


@router.get("/{agent_id}", response_model=AgentManifest)
def get_agent(agent_id: str, request: Request) -> AgentManifest:
    agent = request.app.state.registry.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    return agent

@router.get("/tools/list")
def list_tools(request: Request):
    return request.app.state.tools.list()
