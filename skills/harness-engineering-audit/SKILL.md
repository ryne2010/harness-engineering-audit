---
name: harness-engineering-audit
description: Audit a repository for OpenAI-style harness engineering and Codex/OMX readiness. Use when reviewing AGENTS.md, Codex config, OMX workflows, MCP, hooks, rules, skills, subagents, docs authority, validation commands, repo legibility, generated artifact policy, or production readiness for AI-driven development.
license: MIT
version: 0.2.0
---

# Harness Engineering Audit

Use this skill to turn a repository into a production-ready, agent-legible engineering environment optimized for Codex, OMX, and long-running AI-assisted development.

This skill is **audit-first, AGENTS-first, and low-risk auto-approved**. It may generate reports and planning artifacts before edits, then low-risk recommendations from the audit are approved for follow-up execution without another user approval. Medium/high-risk changes still require explicit approval.

## Core operating model

1. Inspect the repo and collect evidence.
2. Score the repo against the harness-engineering rubric.
3. Produce a strict report with low/medium/high-risk recommendations.
4. Generate AGENTS.md priority and OMX handoff artifacts.
5. Auto-approve low-risk fixes, with root `AGENTS.md` as P0 when it is missing, oversized, stale, or lacks docs/validation pointers.
6. Classify lifecycle as `greenfield-bootstrap`, `brownfield-cleanup`, or `mature-audit`.
7. Use OMX planning/execution or explicit setup modes for auto-approved low-risk fixes; defer medium/high-risk changes until explicit approval.

The default report location is:

```text
.codex/reports/harness-engineering-audit/
```

Each new run replaces the previous generated report directory at that path to avoid stale audit confusion. The included scripts only overwrite the known report directory or an explicitly provided output directory that is marked as a harness-engineering audit report directory.

## When to use

Use this skill when a user asks to audit or improve:

- harness engineering
- agentic development readiness
- Codex readiness
- OMX workflow quality
- `AGENTS.md` scope and quality
- `.codex/config.toml`
- MCP configuration
- skills
- hooks and rules
- subagent/team workflow
- docs authority
- validation commands
- command registries
- generated artifact policy
- stack/tooling upgrade recommendations
- scaffolding/legacy entropy
- repo legibility for AI agents
- production-readiness for agent-first development

## Authoritative principles

Treat OpenAI/Codex guidance as normative:

- `AGENTS.md` should be a concise map, not an encyclopedia.
- Repo-local docs should be the system of record.
- Validation should be executable and evidence-backed.
- Skills should encode repeatable workflows.
- Domain vocabulary should be discoverable and progressively disclosed, so agents use project language consistently without bloating hot-path instructions.
- Docs should be gardened as living knowledge: raw sources, synthesized docs, indexes, logs, and health checks need explicit boundaries and maintenance workflows.
- MCP should solve real external/context access problems.
- Hooks/rules should be deterministic, scoped, and safe.
- Subagents/team workflows should have clear delegation, path scope, and review boundaries.
- Generated artifacts and scaffolding require lifecycle policies.

Use Claude/Cursor/Karpathy/third-party resources only as comparison material, not as authority over Codex behavior.
The vocabulary/domain-language audit surface is informed by Matt Pocock's Dictionary of AI Coding as comparison material: shared terms, handoff artifacts, progressive disclosure, and the distinction between deterministic checks and review are useful harness concepts, but this skill should not copy that repo's prose.
The doc-gardening audit surface is informed by Andrej Karpathy's LLM Wiki gist as comparison material: persistent markdown knowledge bases, source/wiki/schema layering, ingest/query/lint workflows, indexes/logs, and wiki health checks are useful harness concepts, but this skill should not copy that gist's prose.

## Required evidence to inspect

Always inventory these surfaces when present:

- root `AGENTS.md`
- nested `AGENTS.md` and `AGENTS.override.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/rules/**`
- `.codex/prompts/**`
- `.agents/skills/**`
- `.omx/**`
- `.github/workflows/**`
- root README and docs indexes
- `docs/**`
- glossary / terminology / domain-language docs such as `docs/GLOSSARY.md`, `docs/TERMINOLOGY.md`, `internal/CONTEXT.md`, `internal/domain.md`, and `dictionary/**`
- ADR / decision-record surfaces such as `docs/adr/**`, `docs/ADR/**`, and `internal/adr/**`
- doc gardening / wiki / knowledge-base surfaces such as raw sources, generated/synthesized docs, `index.md`, `log.md`, ingest/query/lint workflows, and stale/contradiction/orphan/broken-link checks
- validation scripts and package scripts
- test/build/lint/typecheck/smoke commands
- generated artifact directories
- scaffold/legacy/stage/demo/preview markers
- cross-agent files: `CLAUDE.md`, `.claude/**`, `.cursor/**`, `.windsurf/**`, `.cline/**`, `.gemini/**`, `.github/copilot-instructions.md`

## Run the audit script

From the repo root, after this skill is installed at `.agents/skills/harness-engineering-audit/`, run:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

The script writes:

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

Recommendation defaults are intentionally conservative:

- recommend tools: true
- web verification requested: true
- human approval gate: required
- install/config mutation: false
- write reports: true

Local Python scripts cannot browse. They therefore write a web verification queue and keep `web_verified: false` until a browsing-capable human/agent records evidence. Generated install/config/validation/rollback commands are inert handoff text and must not be executed without explicit approval.

Use a custom output directory only when needed:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --out /tmp/harness-engineering-audit
```

## Execution modes

The script default remains report-only:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --mode audit
```

Additional explicit modes create only low-risk harness artifacts with provenance markers and `setup-rollback-manifest.json`:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --mode safe-setup
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --mode force-ideal-harness
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --mode symphony-repo-local
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --mode symphony-live-handoff
```

`--force` keeps its existing output-overwrite meaning; it is not the force-ideal-harness mode.

Mode boundaries:

- `audit`: reports only, no target source mutation.
- `safe-setup`: creates missing low-risk docs/templates only.
- `force-ideal-harness`: explicit stronger low-risk consolidation; no deletes or CI/config/hooks/security changes.
- `symphony-repo-local`: repo-local Symphony contracts/templates and inert handoff text only.
- `symphony-live-handoff`: approval-gated handoff text only; no install/config mutation.


## Skill update behavior

Normal audit runs check this skill's update status by default and write `update-status.json` plus a `Skill update status` section in `report.md`. This check is report-only and never updates skill files. Disable it with:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --no-check-update
```

Self-update is explicit and approval-gated. To update this one user-scoped skill installation, run:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --self-update --update-scope user
```

The self-update path runs only this command and exits immediately after success:

```bash
gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user --force
```

Project-scoped installs should generally be updated intentionally through the repository and reviewed in a PR. Avoid `gh skill update --all` for this flow because system or manually installed skills may lack GitHub metadata and because this skill should update only itself.

## Score dimensions

The report scores:

1. Agent Legibility
2. Instruction Hygiene
3. Docs Authority
4. Vocabulary / Domain Language Control
5. Doc Gardening / Knowledge Base Readiness
6. Validation Truth
7. Harness Feedback Loops
8. Codex Config Readiness
9. Skills Readiness
10. MCP Readiness
11. Hooks / Rules Safety
12. Subagent / OMX Workflow
13. Cross-Agent Compatibility
14. Entropy / Scaffolding Control
15. Production Readiness
16. Symphony Orchestration Readiness

Scores are strict and intentionally opinionated. A score is not a final truth; it is an evidence-backed signal to guide planning.

The scorecard also includes a lifecycle object and a readiness registry:

- `score_schema_version: "2"`
- `lifecycle.classification`
- `readiness_registry.categories`

The readiness registry exposes additional harness/Symphony categories without silently adding every category as a top-level score dimension.

## Fix classification

Classify every recommendation by confidence and risk.

### Low-risk / high-confidence

Auto-approved by default for an OMX follow-up pass. AGENTS.md items are P0 and should be handled first:

- trim duplicated root `AGENTS.md` content
- add or refresh concise root `AGENTS.md` with docs and validation pointers
- preserve or clarify nested `AGENTS.md` scope boundaries
- add missing docs index links
- document real validation commands
- add a command registry
- add a validation matrix
- add or link concise glossary/domain-language guidance
- add a doc gardening workflow for indexes, logs, source boundaries, and docs health checks
- clarify deterministic automated checks versus judgment-based automated/human review
- add a generated artifact policy
- add a DX preflight script
- classify generated artifacts
- add a repo operating model doc
- document existing MCP/skills/hooks without changing behavior

### Medium-risk

Requires explicit approval before execution:

- restructure docs folders
- add or change MCP servers
- change hook behavior
- change CI validation behavior
- move generated artifacts
- add new skills
- create new repo-level automation

### High-risk

Do not execute without explicit approval:

- delete scaffolding or legacy paths
- rewrite CI or deployment workflows
- change package scripts used by production
- remove hooks/rules/MCP servers used by teams
- alter subagent/team workflow semantics
- change security or sandbox settings

## Low-typing OMX continuation

Do **not** make the user copy or retype the long suggested prompts.

After the audit script runs:

1. Read `report.md` enough to present the summary required below.
2. Use `next-step.json` / `next-step.md` to identify the default next stage.
3. In an interactive OMX runtime, present a structured selection:
   - **Plan auto-approved fixes** (default/recommended)
   - **Execute auto-approved fixes** (only if an execution-ready plan already exists)
   - **Review risky questions** (only for medium/high-risk ambiguity)
   - **Stop after audit**
4. If the user selects a stage, continue in the same session with the corresponding generated prompt file in `prompts/`; do not ask them to paste the command.
5. If no structured selection UI is available, print only the short resume command: `$harness-engineering-audit continue`.

When the user runs `$harness-engineering-audit continue`, inspect `.codex/reports/harness-engineering-audit/next-step.json`. If it exists, resume from its default/recommended stage or present the same selection. If it does not exist, run the audit first.

## AGENTS.md priority lane

Treat `AGENTS.md` improvements as first-class harness fixes:

- Root `AGENTS.md` is P0 when missing, larger than the concise hot-path target, missing validation commands, missing docs/source-of-truth pointers, or missing nested instruction scope guidance.
- Low-risk AGENTS.md changes are auto-approved. Do not wait for another approval to add, trim, or refresh root `AGENTS.md` as a concise operating map.
- Keep root `AGENTS.md` map-like. Move detailed process prose into docs and link to it.
- Preserve nested AGENTS semantics. Do not delete nested instruction files without explicit approval.
- Do not change hooks, MCP, CI, package scripts, security/sandbox settings, source structure, or delete scaffolding as part of the auto-approved AGENTS.md lane.

## OMX handoff workflow

After generating `omx-handoff.md`, the generated prompt files encode this flow:

```text
$ralplan "Read .codex/reports/harness-engineering-audit/prompts/ralplan.md and follow it."

$team "Read .codex/reports/harness-engineering-audit/prompts/team.md and follow it."

$ralph "Read .codex/reports/harness-engineering-audit/prompts/ralph.md and follow it."

$deep-interview "Read .codex/reports/harness-engineering-audit/prompts/deep-interview.md and follow it." # only for medium/high-risk questions
```

## Output discipline

When presenting results, include:

- overall verdict
- score summary
- strongest surfaces
- weakest surfaces
- auto-approved low-risk fixes, especially AGENTS.md P0 items
- medium/high-risk deferred recommendations
- report path
- next OMX selection/resume command

Do not claim the repo is production-ready unless validation truth, instruction hygiene, docs authority, and feedback loops are all strong and evidenced.
