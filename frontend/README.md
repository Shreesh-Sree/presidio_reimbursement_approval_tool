# Presidio frontend

React, TypeScript, Tailwind, Radix UI primitives, and Phosphor icons power the employee, approver, finance, and administrator experience.

Vercel hosts this application. Set `VITE_API_BASE_URL` to the HTTPS AWS API URL, plus Clerk's publishable key and JWT template. Do not put server secrets in frontend environment variables.

```bash
npm install
npm run dev
npm run test
npm run build
```
