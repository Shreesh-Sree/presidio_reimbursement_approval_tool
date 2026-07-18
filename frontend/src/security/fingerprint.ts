import FingerprintJS from "@fingerprintjs/fingerprintjs";

let visitorIdPromise: Promise<string | null> | undefined;

function initFingerprint(): Promise<string | null> {
  if (import.meta.env.VITE_FINGERPRINT_ENABLED !== "true") {
    return Promise.resolve(null);
  }

  visitorIdPromise ??= FingerprintJS.load()
    .then((agent) => agent.get())
    .then((result) => result.visitorId)
    .catch(() => null);
  return visitorIdPromise;
}

// Start eagerly so it resolves before first API call
initFingerprint();

export function getVisitorId(): Promise<string | null> {
  return visitorIdPromise ?? Promise.resolve(null);
}
