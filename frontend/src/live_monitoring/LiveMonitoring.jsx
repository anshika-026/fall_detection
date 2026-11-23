import { useCallback, useEffect, useMemo, useState } from "react";
import { LayoutGrid } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Modal from "../components/Modal";
import ToggleSwitch from "../components/ToggleSwitch";
import useLiveFeed from "../hooks/useLiveFeed";
import { ConnectionBadge } from "../components/Badges";
import CameraTile from "./CameraTile";
import { setVisibleInterval, clearVisibleInterval } from "../lib/visibleInterval";
import { Link } from "react-router-dom";

const COLS = { 1: "grid-cols-1", 2: "grid-cols-1 md:grid-cols-2", 3: "grid-cols-1 md:grid-cols-2 xl:grid-cols-3", 4: "grid-cols-2 xl:grid-cols-4" };
const MAX_LIVE_TILES = 12;   // each tile holds two websockets and a decoded stream: cap what one browser tab does

function Viewer({ camera, skeleton, onClose }) {
  const { canvasRef, live, info } = useLiveFeed(camera, { skeleton });
  return (
    <Modal open onClose={onClose} width="max-w-5xl" title={`${camera.name}${camera.site ? ` · ${camera.site}` : ""}`}>
      {/* The picture is as wide as the popup allows, but never taller than the screen: its height is capped at the
          viewport height minus ~200 px (popup padding + title + caption), so the whole camera fits without scrolling. */}
      <div className="aspect-video bg-ink-900 rounded-xl overflow-hidden relative flex items-center justify-center mx-auto"
        style={{ width: "min(100%, calc((100vh - 200px) * 16 / 9))" }}>
        <canvas ref={canvasRef} className="w-full h-full object-contain" />
        {!live && <p className="absolute text-white/50 text-sm">Waiting for video…</p>}
      </div>
      <p className="text-xs text-slate-500 mt-3">
        {info.detecting ? `${info.people} ${info.people === 1 ? "person" : "people"} in view${info.inferenceMs ? ` · ${info.inferenceMs} ms per analysed frame` : ""}` : "Fall detection is not running on this camera."}
      </p>
    </Modal>
  );
}

export default function LiveMonitoring() {
  const [cameras, setCameras] = useState(null);
  const [error, setError] = useState("");
  const [cols, setCols] = useState(() => Number(localStorage.getItem("falldet_cols")) || 3);
  const [skeleton, setSkeleton] = useState(true);
  const [onlyAlerts, setOnlyAlerts] = useState(false);
  const [open, setOpen] = useState(null);

  const load = useCallback(() => api.cameras().then((c) => { setCameras(c); setError(""); }).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
    const h = setVisibleInterval(load, 5000);
    return () => clearVisibleInterval(h);
  }, [load]);

  const shown = useMemo(() => {
    const list = (cameras || []).filter((c) => c.is_configured);
    const rank = (c) => ({ CONFIRMED: 0, POSSIBLE: 1 }[c.runtime?.worst_state] ?? 2);
    const sorted = [...list].sort((a, b) => rank(a) - rank(b) || a.id - b.id);
    return onlyAlerts ? sorted.filter((c) => rank(c) < 2) : sorted;
  }, [cameras, onlyAlerts]);

  const counts = useMemo(() => {
    const l = cameras || [];
    return {
      alarms: l.filter((c) => c.runtime?.worst_state === "CONFIRMED").length,
      possible: l.filter((c) => c.runtime?.worst_state === "POSSIBLE").length,
      online: l.filter((c) => c.connection === "online").length,
    };
  }, [cameras]);

  const setLayout = (n) => { setCols(n); localStorage.setItem("falldet_cols", String(n)); };
  const live = shown.filter((c) => c.live).slice(0, MAX_LIVE_TILES);
  const overflow = shown.filter((c) => c.live).length - live.length;
  const idle = shown.filter((c) => !c.live);

  return (
    <>
      <PageHeader title="Live Monitoring" action={
        <div className="flex items-center gap-4 text-sm">
          <label className="flex items-center gap-2 text-slate-600"><ToggleSwitch checked={skeleton} onChange={setSkeleton} /> Skeleton</label>
          <label className="flex items-center gap-2 text-slate-600"><ToggleSwitch checked={onlyAlerts} onChange={setOnlyAlerts} /> Alerts only</label>
          <div className="flex items-center gap-1 border border-[#d9dae6] rounded-lg p-0.5 bg-white" role="group" aria-label="Grid size">
            <LayoutGrid size={14} className="mx-1.5 text-slate-400" />
            {[1, 2, 3, 4].map((n) => (
              <button key={n} onClick={() => setLayout(n)} aria-pressed={cols === n}
                className={`px-2 py-1 rounded-md text-xs font-medium ${cols === n ? "bg-brand-500 text-white" : "text-slate-500 hover:bg-slate-100"}`}>{n}</button>
            ))}
          </div>
        </div>} />
      {error && <p className="text-sm text-danger-500 mb-3">{error}</p>}

      <div className="flex flex-wrap gap-2 mb-4 text-sm">
        <span className="badge badge-neutral">{counts.online} online</span>
        <span className={`badge ${counts.alarms ? "badge-danger" : "badge-neutral"}`}>{counts.alarms} confirmed fall{counts.alarms === 1 ? "" : "s"}</span>
        <span className={`badge ${counts.possible ? "badge-warning" : "badge-neutral"}`}>{counts.possible} possible</span>
      </div>

      {cameras && cameras.length === 0 && (
        <div className="card p-10 text-center text-sm text-slate-500">No cameras yet. <Link to="/cameras" className="text-brand-600 font-medium">Add a camera</Link> to start monitoring.</div>
      )}
      {cameras && cameras.length > 0 && shown.length === 0 && <div className="card p-10 text-center text-sm text-slate-500">{onlyAlerts ? "No camera has a possible or confirmed fall right now." : "No configured cameras."}</div>}

      <div className={`grid gap-4 ${COLS[cols]}`}>
        {live.map((c) => <CameraTile key={c.id} camera={c} width={cols >= 3 ? 640 : 960} skeleton={skeleton} onOpen={() => setOpen(c.id)} />)}
      </div>
      {overflow > 0 && <p className="text-xs text-slate-500 mt-3">Showing {MAX_LIVE_TILES} live views; {overflow} more camera{overflow > 1 ? "s are" : " is"} still being analysed in the background. Use "Alerts only" to focus.</p>}

      {idle.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-ink-900 mb-2">Not streaming</h3>
          <div className="card divide-y divide-[#f1f2f7]">
            {idle.map((c) => (
              <div key={c.id} className="px-4 py-3 flex items-center justify-between text-sm">
                <span className="text-ink-900">{c.name} <span className="text-slate-400">{c.site}</span></span>
                <ConnectionBadge value={c.connection} />
              </div>
            ))}
          </div>
        </div>
      )}

      {open && cameras?.find((c) => c.id === open) && <Viewer camera={cameras.find((c) => c.id === open)} skeleton={skeleton} onClose={() => setOpen(null)} />}
    </>
  );
}
