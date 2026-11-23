import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import ToggleSwitch from "../components/ToggleSwitch";
import { ConnectionBadge } from "../components/Badges";
import { setVisibleInterval, clearVisibleInterval } from "../lib/visibleInterval";
import { timeAgo } from "../lib/fall";

const BLANK = { name: "", site: "", protocol: "rtsp", host: "", port: 554, user: "", password: "", stream_path: "", source_url: "", live_feed_enabled: true, fall_detection_enabled: true, sensitivity: "" };

function CameraForm({ camera, onClose, onSaved }) {
  const editing = !!camera;
  const [f, setF] = useState(editing ? { ...BLANK, ...camera, password: "", source_url: "" } : BLANK);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [test, setTest] = useState({ state: "idle", url: null, msg: "" });
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  const connection = () => (f.protocol === "rtmp"
    ? { protocol: "rtmp", source_url: f.source_url }
    : { protocol: f.protocol, host: f.host, port: Number(f.port) || (f.protocol === "rtsps" ? 322 : 554), user: f.user, password: f.password, stream_path: f.stream_path });

  async function runTest() {
    setTest({ state: "busy", url: null, msg: "" });
    try {
      const url = await api.testStream({ ...connection(), camera_id: editing ? camera.id : null });
      setTest({ state: "ok", url, msg: "" });
    } catch (e) {
      setTest({ state: "fail", url: null, msg: e.message });
    }
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { name: f.name, site: f.site, live_feed_enabled: f.live_feed_enabled, fall_detection_enabled: f.fall_detection_enabled, sensitivity: f.sensitivity, ...connection() };
      if (editing && f.protocol !== "rtmp" && !f.password) delete body.password;          // blank = keep the stored one
      if (editing && f.protocol === "rtmp" && !f.source_url) { delete body.source_url; delete body.protocol; }
      if (editing) await api.updateCamera(camera.id, body); else await api.addCamera(body);
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} width="max-w-xl" title={editing ? `Edit ${camera.name}` : "Add camera"}>
      <form onSubmit={save} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label" htmlFor="cn">Camera name</label><input id="cn" required className="input-field" value={f.name} onChange={(e) => set("name", e.target.value)} /></div>
          <div><label className="label" htmlFor="cs">Site / location</label><input id="cs" className="input-field" value={f.site} onChange={(e) => set("site", e.target.value)} /></div>
        </div>
        <div>
          <label className="label" htmlFor="cp">Stream type</label>
          <select id="cp" className="input-field" value={f.protocol} onChange={(e) => set("protocol", e.target.value)}>
            <option value="rtsp">RTSP (IP camera / NVR)</option><option value="rtsps">RTSP over TLS (rtsps, encrypted)</option><option value="rtmp">RTMP link</option>
          </select>
        </div>
        {f.protocol !== "rtmp" ? (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2"><label className="label" htmlFor="ch">IP address or host</label><input id="ch" className="input-field" placeholder="192.168.1.20" value={f.host} onChange={(e) => set("host", e.target.value)} /></div>
              <div><label className="label" htmlFor="cpo">Port</label><input id="cpo" type="number" min="1" max="65535" className="input-field" value={f.port} onChange={(e) => set("port", e.target.value)} /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="label" htmlFor="cu">Username</label><input id="cu" className="input-field" autoComplete="off" value={f.user} onChange={(e) => set("user", e.target.value)} /></div>
              <div><label className="label" htmlFor="cpw">Password</label><input id="cpw" type="password" className="input-field" autoComplete="new-password" placeholder={editing && camera.password_set ? "Unchanged" : ""} value={f.password} onChange={(e) => set("password", e.target.value)} /></div>
            </div>
            <div><label className="label" htmlFor="cpa">Stream path</label><input id="cpa" className="input-field" placeholder="/h264/ch1/sub/av_stream" value={f.stream_path} onChange={(e) => set("stream_path", e.target.value)} />
              <p className="hint">A sub-stream (lower resolution) is plenty for fall detection and is much lighter on the server.</p></div>
          </>
        ) : (
          <div><label className="label" htmlFor="cr">RTMP link</label><input id="cr" className="input-field" placeholder={editing && camera.source_url_set ? camera.source_display : "rtmp://host:1935/live/stream"} value={f.source_url} onChange={(e) => set("source_url", e.target.value)} />
            {editing && camera.source_url_set && <p className="hint">Leave blank to keep the saved link.</p>}</div>
        )}
        <div className="grid grid-cols-2 gap-4 pt-1">
          <label className="flex items-center justify-between gap-3 text-sm"><span>Camera feed on<span className="hint block">Off = camera is not connected at all.</span></span>
            <ToggleSwitch checked={f.live_feed_enabled} onChange={(v) => set("live_feed_enabled", v)} /></label>
          <label className="flex items-center justify-between gap-3 text-sm"><span>Fall detection<span className="hint block">Analyse this camera for falls.</span></span>
            <ToggleSwitch checked={f.fall_detection_enabled} onChange={(v) => set("fall_detection_enabled", v)} /></label>
        </div>
        <div><label className="label" htmlFor="sens">Sensitivity for this camera</label>
          <select id="sens" className="input-field" value={f.sensitivity} onChange={(e) => set("sensitivity", e.target.value)}>
            <option value="">Use the global setting</option><option value="low">Low (fewer alerts)</option><option value="medium">Medium</option><option value="high">High (catch more, more false alarms)</option>
          </select></div>

        <div className="rounded-xl border border-[#e7e8f0] p-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-ink-900">Test connection</p>
            <button type="button" className="btn-secondary btn-sm" onClick={runTest} disabled={test.state === "busy"}>{test.state === "busy" ? "Connecting…" : "Test"}</button>
          </div>
          {test.state === "ok" && <img src={test.url} alt="Camera test frame" className="mt-3 rounded-lg w-full" />}
          {test.state === "fail" && <p className="text-sm text-danger-500 mt-2" role="alert">{test.msg}</p>}
        </div>

        {error && <p className="text-sm text-danger-500" role="alert">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Add camera"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Cameras() {
  const [cameras, setCameras] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);       // null | "new" | camera
  const [confirmDel, setConfirmDel] = useState(null);

  const load = useCallback(() => api.cameras().then((c) => { setCameras(c); setError(""); }).catch((e) => setError(e.message)), []);
  useEffect(() => {
    load();
    const h = setVisibleInterval(load, 5000);
    return () => clearVisibleInterval(h);
  }, [load]);

  async function toggleDetection(c, on) {
    try { await api.updateCamera(c.id, { fall_detection_enabled: on }); load(); } catch (e) { setError(e.message); }
  }
  async function remove() {
    try { await api.deleteCamera(confirmDel.id); setConfirmDel(null); load(); } catch (e) { setError(e.message); setConfirmDel(null); }
  }

  return (
    <>
      <PageHeader title="Camera Management" action={<button className="btn-primary flex items-center gap-1.5" onClick={() => setForm("new")}><Plus size={16} /> Add camera</button>} />
      {error && <p className="text-sm text-danger-500 mb-3" role="alert">{error}</p>}
      <DataTable rows={cameras || []} emptyLabel={cameras ? "No cameras yet. Add one to start monitoring." : "Loading…"}
        columns={[
          { key: "name", label: "Camera", render: (c) => <div><p className="font-medium text-ink-900">{c.name}</p><p className="text-xs text-slate-400">{c.site || "No site"}</p></div> },
          { key: "address", label: "Source", render: (c) => <span className="text-xs text-slate-500">{c.protocol === "rtmp" ? c.source_display : `${c.protocol}://${c.host}:${c.port}${c.stream_path || ""}`}</span> },
          { key: "connection", label: "Connection", render: (c) => (
            <div><ConnectionBadge value={c.connection} />
              {c.runtime?.stream?.detail && c.connection !== "online" && <p className="text-xs text-slate-400 mt-1 max-w-[200px] truncate" title={c.runtime.stream.detail}>{c.runtime.stream.detail}</p>}
              {c.runtime?.stream?.last_frame_at && <p className="text-xs text-slate-400 mt-1">Last frame {timeAgo(c.runtime.stream.last_frame_at)}</p>}</div>) },
          { key: "fall", label: "Fall detection", render: (c) => (
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <ToggleSwitch checked={c.fall_detection_enabled} onChange={(v) => toggleDetection(c, v)} />
              <span className="text-xs text-slate-500">{c.fall_detection_enabled ? (c.runtime?.detecting ? "Running" : "On") : "Off"}</span>
            </div>) },
          { key: "act", label: "", render: (c) => (
            <div className="flex gap-1 justify-end" onClick={(e) => e.stopPropagation()}>
              <button className="p-2 rounded-lg hover:bg-slate-100 text-slate-500" aria-label={`Edit ${c.name}`} onClick={() => setForm(c)}><Pencil size={15} /></button>
              <button className="p-2 rounded-lg hover:bg-danger-50 text-danger-500" aria-label={`Delete ${c.name}`} onClick={() => setConfirmDel(c)}><Trash2 size={15} /></button>
            </div>) },
        ]} />

      {form && <CameraForm camera={form === "new" ? null : form} onClose={() => setForm(null)} onSaved={load} />}
      <Modal open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Delete camera?">
        <p className="text-sm text-slate-600">“{confirmDel?.name}” will stop being monitored. Its past fall incidents are kept.</p>
        <div className="flex justify-end gap-2 mt-5">
          <button className="btn-secondary" onClick={() => setConfirmDel(null)}>Cancel</button>
          <button className="btn-danger" onClick={remove}>Delete</button>
        </div>
      </Modal>
    </>
  );
}
