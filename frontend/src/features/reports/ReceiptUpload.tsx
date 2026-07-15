import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { reportsApi, type Receipt } from "../../lib/api";

type ReceiptUploadProps = {
  itemId: string;
  disabled?: boolean;
  onUploadComplete?: (receipt: Receipt) => void;
};

export function ReceiptUpload({ itemId, disabled = false, onUploadComplete }: ReceiptUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const uploadReceipt = useMutation({
    mutationFn: (file: File) => reportsApi.uploadReceipt(itemId, file),
    onSuccess: (receipt) => {
      onUploadComplete?.(receipt);
      setSelectedFile(null);
    },
  });

  return (
    <div className="space-y-2">
      <Label htmlFor={`receipt-${itemId}`}>Upload receipt</Label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          accept="image/*,application/pdf"
          disabled={disabled || uploadReceipt.isPending}
          id={`receipt-${itemId}`}
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
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
      {uploadReceipt.isError && <p className="text-sm text-rose-600">Upload failed. Please try again.</p>}
    </div>
  );
}
