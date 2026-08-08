"""
Agent registry for JARVIS (Phase 1).

Loads AgentManifests from a directory of JSON files at startup and validates
them. Adding an agent is a data operation: drop a JSON manifest in the
manifests dir and it becomes available. The system never hard-codes agent
personalities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError

from ..models.schemas import AgentManifest


class AgentRegistry:
    def __init__(self, manifests_dir: Path) -> None:
        self._manifests_dir = manifests_dir
        self._agents: Dict[str, AgentManifest] = {}

    def load(self) -> None:
        self._agents.clear()
        if not self._manifests_dir.exists():
            return
        for path in sorted(self._manifests_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                manifest = AgentManifest.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                # Never let one bad manifest take down the registry.
                raise ValueError(f"Invalid agent manifest {path.name}: {exc}")
            self._agents[manifest.id] = manifest

    def get(self, agent_id: str) -> Optional[AgentManifest]:
        return self._agents.get(agent_id)

    def require(self, agent_id: str) -> AgentManifest:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        return agent

    def list(self) -> List[AgentManifest]:
        return sorted(self._agents.values(), key=lambda a: a.id)
