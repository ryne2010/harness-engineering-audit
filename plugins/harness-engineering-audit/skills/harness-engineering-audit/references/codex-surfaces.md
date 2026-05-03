# Codex Surfaces to Audit

Audit these repo surfaces when present.

## AGENTS.md

- root `AGENTS.md`
- nested `AGENTS.md`
- `AGENTS.override.md`
- scope, length, duplication, conflicts, command truth

## Config

- `.codex/config.toml`
- profiles
- sandbox/approval settings
- MCP servers
- model/provider settings if present

## Hooks and rules

- `.codex/hooks.json`
- `.codex/rules/**`
- hook command safety
- deterministic behavior
- overlapping triggers

## Skills

- `.agents/skills/**/SKILL.md`
- `.codex/skills/**` if present
- duplicate names
- script safety
- reference bloat
- implicit invocation suitability

## MCP

- MCP server definitions
- purpose and owner
- auth/secrets
- expected availability
- failure mode

## Subagents and team workflow

- `.codex/agents/*.toml` only when explicitly created by full orchestration
- `.omx/**`
- worktree protocol
- PRD/test-spec artifacts
- team/finisher workflow
- path ownership rules
- custom-agent names avoid built-ins and document explicit invocation only

## Validation

- package scripts
- tools/dev scripts
- CI workflows
- lint/test/typecheck/build/smoke commands
- validation matrix

## Docs authority

- docs index
- spec index
- generated artifact policy
- archive policy
- architecture map
- command registry
- doc gardening workflow
- raw source / synthesized docs boundaries
- docs health checks for stale claims, contradictions, orphan pages, broken links, and missing cross-references
- lane-pack source-of-truth docs under `docs/harness/lane-packs/**`
