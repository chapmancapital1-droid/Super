"""
In-memory store for JARVIS (Phase 1).

Holds sessions, task graphs, and approvals for the life of the process.
The interface is deliberately small so a PostgreSQL-backed store can replace
it in a later phase without touching the orchestrator or API layer.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from ..core.task_engine import TaskGraph
from ..models.schemas import ApprovalRequest


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, str] = {}              # session_id -> name
        self._graphs: Dict[str, TaskGraph] = {}          # task_id -> graph
        self._approvals: Dict[str, ApprovalRequest] = {}
        self._last_agent_by_session: Dict[str, str] = {}

    def new_session(self, name: str = "default") -> str:
        sid = "sess-" + uuid.uuid4().hex[:8]
        self._sessions[sid] = name
        return sid

    def graph_for(self, task_id: str) -> Optional[TaskGraph]:
        return self._graphs.get(task_id)

    def save_graph(self, task_id: str, graph: TaskGraph) -> None:
        self._graphs[task_id] = graph

    def add_approval(self, req: ApprovalRequest) -> None:
        self._approvals[req.id] = req

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        return self._approvals.get(approval_id)

    def list_approvals(self, status: Optional[str] = None) -> List[ApprovalRequest]:
        items = list(self._approvals.values())
        if status:
            items = [a for a in items if a.status == status]
        return items

    def set_agent_for_session(self, session_id: str, agent_id: str) -> None:
        self._last_agent_by_session[session_id] = agent_id
