import { SignIn } from "@clerk/react";

export function SignInPage() {
  return <main className="signin-page"><section><p className="repl-eyebrow">Presidio reimbursements</p><h1>Expenses,<br />clearly approved.</h1><p>Move every business expense from receipt to settlement with clarity, care, and a human touch.</p></section><div className="signin-card"><p className="repl-eyebrow">Welcome back</p><h2>Sign in with your work account</h2><p>Continue through your organization’s approved OAuth provider.</p><SignIn fallbackRedirectUrl="/reports" path="/sign-in" routing="path" transferable={false} /></div></main>;
}
