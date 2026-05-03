# Symphony Repo-Local Setup Handoff

This handoff is inert repo-local planning material. It records the exact decisions required before a live Symphony setup, but it does not install software, mutate configuration, call issue-tracker APIs, create credentials, or start a worker service.

## Approval Required

A human must approve the tool, destination repository/account, configuration files, issue-tracker integration, validation command, and rollback command before any live setup is executed.

## Install / Configure / Validate / Roll Back

- Install command: approval required
- Configuration command: approval required
- Validation command: approval required
- Rollback command: approval required

## Required Contracts

- Task contract source of truth: `docs/harness/task-contract.md`
- Agent role topology: `docs/harness/agent-role-topology.md`
- Task state schema: `docs/harness/task-state-schema.md`
- Proof schema: `docs/harness/observability-proof-schema.md`
- Recovery and reconciliation: `docs/harness/recovery-reconciliation.md`
- Queue capacity policy: `docs/harness/queue-capacity-policy.md`

## Live Setup Gate

Do not proceed to live Symphony setup until the repository has passing validation, a named owner for rollback, and a written mapping from external tracker states to the repo-local task state schema.
