import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { categoriesApi, reportsApi, vendorsApi, type Report } from "../../../lib/api";
import { ReportEditor } from "../ReportEditor";

const draftReport: Report = {
  id: "report-1",
  title: "July client visit",
  status: "draft",
  total: 0,
  currency: "USD",
  line_items: [],
};

function renderEditor() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReportEditor reportId="report-1" />
    </QueryClientProvider>,
  );
}

describe("ReportEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(reportsApi, "get").mockResolvedValue(draftReport);
    vi.spyOn(reportsApi, "listItems").mockResolvedValue([]);
    vi.spyOn(reportsApi, "addItem").mockResolvedValue({ id: "item-1", amount: 0, description: "" });
    vi.spyOn(reportsApi, "updateItem").mockResolvedValue({ id: "item-1", amount: 0, description: "" });
    vi.spyOn(reportsApi, "removeItem").mockResolvedValue(undefined);
    vi.spyOn(reportsApi, "submit").mockResolvedValue({ ...draftReport, status: "submitted" });
    vi.spyOn(categoriesApi, "list").mockResolvedValue([
      { id: "category-1", code: "TRAVEL", name: "Travel" },
    ]);
    vi.spyOn(vendorsApi, "list").mockResolvedValue([
      { id: "vendor-1", name: "City Taxi", normalized_name: "city taxi" },
    ]);
  });

  it("adds an item and recomputes the live total", async () => {
    const user = userEvent.setup();
    renderEditor();

    await user.click(await screen.findByRole("button", { name: /add line item/i }));
    await user.type(screen.getByLabelText(/description for line item 1/i), "Airport transfer");
    fireEvent.change(screen.getByLabelText(/amount for line item 1/i), { target: { value: "42.50" } });

    expect(screen.getByText("Total: $42.50")).toBeInTheDocument();
  });

  it("shows violations and blocks submission", async () => {
    const violatingReport: Report = {
      ...draftReport,
      line_items: [
        {
          id: "item-1",
          amount: 120,
          description: "Client dinner",
          is_policy_violated: true,
          violation_reason: "Receipt is required above $100",
        },
      ],
    };
    vi.mocked(reportsApi.get).mockResolvedValue(violatingReport);
    vi.mocked(reportsApi.listItems).mockResolvedValue(violatingReport.line_items ?? []);
    renderEditor();

    expect((await screen.findAllByText(/receipt is required above \$100/i)).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^submit report$/i })).toBeDisabled();
  });

  it("saves selected category and vendor IDs instead of free-text values", async () => {
    const user = userEvent.setup();
    const addItem = vi.mocked(reportsApi.addItem);
    renderEditor();

    await user.click(await screen.findByRole("button", { name: /add line item/i }));
    await user.type(screen.getByLabelText(/description for line item 1/i), "Airport transfer");
    fireEvent.change(screen.getByLabelText(/amount for line item 1/i), { target: { value: "42.50" } });
    await user.click(screen.getByLabelText(/category for line item 1/i));
    await user.click(screen.getByRole("option", { name: "Travel" }));
    await user.click(screen.getByLabelText(/saved vendor/i));
    await user.click(screen.getByRole("option", { name: "City Taxi" }));
    await user.click(screen.getByRole("button", { name: /save item/i }));

    await expect.poll(() => addItem.mock.calls.length).toBe(1);
    expect(addItem).toHaveBeenCalledWith("report-1", expect.objectContaining({
      category_id: "category-1",
      vendor_id: "vendor-1",
      amount: 42.5,
      currency: "USD",
      description: "Airport transfer",
    }));
  });

  it("allows sent-back reports to be corrected and displays API validation details", async () => {
    const user = userEvent.setup();
    const sentBackReport: Report = {
      ...draftReport,
      status: "sent_back",
      line_items: [
        {
          id: "item-1",
          category_id: "category-1",
          category_name: "Travel",
          amount: 42.5,
          currency: "USD",
          description: "Airport transfer",
          expense_date: "2026-08-02",
        },
      ],
    };
    vi.mocked(reportsApi.get).mockResolvedValue(sentBackReport);
    vi.mocked(reportsApi.listItems).mockResolvedValue(sentBackReport.line_items ?? []);
    vi.mocked(reportsApi.submit).mockRejectedValue(Object.assign(new Error("Request failed"), {
      isAxiosError: true,
      response: { data: { detail: "Active policy requires a receipt for this item." } },
    }));
    renderEditor();

    expect(await screen.findByRole("button", { name: /^resubmit report$/i })).toBeEnabled();
    expect(screen.getByLabelText(/report title/i)).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /^resubmit report$/i }));

    expect(await screen.findByText("Active policy requires a receipt for this item.")).toBeInTheDocument();
  });

  it("saves the report purpose and date range with the draft", async () => {
    const user = userEvent.setup();
    const update = vi.spyOn(reportsApi, "update").mockResolvedValue({
      ...draftReport,
      description: "On-site client workshops",
      start_date: "2026-08-01",
      end_date: "2026-08-03",
    });
    renderEditor();

    await screen.findByLabelText(/report title/i);
    await user.type(screen.getByLabelText(/business purpose/i), "On-site client workshops");
    fireEvent.change(screen.getByLabelText(/report start date/i), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText(/report end date/i), { target: { value: "2026-08-03" } });
    await user.click(screen.getByRole("button", { name: /save draft/i }));

    await expect.poll(() => update.mock.calls.length).toBe(1);
    expect(update).toHaveBeenCalledWith("report-1", {
      title: "July client visit",
      description: "On-site client workshops",
      start_date: "2026-08-01",
      end_date: "2026-08-03",
    });
  });
});
