import { useState } from "react";
import { supabase } from "../../auth/supabase";
import { EmailSignUpForm } from "./EmailSignUpForm";

export function SignInPage() {
  const [showEmailForm, setShowEmailForm] = useState(false);
  const redirectTo = `${window.location.origin}/`;

  const handleGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo },
    });
  };

  const handleGitHub = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo },
    });
  };

  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-[var(--color-surface)] dark:bg-[#000F17]">
      <div className="w-full max-w-[400px] mx-auto px-6">
        <div className="rounded-xl bg-[var(--color-canvas)] p-10 shadow-[0_2px_8px_rgba(0,30,43,0.04),0_8px_24px_rgba(0,30,43,0.06)] dark:shadow-[0_2px_8px_rgba(0,0,0,0.2),0_8px_24px_rgba(0,0,0,0.3)]">
          <div className="text-center mb-8">
            <h1 className="text-[28px] font-semibold tracking-tight text-[var(--color-ink)]">
              AlgoQX
            </h1>
            <p className="mt-1 text-[15px] text-[var(--color-slate)]">Expense Management</p>
          </div>

          {!showEmailForm ? (
            <>
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleGoogle}
                  className="flex w-full items-center justify-center gap-3 rounded-lg border border-[var(--color-hairline-strong)] bg-[var(--color-canvas)] px-6 py-4 text-[15px] font-medium text-[var(--color-ink)] transition-all duration-150 hover:bg-[var(--color-surface)] dark:border-white/16 dark:bg-[#0D2B36] dark:text-[#F9FBFA] dark:hover:bg-[#00384D]"
                >
                  <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                  </svg>
                  Continue with Google
                </button>

                <button
                  type="button"
                  onClick={handleGitHub}
                  className="flex w-full items-center justify-center gap-3 rounded-lg bg-[#001E2B] px-6 py-4 text-[15px] font-medium text-white transition-all duration-150 hover:bg-[#0D2B36] dark:bg-[#F9FBFA] dark:text-[#001E2B] dark:hover:bg-white"
                >
                  <svg viewBox="0 0 24 24" className="size-5 fill-current" aria-hidden="true">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  Continue with GitHub
                </button>
              </div>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[var(--color-hairline)] dark:border-white/10" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="bg-[var(--color-canvas)] px-4 text-[var(--color-slate)] dark:bg-[#001E2B]">Or</span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowEmailForm(true)}
                className="w-full rounded-lg border border-[var(--color-hairline-strong)] px-6 py-4 text-[15px] font-medium text-[var(--color-ink)] transition-all duration-150 hover:bg-[var(--color-surface)] dark:border-white/16 dark:text-[#F9FBFA] dark:hover:bg-[#0D2B36]"
              >
                Request Access with Email
              </button>

              <p className="mt-6 text-center text-[13px] text-[var(--color-slate)]">
                Sign in through your organization's approved identity provider.
              </p>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setShowEmailForm(false)}
                className="mb-4 text-sm text-[var(--color-slate)] hover:text-[var(--color-ink)] dark:hover:text-[#F9FBFA]"
              >
                ← Back to sign in options
              </button>
              <EmailSignUpForm />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
