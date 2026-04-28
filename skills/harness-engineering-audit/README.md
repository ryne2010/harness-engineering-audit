# harness-engineering-audit

A Codex-native skill for auditing repositories against OpenAI-style harness engineering and agentic-development readiness.

The skill is strict, audit-first, and designed to generate intermediate artifacts that support OMX planning and execution.

## What it checks

- `AGENTS.md` and nested instruction files
- Codex project config in `.codex/config.toml`
- MCP servers
- hooks, prompts, and rules
- repo-scoped skills in `.agents/skills`
- OMX contexts, plans, and workflow docs
- validation commands and package scripts
- CI workflows
- docs authority and index coverage
- generated artifact lifecycle
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
omx-handoff.md
```

The scripts do **not** change source files, docs, config, hooks, MCP, skills, or CI. They only write generated reports.

## Recommended workflow

1. Run the audit.
2. Review `.codex/reports/harness-engineering-audit/report.md`.
3. Use `.codex/reports/harness-engineering-audit/omx-handoff.md` as context for `$deep-interview`.
4. Use `$ralplan` to create a PRD and test spec.
5. Use `$team` or `$ralph` to execute only approved fixes.

## Example

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
cat .codex/reports/harness-engineering-audit/report.md
```

Then:

```text
$deep-interview "Read .codex/reports/harness-engineering-audit/omx-handoff.md and conduct a harness-engineering review."
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
- explicit scaffolding/legacy cleanup policy

OpenAI/Codex guidance is the normative source. Cross-agent resources are included only as comparison material.
