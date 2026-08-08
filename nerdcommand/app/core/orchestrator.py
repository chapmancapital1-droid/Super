"""
Orchestrator for JARVIS (Phase 1).

The single authority that:
  1. Interprets the user's objective (simple intent classifier in Phase 1).
  2. Builds a dependency graph of Tasks (the "task graph").
  3. Executes tasks in dependency order, running independent ones in parallel.
  4. Applies human-in-the-loop approval gates for consequential actions.
  5. Aggregates results into a ChatResponse.

Phase 1 uses a deterministic planner (researcher -> strategist -> validator
for multi-step goals) as the seed. A learned planner can replace
`plan()` without changing the execution path.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from ..models.schemas import (
    AgentManifest,
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
    Task,
    TaskEnvelope,
    TaskStatus,
)
from .events import bus
from .observability import get_trace_id, new_trace_id, reset_trace, set_trace
from .registry import AgentRegistry
from .runtime import AgentRuntime
from .senses import SensesEngine, senses
from .task_engine import TaskGraph
from .tools import ToolRegistry
from ..store.memory import SessionStore

_MULTI_STEP = re.compile(
    r"\b(research|analyze|plan|build|create|prepare|develop|model|design|"
    r"compare|investigate|write)\b.*\b(and|then|for|with)\b",
    re.IGNORECASE,
)


class Orchestrator:
    def __init__(
        self,
        registry: AgentRegistry,
        runtime: AgentRuntime,
        tools: ToolRegistry,
        store: SessionStore,
        senses_engine: SensesEngine = senses,
    ) -> None:
        self.registry = registry
        self.runtime = runtime
        self.tools = tools
        self.store = store
        self.senses = senses_engine

    # --- Planning ----------------------------------------------------------
    def _classify(self, message: str) -> str:
        """Return 'multi' or 'single' for the objective."""
        if _MULTI_STEP.search(message) or len(message.split()) > 12:
            return "multi"
        return "single"

    def plan(self, message: str) -> TaskGraph:
        graph = TaskGraph(goal=message)
        kind = self._classify(message)
        if kind == "multi":
            # Hierarchical: research -> strategist -> validator.
            t1 = Task(agent_id="researcher", goal=message,
                      success_criteria=["market/evidence", "sources"],
                      inputs={"objective": message})
            t2 = Task(agent_id="strategist", goal=message,
                      depends_on=[t1.task_id],
                      inputs={"objective": message})
            t3 = Task(agent_id="validator", goal=message,
                      depends_on=[t1.task_id, t2.task_id],
                      inputs={"objective": message})
            for t in (t1, t2, t3):
                graph.add_task(t)
        else:
            t = Task(agent_id="researcher", goal=message,
                     success_criteria=["answer"], inputs={"objective": message})
            graph.add_task(t)
        for t in graph.tasks.values():
            bus.task_created(t.task_id, t.agent_id)
        return graph

    # --- Execution ---------------------------------------------------------
    def _maybe_request_approval(
        self, agent: AgentManifest, task: Task
    ) -> None:
        """Gate consequential actions behind human approval."""
        if not agent.requires_approval:
            return
        req = ApprovalRequest(
            task_id=task.task_id,
            agent_id=agent.id,
            action=f"execute {agent.id} task",
            description=task.goal,
            permission_class="EXTERNAL_ACTION",
            trace_id=get_trace_id(),
        )
        self.store.add_approval(req)
        task.status = TaskStatus.APPROVAL_REQUIRED
        task.touch()
        bus.approval_requested(task.task_id, agent.id, req.action)

    def _execute_task(self, graph: TaskGraph, task: Task) -> TaskEnvelope:
        agent = self.registry.require(task.agent_id)
        self._maybe_request_approval(agent, task)
        if task.status == TaskStatus.APPROVAL_REQUIRED:
            return TaskEnvelope(task_id=task.task_id, agent_id=agent.id,
                                status=TaskStatus.APPROVAL_REQUIRED.value,
                                summary="Awaiting human approval")
        task.status = TaskStatus.RUNNING
        task.touch()
        bus.task_started(task.task_id, agent.id)
        envelope = self.runtime.execute(agent, task)
        if envelope.status == TaskStatus.FAILED.value:
            task.status = TaskStatus.FAILED
            task.error = "; ".join(envelope.errors)
            bus.emit("task.failed", {"task_id": task.task_id,
                                     "agent_id": agent.id,
                                     "errors": envelope.errors})
        else:
            task.status = TaskStatus.COMPLETE
            task.result = {
                "summary": envelope.summary,
                "claims": envelope.claims,
                "sources": envelope.sources,
                "confidence": envelope.confidence,
            }
            task.confidence = envelope.confidence
            bus.task_completed(task.task_id, agent.id)
        task.touch()
        return envelope

    def run(self, request: ChatRequest) -> ChatResponse:
        trace_id = new_trace_id()
        token = set_trace(trace_id)
        try:
            session_id = request.session_id or self.store.new_session()
            graph = self.plan(request.message)
            graph_id = "graph-" + graph.goal[:8].replace(" ", "_")
            self.store.save_graph(graph_id, graph)
            # Simple loop: while tasks remain, run all ready tasks.
            while not graph.all_complete():
                ready = graph.ready_to_run()
                if not ready:
                    break
                for task in ready:
                    self._execute_task(graph, task)

            return self._build_response(session_id, request, graph, trace_id)
        finally:
            reset_trace(token)

    def _build_response(
        self, session_id: str, request: ChatRequest, graph: TaskGraph,
        trace_id: str,
    ) -> ChatResponse:
        summaries = [
            t.result["summary"]
            for t in graph.tasks.values()
            if t.result and t.result.get("summary")
        ]
        summary = " | ".join(summaries) if summaries else (
            "No structured result produced (check approvals).")
        approvals = self.store.list_approvals(status="pending")
        task_id = list(graph.tasks.keys())[0]
        status = "complete"
        if any(t.status == TaskStatus.APPROVAL_REQUIRED
               for t in graph.tasks.values()):
            status = "approval_required"
        elif any(t.status == TaskStatus.FAILED for t in graph.tasks.values()):
            status = "partial"
        graph_id = "graph-" + graph.goal[:8].replace(" ", "_")
        return ChatResponse(
            session_id=session_id,
            task_id=task_id,
            graph_id=graph_id,
            status=status,
            trace_id=trace_id,
            plan=graph.views(),
            summary=summary,
            approvals=approvals,
            senses=self.senses.status(),
        )
