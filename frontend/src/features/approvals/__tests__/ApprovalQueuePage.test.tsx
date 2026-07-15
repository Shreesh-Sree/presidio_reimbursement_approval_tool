import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { approvalsApi } from "../../../lib/api";
import { ActionBar } from "../ActionBar";
import { ApprovalQueuePage } from "../ApprovalQueuePage";

function renderWithQuery(children: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ApprovalQueuePage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(approvalsApi, "queue").mockResolvedValue([
      {
        id: "report-1",
        title: "July client visit",
        status: "submitted",
        total: 356.42,
        currency: "USD",
        submitter_name: "Maya Chen",
      },
    ]);
    vi.spyOn(approvalsApi, "history").mockResolvedValue([]);
    vi.spyOn(approvalsApi, "approve").mockResolvedValue({ id: "report-1", title: "July client visit", status: "approved", total: 356.42 });
  });

  it("lists pending reports for review", async () => {
    renderWithQuery(<ApprovalQueuePage />);

    expect(await screen.findByText("July client visit")).toBeInTheDocument();
    expect(screen.getByText("Maya Chen")).toBeInTheDocument();
    expect(screen.getByText("$356.42")).toBeInTheDocument();
  });

  it("submits an approval action with remarks", async () => {
    const user = userEvent.setup();
    const approve = vi.mocked(approvalsApi.approve);
    renderWithQuery(<ActionBar reportId="report-1" />);

    await user.type(screen.getByLabelText(/remarks/i), "Policy checks complete");
    await user.click(screen.getByRole("button", { name: /^approve$/i }));

    await waitFor(() => expect(approve).toHaveBeenCalledWith("report-1", "Policy checks complete"));
  });

  it("shows completed reports in the manager's team history", async () => {
    vi.mocked(approvalsApi.history).mockResolvedValue([
      {
        id: "report-history-1",
        title: "June customer visit",
        status: "approved_pending_payment",
        total: 120,
        currency: "USD",
        submitter_name: "Maya Chen",
        approval_status: "approved",
        approval_decision_at: "2026-07-15T10:00:00Z",
      },
    ]);
    renderWithQuery(<ApprovalQueuePage />);

    expect(await screen.findByText("My team history")).toBeInTheDocument();
    expect(await screen.findByText("June customer visit")).toBeInTheDocument();
    expect(screen.getByText("Your decision: Approved")).toBeInTheDocument();
  });
});
