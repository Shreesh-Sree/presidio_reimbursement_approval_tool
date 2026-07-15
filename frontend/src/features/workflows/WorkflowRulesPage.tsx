import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
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
  const rules = useQuery({ queryKey: ["workflow-rules"], queryFn: workflowsApi.list });
  const removeRule = useMutation({
    mutationFn: workflowsApi.remove,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workflow-rules"] }),
  });

  const openCreate = () => {
    setEditingRule(null);
    setFormOpen(true);
  };

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Approval management</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Approval workflows</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Escalate reports to the appropriate manager, named reviewer, or approval role.</p>
        </div>
        <Button onClick={openCreate}>New workflow rule</Button>
      </header>

      {rules.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading workflow rules…</p>}
      {rules.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load workflow rules.</p>}
      {rules.data?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No custom workflow rules yet. Reports continue to use their direct manager by default.
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {rules.data?.map((rule) => (
          <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900" key={rule.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950 dark:text-white">{rule.name}</h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Priority {rule.priority} · {thresholdLabel(rule)}</p>
              </div>
              <span className={rule.is_active ? "rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" : "rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200"}>
                {rule.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <ol className="mt-4 space-y-1 text-sm text-slate-700 dark:text-slate-200">
              {rule.approval_chain.map((step, index) => <li key={`${rule.id}-${index}`}>{index + 1}. {stepLabel(step)}</li>)}
            </ol>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={() => { setEditingRule(rule); setFormOpen(true); }} variant="outline">Edit</Button>
              <Button
                aria-label={`Delete ${rule.name}`}
                disabled={removeRule.isPending}
                onClick={() => {
                  if (window.confirm(`Delete ${rule.name}?`)) removeRule.mutate(rule.id);
                }}
                variant="ghost"
              >
                Delete
              </Button>
            </div>
          </article>
        ))}
      </div>

      <WorkflowRuleForm onOpenChange={setFormOpen} open={formOpen} rule={editingRule} />
    </main>
  );
}
