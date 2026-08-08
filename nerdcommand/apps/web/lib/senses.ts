// Senses client: mic, room audio, speech recognition, speech synthesis, camera.
//
// The mic and camera physically live in the browser (getUserMedia). This
// module captures them, computes an ambient audio level, transcribes speech
// (Web Speech API), renders JARVIS' replies out loud (SpeechSynthesis), and
// posts captured frames + transcripts to the backend /api/v1/senses/*.

// --- Browser API types (not all in TS lib.dom) ---------------------------
type SpeechRecognitionCtor = new () => {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: { resultIndex: number; results: { length: number } & { [i: number]: { isFinal: boolean; 0: { transcript: string } } } }) => void) | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  start: () => void;
  stop: () => void;
};

declare global {
  interface Window {
    webkitSpeechRecognition?: SpeechRecognitionCtor;
    SpeechRecognition?: SpeechRecognitionCtor;
  }
}

// --- Speech recognition (speech -> text) ---------------------------------
export function speechRecognitionAvailable(): boolean {
  return typeof window !== "undefined" &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

// --- Speech synthesis (text -> speech) -----------------------------------
export function speak(text: string, onEnd?: () => void): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    onEnd?.();
    return;
  }
  // Cancel anything already playing so a new command isn't read over.
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0;
  utter.pitch = 1.0;
  // Prefer a natural English voice if one is available.
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find((v) => v.lang.startsWith("en"));
  if (preferred) utter.voice = preferred;
  if (onEnd) utter.onend = onEnd;
  window.speechSynthesis.speak(utter);
}

export function speechSynthesisAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

// --- Room audio levels via AnalyserNode -----------------------------------
export interface AudioLevelMeter {
  start: () => Promise<void>;
  stop: () => void;
  level: () => number;
}

export async function startRoomAudioMeter(
  onLevel: (level: number) => void
): Promise<AudioLevelMeter> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const ctx = new AudioContext();
  const source = ctx.createMediaStreamSource(stream);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  source.connect(analyser);
  const data = new Uint8Array(analyser.fftSize);

  let raf = 0;
  const tick = () => {
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      const v = (data[i] - 128) / 128;
      sum += v * v;
    }
    const rms = Math.sqrt(sum / data.length);
    onLevel(rms);
    raf = requestAnimationFrame(tick);
  };
  tick();

  return {
    level: () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      return Math.sqrt(sum / data.length);
    },
    start: async () => {
      await ctx.resume();
      raf = requestAnimationFrame(tick);
    },
    stop: () => {
      cancelAnimationFrame(raf);
      stream.getTracks().forEach((t) => t.stop());
      void ctx.close();
    },
  };
}

// --- Speech recognition runner ---------------------------------------------
export interface SpeechHook {
  start: () => void;
  stop: () => void;
  supported: boolean;
}

export function createSpeechRecognition(opts: {
  onTranscript: (finalText: string) => void;
  onInterim: (text: string) => void;
  onEnd: () => void;
  lang?: string;
}): SpeechHook {
  const Ctor =
    typeof window !== "undefined"
      ? window.SpeechRecognition || window.webkitSpeechRecognition
      : undefined;

  if (!Ctor) {
    return { start: () => {}, stop: () => {}, supported: false };
  }

  const rec = new Ctor();
  rec.lang = opts.lang || "en-US";
  rec.continuous = false;
  rec.interimResults = true;

  rec.onresult = (e) => {
    let interim = "";
    let final = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i];
      if (r.isFinal) final += r[0].transcript;
      else interim += r[0].transcript;
    }
    if (final) opts.onTranscript(final);
    if (interim) opts.onInterim(interim);
  };
  rec.onend = () => opts.onEnd();
  rec.onerror = () => opts.onEnd();

  return {
    start: () => {
      try {
        rec.start();
      } catch {
        /* already started */
      }
    },
    stop: () => {
      try {
        rec.stop();
      } catch {
        /* nop */
      }
    },
    supported: true,
  };
}

// --- Camera (video) ---------------------------------------------------------
export interface CameraHandle {
  stream: MediaStream;
  stop: () => void;
  captureFrame: (width?: number) => string | null;
}

export async function startCamera(): Promise<CameraHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 480 } },
    audio: false,
  });
  return {
    stream,
    stop: () => stream.getTracks().forEach((t) => t.stop()),
    captureFrame: (width = 480) => {
      const video = document.createElement("video");
      video.srcObject = stream;
      video.play();
      const canvas = document.createElement("canvas");
      canvas.width = width;
      const h = Math.round((video.videoHeight / video.videoWidth) * width);
      canvas.height = h || width;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL("image/jpeg", 0.7);
    },
  };
}

// --- Backend posting helpers ------------------------------------------------
export async function postAudioSample(
  level: number,
  transcript: string = ""
): Promise<void> {
  await fetch("/api/v1/senses/audio", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level, transcript }),
  });
}

export async function postVisionFrame(dataB64: string): Promise<void> {
  const mime = dataB64.split(";")[0].replace("data:", "");
  const b64 = dataB64.split(",")[1];
  await fetch("/api/v1/senses/vision", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mime, data_b64: b64 }),
  });
}

export async function getSensesStatus() {
  const res = await fetch("/api/v1/senses/status");
  if (!res.ok) throw new Error("senses status failed");
  return res.json();
}
