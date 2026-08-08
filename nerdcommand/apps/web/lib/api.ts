// Client for the JARVIS API. Uses relative /api URLs so the Next.js dev
// server rewrites them to the backend (see next.config.mjs).

import type {
  AgentManifest,
  ChatRequest,
  ChatResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function chat(payload: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/v1/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function health(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/v1/health");
}

export function listAgents(): Promise<AgentManifest[]> {
  return request<AgentManifest[]>("/v1/agents");
}
