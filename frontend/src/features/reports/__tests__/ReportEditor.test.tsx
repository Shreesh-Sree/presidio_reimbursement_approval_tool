import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reportsApi, type Report } from "../../../lib/api";
import { ReportEditor } from "../ReportEditor";

const draftReport: Report = {
  id: "report-1",
  title: "July client visit",
  status: "draft",
  total: 0,
  currency: "USD",
  line_items: [],
};

function renderEditor(report: Report = draftReport) {
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
    renderEditor(violatingReport);

    expect((await screen.findAllByText(/receipt is required above \$100/i)).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^submit report$/i })).toBeDisabled();
  });
});
