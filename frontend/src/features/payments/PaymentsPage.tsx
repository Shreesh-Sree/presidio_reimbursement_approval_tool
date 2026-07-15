import AccountBalanceWalletOutlinedIcon from "@mui/icons-material/AccountBalanceWalletOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PlaylistAddCheckOutlinedIcon from "@mui/icons-material/PlaylistAddCheckOutlined";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import {
  getApiErrorMessage,
  paymentsApi,
  type PaymentCsvDownload,
  type PaymentFailedInput,
  type PaymentPaidInput,
  type PaymentRecord,
  type PaymentStatus,
} from "../../lib/api";

const paymentStatuses: Array<PaymentStatus | "all"> = ["all", "pending", "batched", "exported", "paid", "failed"];

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatMoney(amount: number, currency: string) {
  try {
    return new Intl.NumberFormat("en-US", { currency, style: "currency" }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(date);
}

function statusColor(status: string): "default" | "primary" | "success" | "warning" | "error" {
  if (status === "paid") return "success";
  if (status === "failed") return "error";
  if (status === "exported") return "primary";
  if (status === "pending" || status === "batched") return "warning";
  return "default";
}

function downloadCsv({ blob, filename }: PaymentCsvDownload) {
  if (typeof window === "undefined" || !window.URL.createObjectURL) return;

  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}

function selectedPaymentTotal(payments: PaymentRecord[]) {
  return payments.reduce((total, payment) => total + payment.amount, 0);
}

export function PaymentsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<PaymentStatus | "all">("pending");
  const [selectedPaymentIds, setSelectedPaymentIds] = useState<Set<string>>(() => new Set());
  const [selectionMessage, setSelectionMessage] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);
  const [batchRemarks, setBatchRemarks] = useState("");
  const [paidPayment, setPaidPayment] = useState<PaymentRecord | null>(null);
  const [providerReference, setProviderReference] = useState("");
  const [paymentDate, setPaymentDate] = useState("");
  const [paidRemarks, setPaidRemarks] = useState("");
  const [failedPayment, setFailedPayment] = useState<PaymentRecord | null>(null);
  const [failureReason, setFailureReason] = useState("");
  const [failureRemarks, setFailureRemarks] = useState("");

  const payments = useQuery({
    queryKey: ["payments", "queue", statusFilter],
    queryFn: () => paymentsApi.list(statusFilter === "all" ? {} : { status: statusFilter }),
  });
  const batches = useQuery({
    queryKey: ["payments", "batches"],
    queryFn: () => paymentsApi.listBatches({ limit: 20 }),
  });

  useEffect(() => {
    setSelectedPaymentIds(new Set());
    setSelectionMessage(null);
  }, [statusFilter]);

  const paymentRows = useMemo(() => payments.data?.items ?? [], [payments.data?.items]);
  const selectedPayments = useMemo(
    () => paymentRows.filter((payment) => selectedPaymentIds.has(payment.id)),
    [paymentRows, selectedPaymentIds],
  );
  const selectedCurrency = selectedPayments[0]?.currency;
  const selectedTotal = selectedPaymentTotal(selectedPayments);

  const refreshPaymentData = () => {
    void queryClient.invalidateQueries({ queryKey: ["payments"] });
  };

  const createBatch = useMutation({
    mutationFn: (input: Parameters<typeof paymentsApi.createBatch>[0]) => paymentsApi.createBatch(input),
    onSuccess: (batch) => {
      refreshPaymentData();
      setSelectedPaymentIds(new Set());
      setBatchRemarks("");
      setBatchDialogOpen(false);
      setActionMessage(`${batch.batch_reference} was created with ${batch.payment_count} payment${batch.payment_count === 1 ? "" : "s"}.`);
    },
  });

  const exportBatch = useMutation({
    mutationFn: (batchId: string) => paymentsApi.exportBatch(batchId),
    onSuccess: (file, batchId) => {
      downloadCsv(file);
      refreshPaymentData();
      const batch = batches.data?.items.find((item) => item.id === batchId);
      setActionMessage(`${batch?.batch_reference ?? "Payment batch"} was exported as CSV.`);
    },
  });

  const markPaid = useMutation({
    mutationFn: ({ paymentId, input }: { paymentId: string; input: PaymentPaidInput }) => paymentsApi.markPaid(paymentId, input),
    onSuccess: (payment) => {
      refreshPaymentData();
      setPaidPayment(null);
      setProviderReference("");
      setPaymentDate("");
      setPaidRemarks("");
      setActionMessage(`${payment.payment_reference} is marked as paid.`);
    },
  });

  const markFailed = useMutation({
    mutationFn: ({ paymentId, input }: { paymentId: string; input: PaymentFailedInput }) => paymentsApi.markFailed(paymentId, input),
    onSuccess: (payment) => {
      refreshPaymentData();
      setFailedPayment(null);
      setFailureReason("");
      setFailureRemarks("");
      setActionMessage(`${payment.payment_reference} was marked for finance follow-up.`);
    },
  });

  function togglePayment(payment: PaymentRecord) {
    if (payment.status !== "pending") return;

    setSelectionMessage(null);
    setSelectedPaymentIds((current) => {
      const next = new Set(current);
      if (next.has(payment.id)) {
        next.delete(payment.id);
        return next;
      }
      const existingCurrency = paymentRows.find((row) => next.has(row.id))?.currency;
      if (existingCurrency && existingCurrency !== payment.currency) {
        setSelectionMessage("A payment batch can contain only one currency. Select payments with the same currency.");
        return current;
      }
      next.add(payment.id);
      return next;
    });
  }

  function submitBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const paymentIds = selectedPayments.map((payment) => payment.id);
    if (paymentIds.length === 0) {
      setSelectionMessage("Select at least one pending payment before creating a batch.");
      setBatchDialogOpen(false);
      return;
    }
    createBatch.mutate({ payment_ids: paymentIds, remarks: batchRemarks.trim() || undefined });
  }

  function openPaidDialog(payment: PaymentRecord) {
    setPaidPayment(payment);
    setProviderReference("");
    setPaymentDate("");
    setPaidRemarks("");
  }

  function submitPaid(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!paidPayment || !providerReference.trim()) return;
    markPaid.mutate({
      paymentId: paidPayment.id,
      input: {
        provider_reference: providerReference.trim(),
        payment_date: paymentDate || undefined,
        remarks: paidRemarks.trim() || undefined,
      },
    });
  }

  function openFailedDialog(payment: PaymentRecord) {
    setFailedPayment(payment);
    setFailureReason("");
    setFailureRemarks("");
  }

  function submitFailed(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!failedPayment || !failureReason.trim()) return;
    markFailed.mutate({
      paymentId: failedPayment.id,
      input: {
        failure_reason: failureReason.trim(),
        remarks: failureRemarks.trim() || undefined,
      },
    });
  }

  return (
    <Box component="main" sx={{ margin: "0 auto", maxWidth: 1440, p: { xs: 2, sm: 3 } }}>
      <Stack spacing={3}>
        <Box sx={{ alignItems: { sm: "flex-end" }, display: "flex", flexDirection: { xs: "column", sm: "row" }, gap: 2, justifyContent: "space-between" }}>
          <Box>
            <Typography color="primary" variant="overline">Finance operations</Typography>
            <Typography component="h1" sx={{ fontSize: { xs: "1.65rem", sm: "2rem" }, fontWeight: 800, letterSpacing: "-0.025em", mt: 0.25 }}>
              Reimbursement payments
            </Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 760, mt: 0.75 }}>
              Batch approved reimbursements, produce a payment-rail CSV, and record settlement outcomes. Recipient bank details are not stored or displayed here.
            </Typography>
          </Box>
          <Stack alignItems={{ xs: "stretch", sm: "flex-end" }} spacing={1} sx={{ minWidth: { sm: 270 } }}>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200" htmlFor="payment-status-filter">Payment status</label>
            <Select id="payment-status-filter" onChange={(event) => setStatusFilter(event.target.value as PaymentStatus | "all")} value={statusFilter}>
              {paymentStatuses.map((status) => <option key={status} value={status}>{status === "all" ? "All statuses" : titleCase(status)}</option>)}
            </Select>
          </Stack>
        </Box>

        {actionMessage && <Alert onClose={() => setActionMessage(null)} severity="success">{actionMessage}</Alert>}
        {selectionMessage && <Alert onClose={() => setSelectionMessage(null)} severity="warning">{selectionMessage}</Alert>}

        <Card>
          <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
            <Box sx={{ alignItems: { md: "center" }, display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 2, justifyContent: "space-between", p: { xs: 2.25, sm: 3 }, pb: 2 }}>
              <Box>
                <Stack alignItems="center" direction="row" spacing={1}>
                  <AccountBalanceWalletOutlinedIcon color="primary" fontSize="small" />
                  <Typography component="h2" fontWeight={750} variant="h6">Payment queue</Typography>
                  {payments.data && <Chip label={`${payments.data.total} total`} size="small" variant="outlined" />}
                </Stack>
                <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">
                  Select pending items with a common currency to prepare one export batch.
                </Typography>
              </Box>
              <Stack alignItems={{ xs: "stretch", sm: "center" }} direction={{ xs: "column", sm: "row" }} spacing={1}>
                {selectedPayments.length > 0 && (
                  <Typography color="text.secondary" variant="body2">
                    {selectedPayments.length} selected · {formatMoney(selectedTotal, selectedCurrency ?? "USD")}
                  </Typography>
                )}
                <Button disabled={selectedPayments.length === 0} onClick={() => setBatchDialogOpen(true)}>
                  <PlaylistAddCheckOutlinedIcon className="mr-1.5" fontSize="small" />
                  Create batch
                </Button>
              </Stack>
            </Box>

            {payments.isError && (
              <Alert severity="error" sx={{ m: { xs: 2.25, sm: 3 }, mt: 0 }}>
                {getApiErrorMessage(payments.error, "Unable to load the payment queue.")}
              </Alert>
            )}
            {payments.isLoading && (
              <Box sx={{ p: { xs: 2.25, sm: 3 }, pt: 0 }}>
                <Stack spacing={1.25}>{Array.from({ length: 5 }, (_, index) => <Skeleton height={52} key={index} variant="rounded" />)}</Stack>
              </Box>
            )}
            {!payments.isLoading && !payments.isError && paymentRows.length === 0 && (
              <Alert icon={<CheckCircleOutlineIcon fontSize="inherit" />} severity="info" sx={{ m: { xs: 2.25, sm: 3 }, mt: 0 }}>
                No {statusFilter === "all" ? "" : `${statusFilter} `}payments are available in this queue.
              </Alert>
            )}
            {paymentRows.length > 0 && (
              <TableContainer>
                <Table aria-label="Reimbursement payment queue" sx={{ minWidth: 900 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox"><span className="sr-only">Select for batch</span></TableCell>
                      <TableCell>Payment</TableCell>
                      <TableCell>Employee</TableCell>
                      <TableCell>Report</TableCell>
                      <TableCell>Batch</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Amount</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {paymentRows.map((payment) => {
                      const currencyConflict = Boolean(selectedCurrency && selectedCurrency !== payment.currency && !selectedPaymentIds.has(payment.id));
                      const selectable = payment.status === "pending" && !currencyConflict;
                      return (
                        <TableRow hover key={payment.id}>
                          <TableCell padding="checkbox">
                            <Tooltip title={payment.status !== "pending" ? "Only pending payments can be batched" : currencyConflict ? `Only ${selectedCurrency} can be added to this batch` : "Select for batch"}>
                              <span>
                                <Checkbox
                                  checked={selectedPaymentIds.has(payment.id)}
                                  disabled={!selectable && !selectedPaymentIds.has(payment.id)}
                                  inputProps={{ "aria-label": `Select ${payment.payment_reference} for a payment batch` }}
                                  onChange={() => togglePayment(payment)}
                                />
                              </span>
                            </Tooltip>
                          </TableCell>
                          <TableCell>
                            <Typography fontWeight={700} variant="body2">{payment.payment_reference}</Typography>
                            <Typography color="text.secondary" variant="caption">Exported {formatDate(payment.exported_at)}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{payment.employee_name ?? "Employee unavailable"}</Typography>
                            {payment.employee_number && <Typography color="text.secondary" variant="caption">Employee #{payment.employee_number}</Typography>}
                          </TableCell>
                          <TableCell>
                            <Typography component={RouterLink} sx={{ color: "primary.main", fontWeight: 650, textDecoration: "none" }} to={`/reports/${payment.report_id}`} variant="body2">
                              {payment.report_number}
                            </Typography>
                          </TableCell>
                          <TableCell><Typography color="text.secondary" variant="body2">{payment.batch?.batch_reference ?? "Not batched"}</Typography></TableCell>
                          <TableCell><Chip color={statusColor(payment.status)} label={titleCase(payment.status)} size="small" /></TableCell>
                          <TableCell align="right"><Typography fontWeight={700} variant="body2">{formatMoney(payment.amount, payment.currency)}</Typography></TableCell>
                          <TableCell align="right">
                            <Stack direction="row" justifyContent="flex-end" spacing={1}>
                              {payment.status === "exported" && <Button onClick={() => openPaidDialog(payment)} variant="outline">Mark paid</Button>}
                              {payment.status === "exported" && <Button onClick={() => openFailedDialog(payment)} variant="destructive">Mark failed</Button>}
                            </Stack>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: { xs: 2.25, sm: 3 }, "&:last-child": { pb: { xs: 2.25, sm: 3 } } }}>
            <Stack alignItems={{ sm: "center" }} direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
              <Box>
                <Typography component="h2" fontWeight={750} variant="h6">Recent payment batches</Typography>
                <Typography color="text.secondary" sx={{ mt: 0.4 }} variant="body2">Exporting a created batch transitions its selected payments to exported.</Typography>
              </Box>
              {batches.isFetching && <CircularProgress aria-label="Refreshing payment batches" size={20} />}
            </Stack>
            {batches.isError && <Alert severity="error" sx={{ mt: 2 }}>{getApiErrorMessage(batches.error, "Unable to load payment batches.")}</Alert>}
            {!batches.isLoading && !batches.isError && batches.data?.items.length === 0 && <Alert severity="info" sx={{ mt: 2 }}>No payment batches have been created yet.</Alert>}
            {batches.isLoading && <Stack spacing={1.25} sx={{ mt: 2 }}>{Array.from({ length: 3 }, (_, index) => <Skeleton height={45} key={index} variant="rounded" />)}</Stack>}
            {batches.data && batches.data.items.length > 0 && (
              <TableContainer sx={{ mt: 2 }}>
                <Table aria-label="Recent payment batches" sx={{ minWidth: 690 }}>
                  <TableHead><TableRow><TableCell>Batch</TableCell><TableCell>Status</TableCell><TableCell>Created</TableCell><TableCell align="right">Payments</TableCell><TableCell align="right">Total</TableCell><TableCell align="right">Export</TableCell></TableRow></TableHead>
                  <TableBody>
                    {batches.data.items.map((batch) => (
                      <TableRow hover key={batch.id}>
                        <TableCell><Typography fontWeight={700} variant="body2">{batch.batch_reference}</Typography></TableCell>
                        <TableCell><Chip color={batch.status === "exported" ? "primary" : "warning"} label={titleCase(batch.status)} size="small" /></TableCell>
                        <TableCell>{formatDate(batch.created_at)}</TableCell>
                        <TableCell align="right">{batch.payment_count}</TableCell>
                        <TableCell align="right">{formatMoney(batch.total_amount, batch.currency)}</TableCell>
                        <TableCell align="right">
                          <Button disabled={exportBatch.isPending} onClick={() => exportBatch.mutate(batch.id)} variant="outline">
                            <FileDownloadOutlinedIcon className="mr-1.5" fontSize="small" />
                            {exportBatch.isPending && exportBatch.variables === batch.id ? "Exporting…" : "Export CSV"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
            {exportBatch.isError && <Alert severity="error" sx={{ mt: 2 }}>{getApiErrorMessage(exportBatch.error, "Unable to export this payment batch.")}</Alert>}
          </CardContent>
        </Card>
      </Stack>

      <Dialog onOpenChange={setBatchDialogOpen} open={batchDialogOpen}>
        <DialogContent aria-describedby="batch-description" className="max-w-lg">
          <DialogTitle>Create payment batch</DialogTitle>
          <DialogDescription id="batch-description">This creates one {selectedCurrency ?? ""} batch for {selectedPayments.length} selected reimbursement payment{selectedPayments.length === 1 ? "" : "s"}.</DialogDescription>
          <Form className="mt-5" onSubmit={submitBatch}>
            <FormField>
              <Label htmlFor="batch-remarks">Finance note (optional)</Label>
              <Textarea id="batch-remarks" maxLength={1000} onChange={(event) => setBatchRemarks(event.target.value)} placeholder="Internal batch context" value={batchRemarks} />
            </FormField>
            {createBatch.isError && <p className="text-sm text-rose-600 dark:text-rose-300">{getApiErrorMessage(createBatch.error, "Unable to create this payment batch.")}</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setBatchDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={createBatch.isPending || selectedPayments.length === 0} type="submit">
                {createBatch.isPending ? "Creating…" : "Create batch"}
              </Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog onOpenChange={(open) => !open && setPaidPayment(null)} open={Boolean(paidPayment)}>
        <DialogContent aria-describedby="paid-description" className="max-w-lg">
          <DialogTitle>Mark reimbursement paid</DialogTitle>
          <DialogDescription id="paid-description">Record the processor reference for {paidPayment?.payment_reference}. This updates the employee-visible reimbursement status.</DialogDescription>
          <Form className="mt-5" onSubmit={submitPaid}>
            <FormField>
              <Label htmlFor="provider-reference">Payment provider reference</Label>
              <Input autoFocus id="provider-reference" maxLength={150} onChange={(event) => setProviderReference(event.target.value)} placeholder="Processor confirmation ID" required value={providerReference} />
            </FormField>
            <FormField>
              <Label htmlFor="payment-date">Payment date (optional)</Label>
              <Input id="payment-date" onChange={(event) => setPaymentDate(event.target.value)} type="date" value={paymentDate} />
            </FormField>
            <FormField>
              <Label htmlFor="paid-remarks">Finance note (optional)</Label>
              <Textarea id="paid-remarks" maxLength={1000} onChange={(event) => setPaidRemarks(event.target.value)} placeholder="Internal settlement note" value={paidRemarks} />
            </FormField>
            {markPaid.isError && <p className="text-sm text-rose-600 dark:text-rose-300">{getApiErrorMessage(markPaid.error, "Unable to mark this reimbursement paid.")}</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setPaidPayment(null)} variant="outline">Cancel</Button>
              <Button disabled={markPaid.isPending || !providerReference.trim()} type="submit">{markPaid.isPending ? "Saving…" : "Mark paid"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>

      <Dialog onOpenChange={(open) => !open && setFailedPayment(null)} open={Boolean(failedPayment)}>
        <DialogContent aria-describedby="failed-description" className="max-w-lg">
          <DialogTitle>Mark payment for follow-up</DialogTitle>
          <DialogDescription id="failed-description">The reimbursement remains approved while finance resolves the payment issue.</DialogDescription>
          <Form className="mt-5" onSubmit={submitFailed}>
            <FormField>
              <Label htmlFor="failure-reason">Reason</Label>
              <Textarea autoFocus id="failure-reason" maxLength={1000} onChange={(event) => setFailureReason(event.target.value)} placeholder="Describe the payment issue" required value={failureReason} />
            </FormField>
            <FormField>
              <Label htmlFor="failure-remarks">Finance note (optional)</Label>
              <Textarea id="failure-remarks" maxLength={1000} onChange={(event) => setFailureRemarks(event.target.value)} placeholder="Internal follow-up note" value={failureRemarks} />
            </FormField>
            {markFailed.isError && <p className="text-sm text-rose-600 dark:text-rose-300">{getApiErrorMessage(markFailed.error, "Unable to update this payment.")}</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setFailedPayment(null)} variant="outline">Cancel</Button>
              <Button disabled={markFailed.isPending || !failureReason.trim()} type="submit">
                <ErrorOutlineIcon className="mr-1.5" fontSize="small" />
                {markFailed.isPending ? "Saving…" : "Mark failed"}
              </Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
    </Box>
  );
}
