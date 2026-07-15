import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { reportsApi, type Report, type ReportLineItem, type ReportLineItemInput } from "../../lib/api";
import { LineItemRow } from "./LineItemRow";

type ReportEditorProps = {
  reportId?: string;
};

function normaliseItem(item: ReportLineItem): ReportLineItem {
  return { ...item, amount: Number(item.amount) || 0 };
}

function requestForItem(item: ReportLineItem): ReportLineItemInput {
  const {
    id: _id,
    receipt: _receipt,
    receipt_url: _receiptUrl,
    is_policy_violated: _isPolicyViolated,
    violation_reason: _violationReason,
    policy_violation_reason: _policyViolationReason,
    ...request
  } = item;
  return request;
}

function displayStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ReportEditor({ reportId }: ReportEditorProps) {
  const params = useParams();
  const id = reportId ?? params.reportId;
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [items, setItems] = useState<ReportLineItem[]>([]);
  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const reportQuery = useQuery({
    queryKey: ["report", id],
    queryFn: () => reportsApi.get(id as string),
    enabled: Boolean(id),
  });
  const itemQuery = useQuery({
    queryKey: ["report", id, "items"],
    queryFn: () => reportsApi.listItems(id as string),
    enabled: Boolean(id),
  });
  const report = reportQuery.data;

  useEffect(() => {
    if (!report) return;
    const reportItems = report.line_items ?? report.items;
    const source = reportItems && reportItems.length > 0 ? reportItems : itemQuery.data ?? reportItems ?? [];
    setTitle(report.title);
    setItems(source.map(normaliseItem));
  }, [itemQuery.data, report]);

  const saveReport = useMutation({
    mutationFn: (nextTitle: string) => reportsApi.update(id as string, { title: nextTitle }),
    onSuccess: (updatedReport) => {
      queryClient.setQueryData<Report>(["report", id], (current) => ({ ...current, ...updatedReport }));
    },
  });
  const saveItem = useMutation({
    mutationFn: async (item: ReportLineItem) => {
      if (item.id.startsWith("new-")) return reportsApi.addItem(id as string, requestForItem(item));
      return reportsApi.updateItem(id as string, item.id, requestForItem(item));
    },
    onMutate: (item) => setSavingItemId(item.id),
    onSuccess: (savedItem, originalItem) => {
      setItems((current) => current.map((item) => (item.id === originalItem.id ? normaliseItem({ ...originalItem, ...savedItem }) : item)));
      queryClient.invalidateQueries({ queryKey: ["report", id, "items"] });
    },
    onSettled: () => setSavingItemId(null),
  });
  const removeItem = useMutation({
    mutationFn: (itemId: string) => reportsApi.removeItem(id as string, itemId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["report", id, "items"] }),
  });
  const submitReport = useMutation({
    mutationFn: () => reportsApi.submit(id as string),
    onSuccess: (updatedReport) => {
      queryClient.setQueryData<Report>(["report", id], (current) => ({ ...current, ...updatedReport }));
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
  const withdrawReport = useMutation({
    mutationFn: () => reportsApi.withdraw(id as string),
    onSuccess: (updatedReport) => {
      queryClient.setQueryData<Report>(["report", id], (current) => ({ ...current, ...updatedReport }));
      queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });

  const violationMessages = useMemo(() => {
    const messages = items
      .filter((item) => item.is_policy_violated || item.violation_reason || item.policy_violation_reason)
      .map((item) => item.violation_reason ?? item.policy_violation_reason ?? "A line item violates the active policy.");
    return Array.from(new Set([...(report?.violations ?? []), ...messages]));
  }, [items, report?.violations]);
  const total = useMemo(() => items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0), [items]);
  const isDraft = report?.status.toLowerCase() === "draft";
  const canSubmit = isDraft && violationMessages.length === 0;

  if (!id) return <main className="p-6 text-sm text-rose-700">A report ID is required.</main>;
  if (reportQuery.isLoading) return <main className="p-6 text-sm text-slate-600 dark:text-slate-300">Loading report…</main>;
  if (reportQuery.isError || !report) return <main className="p-6 text-sm text-rose-700">Unable to load this report.</main>;

  const addLineItem = () => {
    setItems((current) => [
      ...current,
      {
        id: `new-${Date.now()}-${current.length}`,
        amount: 0,
        description: "",
        currency: report.currency ?? "USD",
      },
    ]);
  };

  const deleteLineItem = (item: ReportLineItem) => {
    if (item.id.startsWith("new-")) {
      setItems((current) => current.filter((currentItem) => currentItem.id !== item.id));
      return;
    }
    setItems((current) => current.filter((currentItem) => currentItem.id !== item.id));
    removeItem.mutate(item.id);
  };

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-start lg:justify-between dark:border-slate-800">
        <div className="w-full max-w-xl space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Expense report</p>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">{displayStatus(report.status)}</span>
          </div>
          <Label htmlFor="report-title">Report title</Label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input disabled={!isDraft} id="report-title" onChange={(event) => setTitle(event.target.value)} value={title} />
            {isDraft && <Button disabled={saveReport.isPending || title.trim() === ""} onClick={() => saveReport.mutate(title)}>Save draft</Button>}
          </div>
          {saveReport.isError && <p className="text-sm text-rose-600">Unable to save the report title.</p>}
        </div>
        <div className="rounded-lg bg-slate-100 px-4 py-3 text-right dark:bg-slate-800">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-600 dark:text-slate-300">Live total</p>
          <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">Total: {new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(total)}</p>
        </div>
      </header>

      {violationMessages.length > 0 && (
        <section aria-live="polite" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100" role="alert">
          <h2 className="font-semibold">Submission blocked by policy violations</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {violationMessages.map((message) => <li key={message}>{message}</li>)}
          </ul>
        </section>
      )}

      <section aria-labelledby="line-items-heading" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white" id="line-items-heading">Line items</h2>
            <p className="text-sm text-slate-600 dark:text-slate-300">Add expenses, link receipts, and review any policy flags before submitting.</p>
          </div>
          <Button disabled={!isDraft} onClick={addLineItem}>Add line item</Button>
        </div>
        {items.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No line items yet.</p>}
        <div className="space-y-4">
          {items.map((item, index) => (
            <LineItemRow
              disabled={!isDraft}
              index={index}
              isSaving={savingItemId === item.id}
              item={item}
              key={item.id}
              onDelete={deleteLineItem}
              onSave={(nextItem) => saveItem.mutate(nextItem)}
              onUpdate={(nextItem) => setItems((current) => current.map((item) => (item.id === nextItem.id ? nextItem : item)))}
            />
          ))}
        </div>
      </section>

      <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 pt-5 sm:flex-row sm:justify-end dark:border-slate-800">
        {report.status.toLowerCase() === "submitted" && (
          <Button disabled={withdrawReport.isPending} onClick={() => withdrawReport.mutate()} variant="outline">
            {withdrawReport.isPending ? "Withdrawing…" : "Withdraw report"}
          </Button>
        )}
        {isDraft && (
          <Button disabled={!canSubmit || submitReport.isPending} onClick={() => submitReport.mutate()}>
            {submitReport.isPending ? "Submitting…" : "Submit report"}
          </Button>
        )}
      </footer>
      {submitReport.isError && <p className="text-sm text-rose-600">Unable to submit this report.</p>}
      {withdrawReport.isError && <p className="text-sm text-rose-600">Unable to withdraw this report.</p>}
    </main>
  );
}
