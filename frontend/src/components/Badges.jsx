import { CONNECTION_BADGE, INCIDENT_BADGE } from "../lib/fall";

export function IncidentBadge({ state }) {
  const [cls, label] = INCIDENT_BADGE[state] || ["badge-neutral", state];
  return <span className={`badge ${cls}`}>{label}</span>;
}

export function ConnectionBadge({ value }) {
  const [cls, label] = CONNECTION_BADGE[value] || ["badge-neutral", value];
  return (
    <span className={`badge ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${value === "online" ? "bg-success-500 animate-pulse" : value === "offline" ? "bg-danger-500" : "bg-slate-400"}`} />
      {label}
    </span>
  );
}
