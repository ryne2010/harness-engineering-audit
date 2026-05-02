# Harness Engineering Audit

`harness-engineering-audit` is a Codex skill for auditing repositories against OpenAI-style harness engineering and agentic-development readiness.

It is audit-first and strict, but aggressive about safe follow-up work. It inventories a repo, scores the harness-engineering surface, writes report artifacts, and produces an OMX-ready handoff so auto-approved low-risk fixes can move through `$ralplan`, `$team`, and `$ralph`. Root `AGENTS.md` improvements are P0 when the audit finds missing, stale, oversized, or under-informative instruction surfaces.

## What it checks

- `AGENTS.md` and nested instruction files
- `.codex/config.toml`, MCP servers, hooks, prompts, and rules
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
- cross-agent surfaces such as Claude, Cursor, Gemini CLI, Cline, Windsurf, and Copilot files

## Install with GitHub CLI

Install into the current repo as a Codex project skill:

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit \
  --agent codex \
  --scope project
```

Install a pinned release:

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@v0.2.0 \
  --agent codex \
  --scope project
```

Install globally for your user:

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@v0.2.0 \
  --agent codex \
  --scope user
```

## Download manually

Download the latest GitHub release ZIP, unzip it, and copy the skill into a repo:

```bash
mkdir -p .agents/skills
cp -R /path/to/harness-engineering-audit/skills/harness-engineering-audit \
  .agents/skills/harness-engineering-audit
```

Or install from a local clone:

```bash
gh skill install ./skills/harness-engineering-audit --agent codex --scope project
```

## Run the audit

From a target repo root after installing the skill:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

The audit replaces the previous generated report set at:

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

Use the generated handoff with OMX. In an interactive OMX run, the skill should present **Plan auto-approved fixes** as the default selection so you do not need to copy/paste the long prompt. To resume later, type only:

Upgrade recommendations are report-only by default: tools are recommended, follow-up web verification is requested, human approval is required, and the audit never executes install/config commands or claims local-script web verification.

```text
$harness-engineering-audit continue
```

Manual commands are still generated for portability:

```text
$ralplan "Read .codex/reports/harness-engineering-audit/prompts/ralplan.md and follow it."
$team "Read .codex/reports/harness-engineering-audit/prompts/team.md and follow it."
$ralph "Read .codex/reports/harness-engineering-audit/prompts/ralph.md and follow it."
$deep-interview "Read .codex/reports/harness-engineering-audit/prompts/deep-interview.md and follow it." # medium/high-risk questions only
```

## Optional Codex plugin wrapper

This repo includes an optional plugin wrapper under:

```text
plugins/harness-engineering-audit/
```

The plugin wrapper is secondary. The recommended install path today is `gh skill install`. See [`docs/PLUGIN_DISTRIBUTION.md`](docs/PLUGIN_DISTRIBUTION.md) for the plugin marketplace flow.

## Repository layout

```text
harness-engineering-audit/
  README.md
  LICENSE
  CHANGELOG.md
  Makefile
  pyproject.toml
  docs/
    INSTALL.md
    PUBLISHING.md
    PLUGIN_DISTRIBUTION.md
    USAGE.md
    OMX_WORKFLOW.md
    RELEASE_CHECKLIST.md
  skills/
    harness-engineering-audit/
      SKILL.md
      agents/openai.yaml
      scripts/*.py
      assets/*
      references/*
  plugins/
    harness-engineering-audit/
      .codex-plugin/plugin.json
      skills/harness-engineering-audit/
  .agents/plugins/marketplace.json
  tests/smoke/run_skill_smoke.py
```

## Validate this repo

```bash
make validate
```

Equivalent commands:

```bash
python3 -m py_compile skills/harness-engineering-audit/scripts/*.py tests/smoke/run_skill_smoke.py
python3 tests/smoke/run_skill_smoke.py
```

## Publish

```bash
gh skill publish --dry-run
gh skill publish --tag v0.2.0
```

Full publishing steps are in [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## License

MIT
