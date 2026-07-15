import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reportsApi } from "../../../lib/api";
import { ReceiptAnalysisPanel } from "../ReceiptAnalysisPanel";

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReceiptAnalysisPanel
        item={{ id: "item-1", amount: 75, description: "Taxi", receipt: { id: "receipt-1", url: "/api/attachments/receipt-1" } }}
        reportId="report-1"
      />
    </QueryClientProvider>,
  );
}

describe("ReceiptAnalysisPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(reportsApi, "analyzeReceipt").mockResolvedValue({
      advisory: true,
      context: {
        organization_ref: "tenant-safe",
        report_ref: "report-safe",
        item_ref: "item-safe",
        attachment_ref: "attachment-safe",
        event_id: "event-safe",
      },
      analysis: {
        findings: [
          {
            code: "duplicate_receipt_digest",
            severity: "warning",
            message: "This receipt digest appears on an earlier claim.",
          },
        ],
        ocr: { performed: false },
      },
    });
  });

  it("runs an explicit metadata-only advisory check and presents its finding", async () => {
    const user = userEvent.setup();
    renderPanel();

    expect(screen.getByText(/only receipt metadata is checked/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /check receipt metadata/i }));

    await waitFor(() => {
      expect(reportsApi.analyzeReceipt).toHaveBeenCalledWith("report-1", "item-1", "receipt-1");
    });
    expect(await screen.findByText(/this receipt digest appears on an earlier claim/i)).toBeInTheDocument();
    expect(screen.getByText(/ocr was not performed/i)).toBeInTheDocument();
    expect(screen.getByText(/does not approve, reject, or change this report/i)).toBeInTheDocument();
  });
});
