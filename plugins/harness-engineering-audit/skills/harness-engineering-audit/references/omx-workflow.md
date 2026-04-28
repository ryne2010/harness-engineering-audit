# OMX Workflow for Harness Engineering Fixes

This skill is audit-first. Use OMX to plan and execute approved changes.

## Recommended flow

```text
$deep-interview "Read .codex/reports/harness-engineering-audit/omx-handoff.md and conduct a harness-engineering deep review."
```

```text
$ralplan "Read the audit report and interview output. Produce .omx/plans/prd-harness-engineering-audit.md and .omx/plans/test-spec-harness-engineering-audit.md. Planning must classify low, medium, and high risk changes."
```

```text
$team "Execute only approved low-risk harness-engineering fixes. Keep root AGENTS map-like, preserve repo-specific docs, update validation evidence, and avoid risky config changes."
```

```text
$ralph "Verify the completed harness-engineering cleanup. Include validation, remaining risk, and stop/no-stop verdict."
```

## Planning rules

The plan must distinguish:

- implement now
- document/defer
- do not touch
- requires human approval
- requires team/process agreement

## Execution rules

- Do not auto-delete scaffolding.
- Do not rewrite config without approval.
- Do not add MCP servers without purpose and owner.
- Do not create large `AGENTS.md` files.
- Prefer indexes, registries, and executable checks over duplicated prose.
