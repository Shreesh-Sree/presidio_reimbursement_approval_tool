import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(() => ({ auth: {} })),
}));

vi.mock("@supabase/supabase-js", () => ({ createClient: mocks.createClient }));

describe("Supabase browser session policy", () => {
  beforeEach(() => {
    vi.resetModules();
    mocks.createClient.mockClear();
    window.sessionStorage.clear();
  });

  it("uses explicit session-storage persistence rather than the SDK localStorage default", async () => {
    const { supabaseAuthOptions } = await import("../supabase");

    expect(supabaseAuthOptions).toMatchObject({
      autoRefreshToken: true,
      detectSessionInUrl: true,
      persistSession: true,
      storageKey: "presidio.supabase.auth.session",
    });
    expect(supabaseAuthOptions.storage).toBe(window.sessionStorage);
    expect(mocks.createClient).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(String),
      { auth: supabaseAuthOptions },
    );
  });
});
