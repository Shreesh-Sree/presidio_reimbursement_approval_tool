import { useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { AuthenticatedAttachmentLink } from "../../components/AuthenticatedAttachmentLink";
import { CommentThread } from "../../components/CommentThread";
import type { ReportLineItem } from "../../lib/api";
import { reportsApi } from "../../lib/api";
import { ActionBar } from "./ActionBar";
import { ReceiptAnalysisPanel } from "./ReceiptAnalysisPanel";
import { LoadingState } from "../../components/ui/loading-state";

type ReportReviewProps = {
  reportId?: string;
};

function displayStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function violationFor(item: ReportLineItem) {
  return item.violation_reason ?? item.policy_violation_reason;
}

type AiFinding = {
  id: string;
  message: string;
  severity?: string;
  findingType?: string;
};

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
}

function asText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function asTextList(value: unknown) {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string" && entry.trim() !== "") : [];
}

function asFindings(value: unknown): AiFinding[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry, index) => {
    const finding = asRecord(entry);
    const message = asText(finding?.message);
    if (!message) return [];
    return [{
      id: asText(finding?.id) ?? `ai-finding-${index}`,
      message,
      severity: asText(finding?.severity),
      findingType: asText(finding?.finding_type),
    }];
  });
}

export function ReportReview({ reportId }: ReportReviewProps) {
  const params = useParams();
  const id = reportId ?? params.reportId;
  const queryClient = useQueryClient();
  const reportQuery = useQuery({ queryKey: ["report", id], queryFn: () => reportsApi.get(id as string), enabled: Boolean(id) });
  const itemQuery = useQuery({ queryKey: ["report", id, "items"], queryFn: () => reportsApi.listItems(id as string), enabled: Boolean(id) });
  const report = reportQuery.data;
  const items = useMemo(() => {
    const reportItems = report?.line_items ?? report?.items;
    return reportItems && reportItems.length > 0 ? reportItems : itemQuery.data ?? reportItems ?? [];
  }, [itemQuery.data, report]);
  const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
  const violations = Array.from(new Set([
    ...(report?.violations ?? []),
    ...items.filter((item) => item.is_policy_violated || violationFor(item)).map((item) => violationFor(item) ?? "A line item violates the active policy."),
  ]));
  const aiAudit = asRecord(report?.ai_audit);
  const humanReview = asRecord(aiAudit?.human_review);
  const provider = asRecord(aiAudit?.provider);
  const aiStatus = asText(aiAudit?.status);
  const aiSummary = asText(aiAudit?.summary);
  const aiRecommendation = asText(aiAudit?.recommendation);
  const aiRiskLevel = asText(aiAudit?.risk_level);
  const providerStatus = asText(provider?.status);
  const aiInsights = asTextList(aiAudit?.key_insights);
  const aiFindings = asFindings(aiAudit?.findings);
  const citedFindingIds = asTextList(aiAudit?.cited_finding_ids);
  const citedPolicyRuleRefs = asTextList(aiAudit?.cited_policy_rule_refs);
  const humanReviewMessage = asText(humanReview?.message)
    ?? "AI recommendations are advisory; an authorized human must make the workflow decision.";

  if (!id) return <main className="p-6 text-sm text-rose-700">A report ID is required.</main>;
  if (reportQuery.isLoading) return <main className="p-6"><LoadingState label="Loading report" /></main>;
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
                {receiptUrl && <AuthenticatedAttachmentLink className="h-auto min-h-0 px-0 py-0 text-sm font-medium text-indigo-600 underline underline-offset-2 hover:bg-transparent dark:text-indigo-300" url={receiptUrl}>View receipt</AuthenticatedAttachmentLink>}
                {violation && <p className="text-sm text-rose-700 dark:text-rose-300">Policy violation: {violation}</p>}
                <ReceiptAnalysisPanel item={item} reportId={id} />
              </article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="ai-review-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-950 dark:text-white" id="ai-review-heading">AI review advisory</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">AI analysis highlights evidence and possible risks. It cannot approve, reject, or send back this report.</p>
          </div>
          {aiStatus && <span className="w-fit rounded-full bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-800 dark:bg-violet-950 dark:text-violet-200">{displayStatus(aiStatus)}</span>}
        </div>

        {!aiAudit ? (
          <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-700 dark:bg-slate-800/70 dark:text-slate-200">No AI advisory is available for this report. Complete the policy and receipt review before taking a workflow action.</p>
        ) : (
          <div className="mt-4 space-y-5">
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/70">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Review status</dt>
                <dd className="mt-1 font-medium text-slate-950 dark:text-white">{aiStatus ? displayStatus(aiStatus) : "Pending"}</dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/70">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Risk level</dt>
                <dd className="mt-1 font-medium text-slate-950 dark:text-white">{aiRiskLevel ? displayStatus(aiRiskLevel) : "Not assessed"}</dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/70">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Recommendation</dt>
                <dd className="mt-1 font-medium text-slate-950 dark:text-white">{aiRecommendation ? displayStatus(aiRecommendation) : "Not available"}</dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/70">
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Analysis source</dt>
                <dd className="mt-1 font-medium text-slate-950 dark:text-white">{providerStatus ? displayStatus(providerStatus) : "Not available"}</dd>
              </div>
            </dl>

            <div>
              <h3 className="text-sm font-semibold text-slate-950 dark:text-white">Summary</h3>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{aiSummary ?? "The AI review is still being prepared. Use the policy and receipt evidence above for the current decision."}</p>
            </div>

            {aiInsights.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-950 dark:text-white">Key insights</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-200">
                  {aiInsights.map((insight) => <li key={insight}>{insight}</li>)}
                </ul>
              </div>
            )}

            <div>
              <h3 className="text-sm font-semibold text-slate-950 dark:text-white">Findings</h3>
              {aiFindings.length > 0 ? (
                <ul className="mt-2 space-y-2">
                  {aiFindings.map((finding) => (
                    <li className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700" key={finding.id}>
                      <div className="flex flex-wrap items-center gap-2">
                        {finding.severity && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">{displayStatus(finding.severity)}</span>}
                        {finding.findingType && <span className="text-xs text-slate-500 dark:text-slate-400">{displayStatus(finding.findingType)}</span>}
                      </div>
                      <p className="mt-1 text-slate-700 dark:text-slate-200">{finding.message}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">No AI findings have been recorded.</p>
              )}
            </div>

            {(citedFindingIds.length > 0 || citedPolicyRuleRefs.length > 0) && (
              <section className="rounded-lg border border-indigo-200 bg-indigo-50/70 p-3 dark:border-indigo-900 dark:bg-indigo-950/30">
                <h3 className="text-sm font-semibold text-indigo-950 dark:text-indigo-100">Grounding citations</h3>
                <p className="mt-1 text-sm text-indigo-900 dark:text-indigo-100">The advisory is grounded only in these supplied finding and policy references.</p>
                {citedFindingIds.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-800 dark:text-indigo-200">Findings</p>
                    <ul className="mt-1 flex flex-wrap gap-1.5" aria-label="Cited findings">
                      {citedFindingIds.map((findingId) => <li className="rounded-full bg-white px-2 py-1 font-mono text-xs text-indigo-950 dark:bg-slate-900 dark:text-indigo-100" key={findingId}>{findingId}</li>)}
                    </ul>
                  </div>
                )}
                {citedPolicyRuleRefs.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-800 dark:text-indigo-200">Policy rules</p>
                    <ul className="mt-1 flex flex-wrap gap-1.5" aria-label="Cited policy rules">
                      {citedPolicyRuleRefs.map((ruleRef) => <li className="rounded-full bg-white px-2 py-1 font-mono text-xs text-indigo-950 dark:bg-slate-900 dark:text-indigo-100" key={ruleRef}>{ruleRef}</li>)}
                    </ul>
                  </div>
                )}
              </section>
            )}

            <p className="rounded-lg border border-violet-200 bg-violet-50 p-3 text-sm text-violet-950 dark:border-violet-900 dark:bg-violet-950/40 dark:text-violet-100"><span className="font-semibold">Human review required:</span> {humanReviewMessage}</p>

            <details className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <summary className="cursor-pointer text-sm font-medium text-slate-700 dark:text-slate-200">View raw AI review data</summary>
              <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(aiAudit, null, 2)}</pre>
            </details>
          </div>
        )}
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
                  {entry.actor_name ?? "Workflow automation"}{entry.acting_for_name ? ` · acting for ${entry.acting_for_name}` : ""} · <time dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time>
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
