import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { Button } from "../../components/ui/button";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { getApiErrorMessage, type BootstrapInput } from "../../lib/api";

type BootstrapForm = BootstrapInput & {
  confirmPassword: string;
};

const initialValues: BootstrapForm = {
  organization_name: "Presidio",
  organization_code: "PRESIDIO",
  department_name: "General",
  department_code: "GENERAL",
  full_name: "",
  email: "",
  password: "",
  confirmPassword: "",
};

function normalizeCode(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, "_");
}

export function BootstrapPage() {
  const { bootstrap } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState<BootstrapForm>(initialValues);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateValue = <Key extends keyof BootstrapForm>(key: Key, value: BootstrapForm[Key]) => {
    setValues((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (values.password !== values.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await bootstrap({
        organization_name: values.organization_name.trim(),
        organization_code: normalizeCode(values.organization_code),
        department_name: values.department_name.trim(),
        department_code: normalizeCode(values.department_code),
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        password: values.password,
      });
      navigate("/policies", { replace: true });
    } catch (submissionError) {
      setError(getApiErrorMessage(submissionError, "Unable to complete setup. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl items-center p-4 sm:p-6">
      <section className="w-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Presidio reimbursements</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Set up your organization</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Create the first administrator. For security, this setup can run only once.</p>

        <Form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <fieldset className="space-y-4">
            <legend className="text-sm font-semibold text-slate-950 dark:text-white">Organization</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField>
                <Label htmlFor="bootstrap-organization-name">Organization name</Label>
                <Input autoComplete="organization" id="bootstrap-organization-name" onChange={(event) => updateValue("organization_name", event.target.value)} required value={values.organization_name} />
              </FormField>
              <FormField>
                <Label htmlFor="bootstrap-organization-code">Organization code</Label>
                <Input id="bootstrap-organization-code" maxLength={50} onChange={(event) => updateValue("organization_code", event.target.value.toUpperCase())} required value={values.organization_code} />
              </FormField>
              <FormField>
                <Label htmlFor="bootstrap-department-name">Initial department</Label>
                <Input id="bootstrap-department-name" onChange={(event) => updateValue("department_name", event.target.value)} required value={values.department_name} />
              </FormField>
              <FormField>
                <Label htmlFor="bootstrap-department-code">Department code</Label>
                <Input id="bootstrap-department-code" maxLength={50} onChange={(event) => updateValue("department_code", event.target.value.toUpperCase())} required value={values.department_code} />
              </FormField>
            </div>
          </fieldset>

          <fieldset className="space-y-4 border-t border-slate-200 pt-5 dark:border-slate-800">
            <legend className="text-sm font-semibold text-slate-950 dark:text-white">First administrator</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField className="sm:col-span-2">
                <Label htmlFor="bootstrap-full-name">Full name</Label>
                <Input autoComplete="name" id="bootstrap-full-name" onChange={(event) => updateValue("full_name", event.target.value)} required value={values.full_name} />
              </FormField>
              <FormField>
                <Label htmlFor="bootstrap-email">Email</Label>
                <Input autoComplete="email" id="bootstrap-email" onChange={(event) => updateValue("email", event.target.value)} required type="email" value={values.email} />
              </FormField>
              <FormField>
                <Label htmlFor="bootstrap-password">Password</Label>
                <Input autoComplete="new-password" id="bootstrap-password" minLength={8} onChange={(event) => updateValue("password", event.target.value)} required type="password" value={values.password} />
              </FormField>
              <FormField className="sm:col-start-2">
                <Label htmlFor="bootstrap-password-confirmation">Confirm password</Label>
                <Input autoComplete="new-password" id="bootstrap-password-confirmation" minLength={8} onChange={(event) => updateValue("confirmPassword", event.target.value)} required type="password" value={values.confirmPassword} />
              </FormField>
            </div>
          </fieldset>

          {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/40 dark:text-rose-200" role="alert">{error}</p>}
          <Button className="w-full" disabled={isSubmitting} type="submit">{isSubmitting ? "Creating organization…" : "Create organization and continue"}</Button>
        </Form>

        <p className="mt-5 text-center text-sm text-slate-600 dark:text-slate-300">Already set up? <Link className="font-medium text-indigo-600 underline underline-offset-2 dark:text-indigo-300" to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
