# Symphony Live Setup Handoff

This artifact is an explicit opt-in handoff only. It does not install software, mutate configuration, call live issue-tracker APIs, create credentials, or start a control-plane process.

## Approval Required

Before any live setup command is executed, a human must approve the exact tool, destination repository/account, configuration mutation, issue-tracker integration, validation command, and rollback plan.

## Inert Command Placeholders

- Install command: approval required
- Configuration command: approval required
- Validation command: approval required
- Rollback command: approval required

## Minimum Evidence Before Execution

- Static readiness report reviewed.
- Repo-local Symphony contracts exist and match the target workflow.
- Secrets and credentials are intentionally provisioned outside generated audit artifacts.
- Rollback owner and validation command are named.
