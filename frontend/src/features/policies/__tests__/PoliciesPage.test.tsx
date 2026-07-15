import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { policiesApi, type Policy } from "../../../lib/api";
import { PoliciesPage } from "../PoliciesPage";

const draftPolicy: Policy = {
  id: "policy-1",
  name: "FY26 travel",
  version_label: "v1",
  effective_from: "2026-08-01",
  status: "draft",
  rules: [],
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PoliciesPage />
    </QueryClientProvider>,
  );
}

describe("PoliciesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(policiesApi, "list").mockResolvedValue([draftPolicy]);
    vi.spyOn(policiesApi, "create").mockResolvedValue(draftPolicy);
    vi.spyOn(policiesApi, "activate").mockResolvedValue({ ...draftPolicy, status: "active" });
    vi.spyOn(policiesApi, "uploadDocument").mockResolvedValue(draftPolicy);
  });

  it("lists policy versions", async () => {
    renderPage();

    expect(await screen.findByText("FY26 travel")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("creates a policy version", async () => {
    const user = userEvent.setup();
    const create = vi.mocked(policiesApi.create);
    renderPage();

    await user.click(await screen.findByRole("button", { name: /new policy/i }));
    await user.type(screen.getByLabelText(/^name$/i), "FY27 travel");
    await user.type(screen.getByLabelText(/version label/i), "v2");
    fireEvent.change(screen.getByLabelText(/effective from/i), { target: { value: "2027-01-01" } });
    await user.click(screen.getByRole("button", { name: /save policy/i }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "FY27 travel",
          version_label: "v2",
          effective_from: "2027-01-01",
        }),
      );
    });
  });

  it("activates a draft policy", async () => {
    const user = userEvent.setup();
    const activate = vi.mocked(policiesApi.activate);
    renderPage();

    await user.click(await screen.findByRole("button", { name: /activate fy26 travel/i }));

    await waitFor(() => expect(activate).toHaveBeenCalledWith("policy-1"));
  });

  it("uploads a document from the policy card and refreshes its document link", async () => {
    const user = userEvent.setup();
    const uploadedPolicy = { ...draftPolicy, document_url: "https://files.example/policies/fy26.pdf" };
    vi.mocked(policiesApi.list)
      .mockResolvedValueOnce([draftPolicy])
      .mockResolvedValue([uploadedPolicy]);
    const uploadDocument = vi.mocked(policiesApi.uploadDocument).mockResolvedValue(uploadedPolicy);
    renderPage();
    const file = new File(["policy"], "fy26.pdf", { type: "application/pdf" });

    fireEvent.change(await screen.findByLabelText(/supporting policy document/i), { target: { files: [file] } });
    await user.click(screen.getByRole("button", { name: /upload document/i }));

    await waitFor(() => expect(uploadDocument).toHaveBeenCalledWith("policy-1", file));
    expect(await screen.findByRole("link", { name: /view current document/i })).toHaveAttribute("href", uploadedPolicy.document_url);
  });
});
