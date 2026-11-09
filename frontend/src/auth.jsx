import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTok] = useState(getToken());
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function verify() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.me();
        if (mounted) setUser(me.username);
      } catch {
        setToken(null);
        setTok(null);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    verify();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const onUnauth = () => {
      setToken(null);
      setTok(null);
      setUser(null);
    };
    window.addEventListener("instabi-unauth", onUnauth);
    return () => window.removeEventListener("instabi-unauth", onUnauth);
  }, []);

  async function login(username, password) {
    const res = await api.login(username, password);
    setToken(res.token);
    setTok(res.token);
    setUser(username);
    return res;
  }

  function logout() {
    setToken(null);
    setTok(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
