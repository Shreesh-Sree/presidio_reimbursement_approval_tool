# Main-branch protection checklist

Configure these settings in the repository's GitHub branch-protection or ruleset
UI before treating `main` as a release branch.

## Required protection for `main`

- Require a pull request before merging.
- Require at least one approving review from someone other than the author.
- Dismiss stale approvals when new commits are pushed.
- Require review-thread resolution.
- Require the following successful checks from
  [`.github/workflows/ci.yml`](workflows/ci.yml):
  - `backend`
  - `frontend`
  - `ai-review`
  - `receipt-intelligence`
  - `policy-assistant`
  - `terraform`
  - `secrets`
- Require branches to be up to date before merge when the team can tolerate the
  additional queue time.
- Block force pushes and branch deletion.
- Use squash merge for feature branches unless preserving a well-structured
  commit series has clear value.

## Code-owner reviews

The repository intentionally ships a
[`CODEOWNERS.example`](CODEOWNERS.example), not active ownership rules, because
the real GitHub organization/team names have not been provided.  Replace every
example owner with a real user or team, rename the file to `CODEOWNERS`, and
then enable **Require review from Code Owners**.

Assign at least these ownership boundaries:

- `backend/` — API, migrations, authorization, and core data reviewers
- `frontend/` — UI/accessibility reviewers
- `ai_review_service/` — AI privacy/safety reviewers
- `receipt_intelligence_service/` — receipt privacy/safety reviewers
- `policy_assistant_service/` — policy-RAG privacy/safety reviewers
- `deployment/` — infrastructure/security/cost reviewers
- `.github/` and `docs/` — maintainers responsible for engineering process

## Emergency changes

An administrator may bypass protection only for an incident that cannot wait
for normal review.  Record the reason, open a follow-up PR within one business
day, and restore all checks/ownership requirements immediately afterward.
