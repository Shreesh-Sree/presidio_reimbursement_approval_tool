# Presidio frontend

React, TypeScript, Tailwind, Radix UI primitives, and Phosphor icons power the employee, approver, finance, and administrator experience.

Azure Static Web Apps hosts this application. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for authentication, and `VITE_API_BASE_URL` for the backend API. Do not put server secrets in frontend environment variables.

```bash
npm install
npm run dev
npm run test
npm run build
```
