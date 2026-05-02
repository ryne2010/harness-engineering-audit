# Changelog


## Unreleased

- Adds report-only skill update checks and `update-status.json`.
- Adds explicit `--self-update` / `--update-scope` support that updates only `harness-engineering-audit` and exits with restart guidance.
- Documents safe one-skill update behavior and warns against `gh skill update --all` for this flow.

## v0.2.0

- Adds stack detection, installed tooling inventory, and approval-gated upgrade recommendations.
- Writes `stack-inventory.json`, `tool-inventory.json`, `upgrade-recommendations.*`, `web-verification-queue.json`, and `source-trust-policy.md`.
- Defaults to recommendation reports with web verification requested, honest `web_verified: false` local-script status, required human approval, and no install/config mutation.
- Suppresses external recommendations when native Codex/OMX capabilities already cover the capability.
- Adds a `$ralplan` prompt for approval-gated tool upgrade planning and extends smoke validation.

## v0.1.1

- Adds missing docs referenced by the root README.
- Adds concrete install/download instructions for `ryne2010/harness-engineering-audit`.
- Updates plugin metadata and marketplace source to the published GitHub repository.
- Adds `.gitignore`, validation workflow, and CodeQL workflow.
- Removes generated Python cache files from the distributable repo.
- Makes the smoke test run the skill in isolated stdlib mode.

## v0.1.0

- Initial `harness-engineering-audit` Codex skill.
- Adds Python-only inventory, scoring, and report-rendering scripts.
- Adds OMX handoff artifacts for audit → plan → execution workflows.
- Adds optional Codex plugin wrapper and marketplace example.
