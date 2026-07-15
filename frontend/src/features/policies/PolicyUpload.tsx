import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { policiesApi, type Policy } from "../../lib/api";

type PolicyUploadProps = {
  policyId: string;
  onUploaded?: (policy: Policy) => void;
};

export function PolicyUpload({ policyId, onUploaded }: PolicyUploadProps) {
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
          accept="application/pdf,.doc,.docx"
          id={`policy-document-${policyId}`}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          type="file"
        />
        <Button disabled={!file || upload.isPending} onClick={() => file && upload.mutate(file)} variant="outline">
          {upload.isPending ? "Uploading…" : "Upload document"}
        </Button>
      </div>
      {upload.isError && <p className="text-sm text-rose-600">Unable to upload the document. Please try again.</p>}
    </div>
  );
}
