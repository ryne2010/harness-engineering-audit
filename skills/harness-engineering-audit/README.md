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
- generated artifact lifecycle
- Symphony orchestration readiness (static signals for workflow contracts, task-state handoffs, workspace isolation, agent runner guidance, observability, validation, and recovery)
- scaffolding / preview / legacy entropy
- cross-agent surfaces such as Claude, Cursor, Windsurf, Cline, Gemini, and Copilot files

## Install

Copy this directory into a repo as:

```text
.agents/skills/harness-engineering-audit/
```

Then run from the repo root:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
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

The scripts do **not** change source files, docs, config, hooks, MCP, skills, or CI. They only write generated reports.

Upgrade recommendations are report-only by default: `recommend_tools=true`, web verification is requested but not claimed by local Python scripts, human approval is required, and install/config mutation is disabled.

## Recommended workflow

1. Run the audit.
2. Review `.codex/reports/harness-engineering-audit/report.md`.
3. In OMX, select **Plan auto-approved fixes** when offered, or resume later with `$harness-engineering-audit continue`.
4. Use `$team` to execute auto-approved low-risk fixes, with `AGENTS.md` first.
5. Use `$ralph` to verify validation evidence and residual risk.

## Example

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
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
- reliable validation commands
- deterministic feedback loops
- safe tool configuration
- clear subagent/team workflow
- generated artifact lifecycle
- Symphony orchestration readiness (static signals for workflow contracts, task-state handoffs, workspace isolation, agent runner guidance, observability, validation, and recovery)
- explicit scaffolding/legacy cleanup policy

OpenAI/Codex guidance is the normative source. Cross-agent resources are included only as comparison material.
