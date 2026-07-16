import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { approvalsApi, type Report } from "../../lib/api";

type ApprovalAction = "approve" | "reject" | "send_back";

type ActionBarProps = {
  reportId: string;
  disabled?: boolean;
  onCompleted?: (report: Report) => void;
};

export function ActionBar({ reportId, disabled = false, onCompleted }: ActionBarProps) {
  const queryClient = useQueryClient();
  const [remarks, setRemarks] = useState("");
  const actionMutation = useMutation({
    mutationFn: (action: ApprovalAction) => {
      if (action === "approve") return approvalsApi.approve(reportId, remarks.trim());
      if (action === "reject") return approvalsApi.reject(reportId, remarks.trim());
      return approvalsApi.sendBack(reportId, remarks.trim());
    },
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: ["approval-queue"] });
      queryClient.invalidateQueries({ queryKey: ["report", reportId] });
      setRemarks("");
      onCompleted?.(report);
    },
  });

  const submitAction = (action: ApprovalAction) => {
    if (action !== "approve" && remarks.trim() === "") return;
    actionMutation.mutate(action);
  };

  return (
    <section aria-labelledby="approval-actions" className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div>
        <h2 className="text-lg font-semibold text-slate-950 dark:text-white" id="approval-actions">Approval decision</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Remarks are shared with the report owner. Remarks are required for rejection or send-back.</p>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="approval-remarks">Remarks</Label>
        <Textarea disabled={disabled || actionMutation.isPending} id="approval-remarks" onChange={(event) => setRemarks(event.target.value)} placeholder="Add context for the employee" value={remarks} />
      </div>
      {actionMutation.isError && <p className="text-sm text-orange-600">Unable to submit this decision. Please try again.</p>}
      {actionMutation.isSuccess && <p aria-live="polite" className="text-sm text-orange-700 dark:text-orange-300">Decision submitted.</p>}
      <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
        <Button disabled={disabled || actionMutation.isPending || remarks.trim() === ""} onClick={() => submitAction("send_back")} variant="secondary">
          Send back
        </Button>
        <Button disabled={disabled || actionMutation.isPending || remarks.trim() === ""} onClick={() => submitAction("reject")} variant="destructive">
          Reject
        </Button>
        <Button disabled={disabled || actionMutation.isPending} onClick={() => submitAction("approve")}>
          Approve
        </Button>
      </div>
    </section>
  );
}
