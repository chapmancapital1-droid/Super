"""
Central configuration for JARVIS (Phase 1).

Reads from environment variables with sensible defaults so the service can
run locally with no external dependencies (the "echo" model provider lets
you exercise the full orchestration pipeline without an API key).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Application settings, sourced from environment variables."""

    # --- General ---
    app_name: str = "JARVIS"
    app_version: str = "0.1.0"
    debug: bool = os.getenv("JARVIS_DEBUG", "1") == "1"

    # --- Model router ---
    # Default provider is "echo" (no key needed). Set JARVIS_MODEL_PROVIDER
    # to "openai" and JARVIS_OPENAI_API_KEY to use a real OpenAI-compatible API.
    # Wired to LM Studio by default as requested.
    model_provider: str = os.getenv("JARVIS_MODEL_PROVIDER", "openai")
    openai_api_key: str = os.getenv("JARVIS_OPENAI_API_KEY", "lm-studio")
    openai_base_url: str = os.getenv(
        "JARVIS_OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"
    )
    model_fast: str = os.getenv("JARVIS_MODEL_FAST", "gpt-4o-mini")
    model_reasoning: str = os.getenv("JARVIS_MODEL_REASONING", "gpt-4o")
    model_code: str = os.getenv("JARVIS_MODEL_CODE", "gpt-4o-mini")

    # --- Directories ---
    manifests_dir: Path = Path(os.getenv(
        "JARVIS_MANIFESTS_DIR", str(BASE_DIR / "agents" / "manifests")))
    prompts_dir: Path = Path(os.getenv(
        "JARVIS_PROMPTS_DIR", str(BASE_DIR / "agents" / "prompts")))

    # --- Store ---
    # "memory" = in-process store (default). Later phases: postgres.
    store_backend: str = os.getenv("JARVIS_STORE_BACKEND", "memory")

    # --- Policy ---
    # Actions in these permission classes always require human approval.
    always_approve: tuple = (
        "EXTERNAL_ACTION",
        "FINANCIAL",
        "DESTRUCTIVE",
        "ADMIN",
    )

    @property
    def trace_enabled(self) -> bool:
        return True


settings = Settings()
