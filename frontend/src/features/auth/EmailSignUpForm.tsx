import { useState } from "react";
import { supabase } from "../../auth/supabase";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { apiClient, getApiErrorMessage } from "../../lib/api";

export function EmailSignUpForm() {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      // Create Supabase auth user
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
        },
      });

      if (signUpError) throw signUpError;

      // Create access request in backend
      await apiClient.post("/access-requests", {
        email,
        full_name: fullName,
      });

      setSuccess(true);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Failed to sign up. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="rounded-xl bg-green-50 p-6 dark:bg-green-900/20">
        <h3 className="text-lg font-semibold text-green-900 dark:text-green-100">
          Request Submitted
        </h3>
        <p className="mt-2 text-sm text-green-800 dark:text-green-200">
          Your access request has been sent to the administrator. You'll receive an email once your account is approved.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="fullName">Full Name</Label>
        <Input
          id="fullName"
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
          disabled={isLoading}
          className="mt-1"
        />
      </div>

      <div>
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isLoading}
          className="mt-1"
        />
      </div>

      <div>
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          disabled={isLoading}
          className="mt-1"
        />
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
          Minimum 8 characters
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-200">
          {error}
        </div>
      )}

      <Button type="submit" disabled={isLoading} className="w-full">
        {isLoading ? "Submitting..." : "Request Access"}
      </Button>
    </form>
  );
}
