import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { approvalsApi } from "../../lib/api";

function formatStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ApprovalQueuePage() {
  const navigate = useNavigate();
  const queue = useQuery({ queryKey: ["approval-queue"], queryFn: approvalsApi.queue });

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="border-b border-slate-200 pb-5 dark:border-slate-800">
        <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Manager workspace</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Approval queue</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Review submitted reimbursement reports awaiting your decision.</p>
      </header>

      {queue.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading approval queue…</p>}
      {queue.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load the approval queue.</p>}
      {queue.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">Your approval queue is clear.</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {queue.data?.map((report) => (
          <article className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900" key={report.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold text-slate-950 dark:text-white">{report.title}</h2>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{report.submitter_name ?? "Employee not listed"}</p>
              </div>
              <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800 dark:bg-amber-950 dark:text-amber-200">{formatStatus(report.status)}</span>
            </div>
            <p className="mt-5 text-xl font-semibold text-slate-950 dark:text-white">{new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(Number(report.total) || 0)}</p>
            {report.created_at && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Submitted {new Date(report.created_at).toLocaleDateString()}</p>}
            <Button className="mt-5 w-full" onClick={() => navigate(`/approvals/${report.id}`)} variant="outline">Review report</Button>
          </article>
        ))}
      </div>
    </main>
  );
}
