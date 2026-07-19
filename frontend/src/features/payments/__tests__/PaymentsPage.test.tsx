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

const secondExportedPayment: PaymentRecord = {
  ...exportedPayment,
  id: "payment-exported-2",
  report_id: "report-3",
  report_number: "RPT-2026-003",
  payment_reference: "PAY-RPT-2026-003",
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
    vi.spyOn(paymentsApi, "list").mockResolvedValue({ items: [pendingPayment, exportedPayment, secondExportedPayment], total: 3 });
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
    expect(screen.getAllByText("PB-001")).toHaveLength(3);
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
    await user.click(screen.getAllByRole("button", { name: /^mark paid$/i })[0]);

    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/payment provider reference/i), "PROV-2026-77");
    await user.click(within(dialog).getByRole("button", { name: /^mark paid$/i }));

    await waitFor(() => expect(paymentsApi.markPaid).toHaveBeenCalledWith("payment-exported", {
      provider_reference: "PROV-2026-77",
      payment_date: undefined,
      remarks: undefined,
    }));
  });

  it("does not carry a provider reference from one payment dialog to another", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("PAY-RPT-2026-002");
    const markPaidButtons = screen.getAllByRole("button", { name: /^mark paid$/i });
    await user.click(markPaidButtons[0]);
    const firstDialog = await screen.findByRole("dialog");
    await user.type(within(firstDialog).getByLabelText(/payment provider reference/i), "PROV-A");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    await user.click(markPaidButtons[1]);
    const secondDialog = await screen.findByRole("dialog");
    expect(within(secondDialog).getByLabelText(/payment provider reference/i)).toHaveValue("");
    expect(within(secondDialog).getByText(/pay-rpt-2026-003/i)).toBeInTheDocument();
  });

  it("keeps the payment dialog open and displays a safe mutation error", async () => {
    const user = userEvent.setup();
    vi.spyOn(paymentsApi, "markPaid").mockRejectedValueOnce(new Error("Provider unavailable"));
    renderPage();

    await screen.findByText("PAY-RPT-2026-002");
    await user.click(screen.getAllByRole("button", { name: /^mark paid$/i })[0]);
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/payment provider reference/i), "PROV-UNAVAILABLE");
    await user.click(within(dialog).getByRole("button", { name: /^mark paid$/i }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Provider unavailable");
    expect(within(dialog).getByLabelText(/payment provider reference/i)).toHaveValue("PROV-UNAVAILABLE");
  });

  it("does not let a completed payment mutation close a later payment dialog", async () => {
    const user = userEvent.setup();
    let resolvePayment: ((value: PaymentRecord) => void) | undefined;
    vi.spyOn(paymentsApi, "markPaid").mockImplementationOnce(
      () => new Promise((resolve) => { resolvePayment = resolve; }),
    );
    renderPage();

    await screen.findByText("PAY-RPT-2026-002");
    await user.click(screen.getAllByRole("button", { name: /^mark paid$/i })[0]);
    const firstDialog = await screen.findByRole("dialog");
    await user.type(within(firstDialog).getByLabelText(/payment provider reference/i), "PROV-A");
    await user.click(within(firstDialog).getByRole("button", { name: /^mark paid$/i }));
    await waitFor(() => expect(paymentsApi.markPaid).toHaveBeenCalledWith("payment-exported", expect.anything()));
    await user.keyboard("{Escape}");

    await user.click(screen.getAllByRole("button", { name: /^mark paid$/i })[1]);
    const secondDialog = await screen.findByRole("dialog");
    resolvePayment?.({ ...exportedPayment, status: "paid" });

    await waitFor(() => expect(screen.getByText("Reimbursement marked as paid.")).toBeInTheDocument());
    expect(secondDialog).toBeInTheDocument();
    expect(within(secondDialog).getByLabelText(/payment provider reference/i)).toHaveValue("");
  });
});
