"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, apiPost, getToken, setToken } from "@/lib/api";

interface User { id: string; email: string; name: string }
interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) { setLoading(false); return; }
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiPost<{ access_token: string }>("/api/auth/login", { email, password });
    setToken(res.access_token);
    setUser(await api<User>("/api/auth/me"));
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    await apiPost("/api/auth/register", { email, password, name });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => { setToken(null); setUser(null); }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthCtx {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
