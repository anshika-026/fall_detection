// Shared look-up tables and formatters for fall states.

// Box colours on the video overlay, by fall-engine state.
export const STATE_COLOR = {
  NORMAL: "#2563eb",
  POSSIBLE: "#f59e0b",
  CONFIRMED: "#dc2626",
  RECOVERED: "#0d9488",
  RESOLVED: "#6b7280",
};

export const STATE_LABEL = {
  NORMAL: "Normal",
  POSSIBLE: "Possible fall",
  CONFIRMED: "FALL CONFIRMED",
  RECOVERED: "Recovered",
  RESOLVED: "Resolved",
};

// Incident (database) states -> badge class + label.
export const INCIDENT_BADGE = {
  possible: ["badge-warning", "Possible"],
  confirmed: ["badge-danger", "Confirmed"],
  recovered: ["badge-warning", "Recovered"],
  resolved: ["badge-success", "Resolved"],
  dismissed: ["badge-neutral", "Dismissed"],
};

export const EVENT_LABEL = {
  possible: "Possible fall detected",
  confirmed: "Fall confirmed",
  recovered: "Person got up",
  relapse: "Person down again",
  resolved: "Resolved automatically",
  dismissed: "Dismissed (not a fall)",
  lost: "Person no longer visible",
  acknowledged: "Acknowledged",
  resolved_by_operator: "Resolved by operator",
};

export const CONNECTION_BADGE = {
  online: ["badge-success", "Online"],
  connecting: ["badge-warning", "Connecting"],
  offline: ["badge-danger", "Offline"],
  idle: ["badge-neutral", "Standby"],
  disabled: ["badge-neutral", "Feed off"],
  not_configured: ["badge-neutral", "Not configured"],
};

export const fmtTime = (ts) => (ts ? new Date(ts * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "medium" }) : "—");
export const fmtShort = (ts) => (ts ? new Date(ts * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—");
export const pct = (v) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);

export function fmtDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

export function timeAgo(ts) {
  if (!ts) return "—";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 5) return "just now";
  if (s < 60) return `${Math.round(s)}s ago`;
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}
