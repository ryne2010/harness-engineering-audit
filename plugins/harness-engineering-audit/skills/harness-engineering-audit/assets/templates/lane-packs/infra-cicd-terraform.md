# Infra, CI/CD, And Terraform Lane

Owns Terraform/cloud/IaC surfaces, CI/CD workflows, environment promotion, secrets, deploy validation, rollback, and drift detection.

## Required Evidence

- Plan/diff/validate output
- Environment affected
- Secret handling notes
- Rollback or revert path
- CI/deploy verification

Conservative setup must not mutate CI, hooks, secrets, or live infrastructure.
