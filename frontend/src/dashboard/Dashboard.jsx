import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import KpiPanel from "../components/KpiPanel";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import IncidentDrawer from "../components/IncidentDrawer";
import { IncidentBadge } from "../components/Badges";
import useEvents from "../hooks/useEvents";
import { setVisibleInterval, clearVisibleInterval } from "../lib/visibleInterval";
import { EVENT_LABEL, fmtShort, pct, timeAgo } from "../lib/fall";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [params, setParams] = useSearchParams();
  const openId = params.get("incident");

  const load = useCallback(() => api.dashboard().then((d) => { setData(d); setError(""); }).catch((e) => setError(e.message)), []);

  useEffect(() => {
    load();
    const h = setVisibleInterval(load, 10000);
    return () => clearVisibleInterval(h);
  }, [load]);
  useEvents(useCallback((m) => { if (m.type === "incident" || m.type === "alert" || m.type === "clip") load(); }, [load]));

  const s = data?.summary;
  const v = (n) => (s ? String(n) : null);
  const cams = data?.cameras;
  const offline = cams ? (cams.by_connection.offline || 0) + (cams.by_connection.connecting || 0) : 0;

  return (
    <>
      <PageHeader title="Dashboard" />
      {error && <p className="text-sm text-danger-500 mb-3">{error}</p>}

      {s && s.unacknowledged > 0 && (
        <div className="mb-5 rounded-xl border border-danger-500 bg-danger-50 px-4 py-3 flex items-center gap-3 alert-pulse" role="alert">
          <AlertTriangle className="text-danger-500" size={20} />
          <p className="text-sm text-danger-600 font-medium">{s.unacknowledged} confirmed fall{s.unacknowledged > 1 ? "s" : ""} waiting to be acknowledged.</p>
        </div>
      )}

      <KpiPanel icon={ShieldCheck} title="Fall incidents"
        items={[
          { label: "Total fall incidents", value: v(s?.total), sub: s ? `${s.today} today` : null },
          { label: "Active fall alerts", value: v(s?.active), tone: "warn", sub: "Confirmed, not yet resolved" },
          { label: "Resolved incidents", value: v(s?.resolved) },
          { label: "Possible falls under review", value: v(s?.possible), sub: s ? `${s.dismissed} dismissed as not a fall` : null },
        ]}
        note={cams ? `${cams.detecting} of ${cams.total} camera${cams.total === 1 ? "" : "s"} running fall detection${offline ? ` · ${offline} not connected` : ""}` : null} />

      <div className="grid lg:grid-cols-2 gap-5">
        <section>
          <h3 className="font-semibold text-ink-900 mb-3">Active alerts</h3>
          <DataTable emptyLabel="No active fall alerts" rows={data?.active_incidents || []} onRowClick={(r) => setParams({ incident: r.id })}
            columns={[
              { key: "camera_name", label: "Camera", render: (r) => r.camera_name || `Camera ${r.camera_id}` },
              { key: "confirmed_at", label: "Confirmed", render: (r) => <span title={fmtShort(r.confirmed_at)}>{timeAgo(r.confirmed_at)}</span> },
              { key: "confidence", label: "Confidence", render: (r) => pct(r.confidence) },
              { key: "state", label: "Status", render: (r) => <IncidentBadge state={r.state} /> },
            ]} />
        </section>
        <section>
          <h3 className="font-semibold text-ink-900 mb-3">Recent fall detection activity</h3>
          <DataTable emptyLabel="No detection activity yet" rows={data?.recent_activity || []} onRowClick={(r) => setParams({ incident: r.incident_id })}
            columns={[
              { key: "ts", label: "When", render: (r) => <span title={fmtShort(r.ts)}>{timeAgo(r.ts)}</span> },
              { key: "camera_name", label: "Camera", render: (r) => r.camera_name || `Camera ${r.camera_id}` },
              { key: "kind", label: "Event", render: (r) => EVENT_LABEL[r.kind] || r.kind },
            ]} />
        </section>
      </div>

      {openId && <IncidentDrawer incidentId={Number(openId)} onClose={() => setParams({})} onChanged={load} />}
    </>
  );
}
