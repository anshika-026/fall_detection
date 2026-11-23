// API client for the Fall Detection backend. Same-origin (the dev server and a
// production build both proxy /api and /ws), so there is no base URL to configure.

export const WS_PROTOCOL = window.location.protocol === "https:" ? "wss" : "ws";
export const WS_HOST = window.location.host;
const TOKEN_KEY = "falldet_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => (onUnauthorized = fn);

async function request(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.", 0);
  }
  if (res.status === 401 && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/setup")) {
    setToken("");
    onUnauthorized();
    throw new ApiError("Your session has ended. Please sign in again.", 401);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail)) detail = j.detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
    } catch { /* not JSON */ }
    throw new ApiError(detail, res.status);
  }
  return raw ? res : res.json();
}

const qs = (o) => {
  const p = new URLSearchParams();
  Object.entries(o || {}).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && p.set(k, v));
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  authStatus: () => request("/api/auth/status"),
  setup: (email, password, name) => request("/api/auth/setup", { method: "POST", body: { email, password, name } }),
  login: (email, password) => request("/api/auth/login", { method: "POST", body: { email, password } }),
  me: () => request("/api/auth/me"),
  logout: () => request("/api/auth/logout", { method: "POST" }),

  dashboard: () => request("/api/dashboard"),
  analytics: (days, cameraId) => request(`/api/analytics${qs({ days, camera_id: cameraId })}`),
  incidents: (params) => request(`/api/incidents${qs(params)}`),
  incident: (id) => request(`/api/incidents/${id}`),
  acknowledge: (id) => request(`/api/incidents/${id}/acknowledge`, { method: "POST" }),
  resolve: (id, reason) => request(`/api/incidents/${id}/resolve`, { method: "POST", body: { reason } }),

  cameras: () => request("/api/cameras"),
  addCamera: (c) => request("/api/cameras", { method: "POST", body: c }),
  updateCamera: (id, c) => request(`/api/cameras/${id}`, { method: "PUT", body: c }),
  deleteCamera: (id) => request(`/api/cameras/${id}`, { method: "DELETE" }),
  testStream: async (c) => {
    const res = await request("/api/cameras/test-stream", { method: "POST", body: c, raw: true });
    return URL.createObjectURL(await res.blob());
  },

  settings: () => request("/api/settings"),
  saveSettings: (group, data) => request(`/api/settings/${group}`, { method: "PUT", body: data }),
  resetSettings: (group) => request(`/api/settings/${group}/reset`, { method: "POST" }),
  system: () => request("/api/system"),
};

// Evidence is behind the session token, so images/videos are fetched with the
// header and shown from an object URL (an <img src> cannot send a header).
export async function fetchObjectUrl(path) {
  const res = await request(path, { raw: true });
  return URL.createObjectURL(await res.blob());
}

export const wsUrl = (path, extra = "") =>
  `${WS_PROTOCOL}://${WS_HOST}${path}?token=${encodeURIComponent(getToken())}${extra}`;
