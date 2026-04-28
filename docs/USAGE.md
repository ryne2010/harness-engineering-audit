# Usage

Run from the target repo root:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

Generated output:

```text
.codex/reports/harness-engineering-audit/
  inventory.json
  scorecard.json
  report.md
  findings.md
  recommended-fixes.md
  omx-handoff.md
```

Each run replaces the previous report directory to avoid stale audit confusion.

Recommended flow:

1. Run the audit.
2. Read `report.md`, `findings.md`, and `recommended-fixes.md`.
3. Use `omx-handoff.md` as input to `$deep-interview`.
4. Use `$ralplan` to create a PRD and test spec.
5. Use `$team` or `$ralph` to execute approved fixes.
