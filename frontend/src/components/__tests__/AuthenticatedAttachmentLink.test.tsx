import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { attachmentsApi } from "../../lib/api";
import { AuthenticatedAttachmentLink } from "../AuthenticatedAttachmentLink";

function renderLink(url = "/api/attachments/receipt-1/download") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthenticatedAttachmentLink url={url}>View receipt</AuthenticatedAttachmentLink>
    </QueryClientProvider>,
  );
}

describe("AuthenticatedAttachmentLink", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(attachmentsApi, "download").mockResolvedValue(new Blob(["receipt"], { type: "application/pdf" }));
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:receipt") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  });

  it("uses the authenticated API client for a protected attachment", async () => {
    const user = userEvent.setup();
    renderLink();

    await user.click(screen.getByRole("button", { name: /view receipt/i }));

    await waitFor(() => expect(attachmentsApi.download).toHaveBeenCalledWith("/api/attachments/receipt-1/download"));
  });

  it("keeps an externally hosted document as a normal link", () => {
    renderLink("https://files.example.test/policy.pdf");

    expect(screen.getByRole("link", { name: /view receipt/i })).toHaveAttribute("href", "https://files.example.test/policy.pdf");
  });
});
