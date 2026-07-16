import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { userAdminApi, type ManagedUser, type RoleOption } from "../api";
import { UsersPage } from "../UsersPage";

const managedUsers: ManagedUser[] = [
  {
    id: "employee-1",
    email: "ana@example.com",
    full_name: "Ana Employee",
    status: "active",
    roles: ["employee"],
    manager_id: "manager-1",
    manager_name: "Morgan Manager",
  },
  {
    id: "manager-1",
    email: "morgan@example.com",
    full_name: "Morgan Manager",
    status: "active",
    roles: ["employee", "approver"],
  },
];

const roles: RoleOption[] = [
  { code: "employee", name: "Employee" },
  { code: "approver", name: "Approver" },
  { code: "administrator", name: "Administrator" },
];

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <UsersPage />
    </QueryClientProvider>,
  );
}

describe("UsersPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(userAdminApi, "list").mockResolvedValue(managedUsers);
    vi.spyOn(userAdminApi, "listRoles").mockResolvedValue(roles);
    vi.spyOn(userAdminApi, "create").mockResolvedValue(managedUsers[0]);
    vi.spyOn(userAdminApi, "update").mockResolvedValue(managedUsers[0]);
    vi.spyOn(userAdminApi, "deactivate").mockResolvedValue({ ...managedUsers[0], status: "inactive" });
  });

  it("allowlists a user with multiple roles and a reporting manager", async () => {
    const user = userEvent.setup();
    const create = vi.mocked(userAdminApi.create);
    renderPage();

    await user.click(await screen.findByRole("button", { name: /allowlist user/i }));
    await user.type(screen.getByLabelText(/^full name$/i), "Priya Patel");
    await user.type(screen.getByLabelText(/^email$/i), "priya@example.com");
    await user.click(screen.getByRole("checkbox", { name: "Approver" }));
    await user.click(screen.getByLabelText(/reporting manager/i));
    await user.click(screen.getByRole("option", { name: /Morgan Manager/i }));
    await user.click(screen.getByRole("button", { name: /add to allowlist/i }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith({
        email: "priya@example.com",
        full_name: "Priya Patel",
        roles: ["employee", "approver"],
        manager_id: "manager-1",
      });
    });
  });

  it("edits a user and deactivates an active account", async () => {
    const user = userEvent.setup();
    const update = vi.mocked(userAdminApi.update);
    const deactivate = vi.mocked(userAdminApi.deactivate);
    renderPage();

    await user.click(await screen.findByRole("button", { name: /edit ana employee/i }));
    await user.clear(screen.getByLabelText(/^full name$/i));
    await user.type(screen.getByLabelText(/^full name$/i), "Ana Updated");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(update).toHaveBeenCalledWith(
        "employee-1",
        expect.objectContaining({
          full_name: "Ana Updated",
          roles: ["employee"],
          manager_id: "manager-1",
        }),
      );
    });

    await user.click(screen.getByRole("button", { name: /deactivate ana employee/i }));
    await waitFor(() => expect(deactivate).toHaveBeenCalledWith("employee-1"));
  });
});
