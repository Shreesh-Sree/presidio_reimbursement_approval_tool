import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { LoadingState } from "../../components/ui/loading-state";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { delegationsApi, getApiErrorMessage } from "../../lib/api";

function asUtcDate(value: string, atEndOfDay = false) {
  return `${value}T${atEndOfDay ? "23:59" : "00:00"}:00.000Z`;
}

function displayDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(date);
}

export function DelegationsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [delegateId, setDelegateId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [scope, setScope] = useState("approval");
  const [remarks, setRemarks] = useState("");
  const delegations = useQuery({ queryKey: ["delegations"], queryFn: () => delegationsApi.list() });
  const candidates = useQuery({ queryKey: ["delegation-candidates"], queryFn: delegationsApi.candidates, enabled: dialogOpen });
  const create = useMutation({
    mutationFn: () => delegationsApi.create({
      delegate_user_id: delegateId,
      start_date: asUtcDate(startDate),
      end_date: asUtcDate(endDate, true),
      scope,
      remarks: remarks.trim() || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["delegations"] });
      setDialogOpen(false);
      setDelegateId("");
      setStartDate("");
      setEndDate("");
      setScope("approval");
      setRemarks("");
    },
  });
  const deactivate = useMutation({
    mutationFn: delegationsApi.deactivate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["delegations"] }),
  });

  const canSave = delegateId !== "" && startDate !== "" && endDate !== "" && endDate >= startDate;

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between dark:border-slate-800">
        <div>
          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Manager workspace</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Approval delegation</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600 dark:text-slate-300">Assign a temporary, eligible approver while you are unavailable. The workflow keeps your name as the original approval owner.</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>Delegate approvals</Button>
      </header>

      <section aria-labelledby="active-delegations-heading" className="space-y-4">
        <div>
          <h2 className="font-semibold text-slate-950 dark:text-white" id="active-delegations-heading">Active delegations</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Only one overlapping approval delegation is allowed, so responsibility is always clear.</p>
        </div>
      {delegations.isLoading && <LoadingState label="Loading delegations" />}
        {delegations.isError && <p className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-100">{getApiErrorMessage(delegations.error, "Unable to load delegations.")}</p>}
        {delegations.data?.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">No active delegation is configured.</p>}
        <div className="grid gap-4 md:grid-cols-2">
          {delegations.data?.map((delegation) => (
            <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900" key={delegation.id}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Delegated to</p>
                  <h3 className="mt-1 font-semibold text-slate-950 dark:text-white">{delegation.delegate_name ?? "Eligible approver"}</h3>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{displayDate(delegation.start_date)} – {displayDate(delegation.end_date)}</p>
                </div>
                <span className="w-fit rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">Active</span>
              </div>
              <p className="mt-4 text-sm text-slate-700 dark:text-slate-200">Scope: {delegation.scope === "all" ? "All configured work" : "Approval tasks"}</p>
              {delegation.remarks && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{delegation.remarks}</p>}
              <Button className="mt-5" disabled={deactivate.isPending} onClick={() => deactivate.mutate(delegation.id)} variant="outline">End delegation</Button>
            </article>
          ))}
        </div>
      </section>

      <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
        <DialogContent>
          <DialogTitle>Delegate approval tasks</DialogTitle>
          <DialogDescription>Your substitute must be an active approver in your organization. Existing tasks retain an auditable ownership trail.</DialogDescription>
          <Form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault();
              if (canSave) create.mutate();
            }}
          >
            <FormField>
              <Label htmlFor="delegation-candidate">Delegate to</Label>
              <Select id="delegation-candidate" onChange={(event) => setDelegateId(event.target.value)} required value={delegateId}>
                <option value="">Select an eligible approver</option>
                {candidates.data?.map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
              </Select>
              {candidates.isLoading && <p className="text-xs text-slate-500 dark:text-slate-400">Loading eligible approvers…</p>}
              {candidates.isError && <p className="text-xs text-rose-600">Unable to load eligible approvers.</p>}
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField>
                <Label htmlFor="delegation-start">Starts on</Label>
                <Input id="delegation-start" onChange={(event) => setStartDate(event.target.value)} required type="date" value={startDate} />
              </FormField>
              <FormField>
                <Label htmlFor="delegation-end">Ends on</Label>
                <Input id="delegation-end" min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} required type="date" value={endDate} />
              </FormField>
            </div>
            <FormField>
              <Label htmlFor="delegation-scope">Scope</Label>
              <Select id="delegation-scope" onChange={(event) => setScope(event.target.value)} value={scope}>
                <option value="approval">Approval tasks</option>
                <option value="all">All configured work</option>
              </Select>
            </FormField>
            <FormField>
              <Label htmlFor="delegation-remarks">Reason (optional)</Label>
              <Textarea id="delegation-remarks" maxLength={2000} onChange={(event) => setRemarks(event.target.value)} placeholder="e.g. Annual leave" value={remarks} />
            </FormField>
            {create.isError && <p className="text-sm text-rose-600">{getApiErrorMessage(create.error, "Unable to save this delegation.")}</p>}
            <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
              <Button onClick={() => setDialogOpen(false)} variant="outline">Cancel</Button>
              <Button disabled={!canSave || create.isPending} type="submit">{create.isPending ? "Saving…" : "Save delegation"}</Button>
            </div>
          </Form>
        </DialogContent>
      </Dialog>
    </main>
  );
}
