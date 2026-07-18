import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccessRequestsPage } from "../AccessRequestsPage";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock("../../../lib/api", () => ({
  apiClient: api,
  getApiErrorMessage: (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback,
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><AccessRequestsPage /></QueryClientProvider>);
}

afterEach(() => vi.resetAllMocks());

describe("AccessRequestsPage", () => {
  it("shows a load failure instead of an empty pending-request state", async () => {
    api.get.mockRejectedValueOnce(new Error("Missing permission: user:manage"));

    renderPage();

    expect(await screen.findByRole("alert")).toHaveTextContent("Missing permission: user:manage");
    expect(screen.queryByText("No pending access requests")).not.toBeInTheDocument();
  });
});
