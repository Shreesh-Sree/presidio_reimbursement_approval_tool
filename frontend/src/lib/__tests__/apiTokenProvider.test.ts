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

});
