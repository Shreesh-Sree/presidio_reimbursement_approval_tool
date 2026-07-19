# Supabase/Auth production promotion runbook

`supabase/config.toml` is the reviewed local/declarative baseline. Hosted
Supabase controls remain an external verification until a privileged operator
promotes and records them. Do not copy production project URLs, OAuth secrets,
or connection strings into source files.

## Source policy

- Public self-sign-up and email self-sign-up are disabled.
- Anonymous sign-in is disabled.
- Email confirmation, secure password change, refresh-token rotation, and TOTP
  MFA are enabled in the baseline.
- Local redirect URLs are exact localhost URLs only. Production must use exact
  HTTPS origin and route URLs; wildcard redirects are prohibited.
- OAuth provider secrets stay in the hosted console/secret manager and are not
  part of this repository.

## External promotion checklist

For each staging and production project, a Supabase administrator must:

1. Review the diff of `supabase/config.toml` and promote it through the
   organisation-approved Supabase CLI/management path.
2. Set the Site URL and allow only exact HTTPS redirect URLs for the static app
   and sign-in callback routes. Remove historical, preview, wildcard, and
   unowned domains.
3. Confirm public signup, email signup, anonymous users, manual account
   linking, and unused providers are disabled. Confirm invite/access-request
   flow is the only onboarding path.
4. Configure approved OAuth providers with their exact Supabase callback URL,
   verified client secrets, PKCE/nonce protections, and approved consent
   screen/origins. Test account linking and email-change lifecycle in staging.
5. Confirm email confirmation, secure password change, MFA policy, Auth rate
   limits, CAPTCHA/risk controls where appropriate, and session/refresh-token
   settings match the approved threat model.
6. Verify database backups, point-in-time recovery, network restrictions,
   access roles, RLS policies/grants, JWT rotation process, and migration head.
   The repository does not prove these hosted controls.
7. Save redacted evidence (settings export/screenshots, test run, approver) in
   the deployment record rather than in the repository.

## Required staging tests

1. A random email cannot self-register or obtain application access.
2. An invited/allowlisted user can complete OAuth and returns only to an exact
   allowed URL.
3. A disallowed redirect URL is rejected.
4. MFA enrollment/challenge behaves according to the approved rollout policy.
5. Refresh, sign-out, and identity changes match the frontend session policy.
6. A direct database/API role cannot bypass the intended tenant/RLS boundary.
7. A backup restore and migration-head check succeed in a non-production
   environment.

Production promotion is blocked until the relevant external checks have an
owner-approved record. See [the Azure operations runbook](azure-production-operations.md)
for the complementary Azure/GitHub release checks.
