import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { paymentsApi, type PaymentRecord } from "../../../lib/api";
import { PaymentsPage } from "../PaymentsPage";

const pendingPayment: PaymentRecord = {
  id: "payment-pending",
  report_id: "report-1",
  report_number: "RPT-2026-001",
  employee_name: "Maya Chen",
  employee_number: "E-100",
  payment_reference: "PAY-RPT-2026-001",
  amount: 250,
  currency: "USD",
  status: "pending",
  batch: null,
};

const exportedPayment: PaymentRecord = {
  id: "payment-exported",
  report_id: "report-2",
  report_number: "RPT-2026-002",
  employee_name: "Avery Singh",
  employee_number: "E-101",
  payment_reference: "PAY-RPT-2026-002",
  amount: 75.5,
  currency: "USD",
  status: "exported",
  batch: { id: "batch-1", batch_reference: "PB-001", status: "exported" },
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <PaymentsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("PaymentsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(paymentsApi, "list").mockResolvedValue({ items: [pendingPayment, exportedPayment], total: 2 });
    vi.spyOn(paymentsApi, "listBatches").mockResolvedValue({
      items: [{
        id: "batch-1",
        batch_reference: "PB-001",
        status: "exported",
        currency: "USD",
        total_amount: 75.5,
        payment_count: 1,
      }],
      total: 1,
    });
    vi.spyOn(paymentsApi, "createBatch").mockResolvedValue({
      id: "batch-2",
      batch_reference: "PB-002",
      status: "created",
      currency: "USD",
      total_amount: 250,
      payment_count: 1,
    });
    vi.spyOn(paymentsApi, "exportBatch").mockResolvedValue({
      blob: new Blob(["batch_reference\nPB-001\n"], { type: "text/csv" }),
      filename: "PB-001.csv",
    });
    vi.spyOn(paymentsApi, "markPaid").mockResolvedValue({ ...exportedPayment, status: "paid" });
    vi.spyOn(paymentsApi, "markFailed").mockResolvedValue({ ...exportedPayment, status: "failed" });
  });

  it("lists finance-owned payment records and status controls", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: /reimbursement payments/i })).toBeInTheDocument();
    expect(await screen.findByText("PAY-RPT-2026-001")).toBeInTheDocument();
    expect(screen.getByText("Maya Chen")).toBeInTheDocument();
    expect(screen.getByText("$250.00")).toBeInTheDocument();
    expect(screen.getAllByText("PB-001")).toHaveLength(2);
    expect(paymentsApi.list).toHaveBeenCalledWith({ status: "pending" });
    expect(screen.queryByText(/account number/i)).not.toBeInTheDocument();
  });

  it("creates a compatible single-currency batch from selected pending payments", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("PAY-RPT-2026-001");
    await user.click(screen.getByRole("checkbox", { name: /select pay-rpt-2026-001/i }));
    expect(screen.getByRole("button", { name: /^create batch$/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /^create batch$/i }));

    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/finance note/i), "July provider export");
    await user.click(within(dialog).getByRole("button", { name: /^create batch$/i }));

    await waitFor(() => expect(paymentsApi.createBatch).toHaveBeenCalledWith({
      payment_ids: ["payment-pending"],
      remarks: "July provider export",
    }));
  });

  it("records a provider reference when an exported reimbursement is paid", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("PAY-RPT-2026-002");
    await user.click(screen.getByRole("button", { name: /^mark paid$/i }));

    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/payment provider reference/i), "PROV-2026-77");
    await user.click(within(dialog).getByRole("button", { name: /^mark paid$/i }));

    await waitFor(() => expect(paymentsApi.markPaid).toHaveBeenCalledWith("payment-exported", {
      provider_reference: "PROV-2026-77",
      payment_date: undefined,
      remarks: undefined,
    }));
  });
});
