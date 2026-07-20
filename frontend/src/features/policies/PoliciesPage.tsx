import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Table, FilePdf, UploadSimple } from "@phosphor-icons/react";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { useAuth } from "../../auth/AuthContext";
import { isAdministrator } from "../../auth/permissions";
import { policiesApi, type Policy } from "../../lib/api";
import { PolicyAssistantPanel } from "./PolicyAssistantPanel";
import { PolicyForm } from "./PolicyForm";
import { PolicyUpload } from "./PolicyUpload";

function labelForStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function PoliciesPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = isAdministrator(user);

  const [formOpen, setFormOpen] = useState(false);
  const [extractDialogOpen, setExtractDialogOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [extractFile, setExtractFile] = useState<File | null>(null);

  const policies = useQuery({ queryKey: ["policies"], queryFn: policiesApi.list });

  const activatePolicy = useMutation({
    mutationFn: (policyId: string) => policiesApi.activate(policyId),
    onSuccess: (updatedPolicy) => {
      queryClient.setQueryData<Policy[]>(["policies"], (current) =>
        current?.map((policy) => (policy.id === updatedPolicy.id ? updatedPolicy : policy)) ?? [updatedPolicy],
      );
      queryClient.invalidateQueries({ queryKey: ["policies"] });
    },
  });

  const extractMutation = useMutation({
    mutationFn: (file: File) => policiesApi.extractAndApply(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setExtractDialogOpen(false);
      setExtractFile(null);
    },
  });

  const openCreate = () => {
    setEditingPolicy(null);
    setFormOpen(true);
  };

  const openEdit = (policy: Policy) => {
    setEditingPolicy(policy);
    setFormOpen(true);
  };

  const handleDocumentUploaded = (updatedPolicy: Policy) => {
    queryClient.setQueryData<Policy[]>(["policies"], (current) =>
      current?.map((policy) => (policy.id === updatedPolicy.id ? { ...policy, ...updatedPolicy } : policy)) ?? [updatedPolicy],
    );
    void queryClient.invalidateQueries({ queryKey: ["policies"] });
  };

  return (
    <main className="repl-page">
      <header className="page-header">
        <div>
          <p className="repl-eyebrow">Policy management</p>
          <h1 className="repl-title">Reimbursement policies</h1>
          <p className="repl-lede">Corporate reimbursement limits and policy documents. {!isAdmin && "Contact your administrator to make changes."}</p>
        </div>
        {isAdmin && (
          <div className="flex flex-wrap items-center gap-2">
            <a
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              download="policy_rules_template.xlsx"
              href={policiesApi.getExcelTemplateUrl()}
            >
              <Table size={16} /> Excel Template
            </a>
            <a
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              download="policy_rules_template.pdf"
              href={policiesApi.getPdfTemplateUrl()}
            >
              <FilePdf size={16} /> PDF Template
            </a>
            <Button onClick={() => setExtractDialogOpen(true)} variant="outline">
              <UploadSimple className="mr-1.5" size={16} /> Extract Policy
            </Button>
            <Button onClick={openCreate}>New policy</Button>
          </div>
        )}
      </header>

      {policies.isLoading && <LoadingState label="Loading policies" />}
      {policies.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load policies.</p>}
      {policies.data?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No policy versions yet. {isAdmin ? "Create or extract the first one to set reimbursement limits." : "Policies are managed by administrators."}
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {policies.data?.map((policy) => {
          const isActivated = ["active", "scheduled"].includes(policy.status.toLowerCase());
          return (
            <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900" key={policy.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950 dark:text-white">{policy.name}</h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {policy.version_label} · Effective {policy.effective_from}
                  </p>
                </div>
                <span className={isActivated ? "rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-950 dark:text-orange-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>
                  {labelForStatus(policy.status)}
                </span>
              </div>
              
              <div className="mt-4 space-y-2">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Category Rules ({policy.rules.length})</p>
                {policy.rules.length > 0 ? (
                  <div className="max-h-48 overflow-y-auto divide-y divide-slate-100 rounded-lg border border-slate-100 bg-slate-50/50 text-xs dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-950/40">
                    {policy.rules.map((rule, idx) => (
                      <div className="flex items-center justify-between p-2.5" key={rule.id || idx}>
                        <span className="font-medium text-slate-800 dark:text-slate-200">{rule.category_name || "General"}</span>
                        <div className="flex gap-2 text-slate-600 dark:text-slate-400">
                          {rule.max_per_day != null && <span>Max: ${rule.max_per_day}/day</span>}
                          {rule.receipt_required_above != null && <span>Receipt &gt; ${rule.receipt_required_above}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No category rules defined for this policy.</p>
                )}
              </div>

              {isAdmin && (
                <div className="mt-5 flex flex-wrap gap-2">
                  <Button disabled={isActivated} onClick={() => openEdit(policy)} variant="outline">
                    Edit version
                  </Button>
                  {!isActivated && (
                    <Button
                      aria-label={`Activate ${policy.name}`}
                      disabled={activatePolicy.isPending}
                      onClick={() => activatePolicy.mutate(policy.id)}
                    >
                      Activate
                    </Button>
                  )}
                </div>
              )}

              <div className="mt-5">
                {isAdmin ? (
                  <PolicyUpload currentDocumentUrl={policy.document_url} onUploaded={handleDocumentUploaded} policyId={policy.id} />
                ) : policy.document_url ? (
                  <a href={policy.document_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-brand-green-dark)] hover:underline">
                    <FilePdf size={16} /> Download Policy Document
                  </a>
                ) : null}
              </div>
              <div className="mt-5">
                <PolicyAssistantPanel policy={policy} />
              </div>
            </article>
          );
        })}
      </div>

      <PolicyForm onOpenChange={setFormOpen} open={formOpen} policy={editingPolicy} />

      <Dialog onOpenChange={setExtractDialogOpen} open={extractDialogOpen}>
        <DialogContent>
          <DialogTitle>Extract Policies from File</DialogTitle>
          <DialogDescription>Upload an Excel (.xlsx, .csv) or PDF (.pdf) document to automatically extract and apply category policy rules.</DialogDescription>
          <div className="mt-4 space-y-4">
            <input
              accept=".xlsx,.csv,.pdf"
              className="w-full text-sm text-slate-500 file:mr-4 file:rounded-md file:border-0 file:bg-orange-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-orange-700 hover:file:bg-orange-100 dark:file:bg-orange-950 dark:file:text-orange-300"
              onChange={(e) => setExtractFile(e.target.files?.[0] || null)}
              type="file"
            />
            {extractMutation.isError && (
              <p className="text-xs text-red-600">Failed to extract policy rules. Please check the file format.</p>
            )}
            <div className="flex justify-end gap-2">
              <Button onClick={() => setExtractDialogOpen(false)} variant="outline">Cancel</Button>
              <Button
                disabled={!extractFile || extractMutation.isPending}
                onClick={() => extractFile && extractMutation.mutate(extractFile)}
              >
                {extractMutation.isPending ? "Extracting…" : "Extract & Apply Rules"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}

