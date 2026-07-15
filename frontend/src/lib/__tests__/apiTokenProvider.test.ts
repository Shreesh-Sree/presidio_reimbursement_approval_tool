import axios, { type InternalAxiosRequestConfig } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient, authApi, setApiTokenProvider } from "../api";

const originalAdapter = apiClient.defaults.adapter;

function successfulResponse(config: InternalAxiosRequestConfig) {
  return {
    data: { user_id: "user-1", email: "employee@example.com", roles: ["employee"] },
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

describe("API Clerk token provider", () => {
  it("obtains the current in-memory Clerk token for every API request", async () => {
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

  it("force-refreshes once after an expired-token response", async () => {
    const getToken = vi.fn(({ forceRefresh }: { forceRefresh?: boolean } = {}) =>
      Promise.resolve(forceRefresh ? "replacement-token" : "initial-token"),
    );
    const authorizationHeaders: string[] = [];
    let attempts = 0;

    setApiTokenProvider(getToken);
    apiClient.defaults.adapter = async (config) => {
      authorizationHeaders.push(String(config.headers.Authorization));
      attempts += 1;

      if (attempts === 1) {
        throw new axios.AxiosError(
          "Unauthorized",
          "ERR_BAD_REQUEST",
          config,
          undefined,
          { data: {}, status: 401, statusText: "Unauthorized", headers: {}, config },
        );
      }

      return successfulResponse(config);
    };

    await expect(authApi.me()).resolves.toMatchObject({ email: "employee@example.com" });

    expect(getToken).toHaveBeenNthCalledWith(1, undefined);
    expect(getToken).toHaveBeenNthCalledWith(2, { forceRefresh: true });
    expect(getToken).toHaveBeenCalledTimes(2);
    expect(authorizationHeaders).toEqual(["Bearer initial-token", "Bearer replacement-token"]);
  });
});
