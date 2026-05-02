# OMX Workflow for Harness Engineering Fixes

This skill is audit-first. Use OMX to plan and execute auto-approved low-risk changes. Root `AGENTS.md` improvements are P0 when the audit finds missing, stale, oversized, or under-informative instruction surfaces.

Interactive OMX runs should avoid copy/paste. After the audit, select **Plan auto-approved fixes** when offered, or resume later with:

```text
$harness-engineering-audit continue
```

## Recommended flow

```text
$ralplan "Read .codex/reports/harness-engineering-audit/prompts/ralplan.md and follow it."
```

```text
$team "Read .codex/reports/harness-engineering-audit/prompts/team.md and follow it."
```

```text
$ralph "Read .codex/reports/harness-engineering-audit/prompts/ralph.md and follow it."
```

```text
$deep-interview "Read .codex/reports/harness-engineering-audit/prompts/deep-interview.md and follow it." # medium/high-risk questions only
```

## Planning rules

The plan must distinguish:

- implement now
- document/defer
- do not touch
- auto-approved low-risk
- requires human approval (medium/high-risk)
- requires team/process agreement

## Execution rules

- Do not auto-delete scaffolding.
- Do not rewrite config without approval.
- Do not add MCP servers without purpose and owner.
- Do not create large `AGENTS.md` files.
- Prioritize root `AGENTS.md` improvements before other low-risk fixes.
- Prefer indexes, registries, and executable checks over duplicated prose.
