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
  stack-inventory.json
  tool-inventory.json
  upgrade-recommendations.json
  upgrade-recommendations.md
  web-verification-queue.json
  source-trust-policy.md
  report.md
  findings.md
  recommended-fixes.md
  agents-priority.md
  omx-handoff.md
  next-step.md
  next-step.json
  prompts/
    deep-interview.md
    ralplan.md
    team.md
    ralph.md
    symphony-adoption.md
    tool-upgrade-ralplan.md
```

Each run replaces the previous report directory to avoid stale audit confusion.

The upgrade recommendation layer is report-only. It requests follow-up web verification, keeps local-script `web_verified` status false, requires human approval for every install/config action, and never mutates source or configuration.

Recommended flow:

1. Run the audit.
2. Read `report.md`, `findings.md`, and `recommended-fixes.md`.
3. Read `agents-priority.md` for the P0 AGENTS.md lane.
4. Review `upgrade-recommendations.md` and `source-trust-policy.md` before considering any tooling changes.
5. In OMX, select **Plan auto-approved fixes** when offered, or resume later with `$harness-engineering-audit continue`.
6. Use `$team` / `$ralph` to execute and verify auto-approved low-risk fixes.

The long workflow prompts are stored under `prompts/` so OMX can continue without requiring copy/paste.
