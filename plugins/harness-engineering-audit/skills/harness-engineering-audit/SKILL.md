---
name: harness-engineering-audit
description: Audit a repository for OpenAI-style harness engineering and Codex/OMX readiness. Use when reviewing AGENTS.md, Codex config, OMX workflows, MCP, hooks, rules, skills, subagents, docs authority, validation commands, repo legibility, generated artifact policy, or production readiness for AI-driven development.
---

# Harness Engineering Audit

Use this skill to turn a repository into a production-ready, agent-legible engineering environment optimized for Codex, OMX, and long-running AI-assisted development.

This skill is **audit-first**. It may generate reports and planning artifacts, but it must not modify source files, docs, config, hooks, MCP servers, skills, or CI without a separately approved execution plan.

## Core operating model

1. Inspect the repo and collect evidence.
2. Score the repo against the harness-engineering rubric.
3. Produce a strict report with low/medium/high-risk recommendations.
4. Generate an OMX handoff artifact for planning.
5. Ask for explicit approval before proposing implementation.
6. Use OMX planning/execution for approved fixes.

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
- scaffolding/legacy entropy
- repo legibility for AI agents
- production-readiness for agent-first development

## Authoritative principles

Treat OpenAI/Codex guidance as normative:

- `AGENTS.md` should be a concise map, not an encyclopedia.
- Repo-local docs should be the system of record.
- Validation should be executable and evidence-backed.
- Skills should encode repeatable workflows.
- MCP should solve real external/context access problems.
- Hooks/rules should be deterministic, scoped, and safe.
- Subagents/team workflows should have clear delegation, path scope, and review boundaries.
- Generated artifacts and scaffolding require lifecycle policies.

Use Claude/Cursor/Karpathy/third-party resources only as comparison material, not as authority over Codex behavior.

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
  report.md
  findings.md
  recommended-fixes.md
  omx-handoff.md
```

Use a custom output directory only when needed:

```bash
python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py . --out /tmp/harness-engineering-audit
```

## Score dimensions

The report scores:

1. Agent Legibility
2. Instruction Hygiene
3. Docs Authority
4. Validation Truth
5. Harness Feedback Loops
6. Codex Config Readiness
7. Skills Readiness
8. MCP Readiness
9. Hooks / Rules Safety
10. Subagent / OMX Workflow
11. Cross-Agent Compatibility
12. Entropy / Scaffolding Control
13. Production Readiness

Scores are strict and intentionally opinionated. A score is not a final truth; it is an evidence-backed signal to guide planning.

## Fix classification

Classify every recommendation by confidence and risk.

### Low-risk / high-confidence

Good candidates for an approved OMX plan:

- trim duplicated root `AGENTS.md` content
- add missing docs index links
- document real validation commands
- add a command registry
- add a validation matrix
- add a generated artifact policy
- add a DX preflight script
- classify generated artifacts
- add a repo operating model doc
- document existing MCP/skills/hooks without changing behavior

### Medium-risk

Requires plan and review:

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

## OMX handoff workflow

After generating `omx-handoff.md`, use this flow:

```text
$deep-interview "Read .codex/reports/harness-engineering-audit/omx-handoff.md and conduct a harness-engineering deep review. Ask only questions that affect architecture, validation truth, repo instruction surfaces, or execution risk."

$ralplan "Read the audit report and interview output. Produce .omx/plans/prd-harness-engineering-audit.md and .omx/plans/test-spec-harness-engineering-audit.md. Planning must distinguish low-risk fixes, medium-risk review items, and high-risk deferred work."

$team "Execute only approved low-risk fixes from the harness-engineering plan. Keep root AGENTS map-like, preserve repo-specific docs, update validation evidence, and do not modify risky config without approval."

$ralph "Verify the harness-engineering cleanup. Final output must include what changed, validation run, remaining risk, and stop/no-stop recommendation."
```

## Output discipline

When presenting results, include:

- overall verdict
- score summary
- strongest surfaces
- weakest surfaces
- low-risk approved-candidate fixes
- medium/high-risk deferred recommendations
- report path
- next OMX command to run

Do not claim the repo is production-ready unless validation truth, instruction hygiene, docs authority, and feedback loops are all strong and evidenced.
