import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CHECK_INTERVAL_MS, useSessionKeepAlive } from "../useSessionKeepAlive";

const mocks = vi.hoisted(() => ({ getSession: vi.fn() }));

vi.mock("../supabase", () => ({ supabase: { auth: { getSession: mocks.getSession } } }));

function KeepAliveProbe({ onIdle }: { onIdle: () => void }) {
  useSessionKeepAlive(onIdle);
  return null;
}

describe("useSessionKeepAlive", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
    mocks.getSession.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not overlap a hung Supabase session check", async () => {
    mocks.getSession.mockImplementation(() => new Promise(() => undefined));
    render(<KeepAliveProbe onIdle={vi.fn()} />);

    await act(async () => { await vi.advanceTimersByTimeAsync(CHECK_INTERVAL_MS); });
    await act(async () => { await vi.advanceTimersByTimeAsync(CHECK_INTERVAL_MS * 2); });

    expect(mocks.getSession).toHaveBeenCalledTimes(1);
  });
});
