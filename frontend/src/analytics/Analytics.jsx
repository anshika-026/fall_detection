import { useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import { api } from "../api/client";
import KpiPanel from "../components/KpiPanel";
import PageHeader from "../components/PageHeader";
import DataTable from "../components/DataTable";
import IncidentDrawer from "../components/IncidentDrawer";
import { IncidentBadge } from "../components/Badges";
import { fmtDuration, fmtShort, pct } from "../lib/fall";

const BRAND = "#4f5fea";
const DANGER = "#ab2710";
const RANGES = [7, 30, 90];

function Chart({ title, subtitle, empty, children }) {
  return (
    <section className="card p-5">
      <h3 className="font-semibold text-ink-900">{title}</h3>
      {subtitle && <p className="text-xs text-slate-400 mb-3">{subtitle}</p>}
      <div className="h-56 mt-2">{empty ? <div className="h-full flex items-center justify-center text-sm text-slate-400">No falls in this period</div> : children}</div>
    </section>
  );
}

const axis = { fontSize: 11, fill: "#7c7e94" };
const hourLabel = (h) => `${String(h).padStart(2, "0")}:00`;

export default function Analytics() {
  const [days, setDays] = useState(30);
  const [cameraId, setCameraId] = useState("");
  const [cameras, setCameras] = useState([]);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(null);

  const load = useCallback(() => {
    api.analytics(days, cameraId || undefined).then((d) => { setData(d); setError(""); }).catch((e) => setError(e.message));
  }, [days, cameraId]);

  useEffect(() => { api.cameras().then(setCameras).catch(() => {}); }, []);
  useEffect(() => { setData(null); load(); }, [load]);

  const none = data && data.total_falls === 0;
  const weekday = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  return (
    <>
      <PageHeader title="Analytics" action={
        <div className="flex items-center gap-3">
          <select className="input-field !w-auto" value={cameraId} onChange={(e) => setCameraId(e.target.value)} aria-label="Camera">
            <option value="">All cameras</option>
            {cameras.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <div className="flex border border-[#d9dae6] rounded-lg p-0.5 bg-white" role="group" aria-label="Period">
            {RANGES.map((r) => (
              <button key={r} onClick={() => setDays(r)} aria-pressed={days === r}
                className={`px-3 py-1.5 rounded-md text-sm font-medium ${days === r ? "bg-brand-500 text-white" : "text-slate-500 hover:bg-slate-100"}`}>{r} days</button>
            ))}
          </div>
        </div>} />
      {error && <p className="text-sm text-danger-500 mb-3">{error}</p>}

      <KpiPanel icon={BarChart3} title={`Last ${days} days`}
        items={[
          { label: "Total falls detected", value: data ? String(data.total_falls) : null },
          { label: "Average fall confidence", value: data ? pct(data.confidence.avg) : null, sub: data?.confidence.min != null ? `range ${pct(data.confidence.min)}–${pct(data.confidence.max)}` : null },
          { label: "Avg time to acknowledge", value: data ? fmtDuration(data.avg_seconds_to_acknowledge) : null },
          { label: "Dismissed possible falls", value: data ? String(data.dismissed_possible_falls) : null, sub: "Looked like a fall, were not confirmed" },
        ]}
        note="Counts are confirmed falls only; times are shown in this browser's time zone." />

      <div className="grid lg:grid-cols-2 gap-5 mb-5">
        <Chart title="Daily trend" subtitle="Confirmed falls per day" empty={none}>
          <ResponsiveContainer><LineChart data={data?.daily || []} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="#eceef4" vertical={false} />
            <XAxis dataKey="date" tick={axis} tickFormatter={(d) => d.slice(5)} minTickGap={24} />
            <YAxis allowDecimals={false} tick={axis} />
            <Tooltip /><Line type="monotone" dataKey="falls" name="Falls" stroke={BRAND} strokeWidth={2} dot={false} />
          </LineChart></ResponsiveContainer>
        </Chart>
        <Chart title="Weekly trend" subtitle="Confirmed falls per week (week starting Monday)" empty={none}>
          <ResponsiveContainer><BarChart data={data?.weekly || []} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="#eceef4" vertical={false} />
            <XAxis dataKey="week_start" tick={axis} tickFormatter={(d) => d.slice(5)} />
            <YAxis allowDecimals={false} tick={axis} />
            <Tooltip /><Bar dataKey="falls" name="Falls" fill={BRAND} radius={[4, 4, 0, 0]} />
          </BarChart></ResponsiveContainer>
        </Chart>
        <Chart title="Falls by camera" empty={none}>
          <ResponsiveContainer><BarChart data={data?.by_camera || []} layout="vertical" margin={{ left: 10, right: 16 }}>
            <CartesianGrid stroke="#eceef4" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={axis} />
            <YAxis type="category" dataKey="camera_name" tick={axis} width={110} />
            <Tooltip /><Bar dataKey="falls" name="Falls" fill={DANGER} radius={[0, 4, 4, 0]} />
          </BarChart></ResponsiveContainer>
        </Chart>
        <Chart title="Time of day" subtitle="When falls happen (hour of day)" empty={none}>
          <ResponsiveContainer><BarChart data={data?.by_hour || []} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="#eceef4" vertical={false} />
            <XAxis dataKey="hour" tick={axis} tickFormatter={(h) => (h % 3 === 0 ? hourLabel(h) : "")} interval={0} />
            <YAxis allowDecimals={false} tick={axis} />
            <Tooltip labelFormatter={hourLabel} /><Bar dataKey="falls" name="Falls" fill={BRAND} radius={[3, 3, 0, 0]} />
          </BarChart></ResponsiveContainer>
        </Chart>
        <Chart title="Detection confidence" subtitle="How sure the detector was about each confirmed fall" empty={none}>
          <ResponsiveContainer><BarChart data={data?.confidence.distribution || []} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="#eceef4" vertical={false} />
            <XAxis dataKey="bucket" tick={axis} />
            <YAxis allowDecimals={false} tick={axis} />
            <Tooltip /><Bar dataKey="falls" name="Falls" radius={[4, 4, 0, 0]}>
              {(data?.confidence.distribution || []).map((b) => <Cell key={b.bucket} fill={b.bucket === "<0.5" ? "#e0a319" : BRAND} />)}
            </Bar>
          </BarChart></ResponsiveContainer>
        </Chart>
        <Chart title="Day of week" empty={none}>
          <ResponsiveContainer><BarChart data={(data?.by_weekday || []).map((d) => ({ ...d, name: weekday[d.weekday] }))} margin={{ left: -20, right: 8 }}>
            <CartesianGrid stroke="#eceef4" vertical={false} />
            <XAxis dataKey="name" tick={axis} />
            <YAxis allowDecimals={false} tick={axis} />
            <Tooltip /><Bar dataKey="falls" name="Falls" fill={BRAND} radius={[4, 4, 0, 0]} />
          </BarChart></ResponsiveContainer>
        </Chart>
      </div>

      <h3 className="font-semibold text-ink-900 mb-3">Incident history</h3>
      <DataTable emptyLabel="No fall incidents in this period" rows={data?.history || []} onRowClick={(r) => setOpen(r.id)}
        columns={[
          { key: "confirmed_at", label: "Confirmed", render: (r) => fmtShort(r.confirmed_at) },
          { key: "camera_name", label: "Camera", render: (r) => r.camera_name || `Camera ${r.camera_id}` },
          { key: "confidence", label: "Confidence", render: (r) => pct(r.confidence) },
          { key: "state", label: "Status", render: (r) => <IncidentBadge state={r.state} /> },
          { key: "resolved_at", label: "Time to resolve", render: (r) => (r.resolved_at ? fmtDuration(r.resolved_at - r.confirmed_at) : "Open") },
          { key: "resolve_reason", label: "Outcome", render: (r) => r.resolve_reason || "—" },
        ]} />
      {data && data.history.length >= 200 && <p className="text-xs text-slate-400 mt-2">Showing the 200 most recent incidents of this period.</p>}

      {open && <IncidentDrawer incidentId={open} onClose={() => setOpen(null)} onChanged={load} />}
    </>
  );
}
