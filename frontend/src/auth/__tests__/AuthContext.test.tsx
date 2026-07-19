import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

function renderAuth(queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider><AuthStatus /></AuthProvider>
      </QueryClientProvider>,
    ),
  };
}

afterEach(() => {
  mocks.authStateCallback = undefined;
  mocks.me.mockReset();
  mocks.setTokenProvider.mockReset();
  mocks.unsubscribe.mockReset();
});

describe("Supabase session synchronization", () => {
  it("authorizes one session once and uses the event token without re-reading Supabase storage", async () => {
    mocks.me.mockResolvedValue({ user_id: "user-1", email: "employee@example.com", organization_id: "org-1", roles: ["employee"], permissions: [] });
    renderAuth();

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

  it("clears identity-agnostic query data before a second account is authorized", async () => {
    let authorizeSecondAccount: ((value: { user_id: string; email: string; organization_id: string; roles: string[]; permissions: string[] }) => void) | undefined;
    mocks.me
      .mockResolvedValueOnce({ user_id: "user-a", email: "a@example.com", organization_id: "org-a", roles: ["employee"], permissions: [] })
      .mockImplementationOnce(() => new Promise((resolve) => { authorizeSecondAccount = resolve; }));
    const { queryClient } = renderAuth();

    mocks.authStateCallback?.("SIGNED_IN", {
      access_token: "token-a",
      user: { id: "subject-a", email: "a@example.com" },
    });
    await waitFor(() => expect(screen.getByText("authorized")).toBeInTheDocument());

    queryClient.setQueryData(["reports"], [{ title: "Account A private report" }]);
    expect(queryClient.getQueryData(["reports"])).toEqual([{ title: "Account A private report" }]);

    mocks.authStateCallback?.("SIGNED_IN", {
      access_token: "token-b",
      user: { id: "subject-b", email: "b@example.com" },
    });

    await waitFor(() => expect(mocks.me).toHaveBeenCalledTimes(2));
    expect(screen.getByText("loading")).toBeInTheDocument();
    expect(queryClient.getQueryData(["reports"])).toBeUndefined();

    authorizeSecondAccount?.({ user_id: "user-b", email: "b@example.com", organization_id: "org-b", roles: ["employee"], permissions: [] });
    await waitFor(() => expect(screen.getByText("authorized")).toBeInTheDocument());
  });

  it("clears query data when the same Supabase subject is reauthenticated into another organization", async () => {
    mocks.me
      .mockResolvedValueOnce({ user_id: "user-1", email: "employee@example.com", roles: ["employee"], permissions: [], organization_id: "org-a" })
      .mockResolvedValueOnce({ user_id: "user-1", email: "employee@example.com", roles: ["employee"], permissions: [], organization_id: "org-b" });
    const { queryClient } = renderAuth();
    const session = { access_token: "token-a", user: { id: "same-subject", email: "employee@example.com" } };

    mocks.authStateCallback?.("SIGNED_IN", session);
    await waitFor(() => expect(screen.getByText("authorized")).toBeInTheDocument());
    queryClient.setQueryData(["reports"], [{ title: "Organization A report" }]);

    mocks.authStateCallback?.("SIGNED_OUT", null);
    expect(queryClient.getQueryData(["reports"])).toBeUndefined();
    mocks.authStateCallback?.("SIGNED_IN", { ...session, access_token: "token-b" });

    await waitFor(() => expect(mocks.me).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByText("authorized")).toBeInTheDocument());
    expect(queryClient.getQueryData(["reports"])).toBeUndefined();
  });
});
