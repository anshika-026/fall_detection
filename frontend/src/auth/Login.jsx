import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Activity } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { user, login, setup } = useAuth();
  const [setupMode, setSetupMode] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.authStatus().then((s) => setSetupMode(s.setup_required)).catch((e) => { setError(e.message); setSetupMode(false); });
  }, []);

  if (user) return <Navigate to="/dashboard" replace />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (setupMode) await setup(email, password, name);
      else await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f6fa] px-4">
      <form onSubmit={submit} className="card w-full max-w-sm p-7 space-y-4">
        <div className="flex items-center gap-2.5 mb-1">
          <span className="w-9 h-9 rounded-lg bg-brand-500 text-white flex items-center justify-center"><Activity size={20} /></span>
          <div>
            <h1 className="font-semibold text-ink-900 leading-tight">Fall Detection</h1>
            <p className="text-xs text-slate-500">{setupMode ? "Create the first administrator" : "Sign in to continue"}</p>
          </div>
        </div>
        {setupMode && (
          <div><label className="label" htmlFor="name">Name</label>
            <input id="name" className="input-field" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></div>
        )}
        <div><label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required className="input-field" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></div>
        <div><label className="label" htmlFor="pw">Password</label>
          <input id="pw" type="password" required className="input-field" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={setupMode ? "new-password" : "current-password"} />
          {setupMode && <p className="hint">At least 8 characters.</p>}</div>
        {error && <p className="text-sm text-danger-500" role="alert">{error}</p>}
        <button className="btn-primary w-full" disabled={busy || setupMode === null}>{busy ? "Please wait…" : setupMode ? "Create account" : "Sign in"}</button>
      </form>
    </div>
  );
}
