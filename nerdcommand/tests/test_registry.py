"""Agent registry tests."""
from pathlib import Path

from app.config import Settings
from app.core.registry import AgentRegistry
from app.models.schemas import AgentManifest


def _registry() -> AgentRegistry:
    # Point at the repo's real manifests directory.
    base = Path(__file__).resolve().parent.parent
    reg = AgentRegistry(base / "agents" / "manifests")
    reg.load()
    return reg


def test_loads_core_agents():
    reg = _registry()
    ids = {a.id for a in reg.list()}
    assert {"orchestrator", "researcher", "strategist",
            "developer", "validator"} <= ids


def test_manifest_is_typed():
    reg = _registry()
    researcher = reg.require("researcher")
    assert isinstance(researcher, AgentManifest)
    assert researcher.model_policy == "reasoning"
    assert "web_search" in researcher.tools


def test_unknown_agent_raises():
    reg = _registry()
    try:
        reg.require("does-not-exist")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
