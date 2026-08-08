"""
Senses engine for JARVIS (Phase 8 / vision).

Gives JARVIS the ability to "hear" the room (audio levels, speech transcripts)
and "see" the user (captured camera frames). Capture itself happens in the
browser (the mic/camera live on the user's machine); the backend ingests the
captured data, stores an auditable record, and can analyze it.

Phase 1 of Senses provides:
  - audio ingestion: a transcript + an ambient audio level sample (0.0-1.0),
    so JARVIS can listen to the room and react to loud/quiet/speech.
  - vision ingestion: a captured camera frame (base64 image) so JARVIS can
    "see" the user at their computer. A real vision model plugs in later.

Design notes:
  - No credentials are stored. Audio/frames are treated as sensitive and
    flagged accordingly.
  - Every ingestion emits a typed event on the bus for observability.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from .events import bus
from .observability import get_trace_id, span


class AudioSample:
    """A snapshot of the room's audio: a transcript (if speech) and the
    ambient level of the last capture window."""

    def __init__(
        self,
        level: float,
        transcript: str = "",
        duration_ms: int = 0,
        source: str = "mic",
    ) -> None:
        self.level = max(0.0, min(1.0, level))
        self.transcript = transcript
        self.duration_ms = duration_ms
        self.source = source
        self.timestamp = time.time()
        self.trace_id = get_trace_id()


class VisionFrame:
    """A captured camera frame for JARVIS to "see"."""

    def __init__(
        self,
        mime: str,
        data_b64: str,
        width: int = 0,
        height: int = 0,
        description: str = "",
    ) -> None:
        self.mime = mime
        self.data_b64 = data_b64
        self.width = width
        self.height = height
        self.description = description
        self.timestamp = time.time()
        self.trace_id = get_trace_id()


class SensesEngine:
    """Holds recent audio samples and vision frames and provides analysis
    stubs that a real model (audio/video understanding) can replace."""

    MAX_SAMPLES = 100
    MAX_FRAMES = 20

    def __init__(self) -> None:
        self._audio: List[AudioSample] = []
        self._frames: List[VisionFrame] = []

    # --- audio -------------------------------------------------------------
    def ingest_audio(
        self,
        level: float,
        transcript: str = "",
        duration_ms: int = 0,
        source: str = "mic",
    ) -> AudioSample:
        sample = AudioSample(level, transcript, duration_ms, source)
        self._audio.append(sample)
        if len(self._audio) > self.MAX_SAMPLES:
            self._audio = self._audio[-self.MAX_SAMPLES:]
        span("sense", sense="audio", level=level,
             speech=bool(transcript), trace_id=sample.trace_id)
        bus.emit("sense.audio", {
            "level": level, "transcript": transcript,
            "duration_ms": duration_ms, "trace_id": sample.trace_id,
        })
        return sample

    def analyze_room(self, window: int = 10) -> Dict:
        """Describe recent room audio: speech present? loud? quiet?"""
        recent = self._audio[-window:] if self._audio else []
        if not recent:
            return {"activity": "silence", "peak_level": 0.0,
                    "speech_heard": False, "last_transcript": ""}
        peak = max(s.level for s in recent)
        avg = sum(s.level for s in recent) / len(recent)
        last_speech = next(
            (s.transcript for s in reversed(recent) if s.transcript), "")
        if peak < 0.05:
            activity = "silence"
        elif peak < 0.35:
            activity = "quiet"
        elif peak < 0.7:
            activity = "active"
        else:
            activity = "loud"
        return {
            "activity": activity,
            "peak_level": round(peak, 3),
            "avg_level": round(avg, 3),
            "speech_heard": bool(last_speech),
            "last_transcript": last_speech,
        }

    # --- vision ------------------------------------------------------------
    def ingest_frame(
        self,
        mime: str,
        data_b64: str,
        width: int = 0,
        height: int = 0,
        description: str = "",
    ) -> VisionFrame:
        frame = VisionFrame(mime, data_b64, width, height, description)
        self._frames.append(frame)
        if len(self._frames) > self.MAX_FRAMES:
            self._frames = self._frames[-self.MAX_FRAMES:]
        span("sense", sense="vision", mime=mime, width=width, height=height,
             trace_id=frame.trace_id)
        bus.emit("sense.vision", {
            "mime": mime, "width": width, "height": height,
            "description": description, "trace_id": frame.trace_id,
        })
        return frame

    def last_frame(self) -> Optional[VisionFrame]:
        return self._frames[-1] if self._frames else None

    # --- summary -----------------------------------------------------------
    def status(self) -> Dict:
        room = self.analyze_room()
        return {
            "hearing_enabled": len(self._audio) > 0,
            "room": room,
            "vision_enabled": len(self._frames) > 0,
            "last_frame_at": (
                self._frames[-1].timestamp if self._frames else None),
        }


# Singleton engine for the process.
senses = SensesEngine()
