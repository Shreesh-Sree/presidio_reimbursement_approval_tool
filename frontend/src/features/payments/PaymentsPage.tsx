import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import {
  getApiErrorMessage,
  paymentsApi,
  type PaymentFailedInput,
  type PaymentBatchCreateInput,
  type PaymentPaidInput,
  type PaymentRecord,
  type PaymentStatus,
} from "../../lib/api";

const statuses: Array<PaymentStatus | "all"> = [
  "all",
  "pending",
  "batched",
  "exported",
  "paid",
  "failed",
];
const label = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const money = (amount: number, currency: string) =>
  new Intl.NumberFormat("en-US", { currency, style: "currency" }).format(
    amount,
  );
const download = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
};

export function PaymentsPage() {
  const client = useQueryClient();
  const [filter, setFilter] = useState<PaymentStatus | "all">("pending");
  const [selected, setSelected] = useState(new Set<string>());
  const [message, setMessage] = useState<string | null>(null);
  const [batchOpen, setBatchOpen] = useState(false);
  const [remarks, setRemarks] = useState("");
  const [batchError, setBatchError] = useState<string | null>(null);
  const [paid, setPaid] = useState<PaymentRecord | null>(null);
  const [reference, setReference] = useState("");
  const [paidError, setPaidError] = useState<string | null>(null);
  const [failed, setFailed] = useState<PaymentRecord | null>(null);
  const [reason, setReason] = useState("");
  const [failedError, setFailedError] = useState<string | null>(null);
  const paidDialogPaymentId = useRef<string | null>(null);
  const failedDialogPaymentId = useRef<string | null>(null);
  const payments = useQuery({
    queryKey: ["payments", "queue", filter],
    queryFn: () => paymentsApi.list(filter === "all" ? {} : { status: filter }),
  });
  const batches = useQuery({
    queryKey: ["payments", "batches"],
    queryFn: () => paymentsApi.listBatches({ limit: 20 }),
  });
  const rows = useMemo(() => payments.data?.items ?? [], [payments.data?.items]);
  const chosen = useMemo(
    () => rows.filter((payment) => selected.has(payment.id)),
    [rows, selected],
  );
  const currency = chosen[0]?.currency;
  useEffect(() => setSelected(new Set()), [filter]);
  const refresh = () =>
    void client.invalidateQueries({ queryKey: ["payments"] });
  const closeBatchDialog = () => {
    setBatchOpen(false);
    setRemarks("");
    setBatchError(null);
  };
  const openPaidDialog = (payment: PaymentRecord) => {
    paidDialogPaymentId.current = payment.id;
    setPaid(payment);
    setReference("");
    setPaidError(null);
  };
  const closePaidDialog = () => {
    paidDialogPaymentId.current = null;
    setPaid(null);
    setReference("");
    setPaidError(null);
  };
  const openFailedDialog = (payment: PaymentRecord) => {
    failedDialogPaymentId.current = payment.id;
    setFailed(payment);
    setReason("");
    setFailedError(null);
  };
  const closeFailedDialog = () => {
    failedDialogPaymentId.current = null;
    setFailed(null);
    setReason("");
    setFailedError(null);
  };
  const create = useMutation({
    mutationFn: (input: PaymentBatchCreateInput) => paymentsApi.createBatch(input),
    onSuccess: (batch) => {
      refresh();
      setSelected(new Set());
      closeBatchDialog();
      setMessage(`${batch.batch_reference} was created.`);
    },
    onError: (error) => setBatchError(getApiErrorMessage(error, "Unable to create this payment batch.")),
  });
  const exportBatch = useMutation({
    mutationFn: ({ id, format }: { id: string; format: "xlsx" | "pdf" }) =>
      paymentsApi.exportBatch(id, format),
    onSuccess: (file, variables) => {
      download(file.blob, file.filename);
      refresh();
      setMessage(
        `Batch exported as ${variables.format === "xlsx" ? "Excel" : "PDF"}.`,
      );
    },
  });
  const markPaid = useMutation({
    mutationFn: ({ id, input }: { id: string; input: PaymentPaidInput }) =>
      paymentsApi.markPaid(id, input),
    onSuccess: (_payment, variables) => {
      refresh();
      if (paidDialogPaymentId.current === variables.id) closePaidDialog();
      setMessage("Reimbursement marked as paid.");
    },
    onError: (error, variables) => {
      if (paidDialogPaymentId.current === variables.id) {
        setPaidError(getApiErrorMessage(error, "Unable to mark this reimbursement as paid."));
      }
    },
  });
  const markFailed = useMutation({
    mutationFn: ({ id, input }: { id: string; input: PaymentFailedInput }) =>
      paymentsApi.markFailed(id, input),
    onSuccess: (_payment, variables) => {
      refresh();
      if (failedDialogPaymentId.current === variables.id) closeFailedDialog();
      setMessage("Payment marked for finance follow-up.");
    },
    onError: (error, variables) => {
      if (failedDialogPaymentId.current === variables.id) {
        setFailedError(getApiErrorMessage(error, "Unable to mark this payment for follow-up."));
      }
    },
  });
  const updateBatchStatus = useMutation({
    mutationFn: ({ id, status: newStatus }: { id: string; status: string }) =>
      paymentsApi.updateBatchStatus(id, { status: newStatus }),
    onSuccess: () => {
      refresh();
      setMessage("Batch status updated.");
    },
  });
  const toggle = (payment: PaymentRecord) => {
    if (
      payment.status !== "pending" ||
      (currency && currency !== payment.currency && !selected.has(payment.id))
    )
      return;
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(payment.id)) next.delete(payment.id);
      else next.add(payment.id);
      return next;
    });
  };
  const submitBatch = (event: FormEvent) => {
    event.preventDefault();
    create.mutate({
      payment_ids: chosen.map((payment) => payment.id),
      remarks: remarks || undefined,
    });
  };
  return (
    <main className="repl-page payments-page">
      <header className="repl-page-head">
        <div>
          <p className="repl-eyebrow">Finance operations</p>
          <h1 className="repl-title">Reimbursement payments</h1>
          <p className="repl-lede">
            Export approved reimbursements for Finance as an Excel register or a
            signed-off PDF list, then record their settlement outcome.
          </p>
        </div>
        <label>
          Payment status
          <Select
            onChange={(event) =>
              setFilter(event.target.value as PaymentStatus | "all")
            }
            value={filter}
          >
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status === "all" ? "All statuses" : label(status)}
              </option>
            ))}
          </Select>
        </label>
      </header>
      {message && <div className="repl-alert info">{message}</div>}
      <section className="repl-card payment-card">
        <div className="card-heading">
          <div>
            <h2>Payment queue</h2>
            <p>
              Select pending items with a common currency to prepare one finance
              export batch.
            </p>
          </div>
          <Button disabled={!chosen.length} onClick={() => { setBatchOpen(true); setRemarks(""); setBatchError(null); }}>
            Create batch
          </Button>
        </div>
        <div className="table-scroll">
          <table className="repl-table">
            <thead>
              <tr>
                <th></th>
                <th>Payment</th>
                <th>Employee</th>
                <th>Report</th>
                <th>Status</th>
                <th>Amount</th>
                <th>Settlement</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((payment) => (
                <tr key={payment.id}>
                  <td>
                    <input
                      aria-label={`Select ${payment.payment_reference} for a payment batch`}
                      checked={selected.has(payment.id)}
                      disabled={payment.status !== "pending"}
                      onChange={() => toggle(payment)}
                      type="checkbox"
                    />
                  </td>
                  <td>{payment.payment_reference}</td>
                  <td>{payment.employee_name ?? "Employee unavailable"}</td>
                  <td>
                    <Link to={`/reports/${payment.report_id}`}>
                      {payment.report_number}
                    </Link>
                  </td>
                  <td>
                    <span className="pill">{label(payment.status)}</span>
                  </td>
                  <td>{money(payment.amount, payment.currency)}</td>
                  <td>
                    {payment.batch?.batch_reference && (
                      <span className="pill">{payment.batch.batch_reference}</span>
                    )}
                    {payment.status === "exported" && (
                      <>
                        <Button onClick={() => openPaidDialog(payment)} variant="outline">
                          Mark paid
                        </Button>
                        <Button onClick={() => openFailedDialog(payment)} variant="destructive">
                          Follow up
                        </Button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {payments.isError && (
          <div className="repl-alert error">
            {getApiErrorMessage(
              payments.error,
              "Unable to load the payment queue.",
            )}
          </div>
        )}
      </section>
      <section className="repl-card batch-card">
        <div className="card-heading">
          <div>
            <h2>Finance exports</h2>
            <p>
              Excel is the working register; PDF is the shareable review copy.
              Both exports transition a newly created batch to exported exactly
              once.
            </p>
          </div>
        </div>
        <div className="table-scroll">
          <table className="repl-table">
            <thead>
              <tr>
                <th>Batch</th>
                <th>Status</th>
                <th>Payments</th>
                <th>Total</th>
                <th>Exports</th>
              </tr>
            </thead>
            <tbody>
              {batches.data?.items.map((batch) => (
                <tr key={batch.id}>
                  <td>{batch.batch_reference}</td>
                  <td>
                    <select
                      className="form-input" style={{height:'32px',fontSize:'12px',padding:'0 8px',width:'auto',minWidth:'110px'}}
                      value={batch.status}
                      onChange={(e) => updateBatchStatus.mutate({ id: batch.id, status: e.target.value })}
                    >
                      <option value="created">Created</option>
                      <option value="exported">Exported</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  </td>
                  <td>{batch.payment_count}</td>
                  <td>{money(batch.total_amount, batch.currency)}</td>
                  <td>
                    <Button
                      disabled={exportBatch.isPending}
                      onClick={() =>
                        exportBatch.mutate({ id: batch.id, format: "xlsx" })
                      }
                      variant="outline"
                    >
                      Excel
                    </Button>
                    <Button
                      disabled={exportBatch.isPending}
                      onClick={() =>
                        exportBatch.mutate({ id: batch.id, format: "pdf" })
                      }
                      variant="outline"
                    >
                      PDF
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <Dialog onOpenChange={(open) => { if (!open) closeBatchDialog(); }} open={batchOpen}>
        <DialogContent>
          <DialogTitle>Create finance batch</DialogTitle>
          <DialogDescription>
            Creates one {currency ?? ""} batch for {chosen.length} approved
            reimbursements.
          </DialogDescription>
          <Form className="mt-5" onSubmit={submitBatch}>
            <FormField>
              <Label htmlFor="remarks">Finance note</Label>
              <Textarea
                id="remarks"
                onChange={(event) => setRemarks(event.target.value)}
                value={remarks}
              />
            </FormField>
            {batchError && <p className="repl-alert error" role="alert">{batchError}</p>}
            <Button disabled={create.isPending} type="submit">
              Create batch
            </Button>
          </Form>
        </DialogContent>
      </Dialog>
      <Dialog
        onOpenChange={(open) => { if (!open) closePaidDialog(); }}
        open={Boolean(paid)}
      >
        <DialogContent>
          <DialogTitle>Mark reimbursement paid</DialogTitle>
          <DialogDescription>
            {paid ? `Record the settlement reference for ${paid.payment_reference}.` : "Record the settlement reference."}
          </DialogDescription>
          <Form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault();
              if (paid)
                markPaid.mutate({
                  id: paid.id,
                  input: {
                    provider_reference: reference.trim(),
                    payment_date: undefined,
                    remarks: undefined,
                  },
                });
            }}
          >
            <FormField>
              <Label htmlFor="reference">Payment provider reference</Label>
              <Input
                id="reference"
                onChange={(event) => setReference(event.target.value)}
                required
                value={reference}
              />
            </FormField>
            {paidError && <p className="repl-alert error" role="alert">{paidError}</p>}
            <Button disabled={!reference.trim() || markPaid.isPending} type="submit">
              Mark paid
            </Button>
          </Form>
        </DialogContent>
      </Dialog>
      <Dialog
        onOpenChange={(open) => { if (!open) closeFailedDialog(); }}
        open={Boolean(failed)}
      >
        <DialogContent>
          <DialogTitle>Mark payment for follow-up</DialogTitle>
          <DialogDescription>
            {failed ? `Record the finance follow-up reason for ${failed.payment_reference}.` : "Record the finance follow-up reason."}
          </DialogDescription>
          <Form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault();
              if (failed)
                markFailed.mutate({
                  id: failed.id,
                  input: { failure_reason: reason },
                });
            }}
          >
            <FormField>
              <Label htmlFor="reason">Reason</Label>
              <Textarea
                id="reason"
                onChange={(event) => setReason(event.target.value)}
                required
                value={reason}
              />
            </FormField>
            {failedError && <p className="repl-alert error" role="alert">{failedError}</p>}
            <Button
              disabled={!reason.trim() || markFailed.isPending}
              type="submit"
              variant="destructive"
            >
              Mark failed
            </Button>
          </Form>
        </DialogContent>
      </Dialog>
    </main>
  );
}
