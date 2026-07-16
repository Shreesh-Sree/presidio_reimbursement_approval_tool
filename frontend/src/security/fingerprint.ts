import FingerprintJS from "@fingerprintjs/fingerprintjs";

/**
 * Loads the open-source FingerprintJS agent only when the deployment has
 * explicitly enabled it. The identifier is kept in memory, never persisted by
 * the browser application, and is sent only to this application's API.
 */
let visitorIdPromise: Promise<string | null> | undefined;

export function getVisitorId(): Promise<string | null> {
  if (import.meta.env.VITE_FINGERPRINT_ENABLED !== "true") {
    return Promise.resolve(null);
  }

  visitorIdPromise ??= FingerprintJS.load()
    .then((agent) => agent.get())
    .then((result) => result.visitorId)
    .catch(() => null);
  return visitorIdPromise;
}
