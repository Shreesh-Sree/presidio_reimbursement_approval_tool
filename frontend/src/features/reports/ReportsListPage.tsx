import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
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
    <main className="mx-auto w-full max-w-6xl space-y-8 p-5 sm:p-8">
      <header className="flex flex-col gap-5 border-b border-[#202020]/15 pb-7 sm:flex-row sm:items-end sm:justify-between dark:border-white/15">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#ea2804]">Reimbursements</p>
          <h1 className="mt-2 text-4xl font-extrabold tracking-[-0.06em] text-[#202020] sm:text-5xl dark:text-[#fcfcfc]">Expense reports</h1>
          <p className="mt-2 text-sm text-[#646464] dark:text-white/70">Create, update, and track your reimbursement requests.</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>New report</Button>
      </header>

      <div className="max-w-xs space-y-1.5 rounded-2xl bg-[#f3f0e8] p-4 dark:bg-[#202020]">
        <Label htmlFor="report-status">Filter by status</Label>
        <Select id="report-status" onChange={(event) => setStatus(event.target.value)} value={status}>
          {statuses.map((option) => <option key={option} value={option}>{formatStatus(option)}</option>)}
        </Select>
      </div>

      {reports.isLoading && <LoadingState label="Loading reports" />}
      {reports.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load reports.</p>}
      {reports.data?.length === 0 && <p className="rounded-2xl border border-dashed border-[#202020]/30 p-8 text-center text-sm text-[#646464] dark:border-white/30 dark:text-white/70">No reports match this filter.</p>}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {reports.data?.map((report) => (
          <button className="rounded-[10px] border border-[#202020]/15 bg-white p-5 text-left transition hover:-translate-y-0.5 hover:border-[#202020]/50 dark:border-white/15 dark:bg-[#202020] dark:hover:border-white/50" key={report.id} onClick={() => navigate(`/reports/${report.id}`)} type="button">
            <div className="flex items-start justify-between gap-3">
              <h2 className="font-bold tracking-tight text-[#202020] dark:text-[#fcfcfc]">{report.title}</h2>
              <span className="rounded-full border border-[#202020]/15 bg-[#f9f7f3] px-2.5 py-1 text-xs font-bold text-[#202020] dark:border-white/15 dark:bg-[#303030] dark:text-[#fcfcfc]">{formatStatus(report.status)}</span>
            </div>
            <p className="mt-4 text-2xl font-extrabold tracking-tight text-[#202020] dark:text-[#fcfcfc]">{new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(Number(report.total) || 0)}</p>
            {report.payment && (
              <div className="mt-3 rounded-[10px] bg-[#f3f0e8] px-3 py-2 text-sm text-[#202020] dark:bg-[#303030] dark:text-[#fcfcfc]">
                <p aria-label={`Reimbursement: ${formatStatus(report.payment.status)}`}><span className="font-semibold">Reimbursement:</span> {formatStatus(report.payment.status)}</p>
                <p className="mt-0.5 text-xs text-[#646464] dark:text-white/70">Payment reference: {report.payment.payment_reference}</p>
              </div>
            )}
            {report.created_at && <p className="mt-3 text-sm text-[#646464] dark:text-white/70">Created {new Date(report.created_at).toLocaleDateString()}</p>}
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
            {createReport.isError && <p className="text-sm text-orange-600">Unable to create this report.</p>}
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
