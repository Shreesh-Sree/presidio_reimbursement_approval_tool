import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EmailSignUpForm } from "../EmailSignUpForm";

const mocks = vi.hoisted(() => ({ signUp: vi.fn(), post: vi.fn() }));

vi.mock("../../../auth/supabase", () => ({ supabase: { auth: { signUp: mocks.signUp } } }));
vi.mock("../../../lib/api", () => ({
  apiClient: { post: mocks.post },
  getApiErrorMessage: (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback,
}));

afterEach(() => vi.resetAllMocks());

describe("EmailSignUpForm", () => {
  it("creates the request through the configured API client", async () => {
    const user = userEvent.setup();
    mocks.signUp.mockResolvedValue({ error: null });
    mocks.post.mockResolvedValue({ data: {} });
    render(<EmailSignUpForm />);

    await user.type(screen.getByLabelText("Full Name"), "Pending User");
    await user.type(screen.getByLabelText("Email"), "pending@example.com");
    await user.type(screen.getByLabelText("Password"), "safe-password");
    await user.click(screen.getByRole("button", { name: "Request Access" }));

    expect(await screen.findByText("Request Submitted")).toBeInTheDocument();
    expect(mocks.post).toHaveBeenCalledWith("/access-requests", {
      email: "pending@example.com",
      full_name: "Pending User",
    });
  });
});
