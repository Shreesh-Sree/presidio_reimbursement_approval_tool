import { useEffect, useMemo, useState } from "react";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select } from "../../components/ui/select";
import type { ManagedUser, RoleOption, UserInput } from "./api";

type FormValues = {
  email: string;
  full_name: string;
  roles: string[];
  manager_id: string;
};

type UserFormProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: ManagedUser | null;
  users: ManagedUser[];
  roles: RoleOption[];
  onSubmit: (input: UserInput) => void;
  isPending: boolean;
  isError: boolean;
};

function emptyValues(roles: RoleOption[]): FormValues {
  return {
    email: "",
    full_name: "",
    roles: roles.some((role) => role.code === "employee") ? ["employee"] : [],
    manager_id: "",
  };
}

function valuesFor(user: ManagedUser | null, roles: RoleOption[]): FormValues {
  if (!user) return emptyValues(roles);
  return {
    email: user.email,
    full_name: user.full_name,
    roles: user.roles,
    manager_id: user.manager_id ?? "",
  };
}

export function UserForm({
  open,
  onOpenChange,
  user,
  users,
  roles,
  onSubmit,
  isPending,
  isError,
}: UserFormProps) {
  const [values, setValues] = useState<FormValues>(() => valuesFor(user, roles));
  const [validationMessage, setValidationMessage] = useState("");
  const isEditing = Boolean(user);
  const managerCandidates = useMemo(
    () => users.filter((candidate) =>
      candidate.id !== user?.id
      && candidate.status.toLowerCase() === "active"
      && candidate.roles.some((role) => role.toLowerCase() === "approver"),
    ),
    [user?.id, users],
  );

  useEffect(() => {
    if (!open) return;
    setValues(valuesFor(user, roles));
    setValidationMessage("");
  }, [open, roles, user]);

  const setRoleSelected = (roleCode: string, selected: boolean) => {
    setValues((current) => ({
      ...current,
      roles: selected
        ? [...current.roles, roleCode]
        : current.roles.filter((role) => role !== roleCode),
    }));
  };

  const submit = () => {
    if (values.roles.length === 0) {
      setValidationMessage("Select at least one role.");
      return;
    }

    const input: UserInput = {
      email: values.email.trim(),
      full_name: values.full_name.trim(),
      roles: values.roles,
      manager_id: values.manager_id || null,
    };

    onSubmit(input);
  };

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent>
        <DialogTitle>{isEditing ? "Edit user" : "Invite user"}</DialogTitle>
        <DialogDescription>
          {isEditing
            ? "Update roles and reporting ownership for this user."
            : "This creates a pending invitation and the application access record together. The recipient completes access by accepting the email invitation."}
        </DialogDescription>
        <Form
          className="mt-5"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField>
              <Label htmlFor="user-full-name">Full name</Label>
              <Input
                id="user-full-name"
                onChange={(event) => setValues((current) => ({ ...current, full_name: event.target.value }))}
                required
                value={values.full_name}
              />
            </FormField>
            <FormField>
              <Label htmlFor="user-email">Email</Label>
              <Input
                autoComplete="email"
                id="user-email"
                onChange={(event) => setValues((current) => ({ ...current, email: event.target.value }))}
                required
                type="email"
                value={values.email}
              />
            </FormField>
          </div>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-900 dark:text-slate-100">Roles</legend>
            <p className="text-sm text-slate-600 dark:text-slate-300">There are four roles. A manager can also retain their employee role.</p>
            <div className="grid gap-2 sm:grid-cols-3">
              {roles.map((role) => {
                const roleId = `user-role-${role.code}`;
                return (
                  <label className="flex min-h-10 items-center gap-2 rounded-md border border-slate-300 px-3 text-sm text-slate-800 dark:border-slate-700 dark:text-slate-100" htmlFor={roleId} key={role.code}>
                    <input
                      checked={values.roles.includes(role.code)}
                      className="size-4 accent-orange-600"
                      id={roleId}
                      onChange={(event) => setRoleSelected(role.code, event.target.checked)}
                      type="checkbox"
                    />
                    {role.name}
                  </label>
                );
              })}
            </div>
          </fieldset>

          <FormField>
            <Label htmlFor="user-manager">Reporting manager</Label>
            <Select
              id="user-manager"
              onChange={(event) => setValues((current) => ({ ...current, manager_id: event.target.value }))}
              value={values.manager_id}
            >
              <option value="">No reporting manager</option>
              {managerCandidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name} ({candidate.email})
                </option>
              ))}
            </Select>
            {managerCandidates.length === 0 && (
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-300">
                No reporting managers yet. Create an active user with the Manager / Approver role first, then assign them here.
              </p>
            )}
          </FormField>

          {validationMessage && <p className="text-sm text-orange-600 dark:text-orange-300" role="alert">{validationMessage}</p>}
          {isError && <p className="text-sm text-orange-600 dark:text-orange-300" role="alert">Unable to save this user. Review the details and try again.</p>}

          <div className="flex flex-col-reverse justify-end gap-2 pt-2 sm:flex-row">
            <Button disabled={isPending} onClick={() => onOpenChange(false)} variant="outline">Cancel</Button>
            <Button disabled={isPending || roles.length === 0} type="submit">
              {isPending ? "Saving…" : isEditing ? "Save changes" : "Send invitation"}
            </Button>
          </div>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
