import { describe, expect, it } from "vitest";
import staticWebAppConfig from "../../../staticwebapp.config.json";
import { LOCAL_E2E_BASE_URL, resolveE2eBaseUrl } from "../../../e2e/config";

describe("browser test and static-host safety configuration", () => {
  it("defaults E2E to a local server and rejects production-like or implicit remote targets", () => {
    expect(resolveE2eBaseUrl(undefined, false)).toBe(LOCAL_E2E_BASE_URL);
    expect(() => resolveE2eBaseUrl("https://presidio.algoqx.tech", true)).toThrow(/production-like/i);
    expect(() => resolveE2eBaseUrl("https://staging.example.test", false)).toThrow(/non-local/i);
    expect(resolveE2eBaseUrl("https://staging.example.test", true)).toBe("https://staging.example.test");
  });

  it("ships the required browser hardening headers with the static app", () => {
    const headers = staticWebAppConfig.globalHeaders;
    expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(headers["Content-Security-Policy"]).toContain("object-src 'none'");
    expect(headers["X-Content-Type-Options"]).toBe("nosniff");
    expect(headers["X-Frame-Options"]).toBe("DENY");
    expect(headers["Referrer-Policy"]).toBe("strict-origin-when-cross-origin");
    expect(headers["Permissions-Policy"]).toContain("camera=()");
  });
});
