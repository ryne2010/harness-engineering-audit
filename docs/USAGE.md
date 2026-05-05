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

When run from an interactive terminal without `--mode`, the script prompts for an audit level:

- `minimal` (default, maps to report-only `audit`)
- `safe-setup`
- `force-ideal-harness`
- `symphony-repo-local`
- `symphony-live-handoff`
- `full-orchestration`

Non-interactive runs default to `minimal`/`audit`. Use `--mode minimal` or `--mode audit` to skip the prompt explicitly.

Mode boundaries:

| Mode | What happens | What does not happen |
| --- | --- | --- |
| `audit` / `minimal` | Writes reports, scorecard, next-step artifacts, and inert prompts. | No target source mutation. |
| `safe-setup` | Writes missing low-risk harness docs/templates with rollback manifest. | No `.codex/agents`, no deletes, no CI/config/hooks/security mutation. |
| `force-ideal-harness` | Replaces or consolidates generated low-risk harness docs/templates when provenance allows. | No deletes, no CI/config/hooks/security mutation. |
| `symphony-repo-local` | Writes repo-local Symphony contracts/templates and inert handoff text. | No live daemon/tool install/config mutation. |
| `symphony-live-handoff` | Writes approval-gated live setup handoff text under the report directory. | No target source mutation and no live install/config mutation. |
| `full-orchestration` | Writes lane-pack contracts and `.codex/agents/harness-*.toml` custom-agent definitions. | Never runs agents and never executes live install/config commands. |

The upgrade recommendation layer is report-only. It requests follow-up web verification, keeps local-script `web_verified` status false, requires human approval for every install/config action, and never mutates source or configuration.

The main artifacts include “What happened / What did not happen / What needs approval” plus `next-step.json` fields for `mode_summary`, `approval_state`, `tool_recommendation_state`, and `current_step_explanation`. `tool-upgrade-ralplan` is visible as an optional approval-gated branch, but it is not the default and is not auto-approved.

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
