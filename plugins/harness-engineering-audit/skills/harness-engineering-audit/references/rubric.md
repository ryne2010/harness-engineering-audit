# Harness Engineering Audit Rubric

This rubric scores a repo across 16 dimensions. Scores are intentionally strict and evidence-based.

Score schema v2 also reports lifecycle classification and a nested readiness registry. The registry covers additional harness/Symphony concepts without forcing every category into the top-level score average.

Scale:

- 0-2: absent or misleading
- 3-4: present but weak / stale / risky
- 5-6: workable but incomplete
- 7-8: strong with minor gaps
- 9-10: production-ready and well-evidenced

## 1. Agent Legibility

Can a coding agent quickly discover the repo layout, commands, constraints, and stop conditions?

Signals:

- concise root instructions
- README or docs entrypoint
- architecture map / source-of-truth index
- package scripts visible
- validation commands visible
- generated artifact policy visible

## 2. Instruction Hygiene

Are instruction files scoped, short, and non-duplicative?

Signals:

- root `AGENTS.md` acts as a map
- nested `AGENTS.md` files are used only when needed
- no giant instruction blob
- no contradictory instructions
- detailed workflow guidance lives in docs

## 3. Docs Authority

Are docs the system of record?

Signals:

- docs index or spec index
- docs ownership / authority rules
- current validation matrix
- architecture / ADR / module docs
- active vs archive separation

## 4. Vocabulary / Domain Language Control

Does the repo expose canonical language so agents use the project's terms instead of inventing synonyms?

Signals:

- glossary / terminology / domain-language docs
- terms to prefer and avoid
- ADR or decision-record surfaces
- guidance to flag conflicts with source-of-truth docs or ADRs
- progressive-disclosure rules for loading detailed domain docs only when needed

## 5. Doc Gardening / Knowledge Base Readiness

Does the repo treat docs as a maintained knowledge system rather than a static pile of markdown?

Signals:

- raw source / source-of-truth boundaries are clear
- generated or synthesized docs are labeled and owned
- ingest, query, and lint/health-check workflows are documented
- docs index and chronological log surfaces exist where useful
- stale claims, contradictions, orphan pages, broken links, and missing cross-references are checked
- navigation/search support exists for larger docs corpora

## 6. Validation Truth

Are commands real, documented, and runnable?

Signals:

- scripts for lint/test/typecheck/build/validate
- CI mirrors local validation
- docs reference existing commands
- failures and blockers are explicit

## 7. Harness Feedback Loops

Can agents run checks and diagnose failures without humans micromanaging?

Signals:

- deterministic automated checks: tests, typecheck, lint, build, smoke, preflight
- judgment-based automated review is distinguished from deterministic checks
- human review expectations name the artifact to review, not only the agent summary
- e2e/browser/runtime checks where relevant
- fixtures/golden datasets
- preflight scripts
- failure reports

## 8. Codex Config Readiness

Is `.codex/config.toml` useful, scoped, and safe?

Signals:

- repo-specific config when needed
- sandbox/approval model documented
- MCP servers purposeful
- no user-global assumptions hidden in repo workflow

## 9. Skills Readiness

Are skills focused, discoverable, and non-duplicative?

Signals:

- `.agents/skills/*/SKILL.md`
- clear skill descriptions
- scripts/references bundled as needed
- no duplicate skill names
- no skill bloat

## 10. MCP Readiness

Are MCP servers useful and safe?

Signals:

- MCP config present only when useful
- server purpose documented
- auth/secret risks understood
- no flaky or over-scoped MCPs silently required

## 11. Hooks / Rules Safety

Are hooks/rules deterministic and scoped?

Signals:

- hooks documented
- hooks do not fight each other
- hooks do not hide failures
- hooks are repo-safe and not user-global surprises

## 12. Subagent / OMX Workflow

Are multi-agent workflows durable and conflict-aware?

Signals:

- `.omx/context` and `.omx/plans` when used
- worktree/path-scope protocol
- PRD/test-spec before implementation
- final verification/finisher workflow

## 13. Cross-Agent Compatibility

Do other assistant surfaces conflict with Codex/OMX?

Signals:

- `CLAUDE.md`, `.cursor`, `.windsurf`, `.cline`, `.gemini`, Copilot instructions audited if present
- no contradictory rules across agents
- Codex remains the center of this skill's scoring

## 14. Entropy / Scaffolding Control

Is legacy/scaffold/generated noise governed?

Signals:

- generated artifact policy
- archive policy
- scaffolding retirement plan
- preview/demo/stage artifacts classified
- no historical clutter in production paths

## 15. Production Readiness

Is the repo ready for repeatable agentic development?

Signals:

- strong validation
- docs authority
- low instruction entropy
- clear production vs harness boundaries
- stop/no-stop criteria

## 16. Symphony Orchestration Readiness

Can the repository support a future OpenAI Symphony-style issue-tracker control plane without first requiring a human to rediscover workflow, workspace, validation, observability, and recovery contracts?

Signals:

- repo-owned workflow / agent contracts
- task-state or control-plane handoff surfaces
- workspace isolation guidance
- agent runner / CLI guidance
- observability and proof-of-work reporting
- validation / CI guardrails
- recovery, resume, rollback, or reconciliation guidance

Non-goals for the audit dimension:

- no daemon/service execution
- no live tracker API calls
- no target-repo auto-modification
- no reference implementation setup

## Nested Readiness Registry

The report must also expose evidence/gaps for:

- Task Contract / Ticket Quality
- Agent Role Topology / Isolation
- State Machine / Reconciliation
- Observability Depth
- Environment Reproducibility
- Safety / Trust Boundaries
- Evaluation / Regression Harness
- Cost / Context / Token Budgeting
- Release / Merge Governance
- Queueing / Capacity / Backpressure
- Artifact Provenance / Lifecycle
