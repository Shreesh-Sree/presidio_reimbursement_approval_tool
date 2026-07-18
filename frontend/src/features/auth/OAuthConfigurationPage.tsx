export function OAuthConfigurationPage() {
  return (
    <div className="min-h-[100dvh] bg-[var(--canvas)] flex items-center justify-center">
      <div className="max-w-xl text-center">
        <h1 className="text-2xl font-bold text-[var(--ink)]">OAuth sign-in is not configured</h1>
        <p className="mt-4 text-[var(--ink-muted)]">
          Set <code className="font-mono text-sm">VITE_SUPABASE_URL</code> and{" "}
          <code className="font-mono text-sm">VITE_SUPABASE_ANON_KEY</code> in the environment.
          Do not place Supabase service-role keys in the browser.
        </p>
      </div>
    </div>
  );
}
