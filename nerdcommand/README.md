# NerdCommand.AI — JARVIS (Phase 1)

**Personal AI command system.** One conversational interface acts as the
command center while specialized agents perform individual jobs and return
structured work to the orchestrator.

This is the Phase-1 build described in the
`NerdCommand_AI_JARVIS_Developer_Design_v1.pdf`. It implements the working
JARVIS loop: accept a natural-language objective → build a task graph →
delegate to agents → respect approval gates → return a structured result.

> 📘 **Living build record:** every design decision and all current source is
> captured in **`BUILD_LOG.txt`** (regenerate after any change with
> `python3 scripts/generate_build_log.py`).

## What's here

| Path | Purpose |
|------|---------|
| `app/` | FastAPI backend (API v1) |
| `app/core/orchestrator.py` | Intent → plan → delegate → validate |
| `app/core/task_engine.py` | Dependency graph + readiness scheduling |
| `app/core/registry.py` | Loads agent manifests (JSON) |
| `app/core/router.py` | Model router (echo / OpenAI-compatible) |
| `app/core/runtime.py` | Agent runtime (prompt + model + envelope) |
| `app/core/policy.py` | Permission / approval enforcement |
| `app/core/tools.py` | Permissioned tool gateway (stubs) |
| `app/core/events.py` | Typed event bus with trace_id |
| `app/core/senses.py` | JARVIS' ears + eyes (audio/vision ingestion) |
| `app/api/v1/senses.py` | Voice/vision endpoints |
| `agents/manifests/` | Agent definitions (data, not code) |
| `agents/prompts/` | Per-agent system prompts |
| `apps/web/` | Next.js command-center UI |
| `skills/agency/` | **The Agency** — 270 AI specialist personas |
| `tests/` | Pytest suite |
| `BUILD_LOG.txt` | Living build document (generated) |

## The Agency (installed)

The [`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents)
roster of 270 AI specialist personas is installed under `skills/agency/` so
the dev team can consult the "superagents" directly (e.g.
`skills/agency/multi-agent-systems-architect.md`,
`skills/agency/backend-architect.md`, `skills/agency/api-platform-engineer.md`).
The Phase-1 architecture was built following those personas' guidance
(hierarchical orchestration, typed contracts, least privilege, HITL gates,
trace observability, evals).

## Run it (full stack)

### 1. Backend

```bash
cd nerdcommand
pip install -r requirements.txt
uvicorn app.main:app --reload          # echo provider, no key needed
# API docs: http://127.0.0.1:8000/docs
```

### 2. Frontend (Next.js web UI)

```bash
cd apps/web
npm install
npm run dev                             # http://127.0.0.1:3000
```

The browser uses only relative `/api/*` URLs; Next.js rewrites them to the
backend (see `next.config.mjs`), so no CORS or localhost calls in the browser.

## JARVIS Senses (voice + vision)

JARVIS can hear you, hear the room, speak back, and see you on camera:

- **🎤 Speak to JARVIS** — the web UI's "Senses" panel uses browser speech
  recognition to transcribe the mic and sends the command through the same
  chat pipeline; JARVIS replies out loud via speech synthesis.
- **👂 Hear the room** — a live audio level meter samples ambient loudness and
  posts it to `/api/v1/senses/audio`; the backend classifies the room
  (silence / quiet / active / loud) and tracks speech heard.
- **📷 See you** — the camera panel (`getUserMedia`) shows a live preview and
  "Send frame" posts a base64 frame to `/api/v1/senses/vision` for JARVIS to
  analyze (a real vision model plugs into `app/core/senses.py` later).

Capture happens in the browser because the mic/camera live on the user's
machine; the backend ingests and audits everything. Try it in the live UI —
grant mic/camera permission when prompted.

## Tests

```bash
cd nerdcommand && pytest -q            # backend suite
cd apps/web && npx tsc --noEmit        # frontend typecheck
```

## Updating the build log

The build log is generated from the actual source so it never drifts:

```bash
python3 scripts/generate_build_log.py  # rewrites BUILD_LOG.txt
```

## Architecture note

Per the design doc and the Multi-Agent Systems Architect persona: the
**system prompt guides behavior**; the **policy engine enforces boundaries**.
Natural language is never the source of truth for permissions. Phase 1 ships
a deterministic planner (`researcher → strategist → validator`); a learned
planner can replace `Orchestrator.plan()` without touching the execution
path. The store is in-memory for now; swap `SessionStore` for a
PostgreSQL-backed store in Phase 5.

