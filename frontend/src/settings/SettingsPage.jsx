import { useEffect, useState } from "react";
import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Tabs from "../components/Tabs";
import ToggleSwitch from "../components/ToggleSwitch";

// Field specs: key, label, help text, unit. Defaults and limits live in the backend
// (settings_store.py); the server validates every value and returns a clear error.
const DETECTION = [
  { title: "Fall confirmation", fields: [
    { k: "confirm_seconds", label: "Fall confirmation duration", unit: "s", help: "How long a person must stay down and still before a possible fall becomes a confirmed one. Longer = fewer false alarms, slower alert." },
    { k: "partial_confirm_factor", label: "Extra wait when partly visible", unit: "×", help: "Multiplies the confirmation time when the person is partly hidden or at the frame edge." },
    { k: "max_motion_rate", label: "Stillness limit", unit: "heights/s", help: "Movement faster than this counts as 'not still' (walking, exercising), which delays confirmation." },
    { k: "dismiss_seconds", label: "Dismiss when back on feet after", unit: "s", help: "A possible fall is dropped if the person is upright again for this long." },
    { k: "possible_timeout", label: "Give up on a possible fall after", unit: "s", help: "A possible fall that never settles (the person keeps moving) is dismissed after this long." },
  ] },
  { title: "Recovery and resolution", fields: [
    { k: "recovery_seconds", label: "Upright time to count as recovered", unit: "s", help: "After a confirmed fall, how long the person must be up before the incident shows as recovered." },
    { k: "auto_resolve_seconds", label: "Auto-resolve a recovered incident after", unit: "s", help: "Recovered incidents close themselves after this time if nobody resolves them." },
    { k: "rearm_seconds", label: "Re-arm after resolution", unit: "s", help: "How long upright before the same person can raise a new alert." },
  ] },
  { title: "Detection thresholds (advanced)", advanced: true, fields: [
    { k: "min_drop", label: "Minimum drop", unit: "heights", help: "How far the hips must fall, as a fraction of the person's standing height." },
    { k: "min_velocity", label: "Minimum fall speed", unit: "heights/s", help: "How quickly the hips must fall. Slow, deliberate lowering (lying down on purpose) stays below this." },
    { k: "min_top_drop", label: "Minimum head drop (alternative signal)", unit: "heights", help: "How far the top of the person must fall. Catches falls from a chair or towards the camera, where the hips barely move in the image." },
    { k: "min_top_velocity", label: "Minimum head fall speed", unit: "heights/s", help: "" },
    { k: "floor_lie_seconds", label: "Person on the floor (no fall seen)", unit: "s", help: "Raise a possible fall when someone is lying still on the floor for this long even though the fall itself was not seen (slow lie-down, or the camera lost them). 0 turns this off, so only rapid falls count." },
    { k: "descent_window", label: "Descent window", unit: "s", help: "Time span over which the drop is measured." },
    { k: "min_angle_swing", label: "Torso rotation (alternative signal)", unit: "°", help: "Fast rotation of the body towards horizontal, combined with part of the minimum drop." },
    { k: "min_angle_rate", label: "Torso rotation speed", unit: "°/s", help: "" },
    { k: "lying_torso_angle", label: "Lying: torso angle at least", unit: "°", help: "Angle from vertical at which the torso counts as horizontal." },
    { k: "lying_aspect", label: "Lying: box width/height at least", unit: "", help: "" },
    { k: "lying_aspect_override", label: "Lying: box this wide always counts", unit: "", help: "A box at least this much wider than tall counts as lying even if the torso angle disagrees (falls seen from the front or back flatten the angle). 0 turns this off." },
    { k: "floor_lie_min_fraction", label: "Person on the floor: share of the time lying", unit: "0-1", help: "How much of the waiting period must be classed as lying, so a single flickering frame does not restart the wait. 1 = every frame." },
    { k: "lying_extent_ratio", label: "Lying: body height at most", unit: "of standing", help: "A collapsed body is much shorter than a standing one." },
    { k: "recovery_torso_angle", label: "Upright: torso angle at most", unit: "°", help: "" },
    { k: "recovery_extent_ratio", label: "Upright: body height at least", unit: "of standing", help: "" },
    { k: "upright_lookback", label: "Must have been upright within", unit: "s", help: "A person first seen on the floor is not reported as a fall." },
    { k: "kpt_conf", label: "Keypoint confidence", unit: "", help: "Body points below this confidence are ignored." },
    { k: "min_person_conf", label: "Person confidence", unit: "", help: "People detected below this confidence are ignored." },
    { k: "orphan_timeout", label: "Keep a lost person's incident for", unit: "s", help: "If a person on the floor stops being detected, their incident is closed as 'no longer visible' after this long." },
  ] },
];

const ALERTS = [
  { k: "enabled", label: "Raise alerts for confirmed falls", type: "bool", help: "Off = falls are still recorded, but no pop-up, sound or webhook." },
  { k: "min_confidence", label: "Minimum confidence to alert", type: "num", unit: "0–1", help: "Confirmed falls below this are stored but do not raise an alert." },
  { k: "sound", label: "Play a sound in the dashboard", type: "bool", help: "Browsers only play sound after you have clicked somewhere on the page." },
  { k: "save_snapshot", label: "Save a snapshot of each fall", type: "bool" },
  { k: "save_clip", label: "Save a video clip of each fall", type: "bool", help: "Needs the camera to be running; a few seconds before and after the fall." },
  { k: "webhook_url", label: "Webhook URL", type: "text", help: "A JSON message is POSTed here when a fall is confirmed (for example to a chat or paging tool). Leave empty to turn off." },
];

const PROCESSING = [
  { k: "detect_fps", label: "Analysis rate per camera", type: "num", unit: "frames/s", help: "How often each camera is analysed. Higher = faster reaction but more CPU/GPU. Frames are skipped automatically when the server is busy." },
  { k: "imgsz", label: "Detector input size", type: "num", unit: "px", help: "Smaller is faster but may miss people who are far away." },
  { k: "conf", label: "Detector confidence", type: "num", unit: "0–1", help: "Minimum confidence for the person detector." },
];

function NumberField({ spec, value, onChange }) {
  return (
    <div>
      <label className="label" htmlFor={spec.k}>{spec.label}</label>
      <div className="flex items-center gap-2">
        <input id={spec.k} type="number" step="any" className="input-field" value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
        {spec.unit && <span className="text-xs text-slate-500 whitespace-nowrap">{spec.unit}</span>}
      </div>
      {spec.help && <p className="hint">{spec.help}</p>}
    </div>
  );
}

export default function SettingsPage() {
  const [tab, setTab] = useState("Detection");
  const [s, setS] = useState(null);
  const [draft, setDraft] = useState({});
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.settings().then(setS).catch((e) => setMsg({ err: e.message })); }, []);
  const group = tab.toLowerCase();
  const val = (k) => (draft[group]?.[k] !== undefined ? draft[group][k] : s?.[group]?.[k]);
  const edit = (k, v) => { setMsg(null); setDraft((d) => ({ ...d, [group]: { ...d[group], [k]: v } })); };
  const dirty = Object.keys(draft[group] || {}).length > 0;

  // Number inputs hold text while editing; send numbers (the server validates the range).
  const bodyFor = () => Object.fromEntries(Object.entries(draft[group] || {}).map(([k, v]) =>
    [k, typeof s[group][k] === "number" && v !== "" ? Number(v) : v]));

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      const saved = await api.saveSettings(group, bodyFor());
      setS((p) => ({ ...p, [group]: saved }));
      setDraft((d) => ({ ...d, [group]: {} }));
      setMsg({ ok: "Saved. Running cameras use the new values now." });
    } catch (e) {
      setMsg({ err: e.message });
    } finally {
      setBusy(false);
    }
  }
  async function reset() {
    if (!window.confirm(`Reset all ${tab.toLowerCase()} settings to their defaults?`)) return;
    setBusy(true);
    try {
      const saved = await api.resetSettings(group);
      setS((p) => ({ ...p, [group]: saved }));
      setDraft((d) => ({ ...d, [group]: {} }));
      setMsg({ ok: "Defaults restored." });
    } catch (e) {
      setMsg({ err: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Settings" />
      <Tabs tabs={["Detection", "Alerts", "Processing"]} active={tab} onChange={(t) => { setTab(t); setMsg(null); }} />
      {!s ? <p className="text-sm text-slate-400">{msg?.err || "Loading…"}</p> : (
        <div className="space-y-5 max-w-4xl">
          {tab === "Detection" && (
            <>
              <section className="card p-5">
                <h3 className="font-semibold text-ink-900 mb-3">Detection sensitivity</h3>
                <div className="grid grid-cols-3 gap-3" role="radiogroup" aria-label="Sensitivity">
                  {[["low", "Low", "Fewer alerts. Only clear, fast falls."], ["medium", "Medium", "Balanced (recommended start)."], ["high", "High", "Catches more falls, more false alarms."]].map(([v, t, d]) => (
                    <button key={v} type="button" role="radio" aria-checked={val("sensitivity") === v} onClick={() => edit("sensitivity", v)}
                      className={`text-left rounded-xl border p-4 transition-colors ${val("sensitivity") === v ? "border-brand-500 bg-brand-50" : "border-[#e7e8f0] hover:bg-slate-50"}`}>
                      <p className="font-medium text-ink-900">{t}</p><p className="text-xs text-slate-500 mt-1">{d}</p>
                    </button>
                  ))}
                </div>
                <p className="hint mt-3">Sensitivity scales the fall-speed, drop and rotation thresholds below. Individual cameras can override it on the Cameras page.</p>
              </section>
              {DETECTION.map((sec) => (
                <details key={sec.title} open={!sec.advanced} className="card p-5">
                  <summary className="font-semibold text-ink-900 cursor-pointer">{sec.title}</summary>
                  <div className="grid md:grid-cols-2 gap-x-6 gap-y-4 mt-4">
                    {sec.fields.map((f) => <NumberField key={f.k} spec={f} value={val(f.k)} onChange={(v) => edit(f.k, v)} />)}
                  </div>
                </details>
              ))}
              <section className="card p-5 flex items-center justify-between">
                <div><p className="font-medium text-ink-900">Fall detection engine</p><p className="hint">Master switch for all cameras.</p></div>
                <ToggleSwitch checked={!!val("enabled")} onChange={(v) => edit("enabled", v)} />
              </section>
            </>
          )}

          {(tab === "Alerts" || tab === "Processing") && (
            <section className="card p-5 space-y-5">
              {(tab === "Alerts" ? ALERTS : PROCESSING).map((f) => f.type === "bool" ? (
                <label key={f.k} className="flex items-start justify-between gap-6">
                  <span><span className="label !mb-0">{f.label}</span>{f.help && <span className="hint block">{f.help}</span>}</span>
                  <ToggleSwitch checked={!!val(f.k)} onChange={(v) => edit(f.k, v)} />
                </label>
              ) : f.type === "text" ? (
                <div key={f.k}><label className="label" htmlFor={f.k}>{f.label}</label>
                  <input id={f.k} className="input-field" placeholder="https://…" value={val(f.k) ?? ""} onChange={(e) => edit(f.k, e.target.value)} />
                  {f.help && <p className="hint">{f.help}</p>}</div>
              ) : <NumberField key={f.k} spec={f} value={val(f.k)} onChange={(v) => edit(f.k, v)} />)}
              {tab === "Processing" && <p className="hint">The pose model and the compute device (CPU/GPU) are chosen when the server starts (POSE_MODEL and POSE_DEVICE in backend/.env).</p>}
            </section>
          )}

          <div className="flex items-center gap-3">
            <button className="btn-primary" disabled={!dirty || busy} onClick={save}>{busy ? "Saving…" : "Save changes"}</button>
            <button className="btn-secondary" disabled={busy} onClick={reset}>Reset to defaults</button>
            {msg?.ok && <span className="text-sm text-success-600" role="status">{msg.ok}</span>}
            {msg?.err && <span className="text-sm text-danger-500" role="alert">{msg.err}</span>}
          </div>
        </div>
      )}
    </>
  );
}
