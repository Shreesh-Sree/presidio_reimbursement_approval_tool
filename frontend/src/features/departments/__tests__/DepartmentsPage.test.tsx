import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { departmentsApi, type Department } from "../api";
import { DepartmentsPage } from "../DepartmentsPage";

const departments: Department[] = [
  { id: "engineering", code: "ENG", name: "Engineering", status: "active" },
];

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><DepartmentsPage /></QueryClientProvider>);
}

describe("DepartmentsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(departmentsApi, "list").mockResolvedValue(departments);
    vi.spyOn(departmentsApi, "create").mockResolvedValue({ id: "finance", code: "FIN", name: "Finance", status: "active" });
    vi.spyOn(departmentsApi, "update").mockResolvedValue({ ...departments[0], status: "inactive" });
  });

  it("creates a department and lets an administrator deactivate an empty department", async () => {
    const user = userEvent.setup();
    const create = vi.mocked(departmentsApi.create);
    const update = vi.mocked(departmentsApi.update);
    renderPage();

    await user.click(await screen.findByRole("button", { name: /new department/i }));
    await user.type(screen.getByLabelText(/^name$/i), "Finance");
    await user.type(screen.getByLabelText(/^code$/i), "fin");
    await user.click(screen.getByRole("button", { name: /create department/i }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ code: "fin", name: "Finance" }));

    await user.click(await screen.findByRole("button", { name: /edit engineering/i }));
    await user.click(screen.getByLabelText(/^status$/i));
    await user.click(await screen.findByRole("option", { name: "Inactive" }));
    await user.click(screen.getByRole("button", { name: /save changes/i }));
    await waitFor(() => expect(update).toHaveBeenCalledWith("engineering", {
      code: "ENG",
      name: "Engineering",
      status: "inactive",
    }));
  });
});
