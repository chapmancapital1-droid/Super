"""
NerdCommand.AI — JARVIS API entry point (Phase 1).

Boots the full orchestration stack: agent registry, model router, tool
registry, agent runtime, session store, and orchestrator, then exposes the
versioned v1 API.

Run (local, echo provider — no API key needed):
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .api.v1 import agents, chat, health, senses, tasks
from .config import settings
from .core.orchestrator import Orchestrator
from .core.registry import AgentRegistry
from .core.router import ModelRouter
from .core.runtime import AgentRuntime
from .core.tools import ToolRegistry
from .store.memory import SessionStore
from .core.mcp_manager import mcp_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start MCP Manager
    import asyncio
    asyncio.create_task(mcp_manager.start())
    yield
    # Shutdown logic if needed (e.g. stop MCP servers)

def create_app() -> FastAPI:
    app = FastAPI(
        title="NerdCommand.AI — JARVIS",
        version=settings.app_version,
        description=(
            "Personal AI command system. One interface, many specialized "
            "agents, verified execution."
        ),
        lifespan=lifespan,
    )

    # Wire the engine.
    registry = AgentRegistry(settings.manifests_dir)
    registry.load()

    router = ModelRouter()
    tools = ToolRegistry()
    runtime = AgentRuntime(router, tools, settings.prompts_dir)
    store = SessionStore()
    orchestrator = Orchestrator(registry, runtime, tools, store)

    app.state.settings = settings
    app.state.registry = registry
    app.state.router = router
    app.state.tools = tools
    app.state.runtime = runtime
    app.state.store = store
    app.state.orchestrator = orchestrator

    # Versioned API.
    v1 = __import__("fastapi").APIRouter(prefix="/api/v1")
    v1.include_router(health.router)
    v1.include_router(agents.router)
    v1.include_router(chat.router)
    v1.include_router(tasks.router)
    v1.include_router(senses.router)
    app.include_router(v1)

    return app


app = create_app()
