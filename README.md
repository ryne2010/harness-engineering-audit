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
- glossary, terminology, ADR, and domain-language surfaces that keep agent vocabulary consistent
- doc gardening / knowledge-base readiness, including source boundaries, generated/synthesized docs, indexes/logs, and stale/contradiction/orphan checks
- progressive-disclosure guidance that keeps hot-path instructions concise
- deterministic automated checks versus judgment-based automated/human review boundaries
- lifecycle classification and readiness registry coverage for broader harness/Symphony concepts
- lane-pack registry coverage for grounded source-of-truth surfaces, including universal core lanes plus confidence-gated stack-detected UI/UX, backend/API, data, security, performance, infra, AI/ML/CV, docs, and QA lanes
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


## Safe skill updates

Audit runs check the skill's update status by default and include the result in `.codex/reports/harness-engineering-audit/update-status.json` plus the main report. This is report-only: the skill does **not** auto-update by default.

To update this one skill globally for your user, prefer the explicit install command:

```bash
gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user --force
```

Or use the skill's explicit self-update flag:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py . --self-update --update-scope user
```

After a successful self-update, restart Codex / rerun the audit so the updated files are loaded. Project-scoped installs should generally be updated intentionally through a repo change and PR. Avoid `gh skill update --all` for this use case because it may touch unrelated system/manual skills and may fail on skills without GitHub metadata.

## Run the audit

From a target repo root after installing the skill.

Project-scoped install:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

User-scoped install:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py .
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

Use the generated handoff with OMX. In an interactive OMX run, the skill should present the generated default next stage from `next-step.json` so you do not need to copy/paste a long prompt. To resume later, type only:

```text
$harness-engineering-audit continue
```

Upgrade recommendations are report-only by default: tools are recommended, follow-up web verification is requested, human approval is required, and the audit never executes install/config commands or claims local-script web verification.

Explicit setup modes are available when you want the skill to create low-risk harness infrastructure:

```bash
AUDIT_SCRIPT=.agents/skills/harness-engineering-audit/scripts/run_audit.py
# For a user-scoped install, use:
# AUDIT_SCRIPT=~/.codex/skills/harness-engineering-audit/scripts/run_audit.py

python3 "$AUDIT_SCRIPT" . --mode safe-setup
python3 "$AUDIT_SCRIPT" . --mode force-ideal-harness
python3 "$AUDIT_SCRIPT" . --mode symphony-repo-local
python3 "$AUDIT_SCRIPT" . --mode symphony-live-handoff
python3 "$AUDIT_SCRIPT" . --mode full-orchestration
```

The default `--mode audit` remains report-only. `safe-setup` creates docs-only lane packs under `docs/harness/**` and never creates `.codex/agents`. Stack lanes include activation confidence and recommendation policy fields so weak layout signals can remain advisory instead of inflating missing-lane work. `full-orchestration` is explicit opt-in for project custom-agent TOML and stronger orchestration contracts; it still does not spawn agents or execute live commands. `--force` remains only the output-directory overwrite flag.

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
      release.json
      scripts/*.py
      assets/*
      references/*
  plugins/
    harness-engineering-audit/
      .codex-plugin/plugin.json
      skills/harness-engineering-audit/
  .agents/plugins/marketplace.json
  tests/check_skill_mirror.py
  tests/smoke/run_skill_smoke.py
```

## Validate this repo

```bash
make validate
```

Equivalent commands:

```bash
python3 -m py_compile skills/harness-engineering-audit/scripts/*.py tests/smoke/run_skill_smoke.py tests/check_skill_mirror.py
python3 tests/check_skill_mirror.py
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
