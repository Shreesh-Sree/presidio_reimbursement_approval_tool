import { useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { CommentThread } from "../../components/CommentThread";
import type { ReportLineItem } from "../../lib/api";
import { reportsApi } from "../../lib/api";
import { ActionBar } from "./ActionBar";

type ReportReviewProps = {
  reportId?: string;
};

function displayStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function violationFor(item: ReportLineItem) {
  return item.violation_reason ?? item.policy_violation_reason;
}

export function ReportReview({ reportId }: ReportReviewProps) {
  const params = useParams();
  const id = reportId ?? params.reportId;
  const queryClient = useQueryClient();
  const reportQuery = useQuery({ queryKey: ["report", id], queryFn: () => reportsApi.get(id as string), enabled: Boolean(id) });
  const itemQuery = useQuery({ queryKey: ["report", id, "items"], queryFn: () => reportsApi.listItems(id as string), enabled: Boolean(id) });
  const report = reportQuery.data;
  const items = useMemo(() => report?.line_items ?? report?.items ?? itemQuery.data ?? [], [itemQuery.data, report]);
  const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
  const violations = Array.from(new Set([
    ...(report?.violations ?? []),
    ...items.filter((item) => item.is_policy_violated || violationFor(item)).map((item) => violationFor(item) ?? "A line item violates the active policy."),
  ]));

  if (!id) return <main className="p-6 text-sm text-rose-700">A report ID is required.</main>;
  if (reportQuery.isLoading) return <main className="p-6 text-sm text-slate-600 dark:text-slate-300">Loading report…</main>;
  if (reportQuery.isError || !report) return <main className="p-6 text-sm text-rose-700">Unable to load this report.</main>;

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 lg:flex-row lg:items-start lg:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Manager review</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">{report.title}</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Submitted by {report.submitter_name ?? report.submitter_email ?? "employee"}</p>
        </div>
        <div className="text-left lg:text-right">
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">{displayStatus(report.status)}</span>
          <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">{new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(total)}</p>
        </div>
      </header>

      {violations.length > 0 && (
        <section className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100">
          <h2 className="font-semibold">Policy violations</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{violations.map((violation) => <li key={violation}>{violation}</li>)}</ul>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 className="font-semibold text-slate-950 dark:text-white">Line items</h2>
        </div>
        <div className="divide-y divide-slate-200 dark:divide-slate-800">
          {items.length === 0 && <p className="p-5 text-sm text-slate-600 dark:text-slate-300">No line items were supplied.</p>}
          {items.map((item) => {
            const receiptUrl = item.receipt?.url ?? item.receipt_url;
            const violation = violationFor(item);
            return (
              <article className="space-y-2 p-5" key={item.id}>
                <div className="flex flex-col justify-between gap-2 sm:flex-row">
                  <div>
                    <h3 className="font-medium text-slate-950 dark:text-white">{item.description || "Untitled expense"}</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">{[item.category_name, item.vendor_name, item.expense_date].filter(Boolean).join(" · ") || "No category or vendor supplied"}</p>
                  </div>
                  <p className="font-semibold text-slate-950 dark:text-white">{new Intl.NumberFormat("en-US", { style: "currency", currency: item.currency ?? report.currency ?? "USD" }).format(Number(item.amount) || 0)}</p>
                </div>
                {receiptUrl && <a className="text-sm font-medium text-indigo-600 underline underline-offset-2 dark:text-indigo-300" href={receiptUrl} rel="noreferrer" target="_blank">View receipt</a>}
                {violation && <p className="text-sm text-rose-700 dark:text-rose-300">Policy violation: {violation}</p>}
              </article>
            );
          })}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="font-semibold text-slate-950 dark:text-white">AI audit</h2>
        <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{report.ai_audit ? JSON.stringify(report.ai_audit, null, 2) : "No AI audit data available."}</pre>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="font-semibold text-slate-950 dark:text-white">Status timeline</h2>
        {report.approval_history && report.approval_history.length > 0 ? (
          <ol className="mt-4 space-y-4 border-l-2 border-slate-200 pl-5 dark:border-slate-700">
            {report.approval_history.map((entry) => (
              <li className="relative" key={entry.id}>
                <span className="absolute -left-[1.8rem] top-1.5 size-3 rounded-full border-2 border-white bg-indigo-600 dark:border-slate-900 dark:bg-indigo-400" />
                <p className="font-medium text-slate-950 dark:text-white">{displayStatus(entry.action)}</p>
                <p className="text-sm text-slate-600 dark:text-slate-300">
                  {entry.actor_name ?? "Workflow"} · <time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time>
                </p>
                {entry.remarks && <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{entry.remarks}</p>}
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">No approval history has been recorded yet.</p>
        )}
      </section>

      <CommentThread reportId={id} />

      <ActionBar
        disabled={report.status.toLowerCase() !== "submitted"}
        onCompleted={() => {
          queryClient.invalidateQueries({ queryKey: ["report", id] });
          queryClient.invalidateQueries({ queryKey: ["approval-queue"] });
        }}
        reportId={id}
      />
    </main>
  );
}
