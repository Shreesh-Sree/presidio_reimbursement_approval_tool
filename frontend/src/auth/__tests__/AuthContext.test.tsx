import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "../AuthContext";

const mocks = vi.hoisted(() => ({
  authStateCallback: undefined as ((event: string, session: unknown) => void) | undefined,
  me: vi.fn(),
  setTokenProvider: vi.fn(),
  unsubscribe: vi.fn(),
}));

vi.mock("../supabase", () => ({
  isSupabaseConfigured: true,
  supabase: {
    auth: {
      onAuthStateChange: vi.fn((callback) => {
        mocks.authStateCallback = callback;
        return { data: { subscription: { unsubscribe: mocks.unsubscribe } } };
      }),
      signOut: vi.fn(),
    },
  },
}));

vi.mock("../../lib/api", () => ({
  authApi: { me: mocks.me },
  getApiErrorCode: vi.fn(),
  setApiTokenProvider: mocks.setTokenProvider,
}));

vi.mock("../useSessionKeepAlive", () => ({ useSessionKeepAlive: vi.fn() }));

function AuthStatus() {
  const { status } = useAuth();
  return <output>{status}</output>;
}

afterEach(() => {
  mocks.authStateCallback = undefined;
  mocks.me.mockReset();
  mocks.setTokenProvider.mockReset();
  mocks.unsubscribe.mockReset();
});

describe("Supabase session synchronization", () => {
  it("authorizes one session once and uses the event token without re-reading Supabase storage", async () => {
    mocks.me.mockResolvedValue({ user_id: "user-1", email: "employee@example.com", roles: ["employee"], permissions: [] });
    render(<AuthProvider><AuthStatus /></AuthProvider>);

    const session = {
      access_token: "event-access-token",
      user: { id: "supabase-user-1", email: "employee@example.com" },
    };
    mocks.authStateCallback?.("SIGNED_IN", session);
    mocks.authStateCallback?.("INITIAL_SESSION", session);

    await waitFor(() => expect(mocks.me).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByText("authorized")).toBeInTheDocument());

    const provider = mocks.setTokenProvider.mock.calls[0]?.[0] as (() => Promise<string>) | undefined;
    await expect(provider?.()).resolves.toBe("event-access-token");
  });
});
