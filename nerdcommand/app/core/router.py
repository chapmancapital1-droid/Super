"""
Model router for JARVIS (Phase 1).

A provider-agnostic abstraction so models can be swapped without rewriting
agents. All providers expose a common interface:
    generate(agent, user_prompt, system_prompt, json_schema) -> dict

The router selects a provider/model based on the agent's model_policy
(fast | reasoning | code | local).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import settings
from ..models.schemas import AgentManifest
from .observability import span


class ProviderError(RuntimeError):
    pass


class BaseProvider:
    name = "base"

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class EchoProvider(BaseProvider):
    """No-key provider used for local development and testing. Emits a
    deterministic structured result so the whole pipeline can be exercised
    end-to-end without calling an external API."""

    name = "echo"

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Derive a primitive, deterministic "result" from the task so the
        # downstream orchestrator has structured output to work with.
        return {
            "summary": (
                f"[echo] Drafted plan for: {user_prompt[:120]} "
                f"(model={model}, provider=echo)"
            ),
            "claims": ["Local echo provider produced a structured draft."],
            "sources": [],
            "confidence": 0.5,
            "recommended_next_steps": [],
        }


class OpenAICompatibleProvider(BaseProvider):
    """Calls any OpenAI-compatible /chat/completions endpoint (OpenAI,
    Ollama, vLLM, LM Studio, etc.). Uses response_format=json_object when a
    JSON schema is requested so the model returns structured output."""

    name = "openai"

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import httpx  # deferred import so echo path needs no network lib

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Model call failed: {exc}") from exc

        content = resp.json()["choices"][0]["message"]["content"]
        if json_schema is not None:
            import json

            return json.loads(content)
        return {"summary": content}


class ModelRouter:
    """Selects provider + model based on the agent's model_policy."""

    def __init__(self) -> None:
        self._providers: Dict[str, BaseProvider] = {}
        self._register(EchoProvider())
        if settings.model_provider in ("openai", "auto") and settings.openai_api_key:
            self._register(
                OpenAICompatibleProvider(settings.openai_api_key,
                                         settings.openai_base_url)
            )

    def _register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider

    def provider_for(self, agent: AgentManifest) -> BaseProvider:
        if settings.model_provider in ("openai", "auto") and settings.openai_api_key:
            return self._providers["openai"]
        return self._providers["echo"]

    def model_for(self, agent: AgentManifest) -> str:
        return {
            "fast": settings.model_fast,
            "reasoning": settings.model_reasoning,
            "code": settings.model_code,
        }.get(agent.model_policy, settings.model_fast)

    def generate(
        self,
        agent: AgentManifest,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        provider = self.provider_for(agent)
        model = self.model_for(agent)
        span("model", provider=provider.name, model=model,
             policy=agent.model_policy)
        return provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            json_schema=json_schema,
        )
