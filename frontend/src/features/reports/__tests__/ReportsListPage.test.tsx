import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reportsApi } from "../../../lib/api";
import { ReportsListPage } from "../ReportsListPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ReportsListPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ReportsListPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(reportsApi, "list").mockResolvedValue([]);
    vi.spyOn(reportsApi, "create").mockResolvedValue({
      id: "report-1",
      title: "August client visit",
      status: "draft",
      total: 0,
      currency: "USD",
    });
  });

  it("creates a report with its purpose and date range", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /new report/i }));
    await user.type(screen.getByLabelText(/report title/i), "August client visit");
    await user.type(screen.getByLabelText(/business purpose/i), "On-site client workshop");
    fireEvent.change(screen.getByLabelText(/report start date/i), { target: { value: "2026-08-01" } });
    fireEvent.change(screen.getByLabelText(/report end date/i), { target: { value: "2026-08-03" } });
    await user.click(screen.getByRole("button", { name: /^create report$/i }));

    await waitFor(() => expect(reportsApi.create).toHaveBeenCalledWith({
      title: "August client visit",
      description: "On-site client workshop",
      start_date: "2026-08-01",
      end_date: "2026-08-03",
    }));
  });
});
