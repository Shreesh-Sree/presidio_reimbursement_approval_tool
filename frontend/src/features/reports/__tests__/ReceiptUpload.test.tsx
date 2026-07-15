import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reportsApi } from "../../../lib/api";
import { ReceiptUpload } from "../ReceiptUpload";

function renderUpload(onUploadComplete?: Parameters<typeof ReceiptUpload>[0]["onUploadComplete"]) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReceiptUpload itemId="item-1" onUploadComplete={onUploadComplete} />
    </QueryClientProvider>,
  );
}

describe("ReceiptUpload", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders an accessible file input", () => {
    renderUpload();
    expect(screen.getByLabelText(/upload receipt/i)).toHaveAttribute("type", "file");
  });

  it("uploads the selected receipt", async () => {
    const user = userEvent.setup();
    const uploadedReceipt = { id: "receipt-1", url: "https://files.example/receipt.pdf", file_name: "receipt.pdf" };
    const upload = vi.spyOn(reportsApi, "uploadReceipt").mockResolvedValue(uploadedReceipt);
    const onUploadComplete = vi.fn();
    renderUpload(onUploadComplete);
    const file = new File(["receipt"], "receipt.pdf", { type: "application/pdf" });

    fireEvent.change(screen.getByLabelText(/upload receipt/i), { target: { files: [file] } });
    expect(screen.getByText("receipt.pdf")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^upload$/i }));

    await waitFor(() => expect(upload).toHaveBeenCalledWith("item-1", file));
    expect(onUploadComplete).toHaveBeenCalledWith(uploadedReceipt);
  });

  it("shows an error when the upload fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(reportsApi, "uploadReceipt").mockRejectedValue(new Error("Upload failed"));
    renderUpload();
    const file = new File(["receipt"], "receipt.pdf", { type: "application/pdf" });

    fireEvent.change(screen.getByLabelText(/upload receipt/i), { target: { files: [file] } });
    await user.click(screen.getByRole("button", { name: /^upload$/i }));

    expect(await screen.findByText(/upload failed/i)).toBeInTheDocument();
  });

  it("rejects unsupported files before attempting an upload", () => {
    const upload = vi.spyOn(reportsApi, "uploadReceipt");
    renderUpload();
    const file = new File(["not a receipt"], "notes.txt", { type: "text/plain" });

    fireEvent.change(screen.getByLabelText(/upload receipt/i), { target: { files: [file] } });

    expect(screen.getByText(/receipts must be an image or pdf file/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^upload$/i })).toBeDisabled();
    expect(upload).not.toHaveBeenCalled();
  });
});
