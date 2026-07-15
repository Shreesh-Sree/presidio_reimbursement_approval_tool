# Reimbursement API

The FastAPI application lives in `app.main` and uses Alembic migrations plus
the models registered by `app.models`.

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run `uv run pytest tests -q` for backend tests and `uv run alembic check` to
confirm migrations match metadata. `main:app` remains a compatibility alias
for existing local commands.

## Authentication and access

Browser access is OAuth-only in the default `AUTH_PROVIDER=clerk` mode.  The
React client requests a short-lived custom Clerk JWT and the API verifies its
RS256 signature, issuer, audience, authorized-party origin, and verified
email claim before it looks up an active application user.  Roles and
permissions are always loaded from this database—never trusted from an OAuth
token.

Configure these ignored/local or secret-manager values before starting Clerk
mode:

- `CLERK_JWKS_URL`, `CLERK_ISSUER`, `CLERK_AUDIENCE`, and
  `CLERK_AUTHORIZED_PARTIES`;
- `SUPER_ADMIN_EMAIL`, the one verified address allowed to provision the
  first application administrator; and
- optional `DEFAULT_ORGANIZATION_*` / `DEFAULT_DEPARTMENT_*` values for an
  empty database.

The custom Clerk template (default name `presidio-api`) must contain an
`email` claim, `email_verified: true`, and an `aud` matching
`CLERK_AUDIENCE`. The first configured Super Admin is provisioned only after
that verified email signs in. Administrators then add email allowlist records
and roles through `/api/users`; those users have no local password. Signed-in
but unallowlisted users receive a structured `access_not_granted` response for
the frontend’s explicit no-access page.

`AUTH_PROVIDER=local` is retained only for controlled migration and test
environments. It re-enables legacy password endpoints; never use it for a
browser-facing deployment.

To enforce OAuth-only end-to-end, enable only the intended OAuth connection(s)
in the Clerk Dashboard and disable its email/password, email-code, email-link,
and self-service credential sign-up methods. The React application does not
render a manual credential form, but Clerk controls which hosted sign-in
methods appear.

File bytes are stored through `app.services.storage_service` (`local` by
default; S3 when `STORAGE_BACKEND=s3`). AI review is intentionally not an API
module: configure `AI_REVIEW_SERVICE_URL` to connect to the separately deployed
`../ai_review_service`.
