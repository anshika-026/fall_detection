import { useCallback, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, BarChart3, Camera, LayoutDashboard, LogOut, Settings, Video, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import useEvents, { beep } from "../hooks/useEvents";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/live", label: "Live Monitoring", icon: Video },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/cameras", label: "Cameras", icon: Camera },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [toasts, setToasts] = useState([]);

  // A confirmed fall pops up on every page, whichever one is open.
  const onEvent = useCallback((m) => {
    if (m.type !== "alert") return;
    const id = `${m.incident_id}-${m.timestamp}`;
    setToasts((t) => [{ id, ...m }, ...t].slice(0, 4));
    if (m.sound) beep();
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 30000);
  }, []);
  useEvents(onEvent);

  return (
    <div className="flex min-h-screen bg-[#f5f6fa]">
      <aside className="w-60 shrink-0 bg-ink-900 text-white flex flex-col">
        <div className="px-5 py-5 flex items-center gap-2.5 border-b border-white/10">
          <span className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center"><Activity size={18} /></span>
          <div className="leading-tight">
            <p className="font-semibold">Fall Detection</p>
            <p className="text-[11px] text-white/50">Safety monitoring</p>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${isActive ? "bg-white/10 text-white" : "text-white/60 hover:text-white hover:bg-white/5"}`}>
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-white/10">
          <p className="px-3 text-xs text-white/50 truncate" title={user?.email}>{user?.email}</p>
          <button onClick={logout} className="mt-1 w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-white/60 hover:text-white hover:bg-white/5">
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0 p-6 max-w-[1500px] mx-auto w-full">
        <Outlet />
      </main>

      <div className="fixed top-4 right-4 z-[60] space-y-2 w-80" role="alert" aria-live="assertive">
        {toasts.map((t) => (
          <div key={t.id} className="bg-white border border-danger-500 rounded-xl shadow-lg p-4 alert-pulse">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-danger-600">Fall confirmed</p>
                <p className="text-sm text-ink-900">{t.camera_name}</p>
                <p className="text-xs text-slate-500">Confidence {Math.round(t.confidence * 100)}%</p>
              </div>
              <button aria-label="Dismiss" onClick={() => setToasts((x) => x.filter((y) => y.id !== t.id))} className="text-slate-400 hover:text-slate-600"><X size={16} /></button>
            </div>
            <button className="btn-danger btn-sm mt-3" onClick={() => { navigate(`/dashboard?incident=${t.incident_id}`); setToasts((x) => x.filter((y) => y.id !== t.id)); }}>Review incident</button>
          </div>
        ))}
      </div>
    </div>
  );
}
