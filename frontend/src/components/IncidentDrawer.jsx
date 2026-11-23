import { useCallback, useEffect, useState } from "react";
import { api, fetchObjectUrl } from "../api/client";
import Modal from "./Modal";
import { IncidentBadge } from "./Badges";
import { EVENT_LABEL, fmtDuration, fmtTime, pct } from "../lib/fall";

const REASONS = ["Checked on the person: they are fine", "Assistance given", "False alarm", "Planned activity (exercise, lying down)", "Other"];

// Detail view of one incident: evidence (snapshot, clip), timeline, and the
// operator actions. Everything shown is read from the incident record.
export default function IncidentDrawer({ incidentId, onClose, onChanged }) {
  const [inc, setInc] = useState(null);
  const [error, setError] = useState("");
  const [snap, setSnap] = useState(null);
  const [clip, setClip] = useState({ url: null, msg: "" });
  const [reason, setReason] = useState(REASONS[0]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setInc(await api.incident(incidentId));
    } catch (e) {
      setError(e.message);
    }
  }, [incidentId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!inc) return undefined;
    let dead = false, s = null, c = null;
    if (inc.has_snapshot) fetchObjectUrl(`/api/incidents/${inc.id}/snapshot`).then((u) => { s = u; if (!dead) setSnap(u); }).catch(() => {});
    if (inc.has_clip) fetchObjectUrl(`/api/incidents/${inc.id}/clip`).then((u) => { c = u; if (!dead) setClip({ url: u, msg: "" }); }).catch((e) => !dead && setClip({ url: null, msg: e.message }));
    else if (inc.clip_status === "pending") setClip({ url: null, msg: "The clip is still being prepared…" });
    else if (inc.clip_status === "failed") setClip({ url: null, msg: "No video could be saved for this incident." });
    return () => { dead = true; if (s) URL.revokeObjectURL(s); if (c) URL.revokeObjectURL(c); };
  }, [inc?.id, inc?.has_snapshot, inc?.has_clip, inc?.clip_status]);

  async function act(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await load();
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const open = inc && ["confirmed", "recovered"].includes(inc.state);
  const canResolve = inc && ["possible", "confirmed", "recovered"].includes(inc.state);

  return (
    <Modal open onClose={onClose} width="max-w-3xl" title={inc ? `Incident #${inc.id} · ${inc.camera_name || `Camera ${inc.camera_id}`}` : "Incident"}>
      {error && <p className="text-sm text-danger-500 mb-3">{error}</p>}
      {!inc ? <p className="text-sm text-slate-400">Loading…</p> : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <IncidentBadge state={inc.state} />
            <span className="text-slate-500">Fall confidence <b className="text-ink-900">{pct(inc.confidence)}</b></span>
            <span className="text-slate-500">Started <b className="text-ink-900">{fmtTime(inc.started_at)}</b></span>
            {inc.confirmed_at && <span className="text-slate-500">Confirmed after <b className="text-ink-900">{fmtDuration(inc.confirmed_at - inc.started_at)}</b></span>}
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <p className="label">Snapshot</p>
              <div className="aspect-video bg-ink-900 rounded-xl overflow-hidden flex items-center justify-center">
                {snap ? <img src={snap} alt="Fall snapshot" className="w-full h-full object-contain" /> : <span className="text-xs text-white/40">No snapshot</span>}
              </div>
            </div>
            <div>
              <p className="label">Video clip</p>
              <div className="aspect-video bg-ink-900 rounded-xl overflow-hidden flex items-center justify-center">
                {clip.url ? <video src={clip.url} controls className="w-full h-full" /> : <span className="text-xs text-white/40 px-3 text-center">{clip.msg || "No clip"}</span>}
              </div>
            </div>
          </div>

          <div>
            <p className="label">Timeline</p>
            <ol className="border-l-2 border-[#e7e8f0] ml-1.5 space-y-2.5">
              {inc.events.filter((e) => !e.kind.endsWith("_ignored")).map((e, i) => (
                <li key={i} className="pl-4 relative">
                  <span className="absolute -left-[5px] top-1.5 w-2 h-2 rounded-full bg-brand-500" />
                  <p className="text-sm text-ink-900">{EVENT_LABEL[e.kind] || e.kind}
                    {e.details?.reason && !["possible", "confirmed"].includes(e.kind) ? <span className="text-slate-500"> — {e.details.reason}</span> : null}
                    {e.details?.by ? <span className="text-slate-500"> by {e.details.by}</span> : null}
                  </p>
                  <p className="text-xs text-slate-400">{fmtTime(e.ts)}{e.confidence ? ` · confidence ${pct(e.confidence)}` : ""}</p>
                </li>
              ))}
            </ol>
          </div>

          {inc.metrics && Object.keys(inc.metrics).length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-slate-500">Detection signals</summary>
              <dl className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1 mt-2 text-xs">
                {Object.entries(inc.metrics).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2"><dt className="text-slate-500">{k.replaceAll("_", " ")}</dt><dd className="text-ink-900">{String(v)}</dd></div>
                ))}
              </dl>
            </details>
          )}

          {(inc.acknowledged_by || inc.resolved_by) && (
            <p className="text-xs text-slate-500">
              {inc.acknowledged_by && <>Acknowledged by {inc.acknowledged_by} ({fmtTime(inc.acknowledged_at)}). </>}
              {inc.resolved_by && <>Resolved by {inc.resolved_by} ({fmtTime(inc.resolved_at)}){inc.resolve_reason ? `: ${inc.resolve_reason}` : ""}.</>}
            </p>
          )}

          {canResolve && (
            <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-[#eceef4]">
              {open && !inc.acknowledged_at && (
                <button className="btn-secondary" disabled={busy} onClick={() => act(() => api.acknowledge(inc.id))}>Acknowledge</button>
              )}
              <div className="min-w-[240px] flex-1">
                <label className="label" htmlFor="reason">Resolve with reason</label>
                <select id="reason" className="input-field" value={reason} onChange={(e) => setReason(e.target.value)}>
                  {REASONS.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
              <button className="btn-primary" disabled={busy} onClick={() => act(() => api.resolve(inc.id, reason))}>Resolve incident</button>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
