import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AuthenticatedAttachmentLink } from "../../components/AuthenticatedAttachmentLink";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { policiesApi, type Policy } from "../../lib/api";

type PolicyUploadProps = {
  policyId: string;
  currentDocumentUrl?: string | null;
  onUploaded?: (policy: Policy) => void;
};

export function PolicyUpload({ policyId, currentDocumentUrl, onUploaded }: PolicyUploadProps) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const upload = useMutation({
    mutationFn: (selectedFile: File) => policiesApi.uploadDocument(policyId, selectedFile),
    onSuccess: (policy) => {
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      onUploaded?.(policy);
      setFile(null);
    },
  });

  return (
    <div className="space-y-2 rounded-lg border border-dashed border-slate-300 p-4 dark:border-slate-700">
      <Label htmlFor={`policy-document-${policyId}`}>Supporting policy document</Label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          accept="application/pdf,.doc,.docx,.xls,.xlsx"
          id={`policy-document-${policyId}`}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          type="file"
        />
        <Button disabled={!file || upload.isPending} onClick={() => file && upload.mutate(file)} variant="outline">
          {upload.isPending ? "Uploading…" : "Upload document"}
        </Button>
      </div>
      {currentDocumentUrl && (
        <AuthenticatedAttachmentLink className="h-auto min-h-0 px-0 py-0 text-sm font-medium text-indigo-600 underline underline-offset-2 hover:bg-transparent dark:text-indigo-300" url={currentDocumentUrl}>View current document</AuthenticatedAttachmentLink>
      )}
      {upload.isError && <p className="text-sm text-rose-600">Unable to upload the document. Please try again.</p>}
    </div>
  );
}
