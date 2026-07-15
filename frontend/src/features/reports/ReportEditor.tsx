import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  categoriesApi,
  getApiErrorMessage,
  reportsApi,
  vendorsApi,
  type Report,
  type ReportLineItem,
  type ReportLineItemInput,
} from "../../lib/api";
import { LineItemRow } from "./LineItemRow";

type ReportEditorProps = {
  reportId?: string;
};

function normaliseItem(item: ReportLineItem): ReportLineItem {
  return {
    ...item,
    amount: Number(item.amount) || 0,
    currency: item.currency ?? item.currency_code,
    expense_date: item.expense_date?.slice(0, 10),
  };
}

function requestForItem(item: ReportLineItem): ReportLineItemInput {
  const merchantName = item.merchant_name?.trim();
  return {
    category_id: item.category_id ?? "",
    ...(item.vendor_id ? { vendor_id: item.vendor_id } : {}),
    ...(!item.vendor_id && merchantName ? { merchant_name: merchantName } : {}),
    amount: Number(item.amount) || 0,
    currency: (item.currency ?? item.currency_code ?? "USD").toUpperCase(),
    description: item.description.trim(),
    expense_date: item.expense_date?.slice(0, 10),
  };
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
  const [itemError, setItemError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
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
  const categoriesQuery = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
  const vendorsQuery = useQuery({ queryKey: ["vendors"], queryFn: vendorsApi.list });
  const report = reportQuery.data;

  useEffect(() => {
    if (!report) return;
    const reportItems = report.line_items ?? report.items;
    const source = itemQuery.data ?? reportItems ?? [];
    setTitle(report.title);
    setItems(source.map(normaliseItem));
  }, [itemQuery.data, report]);

  const refreshReport = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["report", id] }),
      queryClient.invalidateQueries({ queryKey: ["report", id, "items"] }),
      queryClient.invalidateQueries({ queryKey: ["reports"] }),
    ]);
  };

  const saveReport = useMutation({
    mutationFn: (nextTitle: string) => reportsApi.update(id as string, { title: nextTitle.trim() }),
    onMutate: () => setReportError(null),
    onSuccess: (updatedReport) => {
      queryClient.setQueryData<Report>(["report", id], (current) => ({ ...current, ...updatedReport }));
      void refreshReport();
    },
    onError: (error) => setReportError(getApiErrorMessage(error, "Unable to save the report title.")),
  });
  const saveItem = useMutation({
    mutationFn: async (item: ReportLineItem) => {
      const request = requestForItem(item);
      if (item.id.startsWith("new-")) return reportsApi.addItem(id as string, request);
      return reportsApi.updateItem(id as string, item.id, request);
    },
    onMutate: (item) => {
      setItemError(null);
      setSavingItemId(item.id);
    },
    onSuccess: (savedItem, originalItem) => {
      setItems((current) => current.map((item) => (
        item.id === originalItem.id ? normaliseItem({ ...originalItem, ...savedItem }) : item
      )));
      void refreshReport();
    },
    onError: (error) => setItemError(getApiErrorMessage(error, "Unable to save this line item.")),
    onSettled: () => setSavingItemId(null),
  });
  const removeItem = useMutation({
    mutationFn: (itemId: string) => reportsApi.removeItem(id as string, itemId),
    onMutate: () => setItemError(null),
    onSuccess: () => void refreshReport(),
    onError: async (error) => {
      setItemError(getApiErrorMessage(error, "Unable to delete this line item."));
      await refreshReport();
    },
  });
  const submitReport = useMutation({
    mutationFn: () => reportsApi.submit(id as string),
    onMutate: () => setSubmitError(null),
    onSuccess: (updatedReport) => {
      queryClient.setQueryData<Report>(["report", id], (current) => ({ ...current, ...updatedReport }));
      void refreshReport();
    },
    onError: async (error) => {
      setSubmitError(getApiErrorMessage(error, "Unable to submit this report."));
      await refreshReport();
    },
  });
  const withdrawReport = useMutation({
    mutationFn: () => reportsApi.withdraw(id as string),
    onMutate: () => setSubmitError(null),
    onSuccess: (updatedReport) => {
      queryClient.setQueryData<Report>(["report", id], (current) => ({ ...current, ...updatedReport }));
      void refreshReport();
    },
    onError: (error) => setSubmitError(getApiErrorMessage(error, "Unable to withdraw this report.")),
  });

  const violationMessages = useMemo(() => {
    const messages = items
      .filter((item) => item.is_policy_violated || item.violation_reason || item.policy_violation_reason)
      .map((item) => item.violation_reason ?? item.policy_violation_reason ?? "A line item violates the active policy.");
    return Array.from(new Set([...(report?.violations ?? []), ...messages]));
  }, [items, report?.violations]);
  const total = useMemo(() => items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0), [items]);
  const status = report?.status.toLowerCase() ?? "";
  const isEditable = status === "draft" || status === "sent_back";
  const canSubmit = isEditable && items.length > 0 && violationMessages.length === 0;

  if (!id) return <main className="p-6 text-sm text-rose-700">A report ID is required.</main>;
  if (reportQuery.isLoading) return <main className="p-6 text-sm text-slate-600 dark:text-slate-300">Loading report…</main>;
  if (reportQuery.isError || !report) return <main className="p-6 text-sm text-rose-700">Unable to load this report.</main>;

  const addLineItem = () => {
    setItemError(null);
    setItems((current) => [
      ...current,
      {
        id: `new-${Date.now()}-${current.length}`,
        amount: 0,
        description: "",
        currency: report.currency ?? "USD",
        expense_date: new Date().toISOString().slice(0, 10),
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
            <Input disabled={!isEditable} id="report-title" onChange={(event) => setTitle(event.target.value)} value={title} />
            {isEditable && <Button disabled={saveReport.isPending || title.trim() === ""} onClick={() => saveReport.mutate(title)}>{status === "sent_back" ? "Save changes" : "Save draft"}</Button>}
          </div>
          {reportError && <p className="text-sm text-rose-600" role="alert">{reportError}</p>}
        </div>
        <div className="rounded-lg bg-slate-100 px-4 py-3 text-right dark:bg-slate-800">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-600 dark:text-slate-300">Live total</p>
          <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">Total: {new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(total)}</p>
        </div>
      </header>

      {(categoriesQuery.isError || vendorsQuery.isError) && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100" role="alert">
          Categories or vendors could not be loaded. Refresh the page before saving a new line item.
        </section>
      )}

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
            <p className="text-sm text-slate-600 dark:text-slate-300">Add expenses, select their policy category, link receipts, and review any policy flags before submitting.</p>
          </div>
          <Button disabled={!isEditable} onClick={addLineItem}>Add line item</Button>
        </div>
        {items.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No line items yet. Add at least one complete item before submitting.</p>}
        {itemError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200" role="alert">{itemError}</p>}
        <div className="space-y-4">
          {items.map((item, index) => (
            <LineItemRow
              categories={categoriesQuery.data ?? []}
              disabled={!isEditable}
              index={index}
              isSaving={savingItemId === item.id}
              item={item}
              key={item.id}
              onDelete={deleteLineItem}
              onReceiptUploaded={() => void refreshReport()}
              onSave={(nextItem) => saveItem.mutate(nextItem)}
              onUpdate={(nextItem) => setItems((current) => current.map((item) => (item.id === nextItem.id ? nextItem : item)))}
              selectionsLoading={categoriesQuery.isLoading || vendorsQuery.isLoading}
              vendors={vendorsQuery.data ?? []}
            />
          ))}
        </div>
      </section>

      <footer className="flex flex-col-reverse gap-2 border-t border-slate-200 pt-5 sm:flex-row sm:justify-end dark:border-slate-800">
        {status === "submitted" && (
          <Button disabled={withdrawReport.isPending} onClick={() => withdrawReport.mutate()} variant="outline">
            {withdrawReport.isPending ? "Withdrawing…" : "Withdraw report"}
          </Button>
        )}
        {isEditable && (
          <Button disabled={!canSubmit || submitReport.isPending} onClick={() => submitReport.mutate()}>
            {submitReport.isPending ? "Submitting…" : status === "sent_back" ? "Resubmit report" : "Submit report"}
          </Button>
        )}
      </footer>
      {submitError && <p className="text-sm text-rose-600" role="alert">{submitError}</p>}
    </main>
  );
}
