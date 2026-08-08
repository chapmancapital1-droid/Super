"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  chat,
  health,
  listAgents,
} from "@/lib/api";
import type {
  AgentManifest,
  ChatResponse,
  TaskView,
} from "@/lib/types";
import SensesPanel from "@/app/components/SensesPanel";
import JarvisCore, { JarvisMode } from "@/app/components/JarvisCore";
import { speak } from "@/lib/senses";

const EXAMPLES = [
  "Research the senior-living market around Cedar Hill and draft an investor plan",
  "Research the competitive landscape and summarize the top three opportunities",
  "What is NerdCommand.AI?",
];

function pillClass(status: string): string {
  const map: Record<string, string> = {
    complete: "complete",
    running: "running",
    queued: "queued",
    waiting: "waiting",
    failed: "failed",
    approval_required: "approval_required",
    blocked: "blocked",
  };
  return map[status] || "queued";
}

function TaskNode({ task }: { task: TaskView }) {
  const deps = task.depends_on.length
    ? `depends on ${task.depends_on.length}`
    : "no dependencies";
  return (
    <div className="node">
      <div className="head">
        <span className="agent">{task.agent_id}</span>
        <span className={`pill ${pillClass(task.status)}`}>{task.status}</span>
      </div>
      <div className="deps">{deps}</div>
      <div className="deps mono" style={{ fontSize: 11 }}>{task.id}</div>
    </div>
  );
}

export default function CommandCenter() {
  const [messages, setMessages] = useState<{ role: string; text: string }[]>(
    []
  );
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [agents, setAgents] = useState<AgentManifest[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [jarvisMode, setJarvisMode] = useState<JarvisMode>("idle");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    health()
      .then(() => !cancelled && setBackendOnline(true))
      .catch(() => !cancelled && setBackendOnline(false));
    listAgents()
      .then((a) => !cancelled && setAgents(a))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, result]);

  useEffect(() => {
    if (!result) return;
    const isRunning = result.plan.some(t => t.status === "running");
    if (isRunning) {
      const activeAgent = result.plan.find(t => t.status === "running")?.agent_id;
      if (activeAgent === "researcher") setJarvisMode("researching");
      else setJarvisMode("thinking");
    } else if (result.status === "complete" && jarvisMode !== "speaking") {
      setJarvisMode("idle");
    }
  }, [result, jarvisMode]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || busy) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    setJarvisMode("thinking");
    try {
      const resp = await chat({
        message: text,
        session_id: sessionId,
      });
      if (resp.session_id) setSessionId(resp.session_id);
      setResult(resp);
      setMessages((m) => [...m, { role: "jarvis", text: resp.summary }]);
      // Speak the reply out loud so JARVIS talks back.
      if (resp.summary) {
        setJarvisMode("speaking");
        speak(resp.summary);
        setTimeout(() => setJarvisMode("idle"), 2000); // Reset after some time
      } else {
        setJarvisMode("idle");
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setMessages((m) => [...m, { role: "jarvis", text: `Error: ${msg}` }]);
      setJarvisMode("idle");
    } finally {
      setBusy(false);
    }
  }, [input, busy, sessionId]);

  return (
    <>
      <header className="topbar">
        <div className="brand">
          NERDCOMMAND<span className="accent">.AI</span>{" "}
          <span className="badge">JARVIS</span>
        </div>
        <div className="status">
          {backendOnline === null
            ? "Contacting backend…"
            : backendOnline
            ? "● SYSTEM ONLINE"
            : "● BACKEND OFFLINE"}
        </div>
      </header>

      <main>
        <div className="grid">
          <div>
            <JarvisCore level={audioLevel} mode={jarvisMode} />

            <div className="card">
              <h2>Command</h2>
              <div className="chat-box">
                {messages.length === 0 && (
                  <div className="empty">
                    Speak to JARVIS. Example commands:
                    <ul style={{ textAlign: "left" }}>
                      {EXAMPLES.map((e) => (
                        <li key={e} style={{ fontSize: 12, margin: "4px 0" }}>
                          “{e}”
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={`msg ${m.role}`}>
                    {m.text}
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
              <div className="chat-input">
                <input
                  value={input}
                  placeholder="What should JARVIS do?"
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()}
                  disabled={busy}
                />
                <button onClick={send} disabled={busy}>
                  {busy ? "Working…" : "Send"}
                </button>
              </div>
            </div>

            {result && (
              <div className="card">
                <h2>Agent Graph</h2>
                {result.plan.map((t) => (
                  <TaskNode key={t.id} task={t} />
                ))}
                <div className="summary">
                  <b>Summary:</b>{" "}
                  {result.summary || "No structured result produced."}
                </div>
                <div className="meta mono">
                  trace: {result.trace_id} · graph: {result.graph_id} · status:{" "}
                  {result.status}
                </div>
              </div>
            )}

            {result && result.approvals.length > 0 && (
              <div className="card">
                <h2>Approval Required</h2>
                {result.approvals.map((a) => (
                  <div key={a.id} className="approval">
                    <div className="action">{a.action}</div>
                    <div className="deps">{a.description}</div>
                    <div className="meta mono">{a.id} · {a.permission_class}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <SensesPanel
              onLevelChange={(l) => setAudioLevel(l)}
              onCommand={async (text) => {
                // A spoken (or tested) command flows into the chat pipeline.
                setInput(text);
                setMessages((m) => [...m, { role: "user", text }]);
                setBusy(true);
                setJarvisMode("thinking");
                try {
                  const resp = await chat({ message: text, session_id: sessionId });
                  if (resp.session_id) setSessionId(resp.session_id);
                  setResult(resp);
                  setMessages((m) => [...m, { role: "jarvis", text: resp.summary }]);
                  if (resp.summary) {
                    setJarvisMode("speaking");
                    speak(resp.summary);
                    setTimeout(() => setJarvisMode("idle"), 3000);
                  } else {
                    setJarvisMode("idle");
                  }
                } catch (err) {
                  const msg = err instanceof Error ? err.message : String(err);
                  setMessages((m) => [...m, { role: "jarvis", text: `Error: ${msg}` }]);
                  setJarvisMode("idle");
                } finally {
                  setBusy(false);
                }
              }}
              onSpeakResponse={(text) =>
                setMessages((m) => [...m, { role: "jarvis", text }])
              }
            />
            <div className="card">
              <h2>Agents</h2>
              {agents.length === 0 ? (
                <div className="empty">No agents loaded.</div>
              ) : (
                agents.map((a) => (
                  <div key={a.id} className="node">
                    <div className="head">
                      <span className="agent">{a.display_name}</span>
                      <span className="pill queued">{a.model_policy}</span>
                    </div>
                    <div className="deps">{a.purpose}</div>
                    <div className="meta mono">
                      tools: {a.tools.join(", ") || "—"}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
