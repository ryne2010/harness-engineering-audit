# Audit Checklist

## Instructions

- [ ] Root `AGENTS.md` exists or there is a clear reason it does not.
- [ ] Root instructions are concise and map-like.
- [ ] Nested instructions are scoped and non-duplicative.
- [ ] Commands in instructions exist.
- [ ] Done criteria are clear.

## Config

- [ ] `.codex/config.toml` exists if repo-specific config is needed.
- [ ] MCP servers are purposeful and documented.
- [ ] Hooks are deterministic and safe.
- [ ] Rules do not conflict with instructions.

## Skills

- [ ] Skills live in `.agents/skills` when repo-scoped.
- [ ] Skill names are unique.
- [ ] `SKILL.md` descriptions are trigger-friendly.
- [ ] Scripts are safe and scoped.

## Docs

- [ ] Docs index exists.
- [ ] Source-of-truth docs are identifiable.
- [ ] Archive/generated docs are distinguished from active docs.
- [ ] Internal links are plausible.

## Validation

- [ ] Lint/test/typecheck/build commands are discoverable.
- [ ] CI mirrors key local checks.
- [ ] Runtime/browser/hardware checks exist where relevant.
- [ ] Failing checks are documented.

## Harness feedback loops

- [ ] Preflight scripts exist where useful.
- [ ] Fixtures/golden data are governed.
- [ ] Generated reports have lifecycle policy.
- [ ] Agents can reproduce and validate changes.

## Entropy control

- [ ] Scaffolding/legacy markers are classified.
- [ ] Generated artifacts are not confused with source-of-truth docs.
- [ ] Old plans/stages are archived or retired.
