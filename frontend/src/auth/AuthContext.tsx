/* oxlint-disable react/only-export-components */
import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";
import { authApi, setApiToken, type BootstrapInput, type LoginResponse, type SessionUser } from "../lib/api";

export type User = SessionUser;

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  bootstrap: (input: BootstrapInput) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const storedUser = window.localStorage.getItem("session_user");
    if (!storedUser) return null;
    try {
      return JSON.parse(storedUser) as User;
    } catch {
      window.localStorage.removeItem("session_user");
      return null;
    }
  });
  const [token, setToken] = useState<string | null>(() => window.localStorage.getItem("access_token"));

  const establishSession = async (data: LoginResponse) => {
    setApiToken(data.access_token);
    setToken(data.access_token);
    const sessionUser = data.user ?? await authApi.me();
    setUser(sessionUser);
    window.localStorage.setItem("session_user", JSON.stringify(sessionUser));
  };

  const login = async (email: string, password: string) => {
    await establishSession(await authApi.login(email, password));
  };

  const bootstrap = async (input: BootstrapInput) => {
    await establishSession(await authApi.bootstrap(input));
  };

  const logout = () => {
    setApiToken(null);
    setUser(null);
    setToken(null);
    window.localStorage.removeItem("session_user");
  };

  return (
    <AuthContext.Provider value={{ user, token, login, bootstrap, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
