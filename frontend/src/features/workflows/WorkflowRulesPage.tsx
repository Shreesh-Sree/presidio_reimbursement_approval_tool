import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { ConfirmDialog } from "../../components/ui/confirm-dialog";
import { workflowsApi, type WorkflowApprovalStep, type WorkflowRule } from "../../lib/api";
import { WorkflowRuleForm } from "./WorkflowRuleForm";

function thresholdLabel(rule: WorkflowRule) {
  const { min_total: minTotal, max_total: maxTotal, currency_code: currency } = rule.conditions;
  const suffix = currency ? ` ${currency}` : "";
  if (minTotal != null && maxTotal != null) return `${minTotal.toLocaleString()}–${maxTotal.toLocaleString()}${suffix}`;
  if (minTotal != null) return `${minTotal.toLocaleString()}${suffix} and above`;
  if (maxTotal != null) return `Up to ${maxTotal.toLocaleString()}${suffix}`;
  return "All report totals";
}

function stepLabel(step: WorkflowApprovalStep) {
  if (step.manager_level) return `Manager level ${step.manager_level}`;
  if (step.user_id) return "Named approver";
  return step.role_code ? `${step.role_code} role` : "Approver";
}

export function WorkflowRulesPage() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<WorkflowRule | null>(null);
  const [deletingRule, setDeletingRule] = useState<WorkflowRule | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const rules = useQuery({
    queryKey: ["workflow-rules", showArchived],
    queryFn: () => showArchived ? workflowsApi.listWithArchived() : workflowsApi.list(),
  });
  const removeRule = useMutation({
    mutationFn: workflowsApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workflow-rules"] }),
  });
  const restoreRule = useMutation({
    mutationFn: workflowsApi.restore,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workflow-rules"] }),
  });
  const activeRules = (rules.data ?? []).filter((rule) => !rule.is_deleted);
  const archivedRules = (rules.data ?? []).filter((rule) => rule.is_deleted);

  const openCreate = () => {
    setEditingRule(null);
    setFormOpen(true);
  };

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Approval management</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Approval workflows</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Escalate reports to the appropriate manager, named reviewer, or approval role.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setShowArchived((value) => !value)} variant="outline">
            {showArchived ? "Hide archived" : "Archived workflows"}
          </Button>
          <Button onClick={openCreate}>New workflow rule</Button>
        </div>
      </header>

      {rules.isLoading && <LoadingState label="Loading workflow rules" />}
      {rules.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load workflow rules.</p>}
      {activeRules.length === 0 && !rules.isLoading && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No custom workflow rules yet. Reports continue to use their direct manager by default.
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {activeRules.map((rule) => (
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900" key={rule.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950 dark:text-white">{rule.name}</h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Priority {rule.priority} · {thresholdLabel(rule)}</p>
              </div>
              <span className={rule.is_active ? "rounded-full bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-700 dark:bg-orange-950 dark:text-orange-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>
                {rule.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <ol className="mt-4 space-y-1 text-sm text-slate-700 dark:text-slate-200">
              {rule.approval_chain.map((step, index) => <li key={`${rule.id}-${index}`}>{index + 1}. {stepLabel(step)}</li>)}
            </ol>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={() => { setEditingRule(rule); setFormOpen(true); }} variant="outline">Edit</Button>
              <Button
                aria-label={`Archive ${rule.name}`}
                disabled={removeRule.isPending}
                onClick={() => setDeletingRule(rule)}
                variant="ghost"
              >
                Archive
              </Button>
            </div>
          </article>
        ))}
      </div>
      {showArchived && (
        <section className="overflow-hidden rounded-2xl border border-amber-400/30 bg-amber-50/60 dark:border-amber-300/20 dark:bg-amber-950/15">
          <header className="border-b border-amber-400/25 px-5 py-4 dark:border-amber-300/15">
            <p className="text-sm font-bold text-amber-900 dark:text-amber-100">Archived workflows</p>
            <p className="mt-1 text-sm text-amber-800/80 dark:text-amber-100/70">Archived rules are excluded from approval routing. Restore one to make it available again.</p>
          </header>
          <div className="divide-y divide-amber-400/20 dark:divide-amber-300/15">
            {archivedRules.length ? archivedRules.map((rule) => (
              <article className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between" key={`archived-${rule.id}`}>
                <div>
                  <p className="font-semibold text-slate-950 dark:text-white">{rule.name}</p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Priority {rule.priority} · {thresholdLabel(rule)}</p>
                </div>
                <Button disabled={restoreRule.isPending} onClick={() => restoreRule.mutate(rule.id)} variant="outline">Restore workflow</Button>
              </article>
            )) : <p className="px-5 py-6 text-sm text-slate-600 dark:text-slate-300">There are no archived workflow rules.</p>}
          </div>
        </section>
      )}

      <WorkflowRuleForm onOpenChange={setFormOpen} open={formOpen} rule={editingRule} />
      <ConfirmDialog
        confirmLabel="Archive"
        description={`Archive ${deletingRule?.name ?? "this workflow rule"}? It will no longer route approvals, and an administrator can restore it later.`}
        onConfirm={() => deletingRule && removeRule.mutate(deletingRule.id, { onSuccess: () => setDeletingRule(null) })}
        onOpenChange={(open) => !open && setDeletingRule(null)}
        open={Boolean(deletingRule)}
        title="Archive workflow rule"
      />
    </main>
  );
}
