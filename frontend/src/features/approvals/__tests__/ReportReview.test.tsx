import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { commentsApi, reportsApi, type Report } from "../../../lib/api";
import { ReportReview } from "../ReportReview";

const reviewedReport: Report = {
  id: "report-1",
  title: "July client visit",
  status: "submitted",
  total: 356.42,
  currency: "USD",
  submitter_name: "Maya Chen",
  line_items: [],
  ai_audit: {
    status: "completed",
    summary: "One taxi receipt may duplicate an earlier claim.",
    key_insights: ["Taxi spend is within the policy cap."],
    recommendation: "request_information",
    risk_level: "medium",
    provider: { status: "fallback" },
    human_review: {
      required: true,
      automated_action_taken: false,
      message: "An authorized manager must make the final workflow decision.",
    },
    findings: [
      {
        id: "finding-1",
        severity: "medium",
        finding_type: "potential_duplicate",
        message: "The taxi receipt resembles an earlier claim.",
      },
    ],
  },
};

function renderReview() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReportReview reportId="report-1" />
    </QueryClientProvider>,
  );
}

describe("ReportReview", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(reportsApi, "get").mockResolvedValue(reviewedReport);
    vi.spyOn(reportsApi, "listItems").mockResolvedValue([]);
    vi.spyOn(commentsApi, "list").mockResolvedValue([]);
  });

  it("presents AI output as an advisory with concise findings and a human decision gate", async () => {
    const user = userEvent.setup();
    renderReview();

    expect(await screen.findByRole("heading", { name: /ai review advisory/i })).toBeInTheDocument();
    expect(screen.getByText(/ai analysis highlights evidence and possible risks/i)).toBeInTheDocument();
    expect(screen.getByText("One taxi receipt may duplicate an earlier claim.")).toBeInTheDocument();
    expect(screen.getByText("The taxi receipt resembles an earlier claim.")).toBeInTheDocument();
    expect(screen.getByText(/human review required/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^approve$/i })).toBeEnabled();

    const rawData = screen.getByText(/"summary": "one taxi receipt may duplicate/i);
    const details = rawData.closest("details");
    expect(details).not.toHaveAttribute("open");
    await user.click(screen.getByText(/view raw ai review data/i));
    expect(details).toHaveAttribute("open");
  });
});
