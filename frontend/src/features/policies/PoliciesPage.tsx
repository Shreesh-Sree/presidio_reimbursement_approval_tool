import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { policiesApi, type Policy } from "../../lib/api";
import { PolicyForm } from "./PolicyForm";
import { PolicyUpload } from "./PolicyUpload";

function labelForStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function PoliciesPage() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
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
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Policy management</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Reimbursement policies</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Maintain versioned limits and activate the policy in effect.</p>
        </div>
        <Button onClick={openCreate}>New policy</Button>
      </header>

      {policies.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading policies…</p>}
      {policies.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load policies.</p>}
      {policies.data?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No policy versions yet. Create the first one to set reimbursement limits.
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {policies.data?.map((policy) => {
          const isActive = policy.status.toLowerCase() === "active";
          return (
            <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900" key={policy.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950 dark:text-white">{policy.name}</h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {policy.version_label} · Effective {policy.effective_from}
                  </p>
                </div>
                <span className={isActive ? "rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>
                  {labelForStatus(policy.status)}
                </span>
              </div>
              <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">
                {policy.rules.length} {policy.rules.length === 1 ? "rule" : "rules"}
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button onClick={() => openEdit(policy)} variant="outline">
                  Edit version
                </Button>
                {!isActive && (
                  <Button
                    aria-label={`Activate ${policy.name}`}
                    disabled={activatePolicy.isPending}
                    onClick={() => activatePolicy.mutate(policy.id)}
                  >
                    Activate
                  </Button>
                )}
              </div>
              <div className="mt-5">
                <PolicyUpload currentDocumentUrl={policy.document_url} onUploaded={handleDocumentUploaded} policyId={policy.id} />
              </div>
            </article>
          );
        })}
      </div>

      <PolicyForm onOpenChange={setFormOpen} open={formOpen} policy={editingPolicy} />
    </main>
  );
}
