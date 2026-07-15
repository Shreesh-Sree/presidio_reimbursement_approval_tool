import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { userAdminApi } from "../api";
import { OrgChartPage } from "../OrgChartPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <OrgChartPage />
    </QueryClientProvider>,
  );
}

describe("OrgChartPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(userAdminApi, "orgChart").mockResolvedValue([
      {
        id: "admin-1",
        name: "Avery Admin",
        email: "avery@example.com",
        roles: ["administrator"],
        reports: [
          {
            id: "manager-1",
            name: "Morgan Manager",
            roles: ["employee", "approver"],
            reports: [
              { id: "employee-1", name: "Ana Employee", roles: ["employee"], reports: [] },
            ],
          },
        ],
      },
    ]);
  });

  it("renders every level of the reporting hierarchy", async () => {
    renderPage();

    expect(await screen.findByText("Avery Admin")).toBeInTheDocument();
    expect(screen.getByText("Morgan Manager")).toBeInTheDocument();
    expect(screen.getByText("Ana Employee")).toBeInTheDocument();
    expect(screen.getAllByRole("treeitem")).toHaveLength(3);
    expect(screen.getAllByText("Approver")).toHaveLength(1);
  });
});
