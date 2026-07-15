/* oxlint-disable react/only-export-components */
import { ClerkProvider } from "@clerk/clerk-react";
import type { ReactNode } from "react";

const configuredPublishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY?.trim();

/**
 * Clerk tokens must be issued by the custom template configured in Clerk. That
 * template includes the verified email claims the API validates before looking
 * up the application's email allowlist.
 */
export const clerkJwtTemplate = import.meta.env.VITE_CLERK_JWT_TEMPLATE?.trim() || "presidio-api";
export const clerkPublishableKey = configuredPublishableKey ?? "";
export const isClerkConfigured = Boolean(configuredPublishableKey);

export function ClerkProviderBoundary({ children }: { children: ReactNode }) {
  if (!isClerkConfigured) return <>{children}</>;

  return <ClerkProvider publishableKey={clerkPublishableKey}>{children}</ClerkProvider>;
}
