import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authApi, setApiTokenProvider, type SessionUser } from "../lib/api";
import { AuthContext, type AuthContextType } from "./AuthContext";

// This is intentionally impossible to enable in a production Vite build.
// It exists solely so Playwright can exercise the complete local workflow
// without using a Supabase account or production data.
export const isLocalE2eAuth = import.meta.env.DEV && import.meta.env.VITE_E2E_LOCAL_AUTH === "true";

const email = import.meta.env.VITE_E2E_EMAIL ?? "employee@example.com";
const password = import.meta.env.VITE_E2E_PASSWORD ?? "correct-horse-battery-staple";

export function LocalE2eAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void authApi.localLogin(email, password)
      .then((session) => {
        if (cancelled) return;
        setApiTokenProvider(async () => session.access_token);
        setToken(session.access_token);
        setUser(session.user);
      })
      .catch(() => {
        if (!cancelled) setError("Local E2E login failed. Start the disposable API test server first.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      setApiTokenProvider(null);
    };
  }, []);

  const value = useMemo<AuthContextType>(() => ({
    user,
    token,
    status: loading ? "loading" : user ? "authorized" : "error",
    isLoading: loading,
    isSignedIn: Boolean(user),
    accessDenied: false,
    error,
    logout: async () => {
      setApiTokenProvider(null);
      setToken(null);
      setUser(null);
    },
  }), [error, loading, token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
