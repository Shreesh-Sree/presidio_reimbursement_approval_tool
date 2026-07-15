## Summary

<!-- Explain the behavior change and its user value. Link the relevant issue, task, or requirement. -->

## Scope

- [ ] Backend/API
- [ ] Frontend/UI
- [ ] AI review, receipt-intelligence, or policy-assistant boundary
- [ ] Database migration
- [ ] Terraform/deployment documentation
- [ ] Documentation only

## Verification

<!-- List exact commands run and their results. Include focused tests as well as affected full suites. -->

## Data, security, and operations

- [ ] No secrets, credentials, raw receipts, or personal data were added to the repository, logs, or prompts.
- [ ] Authorization and tenant/report access were considered for changed endpoints/UI.
- [ ] Database migration and rollback/compatibility impact is documented, if applicable.
- [ ] AI remains advisory-only and receives only its approved minimized contract, if applicable.
- [ ] Cloud cost, monitoring, and recovery impact is documented, if applicable.

## Review checklist

- [ ] The change is focused and uses a conventional commit message.
- [ ] Tests cover the success path and relevant failure/permission behavior.
- [ ] Frontend changes include loading, empty, error, responsive, and keyboard considerations.
- [ ] API changes preserve typed validation and documented error behavior.
- [ ] `docs/LEARNING_MATRIX.md` or an ADR was updated for a material engineering decision.
- [ ] CI is expected to pass without deployment or production credentials.
