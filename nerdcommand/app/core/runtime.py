"""
Agent runtime for JARVIS (Phase 1).

Given an AgentManifest + a Task, the runtime composes the agent's system
prompt with the task context, invokes the model router, and returns a typed
TaskEnvelope. This is where a "persona" becomes an executing capability.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..models.schemas import AgentManifest, Task, TaskEnvelope
from .observability import log, span
from .router import ModelRouter
from .tools import ToolRegistry

# Expected JSON shape the model returns for a task envelope (partial).
_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "claims": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "recommended_next_steps": {"type": "array", "items": {"type": "string"}},
    },
}


class AgentRuntime:
    def __init__(
        self,
        router: ModelRouter,
        tools: ToolRegistry,
        prompts_dir: Path,
    ) -> None:
        self.router = router
        self.tools = tools
        self.prompts_dir = prompts_dir

    def _system_prompt(self, agent: AgentManifest) -> str:
        if agent.system_prompt:
            return agent.system_prompt
        # Fall back to a per-agent prompt file if present.
        path = self.prompts_dir / f"{agent.id}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return (
            f"You are {agent.display_name}. Purpose: {agent.purpose}. "
            "Return concise, structured, honest results. Never fabricate "
            "sources or claim work you did not perform."
        )

    def execute(
        self,
        agent: AgentManifest,
        task: Task,
        tools_inputs: Optional[dict] = None,
    ) -> TaskEnvelope:
        span("agent", agent=agent.id, task=task.task_id)
        log("agent.start", agent=agent.id, task=task.task_id)

        system_prompt = self._system_prompt(agent)
        user_prompt = json.dumps(
            {
                "task_id": task.task_id,
                "goal": task.goal,
                "inputs": task.inputs,
                "constraints": task.constraints,
                "success_criteria": task.success_criteria,
            },
            indent=2,
        )

        try:
            raw = self.router.generate(
                agent,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=_OUTPUT_SCHEMA,
            )
        except Exception as exc:  # noqa: BLE001
            log("agent.error", agent=agent.id, task=task.task_id, error=str(exc))
            return TaskEnvelope(
                task_id=task.task_id,
                agent_id=agent.id,
                status="failed",
                errors=[str(exc)],
            )

        # Normalize whatever the model returned into a typed envelope.
        return TaskEnvelope(
            task_id=task.task_id,
            agent_id=agent.id,
            status="complete",
            confidence=raw.get("confidence"),
            claims=raw.get("claims", []),
            sources=raw.get("sources", []),
            artifacts=raw.get("artifacts", []),
            recommended_next_steps=raw.get("recommended_next_steps", []),
            summary=raw.get("summary", ""),
            errors=raw.get("errors", []),
        )
