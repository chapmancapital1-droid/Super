"""Task and approval endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...core.task_engine import TaskGraph
from ...models.schemas import TaskView

router = APIRouter(tags=["tasks"])


def _find_graph(request: Request, task_id: str) -> TaskGraph:
    graph = request.app.state.store.graph_for(task_id)
    if graph is None:
        raise HTTPException(status_code=404, detail=f"Unknown task: {task_id}")
    return graph


@router.get("/tasks/{graph_id}", response_model=list[TaskView])
def get_tasks(graph_id: str, request: Request) -> list[TaskView]:
    return _find_graph(request, graph_id).views()


@router.get("/approvals")
def list_approvals(request: Request, status: str = "pending") -> dict:
    approvals = request.app.state.store.list_approvals(status=status)
    return {"approvals": [a.model_dump() for a in approvals]}


@router.post("/approvals/{approval_id}/grant")
def grant_approval(approval_id: str, request: Request) -> dict:
    store = request.app.state.store
    approval = store.get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404,
                            detail=f"Unknown approval: {approval_id}")
    approval.status = "granted"
    return {"id": approval.id, "status": "granted"}


@router.post("/approvals/{approval_id}/deny")
def deny_approval(approval_id: str, request: Request) -> dict:
    store = request.app.state.store
    approval = store.get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404,
                            detail=f"Unknown approval: {approval_id}")
    approval.status = "denied"
    return {"id": approval.id, "status": "denied"}
