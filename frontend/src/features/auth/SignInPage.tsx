import { supabase } from "../../auth/supabase";

export function SignInPage() {
  const handleSignIn = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: `${window.location.origin}/sign-in` },
    });
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--canvas)] flex items-center justify-center">
      <div className="flex flex-col items-center text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-white">AlgoQX</h1>
        <p className="text-[var(--ink-muted)]">Reimbursement Tool</p>
        <div className="mt-8">
          <button
            type="button"
            onClick={handleSignIn}
            className="bg-[#00D64F] text-black font-bold px-8 py-4 rounded-full"
          >
            Sign in with GitHub
          </button>
        </div>
        <p className="mt-4 text-sm text-[var(--ink-muted)]">
          Continue through your organization's approved identity provider.
        </p>
      </div>
    </div>
  );
}
