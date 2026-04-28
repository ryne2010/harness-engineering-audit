# OMX Workflow

The skill is audit-first. It does not modify repo source files. Use the generated handoff to start an OMX planning flow.

```text
$deep-interview "Read .codex/reports/harness-engineering-audit/omx-handoff.md and conduct a harness-engineering review."
$ralplan "Use the audit and interview output to write .omx/plans/prd-harness-engineering-audit.md and .omx/plans/test-spec-harness-engineering-audit.md."
$team "Execute approved low-risk fixes from the harness-engineering plan."
$ralph "Verify changes, validation, residual risks, and stop/no-stop recommendation."
```
