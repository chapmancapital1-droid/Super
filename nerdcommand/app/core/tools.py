"""
Tool registry and permissioned tool gateway for JARVIS (Phase 1).

Tools are capabilities granted per-agent by policy (least privilege). Every
call flows through the gateway: permission check -> execute -> audit event.
Phase 1 ships stub implementations so the pipeline is exercisable; real
adapters (web search, browser, GitHub) plug in here.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from ..models.schemas import AgentManifest, EventType
from .observability import span

ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {
            "web_search": self._stub("web_search",
                                     "Web search stub: connect a real adapter."),
            "browser": self._stub("browser",
                                  "Browser stub: connect a real adapter."),
            "pdf_reader": self._stub("pdf_reader",
                                     "PDF reader stub: connect a real adapter."),
            "knowledge_search": self._stub(
                "knowledge_search", "Knowledge search stub: query pgvector later."),
            "python": self._stub("python",
                                 "Python sandbox stub: run code in a sandbox later."),
            "github": self._stub("github",
                                 "GitHub stub: connect a real adapter."),
            "microphone": self._stub(
                "microphone", "Mic/speech stub: browser STT + backend senses."),
            "camera": self._stub(
                "camera", "Camera/vision stub: browser frames + backend senses."),
            "speaker": self._stub(
                "speaker", "Speaker/TTS stub: browser speech synthesis."),
        }

    @staticmethod
    def _stub(name: str, message: str) -> ToolFn:
        def fn(_inputs: Dict[str, Any]) -> Dict[str, Any]:
            return {"tool": name, "ok": True, "stub": True, "message": message}
        return fn

    def list(self) -> list:
        return sorted(self._tools.keys())

    def invoke(self, agent: AgentManifest, tool: str,
               inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Least privilege: the agent must have the tool in its manifest.
        if tool not in agent.tools:
            raise PermissionError(
                f"Agent {agent.id} is not permitted to use tool '{tool}'")
        fn = self._tools.get(tool)
        if fn is None:
            raise KeyError(f"Unknown tool: {tool}")
        span("tool", tool=tool, agent=agent.id)
        result = fn(inputs or {})
        return result


tool_registry = ToolRegistry()
