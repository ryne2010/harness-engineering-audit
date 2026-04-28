# Harness Engineering Audit

`harness-engineering-audit` is a Codex skill for auditing repositories against OpenAI-style harness engineering and agentic-development readiness.

It is audit-first and strict. It inventories a repo, scores the harness-engineering surface, writes report artifacts, and produces an OMX-ready handoff so approved fixes can move through `$deep-interview`, `$ralplan`, `$team`, and `$ralph`.

The skill is designed for:

- Codex and OMX workflows
- `AGENTS.md` and nested instruction hygiene
- `.codex/config.toml` readiness
- MCP, hooks, rules, skills, and subagent review
- cross-agent surface checks such as Claude, Cursor, Gemini CLI, Cline, Windsurf, and related files
- docs authority and validation-command truth
- production-readiness for agentic development

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
    REPOSITORY_STRUCTURE.md
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
  .agents/
    plugins/marketplace.json
  tests/
    smoke/run_skill_smoke.py
```

## Install from GitHub with `gh skill`

Replace `OWNER` with your GitHub username or organization.

Project scope:

```bash
gh skill install OWNER/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope project
```

User scope:

```bash
gh skill install OWNER/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user
```

Pinned version:

```bash
gh skill install OWNER/harness-engineering-audit skills/harness-engineering-audit@v0.1.0 --agent codex --scope project
```

## Install from a local clone

```bash
gh skill install ./skills/harness-engineering-audit --agent codex --scope project
```

Or copy manually into a repo:

```bash
mkdir -p .agents/skills
cp -R skills/harness-engineering-audit .agents/skills/
```

## Run the audit manually

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

## Publish as a GitHub-hosted skill

```bash
python3 -m py_compile skills/harness-engineering-audit/scripts/*.py
python3 tests/smoke/run_skill_smoke.py
gh skill publish --dry-run
git add -A
git commit -m "Initial harness engineering audit skill"
gh repo create OWNER/harness-engineering-audit --public --source=. --remote=origin --push
gh skill publish --tag v0.1.0
```

Full publishing steps are in [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## Optional Codex plugin wrapper

This repo also includes an optional plugin wrapper under:

```text
plugins/harness-engineering-audit/
```

Use this after the skill install path is working and you want a richer plugin distribution model. See [`docs/PLUGIN_DISTRIBUTION.md`](docs/PLUGIN_DISTRIBUTION.md).

## Validation

```bash
make validate
```

This runs Python syntax checks and a smoke test that generates audit artifacts in a temporary repo.

## License

MIT
