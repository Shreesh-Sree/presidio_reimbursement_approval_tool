import { defineConfig, devices } from "@playwright/test";
import { LOCAL_E2E_BASE_URL, resolveE2eBaseUrl } from "./e2e/config";

const baseURL = resolveE2eBaseUrl();
const useLocalViteServer = !process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: useLocalViteServer ? {
    command: "VITE_SUPABASE_URL=http://127.0.0.1:54321 VITE_SUPABASE_ANON_KEY=e2e-public-placeholder VITE_API_BASE_URL=/api npm run dev -- --host 127.0.0.1 --port 4173 --strictPort",
    url: LOCAL_E2E_BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  } : undefined,
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
