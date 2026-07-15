import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../../../auth/AuthContext";
import { authApi, setApiToken } from "../../../lib/api";
import { BootstrapPage } from "../BootstrapPage";

function renderBootstrapPage() {
  return render(
    <MemoryRouter initialEntries={["/bootstrap"]}>
      <AuthProvider>
        <Routes>
          <Route path="/bootstrap" element={<BootstrapPage />} />
          <Route path="/policies" element={<p>Policy setup destination</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("BootstrapPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    setApiToken(null);
    vi.spyOn(authApi, "bootstrap").mockResolvedValue({
      access_token: "bootstrap-token",
      token_type: "bearer",
      user: {
        user_id: "admin-1",
        email: "admin@acme.example",
        roles: ["administrator"],
        permissions: ["*"],
      },
    });
  });

  it("creates the first administrator, stores the session, and opens policy setup", async () => {
    const user = userEvent.setup();
    const bootstrap = vi.mocked(authApi.bootstrap);
    renderBootstrapPage();

    await user.clear(screen.getByLabelText(/organization name/i));
    await user.type(screen.getByLabelText(/organization name/i), "Acme Travel");
    await user.clear(screen.getByLabelText(/organization code/i));
    await user.type(screen.getByLabelText(/organization code/i), "acme travel");
    await user.type(screen.getByLabelText(/^full name$/i), "Avery Admin");
    await user.type(screen.getByLabelText(/^email$/i), "admin@acme.example");
    await user.type(screen.getByLabelText(/^password$/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "SecurePass123!");
    await user.click(screen.getByRole("button", { name: /create organization and continue/i }));

    await waitFor(() => expect(bootstrap).toHaveBeenCalledWith({
      organization_name: "Acme Travel",
      organization_code: "ACME_TRAVEL",
      department_name: "General",
      department_code: "GENERAL",
      full_name: "Avery Admin",
      email: "admin@acme.example",
      password: "SecurePass123!",
    }));
    expect(window.localStorage.getItem("access_token")).toBe("bootstrap-token");
    expect(await screen.findByText("Policy setup destination")).toBeInTheDocument();
  });

  it("prevents submission when passwords do not match", async () => {
    const user = userEvent.setup();
    const bootstrap = vi.mocked(authApi.bootstrap);
    renderBootstrapPage();

    await user.type(screen.getByLabelText(/^full name$/i), "Avery Admin");
    await user.type(screen.getByLabelText(/^email$/i), "admin@acme.example");
    await user.type(screen.getByLabelText(/^password$/i), "SecurePass123!");
    await user.type(screen.getByLabelText(/confirm password/i), "DifferentPass123!");
    await user.click(screen.getByRole("button", { name: /create organization and continue/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(bootstrap).not.toHaveBeenCalled();
  });
});
