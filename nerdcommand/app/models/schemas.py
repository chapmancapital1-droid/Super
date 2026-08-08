"""
Contract-first data models for the JARVIS command system (Phase 1).

Per the API Platform Engineer contract: these schemas are the source of
truth and are reviewed for long-term livability before any implementation.
Every agent, task, and event in the system is a typed object — agents never
pass free-form prose to each other.
"""
from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"            # waiting on dependencies
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"
    APPROVAL_REQUIRED = "approval_required"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PermissionClass(str, enum.Enum):
    READ = "READ"
    WRITE_DRAFT = "WRITE_DRAFT"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    FINANCIAL = "FINANCIAL"
    DESTRUCTIVE = "DESTRUCTIVE"
    ADMIN = "ADMIN"


class EventType(str, enum.Enum):
    TASK_CREATED = "task.created"
    TASK_PLANNED = "task.planned"
    TASK_STARTED = "task.started"
    TASK_WAITING = "task.waiting"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    TOOL_CALLED = "tool.called"
    ARTIFACT_CREATED = "artifact.created"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class AgentManifest(BaseModel):
    """Versioned definition of an agent. Agents are configurations, not
    hard-coded personalities; registering a new agent is a data operation."""

    id: str
    version: str = "1.0.0"
    display_name: str
    purpose: str
    model_policy: str = "fast"                 # fast | reasoning | code | local
    temperature: float = 0.3
    tools: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)   # e.g. "read:web"
    input_schema: str = "Task"
    output_schema: str = "TaskEnvelope"
    requires_approval: bool = False
    max_cost_usd: float = 2.00
    system_prompt: Optional[str] = None        # inline, else loaded from store


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
def _now() -> float:
    return time.time()


def _id(prefix: str = "task") -> str:
    return f"NC-{prefix}-{uuid.uuid4().hex[:8]}"


class Task(BaseModel):
    """A unit of work in the task graph."""

    task_id: str = Field(default_factory=lambda: _id())
    parent_task_id: Optional[str] = None
    agent_id: str
    goal: str
    status: TaskStatus = TaskStatus.QUEUED
    priority: Priority = Priority.MEDIUM
    depends_on: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=_now)
    updated_at: float = Field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()


class TaskView(BaseModel):
    """Lightweight, API-safe projection of a task (what the UI renders)."""

    id: str
    agent_id: str
    goal: str
    status: TaskStatus
    depends_on: List[str] = Field(default_factory=list)


class TaskEnvelope(BaseModel):
    """Structured result envelope agents return. Agents communicate with
    these typed envelopes — never free-form chat."""

    message_type: str = "task_result"
    task_id: str
    agent_id: str
    status: TaskStatus = TaskStatus.COMPLETE
    confidence: Optional[float] = None
    claims: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    summary: str = ""
    errors: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------
class ApprovalRequest(BaseModel):
    """A human-in-the-loop gate on a consequential action."""

    id: str = Field(default_factory=lambda: _id("apr"))
    task_id: str
    agent_id: str
    action: str
    description: str
    permission_class: PermissionClass
    status: str = "pending"                    # pending | granted | denied
    trace_id: str = ""


# ---------------------------------------------------------------------------
# Chat / API
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """A single user turn. The orchestrator interprets intent, plans, and
    executes — the caller does not need to know which agents are involved."""

    message: str
    session_id: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SensesStatus(BaseModel):
    """Snapshot of JARVIS' current hearing/vision state."""

    hearing_enabled: bool = False
    room: Dict[str, Any] = Field(default_factory=dict)
    vision_enabled: bool = False
    last_frame_at: Optional[float] = None


class ChatResponse(BaseModel):
    session_id: str
    task_id: str
    graph_id: str
    status: str
    trace_id: str
    plan: List[TaskView] = Field(default_factory=list)
    summary: str = ""
    approvals: List[ApprovalRequest] = Field(default_factory=list)
    senses: Optional[SensesStatus] = None
