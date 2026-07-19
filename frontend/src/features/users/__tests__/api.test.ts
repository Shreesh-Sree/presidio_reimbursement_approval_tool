import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../../lib/api";
import { userAdminApi } from "../api";

describe("userAdminApi", () => {
  afterEach(() => vi.restoreAllMocks());

  it("does not send Supabase-managed email addresses when updating a user", async () => {
    const patch = vi.spyOn(apiClient, "patch").mockResolvedValue({
      data: {
        id: "employee-1",
        email: "employee@example.com",
        full_name: "Employee Example",
        status: "active",
        roles: ["employee"],
      },
    } as never);

    await userAdminApi.update("employee-1", {
      email: "employee@example.com",
      full_name: "Employee Example",
      roles: ["employee"],
      manager_id: null,
      department_id: "department-1",
    });

    expect(patch).toHaveBeenCalledWith("/users/employee-1", {
      full_name: "Employee Example",
      roles: ["employee"],
      manager_id: null,
      department_id: "department-1",
    });
  });
});
