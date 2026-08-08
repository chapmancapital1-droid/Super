"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createSpeechRecognition,
  getSensesStatus,
  postAudioSample,
  postVisionFrame,
  speak,
  speechRecognitionAvailable,
  speechSynthesisAvailable,
  startCamera,
  startRoomAudioMeter,
} from "@/lib/senses";

type SenseTab = "voice" | "room" | "vision";

export default function SensesPanel({
  onCommand,
  onSpeakResponse,
  onLevelChange,
}: {
  onCommand: (text: string) => void;
  onSpeakResponse: (text: string) => void;
  onLevelChange?: (level: number) => void;
}) {
  const [tab, setTab] = useState<SenseTab>("voice");
  const [micOn, setMicOn] = useState(false);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [finalText, setFinalText] = useState("");
  const [level, setLevel] = useState(0);

  useEffect(() => {
    if (onLevelChange) onLevelChange(level);
  }, [level, onLevelChange]);
  const [roomInfo, setRoomInfo] = useState<string>("Not yet listening.");
  const [roomEnabled, setRoomEnabled] = useState(false);
  const [camOn, setCamOn] = useState(false);
  const [lastFrameAt, setLastFrameAt] = useState<string | null>(null);
  const [voiceSupported] = useState(speechRecognitionAvailable());
  const [ttsSupported] = useState(speechSynthesisAvailable());

  const meterRef = useRef<Awaited<ReturnType<typeof startRoomAudioMeter>> | null>(null);
  const cameraRef = useRef<Awaited<ReturnType<typeof startCamera>> | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const recRef = useRef<ReturnType<typeof createSpeechRecognition> | null>(null);
  const interimRef = useRef("");
  const transcriptRef = useRef("");

  // ---- Speech recognition (mic -> command) --------------------------------
  useEffect(() => {
    recRef.current = createSpeechRecognition({
      onTranscript: (finalText) => {
        transcriptRef.current = finalText.trim();
        setFinalText(finalText.trim());
        void postAudioSample(0.5, finalText.trim());
        // Send the spoken command straight to JARVIS.
        onCommand(finalText.trim());
      },
      onInterim: (text) => {
        interimRef.current = text;
        setInterim(text);
      },
      onEnd: () => setListening(false),
    });
    return () => {
      recRef.current?.stop();
      recRef.current = null;
    };
  }, [onCommand]);

  const toggleListen = useCallback(() => {
    const rec = recRef.current;
    if (!rec || !rec.supported) return;
    if (listening) {
      rec.stop();
      setListening(false);
    } else {
      rec.start();
      setListening(true);
      setInterim("");
    }
  }, [listening]);

  // ---- Room audio meter (hear the room) ----------------------------------
  const toggleRoom = useCallback(async () => {
    if (roomEnabled) {
      meterRef.current?.stop();
      meterRef.current = null;
      setRoomEnabled(false);
      setRoomInfo("Room listening stopped.");
      setLevel(0);
      return;
    }
    try {
      const meter = await startRoomAudioMeter((lvl) => setLevel(lvl));
      meterRef.current = meter;
      setRoomEnabled(true);
      // Post periodic samples so JARVIS' backend tracks ambient level.
      const iv = window.setInterval(() => {
        const lvl = meter.level();
        void postAudioSample(lvl, "");
      }, 2000);
      (meter as unknown as { _iv?: number })._iv = iv;
      setRoomInfo("Listening to the room…");
    } catch {
      setRoomInfo("Mic permission denied or unavailable.");
    }
  }, [roomEnabled]);

  // Poll the backend's room analysis so the UI shows what JARVIS hears.
  useEffect(() => {
    if (!roomEnabled) return;
    const iv = window.setInterval(async () => {
      try {
        const s = await getSensesStatus();
        const room = s.room;
        setRoomInfo(
          `Activity: ${room.activity} · peak ${room.peak_level} · ` +
            `speech: ${room.speech_heard ? "yes" : "no"}` +
            (room.last_transcript ? ` · heard: "${room.last_transcript}"` : "")
        );
      } catch {
        /* backend may be down */
      }
    }, 1500);
    return () => window.clearInterval(iv);
  }, [roomEnabled]);

  // ---- Camera (vision) ----------------------------------------------------
  const toggleCamera = useCallback(async () => {
    if (camOn) {
      cameraRef.current?.stop();
      cameraRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      setCamOn(false);
      return;
    }
    try {
      const cam = await startCamera();
      cameraRef.current = cam;
      if (videoRef.current) {
        videoRef.current.srcObject = cam.stream;
        await videoRef.current.play().catch(() => undefined);
      }
      setCamOn(true);
    } catch {
      setCamOn(false);
    }
  }, [camOn]);

  const capture = useCallback(() => {
    if (!cameraRef.current) return;
    const frame = cameraRef.current.captureFrame();
    if (!frame) return;
    void postVisionFrame(frame);
    setLastFrameAt(new Date().toLocaleTimeString());
  }, []);

  const preview = useCallback((text: string) => {
    speak(text);
    onSpeakResponse(text);
  }, [onSpeakResponse]);

  return (
    <div className="card">
      <h2>JARVIS Senses</h2>
      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        {(["voice", "room", "vision"] as SenseTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "6px 12px",
              border: "1px solid var(--grid)",
              borderRadius: 6,
              background: tab === t ? "var(--indigo)" : "rgba(0,0,0,0.3)",
              color: "#fff",
              cursor: "pointer",
              fontSize: 12,
              boxShadow: tab === t ? "0 0 10px var(--cyan-glow)" : "none",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "voice" && (
        <div>
          <p className="deps">
            Talk to JARVIS and it will hear you, understand your intent, and
            reply out loud. Requires browser mic permission.
          </p>
          {!voiceSupported && (
            <p className="deps" style={{ color: "var(--err)" }}>
              Speech recognition unsupported in this browser (use Chrome/Edge).
            </p>
          )}
          <button
            onClick={toggleListen}
            disabled={!voiceSupported}
            className="chat-input"
            style={{ padding: "8px 14px" }}
          >
            {listening ? "🛑 Listening…" : "🎤 Speak to JARVIS"}
          </button>
          {interim && (
            <div className="meta mono" style={{ marginTop: 8 }}>
              {interim}
            </div>
          )}
          {finalText && (
            <div className="msg jarvis" style={{ marginTop: 8 }}>
              You: {finalText}
            </div>
          )}
          {ttsSupported && (
            <div style={{ marginTop: 12 }}>
              <button onClick={() => preview("JARVIS online. Awaiting your command.")} className="chat-input" style={{ padding: "8px 14px" }}>
                🔊 Test voice reply
              </button>
            </div>
          )}
        </div>
      )}

      {tab === "room" && (
        <div>
          <p className="deps">
            JARVIS listens to the room: ambient loudness and any speech heard.
          </p>
          <button onClick={toggleRoom} className="chat-input" style={{ padding: "8px 14px" }}>
            {roomEnabled ? "⏹ Stop hearing room" : "👂 Hear the room"}
          </button>
          <div style={{ marginTop: 10 }}>
            <div
              className="meta mono"
              style={{
                height: 12,
                background: "rgba(255,255,255,0.05)",
                borderRadius: 6,
                overflow: "hidden",
                border: "1px solid var(--indigo)",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.min(100, Math.round(level * 200))}%`,
                  background: "var(--cyan)",
                  boxShadow: "0 0 10px var(--cyan)",
                  transition: "width 120ms",
                }}
              />
            </div>
            <div className="meta">Level: {level.toFixed(3)}</div>
          </div>
          <div className="meta" style={{ marginTop: 8 }}>{roomInfo}</div>
        </div>
      )}

      {tab === "vision" && (
        <div>
          <p className="deps">
            Let JARVIS see you at your computer. Requires camera permission.
          </p>
          <button onClick={toggleCamera} className="chat-input" style={{ padding: "8px 14px" }}>
            {camOn ? "⏹ Stop camera" : "📷 Turn on camera"}
          </button>
          <div style={{ marginTop: 10 }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: "100%",
                borderRadius: 8,
                border: "1px solid var(--grid)",
                background: "#111",
                minHeight: 120,
                display: camOn ? "block" : "none",
              }}
            />
            {camOn && (
              <button
                onClick={capture}
                className="chat-input"
                style={{ padding: "8px 14px", marginTop: 8 }}
              >
                📸 Send frame to JARVIS
              </button>
            )}
            {lastFrameAt && (
              <div className="meta mono" style={{ marginTop: 6 }}>
                Last frame captured: {lastFrameAt}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
