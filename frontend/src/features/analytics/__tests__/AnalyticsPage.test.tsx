import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { analyticsApi } from "../../../lib/api";
import { AnalyticsPage } from "../AnalyticsPage";

vi.mock("react-chartjs-2", () => ({
  Bar: ({ data }: { data: { labels: string[] } }) => (
    <div aria-label="Monthly requested spend chart" role="img">{data.labels.join(", ")}</div>
  ),
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <AnalyticsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(analyticsApi, "overview").mockResolvedValue({
      generated_at: "2026-07-15T12:00:00Z",
      period_months: 6,
      scope: "organization",
      summary: {
        report_count: 8,
        pending_approval_count: 2,
        approved_pending_payment_count: 3,
        paid_count: 1,
        rejected_count: 1,
        policy_violation_count: 2,
        policy_violation_item_rate: 0.125,
        average_approval_hours: 18.5,
        total_requested: [{ currency: "USD", amount: 1250 }],
      },
      report_statuses: [
        { status: "submitted", count: 2 },
        { status: "approved_pending_payment", count: 3 },
      ],
      spending_by_category: [{ category: "Travel", currency: "USD", amount: 800 }],
      monthly_spend: [{ month: "2026-07", currency: "USD", amount: 1250 }],
    });
  });

  it("renders privacy-safe summary, category spend, and accessible chart data", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: /reimbursement insights/i })).toBeInTheDocument();
    expect(await screen.findByText("8")).toBeInTheDocument();
    expect(screen.getByText("$1,250.00")).toBeInTheDocument();
    expect(screen.getByText("Travel")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /monthly requested spend chart/i })).toHaveTextContent("Jul 2026");
    expect(screen.queryByText(/employee@example/i)).not.toBeInTheDocument();
  });
});
