# harness-engineering-audit

A Codex-native skill for auditing repositories against OpenAI-style harness engineering and agentic-development readiness.

The skill is strict and audit-first, but low-risk audit recommendations are auto-approved for follow-up OMX execution. Root `AGENTS.md` improvements are P0 when the audit finds missing, stale, oversized, or under-informative instruction surfaces.

## What it checks

- `AGENTS.md` and nested instruction files
- Codex project config in `.codex/config.toml`
- MCP servers
- hooks, prompts, and rules
- repo-scoped skills in `.agents/skills`
- OMX contexts, plans, and workflow docs
- validation commands and package scripts
- stack profile and installed tooling signals
- approval-gated official/high-trust upgrade recommendations
- CI workflows
- docs authority and index coverage
- glossary, terminology, ADR, and domain-language surfaces that keep agent vocabulary consistent
- doc gardening / knowledge-base readiness, including source boundaries, generated/synthesized docs, indexes/logs, and stale/contradiction/orphan checks
- progressive-disclosure guidance for keeping hot-path instructions concise
- deterministic automated checks versus judgment-based automated/human review boundaries
- generated artifact lifecycle
- lane-pack registry coverage for grounded source-of-truth surfaces, including universal core lanes plus stack-detected UI/UX, backend/API, data, security, performance, infra, AI/ML/CV, docs, and QA lanes
- Symphony orchestration readiness (static signals for workflow contracts, task-state handoffs, workspace isolation, agent runner guidance, observability, validation, and recovery)
- scaffolding / preview / legacy entropy
- cross-agent surfaces such as Claude, Cursor, Windsurf, Cline, Gemini, and Copilot files

## Install

Copy this directory into a repo as:

```text
.agents/skills/harness-engineering-audit/
```

Then run from the repo root.

Project-scoped install:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

User-scoped install:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py .
```

## Output

By default, each run replaces the previous generated report directory:

```text
.codex/reports/harness-engineering-audit/
```

Generated files:

```text
inventory.json
scorecard.json
report.md
findings.md
recommended-fixes.md
agents-priority.md
omx-handoff.md
next-step.md
next-step.json
prompts/deep-interview.md
prompts/ralplan.md
prompts/team.md
prompts/ralph.md
prompts/symphony-adoption.md
```

Default `audit`/`minimal` runs do **not** change source files, docs, config, hooks, MCP, skills, or CI. They only write generated reports. Explicit setup modes below may write bounded low-risk harness artifacts with provenance markers and a rollback manifest.

Upgrade recommendations are report-only by default: `recommend_tools=true`, web verification is requested but not claimed by local Python scripts, human approval is required, and install/config mutation is disabled.

`report.md`, `next-step.md`, `omx-handoff.md`, and `next-step.json` surface the run state directly: what happened, what did not happen, what needs approval, current mode side effects, and the approval-gated tool recommendation branch.

## Modes

Default audit mode is report-only:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py . --mode audit
```

Explicit setup modes create low-risk harness artifacts with provenance markers and a rollback manifest:

```bash
AUDIT_SCRIPT=~/.codex/skills/harness-engineering-audit/scripts/run_audit.py
# For a project-scoped install, use:
# AUDIT_SCRIPT=.agents/skills/harness-engineering-audit/scripts/run_audit.py

python3 "$AUDIT_SCRIPT" . --mode safe-setup
python3 "$AUDIT_SCRIPT" . --mode force-ideal-harness
python3 "$AUDIT_SCRIPT" . --mode symphony-repo-local
python3 "$AUDIT_SCRIPT" . --mode symphony-live-handoff
python3 "$AUDIT_SCRIPT" . --mode full-orchestration
```

Mode side-effect summary:

| Mode | Target source mutation | Runs agents or installs tools? |
| --- | --- | --- |
| `audit` / `minimal` | No; reports only. | No. |
| `safe-setup` | Missing low-risk docs/templates only; no `.codex/agents`. | No. |
| `force-ideal-harness` | Bounded low-risk docs/template consolidation; no deletes or CI/config/hooks/security changes. | No. |
| `symphony-repo-local` | Repo-local Symphony docs/contracts and inert handoff text. | No live install/config mutation. |
| `symphony-live-handoff` | No target source mutation; report-directory handoff text only. | No. |
| `full-orchestration` | Lane-pack contracts and `.codex/agents/harness-*.toml`. | Never runs agents or live commands. |

`safe-setup` creates docs-only lane packs under `docs/harness/**` and never creates `.codex/agents`. Stack-detected lanes include activation confidence and recommendation policy fields so weak layout signals can remain advisory instead of inflating missing-lane work. `full-orchestration` is explicit opt-in for project custom-agent TOML and stronger orchestration contracts; it still does not spawn agents or execute live commands. `--force` remains only the output-directory overwrite flag; it is not the force-ideal-harness mode.

## Recommended workflow

1. Run the audit.
2. Review `.codex/reports/harness-engineering-audit/report.md`.
3. In OMX, select the generated default next stage when offered, or resume later with `$harness-engineering-audit continue`.
4. Use `$team` to execute auto-approved low-risk fixes, with `AGENTS.md` first.
5. Use `$ralph` to verify validation evidence and residual risk.

## Example

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py .
cat .codex/reports/harness-engineering-audit/report.md
```

Then:

```text
$ralplan "Read .codex/reports/harness-engineering-audit/prompts/ralplan.md and follow it."
```

## Design intent

This skill follows the principle that agent-ready repositories need:

- concise hot-path instructions
- versioned source-of-truth docs
- canonical project vocabulary that agents can load when relevant
- living doc gardening workflows for maintaining synthesized knowledge over time
- reliable validation commands
- deterministic feedback loops
- safe tool configuration
- clear subagent/team workflow
- grounded lane packs and source-of-truth surfaces for repeated agent work without design, contract, docs, or validation drift, with confidence-gated stack recommendations for unusual repo layouts
- generated artifact lifecycle
- Symphony orchestration readiness (static signals for workflow contracts, task-state handoffs, workspace isolation, agent runner guidance, observability, validation, and recovery)
- explicit scaffolding/legacy cleanup policy
- lifecycle classification and readiness registry coverage without bloating the top-level score dimensions

OpenAI/Codex guidance is the normative source. Cross-agent resources are included only as comparison material.


## Safe updates

Normal audit runs check for skill updates by default and write update status into the generated report directory. The check is non-mutating.

Explicit self-update is available only through:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py . --self-update --update-scope user
```

To force-update this one user-scoped skill directly:

```bash
gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user --force
```

Avoid `gh skill update --all`; project-scoped installs should generally be updated intentionally through a repository PR.
