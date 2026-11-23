import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "../api/client";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    if (!getToken()) {
      setReady(true);
      return;
    }
    api.me().then(setUser).catch(() => setToken("")).finally(() => setReady(true));
  }, []);

  const finish = useCallback((res) => {
    setToken(res.token);
    setUser(res.user);
  }, []);

  const value = useMemo(() => ({
    user, ready,
    login: async (email, password) => finish(await api.login(email, password)),
    setup: async (email, password, name) => finish(await api.setup(email, password, name)),
    logout: async () => {
      try { await api.logout(); } catch { /* already signed out */ }
      setToken("");
      setUser(null);
    },
  }), [user, ready, finish]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
