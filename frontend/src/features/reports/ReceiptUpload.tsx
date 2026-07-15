import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { getApiErrorMessage, reportsApi, type Receipt } from "../../lib/api";

type ReceiptUploadProps = {
  itemId: string;
  disabled?: boolean;
  onUploadComplete?: (receipt: Receipt) => void;
};

const maximumReceiptSize = 10 * 1024 * 1024;

function validateReceipt(file: File) {
  if (file.type !== "application/pdf" && !file.type.startsWith("image/")) {
    return "Receipts must be an image or PDF file.";
  }
  if (file.size > maximumReceiptSize) {
    return "Receipts must be 10 MB or smaller.";
  }
  return null;
}

export function ReceiptUpload({ itemId, disabled = false, onUploadComplete }: ReceiptUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const uploadReceipt = useMutation({
    mutationFn: (file: File) => reportsApi.uploadReceipt(itemId, file),
    onMutate: () => setFileError(null),
    onSuccess: (receipt) => {
      onUploadComplete?.(receipt);
      setSelectedFile(null);
    },
    onError: (error) => setFileError(getApiErrorMessage(error, "Upload failed. Please try again.")),
  });

  return (
    <div className="space-y-2">
      <Label htmlFor={`receipt-${itemId}`}>Upload receipt</Label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          accept="image/*,application/pdf"
          disabled={disabled || uploadReceipt.isPending}
          id={`receipt-${itemId}`}
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            const validationError = file ? validateReceipt(file) : null;
            setSelectedFile(validationError ? null : file);
            setFileError(validationError);
          }}
          type="file"
        />
        <Button
          disabled={disabled || !selectedFile || uploadReceipt.isPending}
          onClick={() => selectedFile && uploadReceipt.mutate(selectedFile)}
          variant="outline"
        >
          {uploadReceipt.isPending ? "Uploading…" : "Upload"}
        </Button>
      </div>
      {selectedFile && <p className="text-xs text-slate-600 dark:text-slate-300">{selectedFile.name}</p>}
      {fileError && <p className="text-sm text-rose-600" role="alert">{fileError}</p>}
    </div>
  );
}
