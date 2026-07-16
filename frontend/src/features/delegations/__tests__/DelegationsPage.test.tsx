import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { delegationsApi } from "../../../lib/api";
import { DelegationsPage } from "../DelegationsPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <DelegationsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("DelegationsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(delegationsApi, "list").mockResolvedValue([
      {
        id: "delegation-1",
        delegator_user_id: "manager-1",
        delegate_user_id: "delegate-1",
        delegate_name: "Devon Delegate",
        start_date: "2026-07-15T00:00:00Z",
        end_date: "2026-07-18T23:59:00Z",
        scope: "approval",
        is_active: true,
        remarks: "Out of office",
      },
    ]);
    vi.spyOn(delegationsApi, "candidates").mockResolvedValue([{ id: "delegate-1", full_name: "Devon Delegate" }]);
    vi.spyOn(delegationsApi, "create").mockResolvedValue({
      id: "delegation-2",
      delegator_user_id: "manager-1",
      delegate_user_id: "delegate-1",
      delegate_name: "Devon Delegate",
      start_date: "2026-07-20T00:00:00Z",
      end_date: "2026-07-22T23:59:00Z",
      scope: "approval",
      is_active: true,
    });
  });

  it("shows active delegation and creates a time-bounded approval substitute", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Devon Delegate")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /delegate approvals/i }));
    await user.click(screen.getByLabelText(/delegate to/i));
    await user.click(screen.getByRole("option", { name: "Devon Delegate" }));
    await user.type(screen.getByLabelText(/starts on/i), "2026-07-20");
    await user.type(screen.getByLabelText(/ends on/i), "2026-07-22");
    await user.click(screen.getByRole("button", { name: /^save delegation$/i }));

    await waitFor(() => expect(delegationsApi.create).toHaveBeenCalledWith(expect.objectContaining({
      delegate_user_id: "delegate-1",
      scope: "approval",
      start_date: "2026-07-20T00:00:00.000Z",
      end_date: "2026-07-22T23:59:00.000Z",
    })));
  });
});
