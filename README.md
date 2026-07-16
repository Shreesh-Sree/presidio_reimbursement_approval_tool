# Presidio Reimbursement Platform

An India-focused expense reimbursement platform with policy enforcement, receipt OCR, multi-level approvals, payment exports, audit trails, and an advisory policy RAG assistant.

## Architecture

- **Vercel** hosts the React, TypeScript, Tailwind frontend.
- **Neon** is the sole transactional PostgreSQL database.
- **AWS** hosts the FastAPI core API, AI-review service, Tesseract receipt-intelligence service, and policy-assistant RAG service as isolated containers.
- **Appwrite** is the planned managed boundary for document storage, realtime events, and event-driven functions. It does not receive Neon credentials or make approval/payment decisions.
- **Clerk** provides OAuth sign-in. Application RBAC, user allowlisting, and approval authorization remain in the core API.

The target public API hostname is `api.presidio.algoqx.tech`; Vercel receives its API base URL only after AWS TLS/DNS validation is complete.

## Capabilities

- Expense reports, line items, receipts, INR defaults, and policy validation.
- Nested categories, vendors, policy versioning, workflow archive/restore, and role-based administration.
- Multi-level approvals, delegation, comments, SLA escalation, notifications, and finance CSV/Excel/PDF export.
- OCR with Tesseract, receipt metadata analysis, and low-confidence/unavailable states.
- Policy-document PDF/DOCX extraction and tenant/version-scoped RAG answers with citations.
- Custom React design system with Phosphor icons, Radix controls, custom dialogs/selects, and Luma loading states.

## Local development

```bash
./scripts/run-local-services.sh
cd frontend && npm run dev
```

Configure local values from `backend/.env.example` and `frontend/.env.example`. Never commit `.env` files, Appwrite keys, Neon URLs, Clerk secrets, or AWS credentials.

## Verification

```bash
cd backend && uv run pytest tests -q
cd frontend && npm run test && npm run build && npm run lint
cd ai_review_service && uv run pytest -q
cd receipt_intelligence_service && uv run pytest -q
cd policy_assistant_service && uv run pytest -q
```

## Deployment order

1. Configure Neon `presidio_core` and run Alembic migrations.
2. Configure Appwrite project, storage bucket, realtime/event settings, and API key through AWS Secrets Manager.
3. Deploy the four immutable container images from ECR to AWS.
4. Associate `api.presidio.algoqx.tech`, add the DNS validation record, and verify HTTPS health checks.
5. Set Vercel production variables: `VITE_API_BASE_URL`, Clerk public key/template, and optional Fingerprint flag.
6. Run hosted Playwright end-to-end tests, then stop local development services.
