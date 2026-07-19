import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { approvalsApi } from "../../lib/api";

function formatStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ApprovalQueuePage() {
  const navigate = useNavigate();
  const queue = useQuery({ queryKey: ["approval-queue"], queryFn: approvalsApi.queue });
  const history = useQuery({ queryKey: ["approval-history"], queryFn: approvalsApi.history });

  return (
    <main className="repl-page">
      <header className="hero-band">
        <p className="repl-eyebrow">Manager workspace</p>
        <h1 className="repl-title">Approval queue</h1>
        <p className="repl-lede">Review submitted reimbursement reports awaiting your decision.</p>
      </header>

      {queue.isLoading && <LoadingState label="Loading approval queue" />}
      {queue.isError && <div className="repl-alert error">Unable to load the approval queue.</div>}
      {queue.data?.length === 0 && <div className="empty-state"><div className="empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg></div><h3>Queue clear</h3><p>Your approval queue is clear. No reports awaiting review.</p></div>}
      <div className="service-grid">
        {queue.data?.map((report) => (
          <article className="service-tile" key={report.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{report.title}</h2>
                <p className="mt-1 text-sm text-[var(--color-slate)]">{report.submitter_name ?? "Employee not listed"}</p>
                {report.acting_for_name && <p className="mt-1 text-xs font-medium text-[var(--color-accent-orange)]">Acting for {report.acting_for_name}</p>}
              </div>
              <span className="status-badge badge-pending">{formatStatus(report.status)}</span>
            </div>
            <p className="stat-value" style={{fontSize:'20px'}}>{new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(Number(report.total) || 0)}</p>
            {report.created_at && <p className="mt-1 text-sm text-[var(--color-slate)]">Submitted {new Date(report.created_at).toLocaleDateString()}</p>}
            <Button className="mt-5 w-full" onClick={() => navigate(`/approvals/${report.id}`)} variant="outline">Review report</Button>
          </article>
        ))}
      </div>

      <section aria-labelledby="approval-history-heading" className="space-y-4 border-t border-[var(--color-hairline)] pt-6">
        <div>
          <h2 className="text-lg font-semibold" id="approval-history-heading">My team history</h2>
          <p className="mt-1 text-sm text-[var(--color-slate)]">Review reports you have already approved, rejected, sent back, or had withdrawn.</p>
        </div>
      {history.isLoading && <LoadingState label="Loading approval history" />}
        {history.isError && <div className="repl-alert error">Unable to load your approval history.</div>}
        {history.data?.length === 0 && <p className="rounded-lg border border-dashed border-[var(--color-hairline)] p-6 text-sm text-[var(--color-slate)]">No completed team reviews yet.</p>}
        <div className="service-grid">
          {history.data?.map((report) => (
            <article className="service-tile" key={`history-${report.id}-${report.approval_decision_at ?? report.approval_status ?? "review"}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">{report.title}</h3>
                  <p className="mt-1 text-sm text-[var(--color-slate)]">{report.submitter_name ?? "Employee not listed"}</p>
                </div>
                <span className="status-badge badge-draft">{formatStatus(report.status)}</span>
              </div>
              <p className="mt-4 text-sm font-medium">Your decision: {formatStatus(report.approval_status ?? "recorded")}</p>
              {report.approval_decision_at && <p className="mt-1 text-sm text-[var(--color-slate)]">Reviewed {new Date(report.approval_decision_at).toLocaleDateString()}</p>}
              <Button className="mt-5 w-full" onClick={() => navigate(`/approvals/${report.id}`)} variant="outline">View report</Button>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
