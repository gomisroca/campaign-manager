"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { authApi, tokens } from "@/lib/api";
import { UserResponse } from "@/types/Auth";

// ── Types ─────────────────────────────────────────────────────────────────────
interface AuthState {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName?: string,
  ) => Promise<void>;
  logout: () => void;
}

// ── Context ───────────────────────────────────────────────────────────────────
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // On mount, check if there's a stored token and fetch the current user
  useEffect(() => {
    const token = tokens.getAccess();
    const promise = token
      ? authApi
          .me()
          .then(setUser)
          .catch(() => tokens.clear())
      : Promise.resolve();
    promise.finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    tokens.set(data.access_token, data.refresh_token);
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const data = await authApi.register(email, password, fullName);
      tokens.set(data.access_token, data.refresh_token);
      setUser(data.user);
    },
    [],
  );

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
