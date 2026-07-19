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
    <main className="repl-page">
      <header className="hero-band">
        <div>
          <p className="repl-eyebrow">Reimbursements</p>
          <h1 className="repl-title">Expense reports</h1>
          <p className="repl-lede">Create, update, and track your reimbursement requests.</p>
        </div>
        <div className="hero-actions">
          <Button onClick={() => setDialogOpen(true)}>New report</Button>
        </div>
      </header>

      <div className="max-w-xs">
        <div className="form-field">
          <Label htmlFor="report-status">Filter by status</Label>
        <Select id="report-status" onChange={(event) => setStatus(event.target.value)} value={status}>
          {statuses.map((option) => <option key={option} value={option}>{formatStatus(option)}</option>)}
        </Select>
        </div>
      </div>

      {reports.isLoading && <LoadingState label="Loading reports" />}
      {reports.isError && <div className="repl-alert error">Unable to load reports.</div>}
      {reports.data?.length === 0 && <div className="empty-state"><div className="empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><h3>No reports found</h3><p>No reports match this filter. Create a new report to get started.</p></div>}
      <div className="service-grid">
        {reports.data?.map((report) => (
          <button className="service-tile text-left" key={report.id} onClick={() => navigate(`/reports/${report.id}`)} type="button">
            <div className="flex items-start justify-between gap-3">
              <h2 className="font-bold tracking-tight">{report.title}</h2>
              <span className="status-badge badge-draft">{formatStatus(report.status)}</span>
            </div>
            <p className="stat-value" style={{fontSize:'24px'}}>{new Intl.NumberFormat("en-US", { style: "currency", currency: report.currency ?? "USD" }).format(Number(report.total) || 0)}</p>
            {report.payment && (
              <div className="mt-3 rounded-lg bg-[var(--color-surface)] px-3 py-2 text-sm">
                <p aria-label={`Reimbursement: ${formatStatus(report.payment.status)}`}><span className="font-semibold">Reimbursement:</span> {formatStatus(report.payment.status)}</p>
                <p className="mt-0.5 text-xs text-[var(--color-slate)]">Payment reference: {report.payment.payment_reference}</p>
              </div>
            )}
            {report.created_at && <p className="mt-3 text-sm text-[var(--color-slate)]">Created {new Date(report.created_at).toLocaleDateString()}</p>}
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
