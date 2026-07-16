import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import {
  getApiErrorMessage,
  rolesApi,
  usersApi,
  workflowsApi,
  type WorkflowApprovalStep,
  type WorkflowRule,
  type WorkflowRuleInput,
} from "../../lib/api";

type StepKind = "manager" | "user" | "role";

type DraftStep = {
  kind: StepKind;
  value: string;
};

type FormValues = {
  name: string;
  minTotal: string;
  maxTotal: string;
  currencyCode: string;
  priority: string;
  isActive: boolean;
  steps: DraftStep[];
};

type WorkflowRuleFormProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rule?: WorkflowRule | null;
};

const defaultStep = (): DraftStep => ({ kind: "manager", value: "1" });

function draftStep(step: WorkflowApprovalStep): DraftStep {
  if (step.user_id) return { kind: "user", value: step.user_id };
  if (step.role_code) return { kind: "role", value: step.role_code };
  return { kind: "manager", value: String(step.manager_level ?? 1) };
}

function valuesFor(rule?: WorkflowRule | null): FormValues {
  return {
    name: rule?.name ?? "",
    minTotal: rule?.conditions.min_total?.toString() ?? "",
    maxTotal: rule?.conditions.max_total?.toString() ?? "",
    currencyCode: rule?.conditions.currency_code ?? "",
    priority: String(rule?.priority ?? 100),
    isActive: rule?.is_active ?? true,
    steps: rule?.approval_chain.length ? rule.approval_chain.map(draftStep) : [defaultStep()],
  };
}

function optionalAmount(value: string) {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function inputFor(values: FormValues): WorkflowRuleInput {
  const minTotal = optionalAmount(values.minTotal);
  const maxTotal = optionalAmount(values.maxTotal);
  const conditions = {
    ...(minTotal === undefined ? {} : { min_total: minTotal }),
    ...(maxTotal === undefined ? {} : { max_total: maxTotal }),
    ...(values.currencyCode.trim() ? { currency_code: values.currencyCode.trim().toUpperCase() } : {}),
  };
  const approval_chain = values.steps.map((step) => {
    if (step.kind === "user") return { user_id: step.value };
    if (step.kind === "role") return { role_code: step.value };
    return { manager_level: Number(step.value) };
  });
  return {
    name: values.name.trim(),
    conditions,
    approval_chain,
    priority: Number(values.priority),
    is_active: values.isActive,
  };
}

function stepDescription(step: DraftStep) {
  if (step.kind === "manager") return "Manager level";
  if (step.kind === "user") return "Named approver";
  return "Approver role";
}

export function WorkflowRuleForm({ open, onOpenChange, rule }: WorkflowRuleFormProps) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<FormValues>(() => valuesFor(rule));
  const users = useQuery({ queryKey: ["workflow-approvers"], queryFn: usersApi.list, enabled: open });
  const roles = useQuery({ queryKey: ["workflow-roles"], queryFn: rolesApi.list, enabled: open });

  useEffect(() => {
    if (open) setValues(valuesFor(rule));
  }, [open, rule]);

  const saveRule = useMutation({
    mutationFn: () => {
      const input = inputFor(values);
      return rule ? workflowsApi.update(rule.id, input) : workflowsApi.create(input);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workflow-rules"] });
      onOpenChange(false);
    },
  });

  const approvers = useMemo(
    () => (users.data ?? []).filter((user) => user.status === "active"),
    [users.data],
  );

  const updateStep = (index: number, patch: Partial<DraftStep>) => {
    setValues((current) => ({
      ...current,
      steps: current.steps.map((step, stepIndex) => (stepIndex === index ? { ...step, ...patch } : step)),
    }));
  };

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-3xl">
        <DialogTitle>{rule ? "Edit workflow rule" : "New workflow rule"}</DialogTitle>
        <DialogDescription>
          Route reports by total threshold and define the humans who must review them in order.
        </DialogDescription>
        <Form
          className="mt-5"
          onSubmit={(event) => {
            event.preventDefault();
            saveRule.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField>
              <Label htmlFor="workflow-name">Rule name</Label>
              <Input
                id="workflow-name"
                onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))}
                required
                value={values.name}
              />
            </FormField>
            <FormField>
              <Label htmlFor="workflow-priority">Priority</Label>
              <Input
                id="workflow-priority"
                min="0"
                onChange={(event) => setValues((current) => ({ ...current, priority: event.target.value }))}
                required
                type="number"
                value={values.priority}
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">Lower numbers win when multiple rules match.</p>
            </FormField>
            <FormField>
              <Label htmlFor="workflow-min-total">Minimum report total</Label>
              <Input
                id="workflow-min-total"
                min="0"
                onChange={(event) => setValues((current) => ({ ...current, minTotal: event.target.value }))}
                placeholder="No minimum"
                step="0.01"
                type="number"
                value={values.minTotal}
              />
            </FormField>
            <FormField>
              <Label htmlFor="workflow-max-total">Maximum report total</Label>
              <Input
                id="workflow-max-total"
                min="0"
                onChange={(event) => setValues((current) => ({ ...current, maxTotal: event.target.value }))}
                placeholder="No maximum"
                step="0.01"
                type="number"
                value={values.maxTotal}
              />
            </FormField>
            <FormField>
              <Label htmlFor="workflow-currency">Currency (optional)</Label>
              <Input
                id="workflow-currency"
                maxLength={10}
                onChange={(event) => setValues((current) => ({ ...current, currencyCode: event.target.value }))}
                placeholder="INR"
                value={values.currencyCode}
              />
            </FormField>
            <FormField className="flex items-center gap-2 pt-6">
              <Input
                checked={values.isActive}
                className="h-4 min-h-0 w-4"
                id="workflow-active"
                onChange={(event) => setValues((current) => ({ ...current, isActive: event.target.checked }))}
                type="checkbox"
              />
              <Label htmlFor="workflow-active">Rule is active</Label>
            </FormField>
          </div>

          <section aria-labelledby="workflow-chain-heading" className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="font-medium text-slate-950 dark:text-white" id="workflow-chain-heading">Approval chain</h3>
                <p className="text-sm text-slate-600 dark:text-slate-300">Each entry becomes the next required approval level.</p>
              </div>
              <Button
                disabled={values.steps.length >= 10}
                onClick={() => setValues((current) => ({ ...current, steps: [...current.steps, defaultStep()] }))}
                variant="outline"
              >
                Add step
              </Button>
            </div>
            {values.steps.map((step, index) => (
              <div className="grid gap-2 rounded-md bg-slate-50 p-3 sm:grid-cols-[8rem_minmax(0,1fr)_auto] sm:items-end dark:bg-slate-950" key={`${index}-${step.kind}`}>
                <FormField>
                  <Label htmlFor={`workflow-step-kind-${index}`}>Level {index + 1}</Label>
                  <Select
                    id={`workflow-step-kind-${index}`}
                    onChange={(event) => updateStep(index, { kind: event.target.value as StepKind, value: event.target.value === "manager" ? "1" : "" })}
                    value={step.kind}
                  >
                    <option value="manager">Manager</option>
                    <option value="user">Named user</option>
                    <option value="role">Role</option>
                  </Select>
                </FormField>
                <FormField>
                  <Label htmlFor={`workflow-step-value-${index}`}>{stepDescription(step)}</Label>
                  {step.kind === "manager" ? (
                    <Input
                      id={`workflow-step-value-${index}`}
                      min="1"
                      max="10"
                      onChange={(event) => updateStep(index, { value: event.target.value })}
                      required
                      type="number"
                      value={step.value}
                    />
                  ) : step.kind === "user" ? (
                    <Select
                      id={`workflow-step-value-${index}`}
                      onChange={(event) => updateStep(index, { value: event.target.value })}
                      required
                      value={step.value}
                    >
                      <option value="">Select an approver</option>
                      {approvers.map((user) => <option key={user.id} value={user.id}>{user.full_name ?? user.email} · {user.email}</option>)}
                    </Select>
                  ) : (
                    <Select
                      id={`workflow-step-value-${index}`}
                      onChange={(event) => updateStep(index, { value: event.target.value })}
                      required
                      value={step.value}
                    >
                      <option value="">Select an approval role</option>
                      {roles.data?.map((role) => <option key={role.code} value={role.code}>{role.name}</option>)}
                    </Select>
                  )}
                </FormField>
                <Button
                  aria-label={`Remove approval level ${index + 1}`}
                  disabled={values.steps.length === 1}
                  onClick={() => setValues((current) => ({ ...current, steps: current.steps.filter((_, stepIndex) => stepIndex !== index) }))}
                  variant="ghost"
                >
                  Remove
                </Button>
              </div>
            ))}
          </section>

          {saveRule.isError && <p className="text-sm text-rose-600" role="alert">{getApiErrorMessage(saveRule.error, "Unable to save this workflow rule.")}</p>}
          <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
            <Button onClick={() => onOpenChange(false)} variant="outline">Cancel</Button>
            <Button disabled={saveRule.isPending} type="submit">{saveRule.isPending ? "Saving…" : "Save rule"}</Button>
          </div>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
