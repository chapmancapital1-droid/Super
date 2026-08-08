"use client";

import React, { useEffect, useState } from "react";

export type JarvisMode = "idle" | "thinking" | "speaking" | "researching";

export default function JarvisCore({ 
  level, 
  mode = "idle" 
}: { 
  level: number;
  mode?: JarvisMode;
}) {
  const [rotation, setRotation] = useState(0);

  useEffect(() => {
    const speed = mode === "thinking" ? 3 : mode === "researching" ? 2 : 1;
    const iv = setInterval(() => {
      setRotation((r) => (r + speed) % 360);
    }, 50);
    return () => clearInterval(iv);
  }, [mode]);

  const scale = 1 + level * 2;
  const opacity = 0.3 + level * 0.7;

  const modeColors: Record<JarvisMode, string> = {
    idle: "var(--cyan)",
    thinking: "#ff00ff", // Magenta for thinking
    speaking: "#00ff00", // Green for speaking
    researching: "#ffff00", // Yellow for researching
  };

  const currentColor = modeColors[mode];

  return (
    <div className="jarvis-core-container">
      <div className="hud-overlay" />
      <div
        className="core-inner"
        style={{
          transform: `rotateX(${rotation * 0.5}deg) rotateY(${rotation}deg) scale(${scale})`,
        }}
      >
        <div className="box-face front" style={{ borderColor: currentColor }} />
        <div className="box-face back" style={{ borderColor: currentColor }} />
        <div className="box-face left" style={{ borderColor: currentColor }} />
        <div className="box-face right" style={{ borderColor: currentColor }} />
        <div className="box-face top" style={{ borderColor: currentColor }} />
        <div className="box-face bottom" style={{ borderColor: currentColor }} />
        
        {/* Inner core pulse */}
        <div className="inner-pulse" style={{ opacity, background: currentColor, boxShadow: `0 0 30px ${currentColor}` }} />
      </div>
      
      {/* Decorative circles */}
      <div className="ring ring-1" style={{ borderColor: currentColor }} />
      <div className="ring ring-2" style={{ transform: `rotate(${rotation * -0.5}deg)`, borderColor: currentColor }} />
      <div className="ring ring-3" style={{ transform: `rotate(${rotation * 0.8}deg)`, borderColor: currentColor }} />
      
      <div className="status-label">
        <div className="glitch" data-text={mode.toUpperCase()}>{mode.toUpperCase()}</div>
        <div className="monitoring" style={{ color: currentColor }}>
          <span>MODE: {mode.toUpperCase()}</span>
          <span>GAIN: {(level * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
