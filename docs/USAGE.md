# Usage

Run from the target repo root.

Project-scoped install:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

User-scoped install:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py .
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
  update-status.json
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
5. In OMX, select the generated default next stage when offered, or resume later with `$harness-engineering-audit continue`.
6. Use `$team` / `$ralph` to execute and verify auto-approved low-risk fixes.

The long workflow prompts are stored under `prompts/` so OMX can continue without requiring copy/paste.


## Update checks

By default, normal audit runs perform a non-mutating update check for `ryne2010/harness-engineering-audit` and write `update-status.json`. If GitHub CLI, `gh skill`, or network access is unavailable, the audit still succeeds and reports the update status as `tooling_missing` or `unknown`.

Disable the check when needed:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py . --no-check-update
```

Self-update requires explicit intent and updates only this skill:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py . --self-update --update-scope user
```

Do not use `gh skill update --all` for this workflow. Use the explicit one-skill install command instead, and treat project-scoped updates as intentional repo/PR changes.
