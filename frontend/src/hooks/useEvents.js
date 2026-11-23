import { useEffect, useRef } from "react";
import { wsUrl } from "../api/client";

// Subscribes to /ws/events (incident changes and fall alerts) with automatic
// reconnect. `handler` is read through a ref, so changing it never reconnects.
export default function useEvents(handler) {
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    let disposed = false, sock = null, timer = null, delay = 1000;
    const open = () => {
      if (disposed) return;
      sock = new WebSocket(wsUrl("/ws/events"));
      sock.onopen = () => { delay = 1000; };
      sock.onmessage = (ev) => {
        try {
          const m = JSON.parse(ev.data);
          if (m.type !== "ping") ref.current?.(m);
        } catch { /* ignore a malformed message */ }
      };
      sock.onclose = (ev) => {
        if (disposed || ev.code === 4401) return;
        timer = setTimeout(open, delay);
        delay = Math.min(delay * 2, 30000);
      };
    };
    open();
    return () => { disposed = true; clearTimeout(timer); sock?.close(); };
  }, []);
}

// A short two-tone beep for a new confirmed fall (Web Audio; no asset needed).
let audio = null;
export function beep() {
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const t = audio.currentTime;
    [880, 660, 880].forEach((f, i) => {
      const o = audio.createOscillator(), g = audio.createGain();
      o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t + i * 0.22);
      g.gain.exponentialRampToValueAtTime(0.25, t + i * 0.22 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.22 + 0.2);
      o.connect(g).connect(audio.destination);
      o.start(t + i * 0.22);
      o.stop(t + i * 0.22 + 0.22);
    });
  } catch { /* autoplay blocked until the user interacts: fine */ }
}
