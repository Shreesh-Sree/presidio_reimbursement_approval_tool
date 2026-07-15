# Engineering learning matrix

This project is a working application and a learning portfolio.  The aim is
to connect each curriculum topic to a real decision, test, or deliverable—not
to add a framework merely to check a box.  Each feature PR should update the
relevant evidence link below when it materially changes the architecture.

## How to use this matrix

- **Implemented evidence** points to code or infrastructure that already
  demonstrates the topic.
- **Next evidence** is a small, useful project task that demonstrates a topic
  not yet exercised by the application.
- **Scope decision** records why an alternative is deferred.  Deferred does
  not mean forgotten; it prevents unnecessary cost and complexity.

## Architecture anchor

The application is a React/Vite client, a FastAPI reimbursement API, and three
isolated supporting services: advisory AI review, receipt intelligence, and a
policy assistant.  Each service owns its datastore and cannot approve, reject,
route, or pay a report.  Production infrastructure is described by the modular
Terraform configuration in `deployment/terraform/`; it provisions the services
as private, separately credentialed containers, but this repository does not
apply infrastructure or deploy a runtime without explicit approval.

## Week 1 — advanced foundations and problem solving

| Topic | Implemented evidence | Next evidence / scope decision |
| --- | --- | --- |
| GitHub collaboration, branches, reviews | `PLAN.md` and `TASKS.md` describe phased delivery; [`CONTRIBUTING.md`](../CONTRIBUTING.md) defines short-lived branches and review gates. | Use a feature/fix/docs branch per logical change, open a PR, and require the CI checks in [`.github/BRANCH_PROTECTION.md`](../.github/BRANCH_PROTECTION.md). |
| Hash maps | `ai_review_service/ai_review_service/rules.py` uses maps for receipt digests, claim signatures, category totals, and historical baselines. | Add a test that compares the map-based duplicate check with an intentionally small fixture and explain its linear scan behavior in the PR. |
| Recursion, recursion trees, DAG safety | `backend/app/services/org_chart_service.py` recursively builds a cycle-safe manager tree; `OrgChartPage.tsx` and `CategoriesPage.tsx` recursively render nested data. | Keep cycle guards in both persistence and presentation paths; add depth/cycle fixtures before expanding hierarchy features. |
| SQL joins, indexing, transactions | SQLAlchemy services and Alembic migrations implement normalized relationships; `004_payment_operations`, `005_delegated_approvals`, and `006_policy_tenant_scope` add queue, batch, due-date, audit, and tenant indexes. | Add `EXPLAIN` notes and measured composite indexes when report lists or approval queues show a real query need. Use one transaction for each payment/approval state transition and audit event. |
| System design: scale, fault tolerance, caching, load balancing | `deployment/README.md` documents the intentionally single-host, low-cost design, private RDS, static CloudFront delivery, and separate advisory-service boundaries. | CloudFront caches static assets and TanStack Query caches client reads; do not add Redis, an ALB, or Kubernetes until measured load justifies their fixed cost.  Add a reviewed queue/independent runtime only when service volume needs it. |
| SDLC | Feature folders, migrations, unit tests, Terraform, and this CI workflow provide a build-to-release path. | Use issue → branch → failing test where applicable → implementation → review → CI → release notes.  Record material design decisions as ADRs under `docs/adr/`. |

## Week 2 — backend engineering and cloud integration

| Topic | Implemented evidence | Next evidence / scope decision |
| --- | --- | --- |
| Application design / MVC-style separation | FastAPI routes live in `backend/app/api/routes/`, domain work in `backend/app/services/`, and persistence models in `backend/app/models/`. | FastAPI is the selected backend framework; Node/Flask layouts are comparison exercises.  Keep route handlers thin and put authorization-sensitive business rules in services with focused tests. |
| Middleware: global and route-specific | `backend/app/main.py` configures CORS and `RequestCorrelationMiddleware`; `app/core/deps.py` supplies route-level authentication and permission dependencies. | Keep request IDs opaque, expose `X-Request-ID`, and retain route permissions for protected operations.  Add rate limits separately rather than coupling them to authentication. |
| Async patterns | FastAPI uses background tasks for notification delivery; AI review has a bounded async worker; the approval queue performs an idempotent SLA-overdue sweep. The manual receipt and policy calls have bounded optional-service timeouts and never run during approval decisions. | Do not make approvals wait for an LLM or receipt analysis. Add an AI-owned queue only when a single-process worker becomes a measured bottleneck. |
| Microservices | `ai_review_service/`, `receipt_intelligence_service/`, and `policy_assistant_service/` each have independent contracts, tokens, persistence, and no core ORM import. | Keep every future AI capability in a separately owned service/database boundary.  The receipt service accepts digest metadata only; the policy assistant scopes retrieval by tenant and policy version. |
| Logging | `backend/app/core/observability.py` emits privacy-safe JSON request logs with correlation IDs; receipt/policy services log only safe operational metadata; Terraform creates CloudWatch log groups. | Add CloudWatch metric filters/alarms for API 5xx and AI-service failures before introducing distributed tracing or a paid observability platform. |
| Authentication and authorization | Clerk OAuth sessions are verified by `app/core/clerk.py` (RS256/JWKS, issuer, audience, and authorized party); `oauth_access_service.py` gates verified emails against the app allowlist and `require_permission()` enforces database-backed RBAC. | Keep OAuth identity separate from application authorization: never trust role claims from an IdP, do not reintroduce a browser password flow, and review any identity-provider or allowlist policy change as security-sensitive. |
| API design, pagination, filtering, sorting | Typed Pydantic inputs/outputs and FastAPI OpenAPI docs are available; report lists filter by status and finance queues/batches expose `limit`/`offset`. | Extend pagination/filter/sort metadata consistently before large list views.  Keep REST because resources and workflows map cleanly to it; document GraphQL as a comparison, not a parallel API. |
| Rate limiting and throttling | No distributed limiter is deployed. | Add a narrowly scoped login/bootstrap limiter before public exposure.  Avoid a managed API gateway solely for this feature while the cost cap is active. |
| API documentation | FastAPI exposes `/docs`; module README files document local/production operation. | Add examples for the most important error responses and maintain an API change section in PR descriptions. |
| Finance payment lifecycle | `payment_service.py`, finance routes, and migration `004_payment_operations` implement pending/batched/exported/paid/failed transitions, CSV batches, provider references, and immutable payment events. | Keep bank/ERP connectivity out of the core workflow until a provider contract, idempotency strategy, and finance approval are reviewed. |
| Delegation and SLA | `delegation_service.py`, `approval_service.py`, and migration `005_delegated_approvals` preserve the original approver, acting-for audit trail, due date, reminder, and escalation timestamps. | The queue performs a small-deployment sweep today.  A scheduler/queue can invoke the same idempotent service method later for stricter timing. |
| Containers and cloud deployment | `deployment/docker/` has backend and advisory-service Dockerfiles; Terraform provisions private, separately networked runtime containers and scripts build/push the four images. | AWS is the selected cloud. ECS/Cloud Run tutorials are comparison exercises until measured scale requires a different runtime. Terraform validation is safe in CI; any apply remains explicitly human-authorized. |

## Week 3 — frontend engineering and UX

| Topic | Implemented evidence | Next evidence / scope decision |
| --- | --- | --- |
| TypeScript, React hooks, re-render control | The frontend is TypeScript; feature pages use `useState`, `useEffect`, `useMemo`, TanStack Query, and React Router.  `ThemeModeProvider` uses memoized theme/context values and callbacks. | Use `useMemo`/`useCallback` only after profiling an expensive or unstable render; capture the reason in the PR rather than applying them mechanically. |
| Error boundaries and developer tools | `AppErrorBoundary.tsx` provides a route-level recovery screen; Query loading/error states exist across feature pages. | Use React DevTools/Lighthouse before performance or accessibility claims and connect boundary reporting only to a privacy-reviewed monitoring sink. |
| State management | `AuthContext` owns authentication context; server state is owned by TanStack Query. | Keep Redux/Zustand out until a documented cross-feature client-state problem cannot be expressed with context/query state. |
| Component libraries and layout systems | The Material-inspired UI uses MUI theme tokens/components alongside the existing responsive utilities; `appTheme.ts` centralizes palette, typography, shape, focus, and component rules. | TailGrid is a design reference rather than a second runtime component library.  Keep shared visual tokens centralized and avoid duplicate styling systems. |
| Dynamic navigation and routing | `App.tsx` derives navigation and protected routes from permissions, then lazy-loads each protected feature route behind a shared loading boundary. | Preserve permission checks on the API as the authority; client routing is usability, not authorization. Profile new chunks before adding prefetching. |
| Material-inspired light/dark theme | `ThemeModeProvider.tsx` supplies persisted light/dark/system selection, `appTheme.ts` creates the MUI palette, and the document color scheme/Tailwind dark class stay synchronized. | Continue contrast, keyboard-focus, and system-preference tests; do not add a second theme system solely for appearance. |
| API consumption and environment variables | `src/lib/api.ts` centralizes Axios calls and Vite environment usage; feature pages use TanStack Query mutations/queries. | Define cache keys, invalidation behavior, empty/error states, and environment-variable documentation for each new API domain. |
| Accessibility and responsiveness | Pages use flex/grid breakpoints and semantic tree roles; the MUI theme supplies visible focus treatment; analytics uses labelled tables and a chart with an accessible label. | Add automated axe/Lighthouse checks and keyboard/contrast coverage for new dialogs, charts, and theme controls. |
| Browser storage, JWT, and CSRF | Clerk owns the browser session; `AuthContext` holds only a short-lived API bearer token in memory and clears it on sign-out/access denial. | Continue to avoid localStorage for access tokens. If the API ever changes to cookie-based auth, add explicit CSRF protections and tests before enabling it. |
| Charts and form validation | `AnalyticsPage.tsx` uses Chart.js/react-chartjs-2 for currency-separated monthly spend plus accessible tabular summaries; existing policy/report forms use component-level validation. | Adopt React Hook Form + Zod where a form's validation or field dependencies outgrow the current focused components. |
| Feature structure and testing | `frontend/src/features/*` groups UI, API use, and Vitest/Testing Library tests by domain. | Keep UI behavior tests next to the feature; exercise loading, errors, permissions, keyboard flow, and a successful mutation. |
| Optional Vercel/Netlify deployment | The production target is AWS and is documented in `deployment/`. | Vercel/Netlify can be used only as an isolated preview-learning exercise, never as an unreviewed second production origin. |

## Week 4 — DevOps and system reliability

| Topic | Implemented evidence | Next evidence / scope decision |
| --- | --- | --- |
| CI/CD choice | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs backend, frontend, AI-review, receipt-intelligence, policy-assistant, Terraform, and secret-scan validation for every PR and `main` push. | GitHub Actions is the selected CI platform; GitLab CI is a comparison exercise.  Deployment remains a separately authorized manual workflow; CI never runs `terraform apply`, pushes images, or changes AWS state. |
| Cloud provider choice | `deployment/terraform/` and `deployment/README.md` implement AWS with a documented monthly budget. | AWS is the selected provider.  Azure/GCP are architecture comparisons unless a product requirement changes. |
| Infrastructure as Code | Modular Terraform covers network, storage, registry, database, secrets, runtime, edge, mail, logs, alarms, and budget alerts. | CI performs format/validation only.  State bootstrap, plans, applies, and destruction require a human-approved environment and local/approved deployment identity. |
| Least privilege and secrets | Terraform limits runtime IAM actions, separates core/AI Secrets Manager values, keeps the Groq key only in the AI-review secret, and gives the browser only Clerk’s publishable key. | Use OIDC for any future GitHub-to-AWS deployment role. Never commit `.env`, database URLs, provider keys, Terraform state, generated credentials, or a Super Admin email. |
| Docker and orchestration | Backend/AI Dockerfiles and a private Docker Compose runtime isolate processes on the low-cost host; receipt intelligence and policy assistant each receive a private Docker network, a distinct secret, and a separate SQLite volume. | Kubernetes is intentionally not a production dependency under the USD 75 cap. A local `kind` exercise may be added later for learning, without creating EKS or changing production. |
| Monitoring and logging | CloudWatch log groups and EC2/RDS capacity/storage alarms are provisioned in Terraform; the core `/api/health` and DB-aware `/api/ready` endpoints pair with structured correlation logs. | Add CloudWatch metric filters, alert runbooks, and recovery drills before adding Prometheus/Grafana infrastructure. |
| SRE and DevOps | Budget guardrails, backups, deletion protection, payment/audit events, and idempotent SLA escalation are part of the operational design. | Treat DevOps as delivery automation and SRE as measurable reliability work: define a service objective only after baseline traffic/error data exists. |

## AI curriculum — safe, human-in-the-loop application

| Topic | Implemented evidence | Next evidence / scope decision |
| --- | --- | --- |
| LLM foundations: tokens, context, transformers | The AI service deliberately limits provider context to totals, category codes, and sanitized findings. | Maintain a provider-context budget test and document why chunk size/context size change cost, latency, and recall.  Transformer internals are learned conceptually, not reimplemented. |
| Receipt intelligence and OCR boundary | `receipt_intelligence_service` validates supported metadata, receipt thresholds, scoped SHA-256 duplicates, bounded text extraction, and prompt-injection flags without receiving raw receipt files. | OCR remains deliberately disabled.  Any future OCR adapter must be independently reviewed, preserve the digest-only persistence boundary, and avoid automatic policy/workflow actions. |
| Embeddings and semantic similarity | `policy_assistant_service/vector_store.py` uses deterministic token feature hashing and cosine similarity in a service-owned SQLite index; it does not send policy text to an embedding provider. | Evaluate a vetted embedding/vector adapter only with measured retrieval quality, retention, privacy, and cost evidence.  Receipt bytes, employee profiles, and raw report text remain out of that index. |
| Prompt engineering | `redaction.py` builds a constrained advisory prompt and the deterministic evaluator controls recommendations. | Keep system-like task constraints separate from user/document data, use short task prompts and fixture-based zero/few-shot experiments, and never request, store, or depend on chain-of-thought.  Use concise structured results instead. |
| Structured outputs | AI-review validates Gemini/Groq JSON drafts with strict Pydantic contracts and citation allowlists; Groq uses JSON Object Mode while the policy assistant returns source-grounded citations and an explicit insufficient-evidence response. | Evaluate stricter JSON Schema mode only with a supported model and a fallback test; invalid output must always fall back to the deterministic narrative. |
| RAG | `policy_assistant_service` ingests sanitized policy text, chunks it with opaque tenant/version/source IDs, retrieves only matching scope, and returns citations from its own SQLite vector index. `PolicyAssistantPanel` explicitly indexes approved text and displays cited answers through a token-protected core boundary. Terraform isolates it on a private network with its own datastore/token; external providers are disabled by default. | Prefer RAG for changing policy facts; do not fine-tune a model for policy content. Any Terraform apply still requires a separate secrets, network, retention, and cost review. |
| RAG evaluation and trade-offs | Policy-assistant tests cover tenant isolation, grounding/citations, no-evidence responses, and injection defenses; its README documents deterministic retrieval trade-offs. | Add a small gold policy-question set with retrieval precision, citation correctness, groundedness, latency, and cost measurements before enabling an external model/provider. |
| Agentic AI, tools, memory, MCP | The current asynchronous reviewer is a bounded workflow, not an autonomous agent; it has no write capability into reimbursement records. | Preserve human approval as the only workflow authority.  Do not expose database/action tools through MCP or add persistent agent memory.  Consider an authenticated, read-only policy-search tool only after a threat model and tenant-isolation review; multi-agent planning remains a learning exercise, not a workflow dependency. |
| Building AI applications | `ai_review_service`, `receipt_intelligence_service`, and `policy_assistant_service` are standalone FastAPI services with separate persistence and tests. The policy Q&A panel and manual receipt-metadata review demonstrate evidence-based user interfaces without workflow authority. | Sentiment analysis is out of scope because it does not improve reimbursement correctness. Keep provider adapters optional and isolated from core data and budgets. |
| Prompt injection | The policy assistant strips suspicious document lines, rejects suspicious questions, and returns only source-grounded evidence; receipt intelligence detects/ignores instruction-like supplied text. | Maintain adversarial fixtures, bounded input, and citation constraints whenever a parser/provider is added.  Never treat document content as system instructions. |
| AI privacy and security | The core converts AI-review and policy-assistant UUID references to stable keyed-HMAC aliases before their HTTP boundaries (`AI_REVIEW_REFERENCE_HMAC_KEY` and `POLICY_ASSISTANT_REFERENCE_HMAC_KEY`); AI-review contracts reject direct identifiers/redact common PII; receipt intelligence persists only scope/digest observations; the policy assistant keeps policy text locally and does not persist questions/log content. | Define retention/deletion rules for AI jobs and vector data, redact logs, restrict provider keys, review third-party retention terms, and never put raw receipts or Neon/AWS credentials in prompts. |

## Definition of done for a learning-backed change

1. The PR names the relevant row(s) above and explains the user value.
2. A test, reproducible command, diagram, or benchmark proves the claimed
   behavior.
3. The security, privacy, cost, and operational impact is explicit.
4. CI passes without external deployment or production credentials.
5. The scope decision is updated when a deferred technology becomes necessary.
