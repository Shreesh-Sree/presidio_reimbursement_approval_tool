import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/button";
import { Form, FormField } from "../../components/ui/form";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { useAuth } from "../../auth/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/reports");
    } catch {
      setError("Login failed. Check your email and password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md items-center p-4">
      <section className="w-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-8">
        <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Presidio reimbursements</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Sign in</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Use your company account to manage reimbursement reports.</p>
        <Form className="mt-6" onSubmit={handleSubmit}>
          <FormField>
            <Label htmlFor="login-email">Email</Label>
            <Input autoComplete="email" id="login-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
          </FormField>
          <FormField>
            <Label htmlFor="login-password">Password</Label>
            <Input autoComplete="current-password" id="login-password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          </FormField>
          {error && <p className="text-sm text-rose-600" role="alert">{error}</p>}
          <Button className="w-full" disabled={isSubmitting} type="submit">{isSubmitting ? "Signing in…" : "Sign in"}</Button>
        </Form>
      </section>
    </main>
  );
}
