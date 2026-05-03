# Harness Engineering Source Synthesis

Generated: 2026-05-03

Purpose: compile the harness-engineering, Symphony, LLM wiki, AI-coding vocabulary, and recent lane-pack concepts into a practical reference for improving `harness-engineering-audit`.

## Source Set

- OpenAI, Harness engineering: https://openai.com/index/harness-engineering/
- OpenAI, Symphony orchestration: https://openai.com/index/open-source-codex-orchestration-symphony/
- OpenAI Symphony spec: https://github.com/openai/symphony/blob/main/SPEC.md
- Karpathy, LLM Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Matt Pocock, Dictionary of AI Coding: https://github.com/mattpocock/dictionary-of-ai-coding
- Local discussion in this repo: lane packs, grounded source-of-truth surfaces, full-orchestration mode, knowledge-base readiness, doc gardening, task contracts, agent role topology, reconciliation, observability, reproducibility, safety, evaluations, token budgets, release governance, capacity/backpressure, and artifact lifecycle.

## Executive Thesis

A supercharged agent-driven-development repo is not just a codebase plus an `AGENTS.md`. It is a repo-local operating system for agents. The model remains stateless, non-deterministic, and bounded by its context window; the repo must therefore supply durable memory, executable verification, grounded source-of-truth surfaces, recoverable orchestration state, and tool access to the real product environment.

The target state is: one user can ask for a production feature, and the repo gives Codex/OMX enough structure to route the task, load only the relevant context, inspect real app behavior, implement within enforced boundaries, generate proof, and leave durable knowledge for future runs.

The skill should not contain built-in recipes for specific feature types. Instead, it should verify that the repo has generic surfaces that let the existing agent stack succeed on whatever feature the repo actually contains:

- product/task contracts that disambiguate target screens, user-visible terms, supported hosts, and acceptance criteria;
- UI/UX source surfaces with visual targets, design constraints, host matrix, accessibility expectations, and visual QA evidence;
- stack-specific lane surfaces for native, web, backend, data, AI/ML, infra, security, performance, docs, and QA concerns when those stacks are present;
- app-driving tools for relevant hosts, screenshots, logs, traces, runtime events, and proof artifacts;
- automated checks and automated reviews that can catch regressions without waiting for a human;
- safety boundaries around sensitive data, credentials, filesystem writes, network calls, and permissions;
- a review packet contract that proves the feature works in the real product.

Without those surfaces, the prompt is under-specified and the agent must guess.

## Technique Catalog

### 1. Harness As The Productive Unit

The Dictionary of AI Coding separates the model from the harness: tools, prompts, context management, permissions, hooks, and environment access determine whether a model behaves like a coding agent. Harness engineering should audit the whole surrounding system, not just the prompt.

Implications for this skill:

- Score tools, approval posture, sandbox, filesystem scope, browser/device access, MCPs, and validation commands as first-class readiness surfaces.
- Treat model choice as secondary to whether the repo exposes the right evidence and actions.
- Record missing capabilities as repo work, not as "try a smarter model" advice.

### 2. Repo-Local Knowledge Is The System Of Record

OpenAI's harness engineering post argues for a short `AGENTS.md` as a map, with deeper source-of-truth docs in a structured `docs/` directory. The key point is agent legibility: if knowledge is only in Slack, a design meeting, a cloud doc, or a person's head, the agent cannot reliably use it.

Recommended repo surfaces:

- `AGENTS.md` as a concise entry point and routing map.
- `docs/index.md` or equivalent doc index.
- `docs/product/**` for product specs, feature definitions, and user-facing behavior.
- `docs/architecture/**` for domains, layers, dependency rules, contracts, and ADRs.
- `docs/ui/**` for visual targets, design-system decisions, interaction states, host matrix, and accessibility.
- `docs/harness/**` for agent workflows, validation matrix, tool registry, lane packs, artifact policy, and evidence standards.
- `docs/generated/**` only when provenance, freshness, and ownership are explicit.

The anti-pattern is a large monolithic instruction file. It wastes context, becomes stale, and is hard to verify mechanically.

### 3. Progressive Disclosure And Context Budgets

The Dictionary's terms around context, context window, prefix cache, attention degradation, smart zone, handoff, compaction, skills, and subagents should become operational checks.

Harness rules:

- Hot-path instructions must stay small and stable.
- Expensive details should live behind skill/lane docs that load only when relevant.
- Generated timestamps or changing content should not be injected near the top of persistent prompts unless necessary, because changing prefixes can hurt cache behavior.
- Large tasks should create handoff artifacts and tickets before implementation.
- Subagents should isolate noisy exploration or specialist review, not duplicate the parent context.
- Long-running work should checkpoint decisions into files before compaction.

Audit checks should measure whether a repo has an explicit context budget, not just whether it has documentation.

### 4. Persistent Wiki / Doc Gardening

Karpathy's LLM Wiki pattern is directly applicable to repo engineering knowledge. Raw sources stay immutable, the generated/synthesized wiki accumulates knowledge, and a schema tells the agent how to ingest, query, and lint.

Repo adaptation:

- `raw/` or `docs/sources/`: immutable raw material such as meeting notes, user feedback, specs, screenshots, logs, transcripts, design exports, research links, benchmark output, model cards, and incident notes.
- `docs/knowledge/`: agent-maintained synthesis pages such as domain summaries, entity pages, system maps, decision matrices, and comparison tables.
- `docs/knowledge/index.md`: content-oriented catalog.
- `docs/knowledge/log.md`: chronological append-only history of ingests, queries, lint passes, and major synthesis changes.
- `docs/knowledge/schema.md` or `docs/harness/doc-gardening.md`: workflow rules for ingest/query/lint, citation style, update cadence, and ownership.

Doc gardening operations:

- Ingest new source into raw storage, summarize it, update impacted pages, update the index, and append the log.
- Query existing wiki pages and file valuable answers back into durable docs.
- Lint for contradictions, stale claims, orphan pages, missing cross-links, missing source anchors, and concepts mentioned without a page.
- Prefer mechanical validators for links, provenance, and freshness where possible.

The skill already audits doc gardening; the next level is to generate a complete repo-local knowledge operating model and optional validators.

### 5. Canonical Vocabulary And Design Concept

The Dictionary repo is itself a strong harness pattern: terms live as individual markdown files, the README is generated, internal domain docs tell agents where to read before exploring, and contributors are told to use canonical language and flag ADR conflicts.

Repo adaptation:

- `docs/glossary.md` or `docs/domain/vocabulary.md` defines project terms, forbidden synonyms, and examples.
- Domain docs explain when to use each term in issue titles, test names, code symbols, and user-facing labels.
- New feature planning should "grill" the user or product source until the design concept stabilizes.
- If an agent needs a term that is missing, it should either avoid inventing language or record a vocabulary gap.

This matters because one-shot implementation fails when the user and agent do not share a design concept. A prompt that references a specific control, workflow, or product term needs a discoverable design target, product term, or screen mapping.

### 6. Task Contracts And Ticket Quality

Symphony moves work from interactive sessions into issue/task contracts. The Dictionary also distinguishes specs and tickets as handoff artifacts.

Minimum task contract:

- title and user-visible goal;
- affected product area and lane IDs;
- acceptance criteria;
- non-goals;
- dependencies/blockers;
- touched surfaces and ownership;
- risk classification;
- required validation evidence;
- rollback and recovery notes;
- review packet requirements.

High-quality tasks should be executable in a fresh agent session without relying on chat history.

### 7. Lane Packs And Grounded Source-Of-Truth Surfaces

Lane packs are repo-local capability surfaces for repeated agent work. They should not merely document "how to work"; they should name sources of truth, write scopes, validation evidence, and handoff expectations for a lane.

Universal core lanes:

- lane registry;
- agent handoff protocol;
- workflow library;
- contract boundaries;
- runtime evidence standards;
- change taxonomy;
- decision memory;
- context budget architecture;
- tool capability registry;
- drift and staleness control.

Stack-detected lanes:

- frontend UI/UX;
- backend/API contracts;
- data persistence;
- security/trust;
- performance, scalability, reliability;
- infra/CI/CD/Terraform;
- AI/ML/CV/data science;
- mobile native;
- desktop native;
- CLI/developer tooling;
- observability/SRE;
- docs gardening/knowledge;
- QA/evaluation.

Avoid adding a universal catalog of feature-specific capability cards to the skill. If a target repo already has project-defined capability docs, the audit should discover and link them. If not, the skill can recommend a generic "project capability surface" only when repeated feature work in that repo clearly needs one.

### 8. Agent Role Topology

Subagents should be isolated by purpose and context, not just by name.

Useful roles:

- planner/architect for problem decomposition;
- executor for bounded code changes;
- UI/UX designer for screen and interaction intent;
- frontend executor for component implementation;
- mobile/native executor for platform APIs and permissions;
- backend/API executor for contracts and server behavior;
- data/migration executor for schema safety;
- security reviewer for trust boundaries;
- performance reviewer for latency, memory, and capacity;
- test engineer for regression harness and e2e coverage;
- verifier for proof and claim validation;
- docs gardener for source-of-truth updates.

Each role needs:

- owned lane docs;
- write scope;
- evidence requirements;
- escalation rules;
- handoff format;
- banned actions.

The skill should avoid making custom agents the default in conservative modes. It should generate role topology docs in safe setup and custom-agent TOML only in explicit full orchestration.

### 9. Symphony-Style Orchestration

Symphony reframes agent work from "manage sessions" to "manage work". Its strongest concepts are:

- issue tracker as control plane;
- one active task maps to one isolated workspace;
- repo-owned `WORKFLOW.md` governs runtime behavior;
- single orchestrator authority owns claims, retries, dispatch, and reconciliation;
- active/terminal states drive eligibility;
- blockers form a dependency graph;
- bounded global and per-state concurrency;
- retry with backoff;
- terminal cleanup and restart recovery;
- operator-visible observability;
- trust posture documented by the implementation.

Repo-local static readiness can be audited without running Symphony. Full setup should remain explicit because it can create workspaces, run agents, mutate trackers, and require credentials.

### 10. State Machine And Reconciliation

A production harness needs a state model for work, not just a checklist.

State concepts:

- issue/tracker state;
- internal orchestration claim state;
- run attempt state;
- retry queue state;
- workspace lifecycle state;
- validation state;
- review state;
- artifact state.

Reconciliation rules:

- one authority mutates scheduling state;
- running tasks are refreshed against the tracker;
- terminal tasks stop runs and clean workspaces according to policy;
- non-active tasks stop runs without pretending success;
- stalled runs are detected and retried;
- startup cleanup removes stale terminal workspaces;
- persisted artifacts survive process restarts even if live scheduler state does not.

The audit should score whether repos can recover from interrupted agent work and whether task state is inspectable.

### 11. Environment Reproducibility And Isolated Workspaces

OpenAI's harness engineering post emphasizes worktree-bootable apps and isolated observability stacks. Symphony emphasizes deterministic per-issue workspaces and path-bounded execution.

Required surfaces:

- bootstrap command;
- dependency installation command;
- app/server start command;
- database/service setup command;
- fixture/seed data command;
- test account and credential policy;
- worktree or workspace naming policy;
- cleanup command;
- path boundary and sandbox policy;
- per-platform/device setup for mobile, desktop, web, watch, tablet, TV, and browser extension hosts.

For platform-specific features, one-shot success requires the repo to document and expose its own host setup, fixtures, permissions, service stubs, and validation commands. The skill should audit for those generic categories, not predefine feature recipes.

### 12. Observability Depth

Agent-readable observability is a major multiplier. Logs, metrics, traces, browser/device snapshots, screenshots, videos, and runtime events let agents verify behavior instead of guessing.

Maturity levels:

- Level 0: tests only.
- Level 1: structured logs available locally.
- Level 2: app can be launched per workspace/worktree.
- Level 3: UI/device can be driven by tools with screenshots and DOM/accessibility snapshots.
- Level 4: logs, metrics, traces, and app events are queryable per workspace.
- Level 5: proof packets are generated automatically with before/after evidence, video, trace links, metrics, and test results.

The audit should distinguish "has tests" from "agent can observe the real app behavior".

### 13. Evaluation And Regression Harness

Automated checks are deterministic; automated reviews are judgment-based. Both are useful, but they must not be conflated.

Evaluation surfaces:

- unit/integration/e2e tests;
- visual regression tests;
- accessibility checks;
- contract tests;
- migration dry-runs;
- security scans;
- performance benchmarks and budgets;
- model/data eval sets when the repo has AI/ML/data-extraction signals;
- prompt and AI-output evals;
- fixture corpora;
- reviewer prompts and rubrics;
- flaky test policy.

For AI/ML/data-extraction features, the harness should require eval fixtures, expected outputs, confidence thresholds, failure cases, and regression comparisons. A feature is not production-grade because it compiles; it is production-grade when the repo can detect behavioral drift.

### 14. Safety And Trust Boundaries

Safety is a harness property.

Surfaces:

- sandbox and approval modes;
- credential mounting policy;
- network policy;
- filesystem path bounds;
- allowed tools and trust tiers;
- PII/data handling;
- secrets scanning;
- external source trust policy;
- dependency policy;
- generated artifact write policy;
- native device permission policy;
- protected branch and release policy.

For full orchestration, the implementation must document whether it assumes a trusted environment, stricter sandboxing, operator approval, or a hybrid.

### 15. Cost, Context, And Token Budgeting

Agent throughput can be limited by attention and cost, not just CPU.

Policies:

- keep stable prompt prefixes stable;
- put low-frequency docs behind skills/lane packs;
- maintain context packs by lane;
- require handoff artifacts before context-heavy implementation;
- load source files and contracts on demand;
- compact only after writing load-bearing decisions to disk;
- track token/runtime cost when orchestration is active;
- route small lookup tasks to fast/read-only lanes;
- avoid repeated rediscovery with indexes, search, and synthesized docs.

This is both a quality and cost problem. Attention degradation causes faithfulness errors; prefix churn increases spend.

### 16. Release, Merge, And Governance

High agent throughput changes merge economics, but it does not remove governance.

Required policies:

- PR size and lifetime targets;
- required proof packet by change type;
- blocking vs non-blocking checks;
- flaky check policy;
- rebase/conflict handling;
- rollback plan;
- release notes/changelog rules;
- post-merge monitor window;
- ownership and approval rules for high-risk lanes;
- auto-merge eligibility.

The repo should support fast correction while preventing high-risk changes from bypassing evidence.

### 17. Queueing, Capacity, And Backpressure

Symphony's bounded concurrency and retry model should generalize beyond issue trackers.

Surfaces:

- global concurrency limits;
- per-lane and per-state concurrency;
- blocked dependency handling;
- retry/backoff policy;
- rate-limit tracking;
- cancellation/stop conditions;
- stale claim recovery;
- task aging and priority;
- abandoned work detection;
- capacity dashboards.

The skill should inspect whether a repo can run many agent tasks without overwhelming CI, rate limits, reviewers, or shared environments.

### 18. Artifact Lifecycle Beyond Generated Files

Generated source files are only one artifact class. A production agent repo also creates and consumes:

- raw source documents;
- synthesized docs;
- screenshots;
- videos;
- traces;
- benchmark reports;
- model eval results;
- coverage reports;
- migration plans;
- design exports;
- app logs;
- review packets;
- prompt transcripts;
- release notes;
- deployment manifests;
- datasets and fixtures;
- cache/state snapshots.

Each artifact class needs:

- source of truth;
- owner;
- provenance;
- freshness rule;
- retention policy;
- privacy classification;
- verification method;
- cleanup rule;
- whether agents may edit, regenerate, or only read it.

### 19. Entropy Control And Garbage Collection

The OpenAI harness post treats failures as signals for missing docs, tools, guardrails, or abstractions. Over time, taste becomes encoded in docs and tooling, and cleanup becomes recurring background work.

Surfaces:

- golden principles;
- architecture and taste invariants;
- structural tests;
- custom lint error messages with remediation instructions;
- file-size and naming limits;
- boundary validators;
- recurring cleanup plans;
- quality grades by domain/layer;
- drift/staleness checks;
- follow-up issue creation.

The audit should not merely identify missing docs; it should recommend how each repeated failure becomes a durable harness improvement.

## Current Skill Coverage

Recent work already moved `harness-engineering-audit` toward this model:

- lane-pack catalog and registry;
- docs-only `safe-setup`;
- explicit `full-orchestration` for custom-agent TOML;
- stack-detected lane packs;
- activation confidence and advisory candidate policy;
- token-aware stack-signal matching;
- source/plugin mirror tests;
- smoke tests for safe setup vs full orchestration boundaries;
- lifecycle readiness registry;
- doc gardening readiness;
- Symphony static readiness;
- generated artifact policy;
- source trust policy;
- upgrade recommendations;
- stack/tool inventory.

That is a strong foundation. The biggest remaining opportunities are not more taxonomy breadth. They are making each lane operational enough that a future agent can execute from it with less guessing.

## What The Skill Should Not Reimplement

Several important behaviors are already provided by Codex, OMX, and the repo's `AGENTS.md` context path:

- workflow entrypoints such as `$autopilot`, `$ralplan`, `$ralph`, `$team`, and validation loops;
- skill discovery and progressive skill loading;
- native subagent spawning and role isolation;
- mode/state persistence under `.omx/`;
- tool execution, approval modes, sandbox policy, and app/plugin capabilities;
- AGENTS-based routing from the root map into deeper repo docs.

`harness-engineering-audit` should not duplicate those systems. Its job is narrower:

- audit whether the repo gives those systems enough grounded context to work well;
- create conservative source-of-truth docs when missing;
- identify gaps in validation, observability, safety, runtime setup, and docs authority;
- recommend explicit opt-in orchestration surfaces only when the repo has the signals and the user asks for that mode.

## Recommended Further Improvements

### P0: Audit The AGENTS-To-Lane Routing Contract

Do not build a separate prompt-to-lane orchestrator inside the skill. Codex/OMX and the repo's `AGENTS.md` context path already provide the primary routing surface.

The improvement is to audit whether that routing contract is explicit enough:

- root `AGENTS.md` maps task classes to relevant docs, skills, commands, and lanes;
- lane docs name when they apply and what evidence they require;
- stack-detected lane registry reports active, recommended, present, and advisory lanes;
- task contracts point to source-of-truth docs instead of relying on chat history;
- missing route information is reported as a doc gap, not solved by adding another router.

This keeps the skill small while strengthening the existing Codex/OMX path.

### P0: Add Review Packet Contract

One-shot production work needs a standard deliverable beyond "tests pass".

Review packet should include:

- task contract;
- lanes used;
- files changed;
- source docs consulted;
- automated checks;
- automated reviews;
- screenshots/videos where relevant;
- logs/metrics/traces where relevant;
- before/after evidence;
- risks and rollbacks;
- doc updates;
- follow-up tasks.

The audit should check whether repo workflows can produce this packet for each change class.

### P0: Add Agent-Readable App Runtime Contract

The skill should generate/audit `docs/harness/runtime/app-runtime.md` with:

- how to boot the app per workspace;
- how to seed data;
- how to select target host/device;
- how to drive UI flows;
- how to capture screenshots/video when relevant;
- how to query logs/metrics/traces when relevant;
- how to reset state;
- how to run without real production credentials.

This is the missing bridge between source-code readiness and real product behavior.

### P1: Audit Project-Defined Capability Surfaces

Do not ship a fixed catalog of product-feature capability cards. Instead, audit whether the repo has project-defined capability docs for repeated feature classes it actually uses.

Generic fields for a project-defined capability surface:

- product behavior;
- owner/source of truth;
- APIs and contracts;
- permissions and trust boundaries;
- UX states;
- fixtures;
- failure modes;
- validation commands;
- proof requirements.

### P1: Add Source-Backed Claim Validation For Docs

Karpathy's wiki pattern becomes much stronger when claims cite source files and broken links fail validation.

Implement optional validators for:

- every knowledge page has source links;
- source links resolve;
- generated synthesis pages include provenance;
- stale pages are flagged by age or source updates;
- orphan pages are listed;
- contradictions are tracked as explicit issues.

The skill can first generate docs and checklists; later it can add validators behind safe setup or full orchestration.

### P1: Add Architecture Boundary Contract Packs

OpenAI's harness example uses strict dependency direction and structural tests. The skill should not invent app architecture, but it can detect and scaffold boundary contracts:

- domain layer graph;
- allowed dependency edges;
- cross-cutting provider interfaces;
- schema/type naming rules;
- file-size limits;
- generated code boundaries;
- custom lint hooks or test placeholders.

Safe setup can create the docs. Force/full modes can propose or create mechanical validators when stack signals are strong.

### P1: Add Journey Capsules

For UI/product features, create `docs/harness/journeys/`.

Each journey capsule:

- names the user goal;
- maps screens/components/routes;
- lists required fixtures/accounts;
- defines happy path, edge cases, accessibility path, and error path;
- stores screenshots or visual targets;
- maps automated checks and app-driving commands;
- records latest proof artifacts.

This is the UI equivalent of a test fixture plus product spec plus visual source of truth.

### P1: Add Evaluation Dataset Registry

AI/ML/data extraction lanes need durable evals when those stacks are present.

Registry fields:

- dataset/fixture path;
- privacy classification;
- gold output;
- scorer;
- confidence thresholds;
- known failure cases;
- regression history;
- freshness owner.

The skill should not prescribe domain-specific datasets. It should require that the repo's own eval registry names fixtures, expected outputs, privacy rules, and regression assertions for the feature class being implemented.

### P1: Add Orchestration Readiness Levels

Static Symphony readiness is useful, but repos need a ladder:

- Level 0: no orchestration.
- Level 1: task contracts and handoff docs.
- Level 2: lane packs and review packet contract.
- Level 3: workspace/runtime contract and app-driving tools.
- Level 4: issue-state machine, retry/reconciliation docs, and queue/capacity policy.
- Level 5: full orchestration with per-task isolated workspaces and proof packets.

The audit should score the level and explain the next smallest upgrade.

### P1: Add Capacity And Cost Control Surfaces

Generate/audit:

- `docs/harness/capacity.md`;
- `docs/harness/context-budget.md`;
- `docs/harness/rate-limits.md`;
- `docs/harness/ci-capacity.md`.

Track concurrency, model/tool cost, CI saturation, queue age, flaky retries, and token budget. This matters once a single user runs many parallel agent tasks.

### P2: Add Failure-To-Harness Feedback Loop

Every agent miss should become one of:

- missing source doc;
- missing task contract detail;
- missing validation check;
- missing tool;
- missing fixture;
- missing boundary rule;
- missing vocabulary term;
- missing project capability surface;
- missing review packet field.

The skill should generate a "failure classification" template and include it in review packets.

### P2: Add External Knowledge Intake Policy

The wiki pattern and source-trust policy should converge:

- raw intake location;
- accepted source types;
- source trust tiers;
- citation/anchor rules;
- image/media handling;
- external doc freshness;
- when web verification is required;
- when unverified community advice must stay advisory.

This prevents agents from turning a helpful blog post into ungrounded repo policy.

### P2: Add Handoff Compression Standards

Because long sessions degrade, every major workflow should define:

- what must be written before compaction;
- how to summarize decisions;
- what source docs must be reloaded after compaction;
- how subagents return evidence;
- when to clear and restart instead of continuing.

This can be checked as part of agent handoff protocol.

## Suggested Skill Roadmap

1. Audit and tighten the `AGENTS.md` to lane-doc routing contract.
2. Add review-packet contract templates and scoring.
3. Add app-runtime observability contract templates.
4. Audit project-defined capability surfaces without shipping a fixed product-feature catalog.
5. Add journey capsules for UI/product validation.
6. Add source-backed doc-gardening validators.
7. Add architecture boundary contract docs and optional validator generation.
8. Add evaluation dataset registry for AI/ML/data extraction stacks when present.
9. Add orchestration readiness levels with concrete next-upgrade recommendations.
10. Add capacity/cost dashboards and context-budget checks.
11. Add failure-to-harness feedback loop templates.

## Bottom Line

The skill should continue to be conservative by default. `audit` should report. `safe-setup` should create docs and inert contracts. `full-orchestration` should remain explicit for custom-agent and runner surfaces.

But the ideal target is stronger than "repo has good agent docs". The ideal repo gives agents:

- a map;
- grounded sources;
- scoped lanes;
- executable tools;
- observable runtime behavior;
- durable state;
- strict boundaries;
- repeatable evaluations;
- proof packets;
- and a feedback loop that turns every failure into a better harness.

That is what makes one-shot production implementation realistic.
