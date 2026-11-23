import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../api/client";
import { STATE_COLOR, STATE_LABEL } from "../lib/fall";

// COCO-17 limb pairs for the optional skeleton overlay.
const SKELETON = [[5, 6], [5, 7], [7, 9], [6, 8], [8, 10], [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [0, 1], [0, 2], [1, 3], [2, 4]];

// Adapted from SMC's useLiveCameraFeed: same two-socket design (JPEG frames +
// detection JSON), same reconnect-with-backoff, same "live means frames are really
// arriving" rule. Differences: boxes are coloured by FALL STATE and labelled with
// the state, an optional skeleton is drawn, and the detection payload also reports
// whether detection is running and how long inference takes.
const KP_MIN = 0.3;   // a joint is drawn above this confidence (drawing only: it does not change what the fall engine decides)

function drawPerson(ctx, p, k, skeleton) {
  const color = STATE_COLOR[p.state] || STATE_COLOR.NORMAL;
  const [x1, y1, x2, y2] = p.bbox;
  const alert = p.state === "CONFIRMED" || p.state === "POSSIBLE";

  if (skeleton && p.keypoints) {
    ctx.lineWidth = 2 * k;
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.9;
    for (const [a, b] of SKELETON) {
      const A = p.keypoints[a], B = p.keypoints[b];
      if (A && B && A[2] > KP_MIN && B[2] > KP_MIN) {
        ctx.beginPath();
        ctx.moveTo(A[0], A[1]);
        ctx.lineTo(B[0], B[1]);
        ctx.stroke();
      }
    }
    ctx.fillStyle = "#fff";
    for (const kp of p.keypoints) {
      if (kp[2] > KP_MIN) {
        ctx.beginPath();
        ctx.arc(kp[0], kp[1], 2.5 * k, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  }

  ctx.lineWidth = (alert ? 4 : 2) * k;
  ctx.strokeStyle = color;
  ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

  const label = p.state === "NORMAL" ? "Person" : `${STATE_LABEL[p.state]}${p.fall_confidence ? ` ${Math.round(p.fall_confidence * 100)}%` : ""}`;
  ctx.font = `600 ${13 * k}px sans-serif`;
  const pad = 5 * k, h = 20 * k;
  const w = ctx.measureText(label).width + pad * 2;
  const y = y1 - h >= 0 ? y1 - h : y1;
  ctx.fillStyle = color;
  ctx.fillRect(x1, y, w, h);
  ctx.fillStyle = "#fff";
  ctx.fillText(label, x1 + pad, y + h - 6 * k);
}

export default function useLiveFeed(camera, { width, skeleton = true } = {}) {
  const canvasRef = useRef(null);
  const [status, setStatus] = useState("connecting");
  const [flowing, setFlowing] = useState(false);
  const [info, setInfo] = useState({ people: 0, worst: "NORMAL", detecting: false, inferenceMs: null, stale: false });
  const detRef = useRef({ people: [], frameW: null });
  const skeletonRef = useRef(skeleton);
  const lastFrameRef = useRef(0);
  skeletonRef.current = skeleton;

  useEffect(() => {
    if (!camera?.live) {
      setStatus(camera?.is_configured ? "disabled" : "offline");
      return;
    }
    const flowTimer = setInterval(() => setFlowing(Date.now() - lastFrameRef.current < 3000), 1000);
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const img = new Image();
    let objectUrl = null;

    // What is drawn is not the raw detection: each person glides from where they were drawn to where the newest analysis
    // says they are (analysis arrives only a few times a second, the picture many), and a person one analysis misses is kept
    // for a moment instead of vanishing. Both remove the "skeleton jumps / lags / blinks out" look.
    const shown = new Map();      // key -> person as currently drawn
    let lastTick = performance.now();
    const TAU = 0.09;             // seconds to cover ~63% of the distance to the newest position
    const KEEP_MS = 600;          // keep a person this long after the analysis stopped reporting them

    function ingest(people) {
      const now = performance.now();
      const seen = new Set();
      people.forEach((p, i) => {
        const key = p.track_id ?? `anon${i}`;
        seen.add(key);
        const cur = shown.get(key);
        shown.set(key, {
          ...p, seenAt: now,
          bbox: cur ? cur.bbox : p.bbox,                                   // drawn position starts where it was
          keypoints: p.keypoints ? p.keypoints.map((k, j) => (cur?.keypoints?.[j] ? [cur.keypoints[j][0], cur.keypoints[j][1], k[2]] : [...k])) : null,
          target: p,
        });
      });
      for (const [key, v] of shown) if (!seen.has(key) && now - v.seenAt > KEEP_MS) shown.delete(key);
    }

    function step() {
      const now = performance.now();
      const a = 1 - Math.exp(-((now - lastTick) / 1000) / TAU);
      lastTick = now;
      for (const [key, v] of shown) {
        if (now - v.seenAt > KEEP_MS) { shown.delete(key); continue; }
        const t = v.target;
        if (!t) continue;
        v.bbox = v.bbox.map((x, i) => x + (t.bbox[i] - x) * a);
        if (v.keypoints && t.keypoints) v.keypoints = v.keypoints.map((k, j) => [k[0] + (t.keypoints[j][0] - k[0]) * a, k[1] + (t.keypoints[j][1] - k[1]) * a, t.keypoints[j][2]]);
      }
    }

    function redraw() {
      if (!img.width) return;
      ctx.drawImage(img, 0, 0);
      const { frameW } = detRef.current;
      const scale = frameW ? img.width / frameW : 1;
      ctx.save();
      ctx.scale(scale, scale);
      for (const p of shown.values()) drawPerson(ctx, p, 1 / scale, skeletonRef.current);
      ctx.restore();
    }

    let raf = 0;
    function frame() {
      step();
      redraw();
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    let disposed = false;
    const timers = new Set();
    function keepConnected(url, setup, onDown) {
      let delay = 1000, current = null;
      const open = () => {
        if (disposed) return;
        const sock = new WebSocket(url);
        current = sock;
        setup(sock, () => (delay = 1000));
        sock.onclose = (ev) => {
          onDown?.();
          if (disposed || ev.code === 4401 || ev.code === 4403) return;
          const t = setTimeout(() => { timers.delete(t); open(); }, delay);
          timers.add(t);
          delay = Math.min(delay * 2, 30000);
        };
      };
      open();
      return () => current?.close();
    }

    const closeLive = keepConnected(
      wsUrl(`/ws/live/${camera.id}`, width ? `&w=${width}` : ""),
      (sock, reset) => {
        sock.binaryType = "blob";
        sock.onopen = () => { reset(); setStatus("live"); };
        sock.onerror = () => setStatus("offline");
        sock.onmessage = (ev) => {
          lastFrameRef.current = Date.now();
          setFlowing(true);
          if (objectUrl) URL.revokeObjectURL(objectUrl);
          objectUrl = URL.createObjectURL(ev.data);
          img.src = objectUrl;
        };
      },
      () => { setStatus("offline"); setFlowing(false); },
    );
    img.onload = () => {
      if (canvas.width !== img.width || canvas.height !== img.height) {
        canvas.width = img.width;
        canvas.height = img.height;
      }
      redraw();
    };

    const closeDet = keepConnected(wsUrl(`/ws/detections/${camera.id}`), (sock, reset) => {
      sock.onopen = reset;
      sock.onmessage = (ev) => {
        try {
          const d = JSON.parse(ev.data);
          const people = d.people || [];
          const stale = typeof d.updated_at === "number" && d.server_time - d.updated_at > 3;
          detRef.current = { people: stale ? [] : people, frameW: d.frame_w || null };
          ingest(stale ? [] : people);
          setInfo({ people: stale ? 0 : people.length, worst: stale ? "NORMAL" : d.worst_state, detecting: !!d.detecting, inferenceMs: d.inference_ms, stale });
        } catch { /* keep the last good overlay */ }
      };
      sock.onerror = () => {};
    });

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      timers.forEach(clearTimeout);
      closeLive();
      closeDet();
      clearInterval(flowTimer);
      setFlowing(false);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [camera?.id, camera?.live, camera?.is_configured, width]);

  const live = status === "live" && flowing;
  return { canvasRef, status, live, info };
}
