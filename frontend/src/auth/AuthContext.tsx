/* oxlint-disable react/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { isSupabaseConfigured, supabase } from "./supabase";
import { authApi, getApiErrorCode, setApiTokenProvider, type SessionUser } from "../lib/api";
import { useSessionKeepAlive } from "./useSessionKeepAlive";

export type User = SessionUser;
export type AuthStatus = "configuration_missing" | "loading" | "signed_out" | "authorized" | "access_denied" | "error";

export interface AuthContextType {
  user: User | null;
  token: string | null;
  status: AuthStatus;
  isLoading: boolean;
  isSignedIn: boolean;
  accessDenied: boolean;
  deniedEmail?: string | null;
  error: string | null;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

const missingConfigurationValue: AuthContextType = {
  user: null,
  token: null,
  status: "configuration_missing",
  isLoading: false,
  isSignedIn: false,
  accessDenied: false,
  error: null,
  logout: async () => undefined,
};

function SupabaseSessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [deniedEmail, setDeniedEmail] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let gotSession = false;
    let authorizedSubject: string | null = null;
    let authorizingSubject: string | null = null;

    const clearApplicationSession = () => {
      if (cancelled) return;
      setApiTokenProvider(null);
      setToken(null);
      setUser(null);
      authorizedSubject = null;
      authorizingSubject = null;
    };

    const synchronizeApplicationSession = async (session: Session | null) => {
      if (!session || !session.access_token) {
        clearApplicationSession();
        if (!cancelled) {
          setDeniedEmail(null);
          setError(null);
          setStatus("signed_out");
        }
        return;
      }

      gotSession = true;
      // Supabase serializes auth-state callbacks. Using getSession() from the
      // API interceptor while this callback is executing can wait on that
      // callback's lock and leave the dashboard in its loading state. The
      // callback already provides the current token, so use it directly.
      setApiTokenProvider(async () => session.access_token);
      setToken(session.access_token);

      // SIGNED_IN and INITIAL_SESSION can describe the same browser session.
      // One authorization request is enough; token refreshes only update the
      // request token and do not hold navigation behind another /auth/me call.
      if (authorizedSubject === session.user.id || authorizingSubject === session.user.id) {
        return;
      }

      if (!cancelled) {
        setDeniedEmail(null);
        setError(null);
        setStatus("loading");
      }
      authorizingSubject = session.user.id;

      try {
        const sessionUser = await authApi.me();
        if (cancelled) return;

        authorizedSubject = session.user.id;
        setUser(sessionUser);
        setStatus("authorized");
      } catch (sessionError) {
        clearApplicationSession();
        if (cancelled) return;

        if (getApiErrorCode(sessionError) === "access_not_granted") {
          setDeniedEmail(session.user?.email ?? null);
          setError(null);
          setStatus("access_denied");
          return;
        }

        setError(null);
        setStatus("signed_out");
      } finally {
        if (authorizingSubject === session.user.id) {
          authorizingSubject = null;
        }
      }
    };

    const hasAuthCallback = window.location.hash.includes("access_token") || new URLSearchParams(window.location.search).has("code");

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (cancelled) return;
      if (event === "SIGNED_OUT") {
        clearApplicationSession();
        setDeniedEmail(null);
        setError(null);
        setStatus("signed_out");
      } else if (event === "INITIAL_SESSION") {
        if (session) {
          gotSession = true;
          window.setTimeout(() => { void synchronizeApplicationSession(session); }, 0);
        } else if (!hasAuthCallback) {
          setStatus("signed_out");
        }
      } else if (session) {
        gotSession = true;
        window.setTimeout(() => { void synchronizeApplicationSession(session); }, 0);
      }
    });

    if (hasAuthCallback) {
      setTimeout(() => {
        if (!cancelled && !gotSession) {
          setStatus("signed_out");
        }
      }, 10000);
    }

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextType>(() => ({
    user,
    token,
    status,
    isLoading: status === "loading",
    isSignedIn: Boolean(user),
    accessDenied: status === "access_denied",
    deniedEmail,
    error,
    logout: async () => {
      setApiTokenProvider(null);
      setToken(null);
      setUser(null);
      setDeniedEmail(null);
      setError(null);
      setStatus("signed_out");
      await supabase.auth.signOut();
    },
  }), [deniedEmail, error, status, token, user]);

  const handleIdle = useCallback(async () => {
    setApiTokenProvider(null);
    setToken(null);
    setUser(null);
    setDeniedEmail(null);
    setError(null);
    setStatus("signed_out");
    await supabase.auth.signOut();
  }, []);

  useSessionKeepAlive(handleIdle);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!isSupabaseConfigured) {
    return <AuthContext.Provider value={missingConfigurationValue}>{children}</AuthContext.Provider>;
  }

  return <SupabaseSessionProvider>{children}</SupabaseSessionProvider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
