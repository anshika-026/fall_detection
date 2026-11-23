import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AppShell from "./layouts/AppShell";
import ErrorBoundary from "./components/ErrorBoundary";
import Login from "./auth/Login";
import Dashboard from "./dashboard/Dashboard";
import LiveMonitoring from "./live_monitoring/LiveMonitoring";
import Analytics from "./analytics/Analytics";
import Cameras from "./cameras/Cameras";
import SettingsPage from "./settings/SettingsPage";

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-10 text-sm text-slate-400">Loading…</div>;
  return user ? children : <Navigate to="/login" replace />;
}

// Keyed by route so a crash on one page clears when the user navigates away.
function Page({ children }) {
  const { pathname } = useLocation();
  return <ErrorBoundary key={pathname}>{children}</ErrorBoundary>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected><AppShell /></Protected>}>
            <Route path="/dashboard" element={<Page><Dashboard /></Page>} />
            <Route path="/live" element={<Page><LiveMonitoring /></Page>} />
            <Route path="/analytics" element={<Page><Analytics /></Page>} />
            <Route path="/cameras" element={<Page><Cameras /></Page>} />
            <Route path="/settings" element={<Page><SettingsPage /></Page>} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
