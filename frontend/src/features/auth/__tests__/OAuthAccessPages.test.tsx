import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "../../../App";
import { AuthContext, type AuthContextType } from "../../../auth/AuthContext";
import { AccessDeniedPage } from "../AccessDeniedPage";
import { OAuthConfigurationPage } from "../OAuthConfigurationPage";

vi.mock("../../../auth/clerk", () => ({
  clerkJwtTemplate: "presidio-api",
  clerkPublishableKey: "",
  isClerkConfigured: false,
}));

const deniedContext: AuthContextType = {
  user: null,
  token: null,
  status: "access_denied",
  isLoading: false,
  isSignedIn: true,
  accessDenied: true,
  deniedEmail: "outside@example.com",
  error: null,
  logout: async () => undefined,
};

describe("OAuth access states", () => {
  it("shows the configuration state instead of a manual credential fallback", () => {
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(screen.getByRole("heading", { name: /oauth sign-in is not configured/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  });

  it("explains the required public Clerk configuration without exposing a secret", () => {
    render(<OAuthConfigurationPage />);

    expect(screen.getByRole("heading", { name: /oauth sign-in is not configured/i })).toBeInTheDocument();
    expect(screen.getByText("VITE_CLERK_PUBLISHABLE_KEY")).toBeInTheDocument();
    expect(screen.getByText(/do not place clerk secret keys/i)).toBeInTheDocument();
  });

  it("gives an allowlist-rejected OAuth user a clear message and a sign-out action", async () => {
    const user = userEvent.setup();
    const logout = vi.fn().mockResolvedValue(undefined);
    render(
      <AuthContext.Provider value={{ ...deniedContext, logout }}>
        <AccessDeniedPage />
      </AuthContext.Provider>,
    );

    expect(screen.getByRole("heading", { name: /you don.t have access yet/i })).toBeInTheDocument();
    expect(screen.getByText(/outside@example\.com/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /sign out/i }));
    await waitFor(() => expect(logout).toHaveBeenCalledOnce());
  });
});
