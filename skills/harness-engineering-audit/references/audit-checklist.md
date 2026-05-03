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

## Vocabulary / domain language

- [ ] Glossary, terminology, or domain-language docs are discoverable when the repo has domain-specific concepts.
- [ ] Canonical terms and terms to avoid are documented where useful.
- [ ] ADRs or decision records are discoverable.
- [ ] Agents are told to surface conflicts with canonical docs or ADRs.
- [ ] Detailed domain docs are progressively disclosed instead of pasted into hot-path instructions.

## Doc gardening / knowledge base

- [ ] Raw sources and source-of-truth docs are distinct from generated/synthesized docs.
- [ ] Generated or synthesized docs have ownership and freshness rules.
- [ ] Ingest/query/lint workflows are documented where docs are expected to compound over time.
- [ ] Docs indexes and chronological logs exist where useful.
- [ ] Stale claims, contradictions, orphan pages, broken links, and missing cross-references are checked.
- [ ] Navigation/search support exists for larger docs corpora.

## Lane packs / grounded sources

- [ ] Lane registry exists or is recommended.
- [ ] UI-capable repos have UI/UX source-of-truth guidance for visual targets, host matrix, accessibility, and visual QA.
- [ ] Stack-relevant backend/API, data, security, performance, infra, AI/ML/CV, docs, and QA lanes are present or recommended.
- [ ] `safe-setup` lane outputs are docs-only and do not create `.codex/agents`.
- [ ] Project custom-agent TOML is reserved for explicit `full-orchestration`.
- [ ] Stack-detected lane recommendations show activation confidence, matched evidence, and whether the lane is recommended or advisory-only.

## Validation

- [ ] Lint/test/typecheck/build commands are discoverable.
- [ ] CI mirrors key local checks.
- [ ] Runtime/browser/hardware checks exist where relevant.
- [ ] Failing checks are documented.

## Harness feedback loops

- [ ] Preflight scripts exist where useful.
- [ ] Deterministic automated checks are distinguished from automated/human review.
- [ ] Fixtures/golden data are governed.
- [ ] Generated reports have lifecycle policy.
- [ ] Agents can reproduce and validate changes.

## Entropy control

- [ ] Scaffolding/legacy markers are classified.
- [ ] Generated artifacts are not confused with source-of-truth docs.
- [ ] Old plans/stages are archived or retired.
