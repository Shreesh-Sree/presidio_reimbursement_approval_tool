import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { policiesApi, type Policy, type PolicyInput } from "../../lib/api";
import { PolicyUpload } from "./PolicyUpload";
import { RuleEditor } from "./RuleEditor";

type PolicyFormProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  policy?: Policy | null;
};

function valuesFor(policy?: Policy | null): PolicyInput {
  return {
    name: policy?.name ?? "",
    version_label: policy?.version_label ?? "",
    effective_from: policy?.effective_from?.slice(0, 10) ?? "",
    effective_to: policy?.effective_to?.slice(0, 10) ?? null,
    rules: policy?.rules ?? [],
  };
}

export function PolicyForm({ open, onOpenChange, policy }: PolicyFormProps) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<PolicyInput>(() => valuesFor(policy));

  useEffect(() => {
    if (open) setValues(valuesFor(policy));
  }, [open, policy]);

  const savePolicy = useMutation({
    mutationFn: () => (policy ? policiesApi.update(policy.id, values) : policiesApi.create(values)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      onOpenChange(false);
    },
  });

  const updateValue = <Key extends keyof PolicyInput>(key: Key, value: PolicyInput[Key]) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogTitle>{policy ? "Edit policy version" : "New policy version"}</DialogTitle>
        <DialogDescription>Define the effective dates and the limits employees must follow.</DialogDescription>
        <Form
          className="mt-5"
          onSubmit={(event) => {
            event.preventDefault();
            savePolicy.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField>
              <Label htmlFor="policy-name">Name</Label>
              <Input
                id="policy-name"
                onChange={(event) => updateValue("name", event.target.value)}
                required
                value={values.name}
              />
            </FormField>
            <FormField>
              <Label htmlFor="policy-version">Version label</Label>
              <Input
                id="policy-version"
                onChange={(event) => updateValue("version_label", event.target.value)}
                required
                value={values.version_label}
              />
            </FormField>
            <FormField>
              <Label htmlFor="policy-effective-from">Effective from</Label>
              <Input
                id="policy-effective-from"
                onChange={(event) => updateValue("effective_from", event.target.value)}
                required
                type="date"
                value={values.effective_from}
              />
            </FormField>
            <FormField>
              <Label htmlFor="policy-effective-to">Effective to</Label>
              <Input
                id="policy-effective-to"
                onChange={(event) => updateValue("effective_to", event.target.value || null)}
                type="date"
                value={values.effective_to ?? ""}
              />
            </FormField>
          </div>

          <RuleEditor onChange={(rules) => updateValue("rules", rules)} value={values.rules} />

          {policy && <PolicyUpload policyId={policy.id} />}
          {savePolicy.isError && <p className="text-sm text-rose-600">Unable to save this policy version.</p>}
          <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
            <Button onClick={() => onOpenChange(false)} variant="outline">
              Cancel
            </Button>
            <Button disabled={savePolicy.isPending} type="submit">
              {savePolicy.isPending ? "Saving…" : "Save policy"}
            </Button>
          </div>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
