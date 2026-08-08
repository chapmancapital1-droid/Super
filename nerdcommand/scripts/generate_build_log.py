#!/usr/bin/env python3
"""
Build Log generator for NerdCommand.AI JARVIS.

Assembles BUILD_LOG.txt: a living document that captures the design rationale,
architecture, every build decision and why, and the *current* source code of
the whole project (inlined verbatim from the repo).

Regenerate after any change:
    python3 scripts/generate_build_log.py

The generated file stays in sync with the code because it reads the real
source files rather than embedding stale copies.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Narrative sections (the "why" behind the build)
# ---------------------------------------------------------------------------
HEADER = """
================================================================================
  NERDCOMMAND.AI - JARVIS  |  BUILD LOG  |  v0.1.0 (Phase 1)
================================================================================
  Personal AI Command System: one interface, many specialists, verified
  execution. This document is the living build record for the project: what
  was built, why each decision was made, and the current source of every file.
  It is regenerated from the actual code with:
      python3 scripts/generate_build_log.py
================================================================================

TABLE OF CONTENTS
  1. Executive summary
  2. Why this architecture (the design philosophy)
  3. The build phases and what each delivered
  4. Repository layout
  5. Backend (Phase 1) - design + source
  6. Frontend (Next.js web UI) - design + source
  7. Agent manifests and system prompts
  8. Tests and how to run them
  9. How to run the full stack
  10. What comes next
================================================================================

--------------------------------------------------------------------------------
1. EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
JARVIS is the NerdCommand.AI personal AI command system. The user speaks in
ordinary language; JARVIS interprets the goal, plans the work as a task graph,
delegates to specialized agents, respects human approval gates for
consequential actions, and returns a verified structured result.

This Phase-1 build delivers a working end-to-end "command loop":
    natural language -> orchestrator -> task graph -> agents -> result
backed by a FastAPI service and a Next.js command-center UI.

The architectural foundation is captured in a separate design PDF
(nerdcommand-design/NerdCommand_AI_JARVIS_Developer_Design_v1.pdf). This
BUILD_LOG records the implementation of that design.

--------------------------------------------------------------------------------
2. WHY THIS ARCHITECTURE (THE DESIGN PHILOSOPHY)
--------------------------------------------------------------------------------
The core principle is that JARVIS is an OPERATING SYSTEM for AI work, not a
collection of chatbots. Five rules drive every decision:

  (1) One interface, many specialists.
      The user talks to JARVIS, never to a menu of bots. The orchestrator is
      the single authority that routes and supervises work.

  (2) Intent before execution; plan before complex action.
      Multi-step work becomes an explicit, inspectable dependency graph. A
      deterministic planner (research -> strategist -> validate) seeds Phase 1;
      a learned planner can replace plan() without touching execution.

  (3) Structured contracts, not free-form chatter.
      Agents communicate via typed TaskEnvelopes and a typed event bus, never
      by passing prose to each other. Schemas are the source of truth.

  (4) Least privilege + human approval.
      Every agent holds only the tools and permissions its role requires. The
      policy engine (code) enforces boundaries; the system prompt only guides
      behavior. Consequential actions require approval gates.

  (5) Observable, model-agnostic, modular.
      Every agent call and tool call carries a shared trace_id. Models sit
      behind a router so they can be swapped without rewriting agents. New
      agents are added as data (manifests), not code.

--------------------------------------------------------------------------------
3. THE BUILD PHASES AND WHAT EACH DELIVERED
--------------------------------------------------------------------------------
  PHASE 0 - Design document
      Produced NerdCommand_AI_JARVIS_Developer_Design_v1.pdf: full architecture,
      master JARVIS system prompt, API/DB/repo contracts, security model, and a
      10-phase roadmap. The spec the team builds from.

  PHASE 1a - The Agency (skills library)
      Installed msitarzewski/agency-agents (270 AI specialist personas) into
      skills/agency/ so the team can consult the "superagents" (multi-agent
      systems architect, backend architect, API platform engineer) directly.
      The Phase-1 backend was built following their guidance.

  PHASE 1b - Backend (this version)
      FastAPI service implementing the full command loop:
        - agent registry (manifests as data)
        - model router (echo provider for no-key dev; OpenAI-compatible)
        - agent runtime (prompt + model + typed envelope)
        - task engine (dependency graph + readiness scheduling)
        - policy engine (permission + approval enforcement)
        - tool gateway (permissioned stubs)
        - typed event bus with trace_id
        - in-memory session store (PostgreSQL-ready interface)
        - orchestrator (intent -> plan -> execute -> aggregate)
      15 passing pytest tests.

  PHASE 1c - Frontend (this version)
      Next.js App Router command-center UI:
        - chat box that posts to /api/v1/chat
        - live agent graph rendering (task nodes + status pills)
        - approvals panel
        - agent roster panel
        - health/online indicator
      Browser uses only relative /api URLs; the Next dev server rewrites them
      to the FastAPI backend (preview-safe, no CORS/localhost in browser).

  PHASE 8a - Senses: Voice + Vision (this version)
      JARVIS gains ears and eyes:
        - Speak to JARVIS: browser speech recognition (Web Speech API)
          transcribes the mic, sends the command through the same chat
          pipeline, and JARVIS replies out loud (speech synthesis).
        - Hear the room: a live audio level meter (AudioContext AnalyserNode)
          samples ambient loudness and posts periodic samples to the backend,
          which classifies the room as silence/quiet/active/loud and tracks
          any speech heard.
        - See you: browser getUserMedia camera feeds a live preview; a
          "send frame" button posts a base64 frame to the backend vision
          endpoint for JARVIS to analyze (a real vision model plugs in later).
      Browser capture is required because the mic/camera physically live on
      the user's machine; the backend ingests and stores auditable records.
      New backend: app/core/senses.py, app/api/v1/senses.py. New frontend:
      lib/senses.ts, app/components/SensesPanel.tsx.

--------------------------------------------------------------------------------
4. REPOSITORY LAYOUT
--------------------------------------------------------------------------------
  nerdcommand/
  ├── app/                      FastAPI backend
  │   ├── main.py               app factory + API wiring
  │   ├── config.py             settings (env-driven)
  │   ├── models/schemas.py     contract-first Pydantic models
  │   ├── core/                 engine
  │   │   ├── orchestrator.py   intent -> plan -> execute -> aggregate
  │   │   ├── task_engine.py    dependency graph + readiness
  │   │   ├── registry.py       agent manifests loader
  │   │   ├── router.py         model router (echo / openai)
  │   │   ├── runtime.py        agent prompt + model + envelope
  │   │   ├── policy.py         permission / approval enforcement
  │   │   ├── tools.py          permissioned tool gateway (stubs)
  │   │   ├── events.py         typed event bus with trace_id
  │   │   └── observability.py  trace_id + span sink
  │   ├── store/memory.py       in-memory session store
  │   ├── api/v1/               versioned endpoints (health, agents, chat, tasks, senses)
  │   └── core/senses.py        audio/vision ingestion engine (ears + eyes)
  ├── agents/
  │   ├── manifests/            agent definitions (JSON - data, not code)
  │   └── prompts/              per-agent system prompts
  ├── apps/web/                 Next.js command-center UI
  │   ├── app/page.tsx          command center page
  │   ├── app/layout.tsx        root layout
  │   ├── app/globals.css       JARVIS brand styling
  │   ├── lib/api.ts            API client (relative URLs)
  │   ├── lib/types.ts          TS mirror of the Pydantic models
  │   └── next.config.mjs       /api rewrite proxy to backend
  ├── skills/agency/            270 AI specialist personas (The Agency)
  ├── tests/                    pytest suite
  ├── scripts/generate_build_log.py   this generator
  └── BUILD_LOG.txt             this document

--------------------------------------------------------------------------------
5. BACKEND (PHASE 1) - DESIGN + SOURCE
--------------------------------------------------------------------------------
Design: The backend is a set of small, single-purpose modules around a central
orchestrator. The orchestrator is the only place that understands the full
pipeline; agents, tools, and memory are swappable behind it. Every boundary is
a typed Pydantic contract (schemas.py). The model router keeps providers
interchangeable. The policy engine is code, separate from the prompt.

Source files below are inlined verbatim from the repository.

--------------------------------------------------------------------------------
6. FRONTEND (NEXT.JS WEB UI) - DESIGN + SOURCE
--------------------------------------------------------------------------------
Design: the web UI is a Next.js App Router command center. The browser never
calls the backend directly; it uses relative /api/* URLs and Next.js rewrites
them to the FastAPI service (next.config.mjs). This keeps the client CORS-free
and preview-safe. The page (app/page.tsx) is a single "command center" screen
that:
  - takes a natural-language command and posts it to /api/v1/chat
  - renders the returned task graph as live agent nodes with status pills
  - shows a human-approval panel when the orchestrator gates an action
  - lists the registered agents (from /api/v1/agents)
  - shows a backend-online indicator (from /api/v1/health)
TypeScript types mirror the Pydantic models so the contract is shared.

Sections 7 (agent manifests/prompts), 8 (tests), and 9 (run instructions) are
captured by the inlined files below and the README.

--------------------------------------------------------------------------------
ALL SOURCE FILES (current code, inlined verbatim)
--------------------------------------------------------------------------------

"""

FOOTER = """
--------------------------------------------------------------------------------
10. WHAT COMES NEXT (roadmap - from the design PDF)
--------------------------------------------------------------------------------
  Phase 2 - Orchestrator depth  : learned intent classification + dynamic plans
  Phase 3 - Agent runtime       : more core agents via manifests only
  Phase 4 - Tools               : real web_search, browser, GitHub, Python sandbox
  Phase 5 - Memory              : PostgreSQL + pgvector (replace SessionStore)
  Phase 6 - Visual OS           : React Flow live node graph (replace static list)
  Phase 7 - Validator           : eval harness + QA gates
  Phase 8 - Voice               : speech input/output
  Phase 9 - Autonomy            : policies, approvals, scheduled tasks
  Phase 10 - Productization     : multi-tenant SaaS + billing + marketplace

This BUILD_LOG will be updated (regenerated) as the program grows so it always
reflects the current code and rationale.

================================================================================
  END BUILD LOG - NerdCommand.AI JARVIS v0.1.0
================================================================================
"""


def render_code_block(name: str, text: str) -> str:
    sep = "-" * 60
    ruler = "=" * 72
    return (
        "\n"
        + ruler
        + "\n"
        + "  FILE: "
        + name
        + "\n"
        + ruler
        + "\n"
        + text.rstrip()
        + "\n"
        + "\n"
        + sep
        + "\n"
    )


def collect_files(root: Path) -> list[tuple[str, Path]]:
    """Collect source files in a stable, meaningful order."""
    order: list[tuple[str, Path]] = []

    def add(rel: str):
        p = root / rel
        if p.exists() and p.is_file():
            order.append((rel, p))

    # Backend: package, then core, then store, then api.
    add("app/__init__.py")
    add("app/config.py")
    add("app/models/__init__.py")
    add("app/models/schemas.py")
    add("app/core/__init__.py")
    add("app/core/observability.py")
    add("app/core/events.py")
    add("app/core/policy.py")
    add("app/core/registry.py")
    add("app/core/router.py")
    add("app/core/tools.py")
    add("app/core/mcp_manager.py")
    add("app/core/runtime.py")
    add("app/core/task_engine.py")
    add("app/core/senses.py")
    add("app/core/orchestrator.py")
    add("app/store/__init__.py")
    add("app/store/memory.py")
    add("app/api/__init__.py")
    add("app/api/v1/__init__.py")
    add("app/api/v1/health.py")
    add("app/api/v1/agents.py")
    add("app/api/v1/chat.py")
    add("app/api/v1/tasks.py")
    add("app/api/v1/senses.py")
    add("app/main.py")

    # Config / metadata.
    add("requirements.txt")
    add("pyproject.toml")
    add(".env.example")
    add("README.md")
    add("mcp_config.json")

    # Agent manifests + prompts.
    for m in sorted((root / "agents" / "manifests").glob("*.json")):
        add(f"agents/manifests/{m.name}")
    for m in sorted((root / "agents" / "prompts").glob("*.txt")):
        add(f"agents/prompts/{m.name}")

    # Frontend.
    add("apps/web/package.json")
    add("apps/web/next.config.mjs")
    add("apps/web/tsconfig.json")
    add("apps/web/next-env.d.ts")
    add("apps/web/lib/types.ts")
    add("apps/web/lib/api.ts")
    add("apps/web/lib/senses.ts")
    add("apps/web/app/layout.tsx")
    add("apps/web/app/globals.css")
    add("apps/web/app/components/SensesPanel.tsx")
    add("apps/web/app/page.tsx")

    # Tests.
    for t in sorted((root / "tests").glob("test_*.py")):
        add(f"tests/{t.name}")

    # Scripts.
    add("scripts/wire_agency.py")
    add("scripts/verify_llms.py")
    add("scripts/generate_build_log.py")

    return order


def build() -> str:
    lines = [HEADER]
    for rel, path in collect_files(ROOT):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            text = f"(unable to read: {exc})"
        lines.append(render_code_block(rel, text))
    lines.append(FOOTER)
    return "\n".join(lines)


def main() -> None:
    out = ROOT / "BUILD_LOG.txt"
    out.write_text(build(), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
