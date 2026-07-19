# Presidio frontend

React, TypeScript, Tailwind, Radix UI primitives, and Phosphor icons power the employee, approver, finance, and administrator experience.

Azure Static Web Apps hosts this application. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for authentication, and `VITE_API_BASE_URL` for the backend API. Do not put server secrets in frontend environment variables.

```bash
npm ci
npm run dev
npm run test
npm run build
```

## Browser security and session policy

- `staticwebapp.config.json` supplies CSP, clickjacking, MIME-sniffing, referrer, permissions, and HSTS headers to Azure Static Web Apps. Its CSP permits the deployed API on `*.azurecontainerapps.io` and Supabase on `*.supabase.co`; add an explicit CSP source before changing either hosted dependency. After deployment, an operator must verify the live headers and OAuth/API/download flows at the TLS endpoint.
- Supabase sessions are intentionally stored in `sessionStorage`, not `localStorage`. They persist through the OAuth return and a same-tab refresh, then end with the browser tab/session. The API bearer-token provider is memory-only and the React Query cache is cleared before sign-out and whenever the authenticated subject or returned organization scope changes.
- Browser API calls default to a 15-second deadline (`VITE_API_REQUEST_TIMEOUT_MS`, bounded to 1–60 seconds). Axios accepts caller-provided `AbortSignal`s; request cancellation is not retried. Session keepalive checks are serialized so a hung Supabase call cannot overlap later checks.

## Hermetic E2E tests

`npm run test:e2e` starts a local Vite server at `http://127.0.0.1:4173` by default and uses placeholder public auth configuration; it never defaults to a deployed site. Install the Chromium test browser once before running it:

```bash
npx playwright install chromium
npm run test:e2e
```

On Linux CI images that do not already include browser libraries, use `npx playwright install --with-deps chromium` during image setup. An explicit remote target is rejected unless `E2E_ALLOW_REMOTE=1` is set, and production-like hostnames (including `presidio.algoqx.tech`) are always refused. Only use the opt-in with a disposable, non-production environment.
