export const LOCAL_E2E_BASE_URL = "http://127.0.0.1:4173";

const loopbackHostnames = new Set(["127.0.0.1", "::1", "[::1]", "0.0.0.0", "localhost"]);
const productionHostnames = new Set(["presidio.algoqx.tech"]);

function isLoopbackHostname(hostname: string) {
  const normalized = hostname.toLowerCase();
  return loopbackHostnames.has(normalized) || normalized.endsWith(".localhost");
}

function isProductionLikeHostname(hostname: string) {
  const normalized = hostname.toLowerCase();
  return productionHostnames.has(normalized) || /(^|[.-])(prod|production)([.-]|$)/.test(normalized);
}

/**
 * Browser tests must be hermetic by default. A remote target needs an
 * affirmative opt-in and production-like hostnames are never accepted.
 */
export function resolveE2eBaseUrl(
  candidate = process.env.E2E_BASE_URL,
  allowRemote = process.env.E2E_ALLOW_REMOTE === "1",
) {
  const configuredUrl = candidate?.trim() || LOCAL_E2E_BASE_URL;
  let url: URL;
  try {
    url = new URL(configuredUrl);
  } catch {
    throw new Error(`E2E_BASE_URL must be an absolute HTTP(S) URL; received ${JSON.stringify(configuredUrl)}.`);
  }

  if (!/^https?:$/.test(url.protocol) || url.username || url.password) {
    throw new Error("E2E_BASE_URL must be an unauthenticated HTTP(S) URL.");
  }

  if (isProductionLikeHostname(url.hostname)) {
    throw new Error(`Refusing to run E2E tests against production-like host ${url.hostname}.`);
  }

  if (!isLoopbackHostname(url.hostname) && !allowRemote) {
    throw new Error(
      "Refusing a non-local E2E target. Set E2E_ALLOW_REMOTE=1 only for a disposable, non-production environment.",
    );
  }

  return url.toString().replace(/\/$/, "");
}
