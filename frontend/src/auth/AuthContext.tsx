/* oxlint-disable react/only-export-components */
import { useAuth as useClerkAuth } from "@clerk/clerk-react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { clerkJwtTemplate, isClerkConfigured } from "./clerk";
import { authApi, getApiErrorCode, getApiErrorMessage, setApiToken, type SessionUser } from "../lib/api";

export type User = SessionUser;
export type AuthStatus = "configuration_missing" | "loading" | "signed_out" | "authorized" | "access_denied" | "error";

export interface AuthContextType {
  user: User | null;
  token: string | null;
  status: AuthStatus;
  isLoading: boolean;
  isSignedIn: boolean;
  accessDenied: boolean;
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

function ClerkSessionProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn, signOut } = useClerkAuth();
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const clearApplicationSession = () => {
      setApiToken(null);
      if (!cancelled) {
        setToken(null);
        setUser(null);
      }
    };

    const synchronizeApplicationSession = async () => {
      if (!isLoaded) {
        if (!cancelled) setStatus("loading");
        return;
      }

      if (!isSignedIn) {
        clearApplicationSession();
        if (!cancelled) {
          setError(null);
          setStatus("signed_out");
        }
        return;
      }

      if (!cancelled) {
        setError(null);
        setStatus("loading");
      }

      try {
        const clerkToken = await getToken({ template: clerkJwtTemplate });
        if (!clerkToken) throw new Error("A Clerk API token could not be created for this session.");
        if (cancelled) return;

        setApiToken(clerkToken);
        const sessionUser = await authApi.me();
        if (cancelled) return;

        setToken(clerkToken);
        setUser(sessionUser);
        setStatus("authorized");
      } catch (sessionError) {
        clearApplicationSession();
        if (cancelled) return;

        if (getApiErrorCode(sessionError) === "access_not_granted") {
          setError(null);
          setStatus("access_denied");
          return;
        }

        setError(getApiErrorMessage(sessionError, "We could not verify access to the reimbursement platform."));
        setStatus("error");
      }
    };

    void synchronizeApplicationSession();
    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn]);

  const value = useMemo<AuthContextType>(() => ({
    user,
    token,
    status,
    isLoading: status === "loading",
    isSignedIn: Boolean(isSignedIn),
    accessDenied: status === "access_denied",
    error,
    logout: async () => {
      setApiToken(null);
      setToken(null);
      setUser(null);
      setError(null);
      setStatus("signed_out");
      await signOut();
    },
  }), [error, isSignedIn, signOut, status, token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (!isClerkConfigured) {
    return <AuthContext.Provider value={missingConfigurationValue}>{children}</AuthContext.Provider>;
  }

  return <ClerkSessionProvider>{children}</ClerkSessionProvider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
