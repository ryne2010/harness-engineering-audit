# Risk Model

The skill separates audit findings from implementation decisions.

## Low-risk / high-confidence

Safe candidates for an approved OMX plan:

- add missing report/index links
- document existing commands
- add a validation matrix
- add a generated artifact policy
- trim duplicate root `AGENTS.md` content
- add a DX preflight script that only reads state
- classify scaffolding without deleting it
- document MCP/skills/hooks that already exist

## Medium-risk

Requires plan and review:

- restructure docs folders
- add or modify MCP servers
- change hook behavior
- change CI validation behavior
- move generated artifacts
- create new custom skills
- add repo automation

## High-risk

Do not execute without explicit approval:

- delete scaffolding or legacy paths
- rewrite CI/deploy workflows
- remove hooks/rules/MCP servers used by a team
- change Codex sandbox/approval policy
- alter package scripts used by production
- restructure source packages
- delete generated artifacts without lifecycle proof

## Required implementation standard

Every fix needs:

- issue statement
- evidence
- confidence/risk classification
- files touched
- validation command
- rollback strategy if non-trivial
