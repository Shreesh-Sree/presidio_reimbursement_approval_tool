import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { reportsApi } from "../../lib/api";

const statuses = ["all", "draft", "submitted", "approved_pending_payment", "paid", "rejected", "sent_back"];

function formatStatus(status: string) {
  return status.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function ReportsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const reports = useQuery({ queryKey: ["reports", status], queryFn: () => reportsApi.list(status === "all" ? undefined : status) });
  const createReport = useMutation({
    mutationFn: () => reportsApi.create({
      title: title.trim(),
      description: description.trim() || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      setDialogOpen(false);
      setTitle("");
      setDescription("");
      setStartDate("");
      setEndDate("");
      navigate(`/reports/${report.id}`);
    },
  });

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Reimbursements</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">My expense reports</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Create, update, and track your reimbursement requests.</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>New report</Button>
      </header>

      <div className="max-w-xs space-y-1.5">
        <Label htmlFor="report-status">Filter by status</Label>
        <Select id="report-status" onChange={(event) => setStatus(event.target.value)} value={status}>
          {statuses.map((option) => <option key={option} value={option}>{formatStatus(option)}</option>)}
        </Select>
      </div>

      {reports.isLoading && <p className="text-sm text-slate-600 dark:text-slate-300">Loading reports…</p>}
      {reports.isError && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200">Unable to load reports.</p>}
      {reports.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No reports match this filter.</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {reports.data?.map((report) => (
          <button className="rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-indigo-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-700" key={report.id} onClick={() => navigate(`/reports/${report.id}`)} type="button">
            <div className="flex items-start justify-between gap-3">
              <h2 className="font-semibold text-slate-950 dark:text-white">{report.title}</h2>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">{formatStatus(report.status)}</span>
            </div>
            <p className="mt-4 text-lg font-semibold text-slate-950 dark:text-white">{new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(Number(report.total) || 0)}</p>
            {report.payment && (
              <div className="mt-3 rounded-lg bg-indigo-50 px-3 py-2 text-sm text-indigo-950 dark:bg-indigo-950/40 dark:text-indigo-100">
                <p aria-label={`Reimbursement: ${formatStatus(report.payment.status)}`}><span className="font-semibold">Reimbursement:</span> {formatStatus(report.payment.status)}</p>
                <p className="mt-0.5 text-xs text-indigo-800 dark:text-indigo-200">Payment reference: {report.payment.payment_reference}</p>
              </div>
            )}
            {report.created_at && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Created {new Date(report.created_at).toLocaleDateString()}</p>}
          </button>
        ))}
      </div>

      <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
        <DialogContent>
          <DialogTitle>New expense report</DialogTitle>
          <DialogDescription>Start a draft, then add your line items and receipts.</DialogDescription>
          <Form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault();
              createReport.mutate();
            }}
          >
            <FormField>
              <Label htmlFor="new-report-title">Report title</Label>
              <Input id="new-report-title" onChange={(event) => setTitle(event.target.value)} placeholder="e.g. July client visit" required value={title} />
            </FormField>
            <FormField>
              <Label htmlFor="new-report-purpose">Business purpose</Label>
              <Textarea id="new-report-purpose" onChange={(event) => setDescription(event.target.value)} placeholder="Why is this expense needed for the business?" required value={description} />
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField>
                <Label htmlFor="new-report-start-date">Report start date</Label>
                <Input id="new-report-start-date" onChange={(event) => setStartDate(event.target.value)} required type="date" value={startDate} />
              </FormField>
              <FormField>
                <Label htmlFor="new-report-end-date">Report end date</Label>
                <Input id="new-report-end-date" min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} required type="date" value={endDate} />
              </FormField>
            </div>
            {createReport.isError && <p className="text-sm text-rose-600">Unable to create this report.</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={createReport.isPending || title.trim() === "" || description.trim() === "" || !startDate || !endDate} type="submit">{createReport.isPending ? "Creating…" : "Create report"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
    </main>
  );
}
