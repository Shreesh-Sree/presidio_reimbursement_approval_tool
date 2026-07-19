import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  API_REQUEST_TIMEOUT_MS,
  apiClient,
  authApi,
  getApiErrorMessage,
  isApiRequestCancelled,
  isRetryableApiError,
  setApiTokenProvider,
} from "../api";

const originalAdapter = apiClient.defaults.adapter;

function successfulResponse(config: InternalAxiosRequestConfig) {
  return {
    data: { user_id: "user-1", email: "employee@example.com", organization_id: "org-1", roles: ["employee"] },
    status: 200,
    statusText: "OK",
    headers: {},
    config,
  };
}

afterEach(() => {
  setApiTokenProvider(null);
  apiClient.defaults.adapter = originalAdapter;
});

describe("API token provider", () => {
  it("obtains the current in-memory token for every API request", async () => {
    const getToken = vi.fn()
      .mockResolvedValueOnce("short-lived-token-one")
      .mockResolvedValueOnce("short-lived-token-two");
    const authorizationHeaders: string[] = [];

    setApiTokenProvider(getToken);
    apiClient.defaults.adapter = async (config) => {
      authorizationHeaders.push(String(config.headers.Authorization));
      return successfulResponse(config);
    };

    await authApi.me();
    await authApi.me();

    expect(getToken).toHaveBeenCalledTimes(2);
    expect(authorizationHeaders).toEqual(["Bearer short-lived-token-one", "Bearer short-lived-token-two"]);
  });

  it("applies a bounded deadline and preserves a caller cancellation signal", async () => {
    const controller = new AbortController();
    apiClient.defaults.adapter = async (config) => {
      expect(config.timeout).toBe(API_REQUEST_TIMEOUT_MS);
      expect(config.signal).toBe(controller.signal);
      return successfulResponse(config);
    };

    await apiClient.get("/auth/me", { signal: controller.signal });
  });

  it("classifies timeout, cancellation, and retryable API errors", () => {
    const timeout = new AxiosError("timeout", "ECONNABORTED");
    const cancelled = new AxiosError("cancelled", "ERR_CANCELED");
    const server = new AxiosError("server", undefined, undefined, undefined, {
      data: {},
      status: 503,
      statusText: "Service Unavailable",
      headers: {},
      config: {} as InternalAxiosRequestConfig,
    });

    expect(getApiErrorMessage(timeout, "fallback")).toMatch(/timed out/i);
    expect(isApiRequestCancelled(cancelled)).toBe(true);
    expect(isRetryableApiError(cancelled)).toBe(false);
    expect(isRetryableApiError(server)).toBe(true);
  });

});
