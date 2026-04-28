# Harness Engineering Audit

`harness-engineering-audit` is a Codex skill for auditing repositories against OpenAI-style harness engineering and agentic-development readiness.

It is audit-first and strict. It inventories a repo, scores the harness-engineering surface, writes report artifacts, and produces an OMX-ready handoff so approved fixes can move through `$deep-interview`, `$ralplan`, `$team`, and `$ralph`.

## What it checks

- `AGENTS.md` and nested instruction files
- `.codex/config.toml`, MCP servers, hooks, prompts, and rules
- repo-scoped skills in `.agents/skills`
- OMX contexts, plans, and workflow docs
- validation commands and package scripts
- CI workflows
- docs authority and index coverage
- generated artifact lifecycle
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
  skills/harness-engineering-audit@v0.1.1 \
  --agent codex \
  --scope project
```

Install globally for your user:

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@v0.1.1 \
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
  report.md
  findings.md
  recommended-fixes.md
  omx-handoff.md
```

Use the generated handoff with OMX:

```text
$deep-interview "Read .codex/reports/harness-engineering-audit/omx-handoff.md and conduct a harness-engineering review."
$ralplan "Use the harness-engineering audit report and interview output to write the PRD and test spec."
$team "Execute only approved low-risk harness-engineering fixes."
$ralph "Verify the cleanup and produce the final stop/no-stop recommendation."
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
gh skill publish --tag v0.1.1
```

Full publishing steps are in [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## License

MIT

test workflow
