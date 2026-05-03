# AGENTS.md

This repo packages the `harness-engineering-audit` Codex skill.

## Operating Map

- Source skill payload: `skills/harness-engineering-audit/`
- Plugin mirror payload: `plugins/harness-engineering-audit/skills/harness-engineering-audit/`
- Smoke test: `tests/smoke/run_skill_smoke.py`
- Mirror parity check: `tests/check_skill_mirror.py`
- User docs: `README.md` and `docs/`
- Generated audit output: `.codex/reports/harness-engineering-audit/`

## Development Rules

- Keep the source skill and plugin mirror in sync.
- Do not add dependencies for validation or packaging unless explicitly requested.
- Keep audit mode report-only; setup modes must remain explicit and bounded.
- Keep user-scope and project-scope install examples distinct.
- Prefer small, reversible patches over broad rewrites.

## Validation

Run before claiming completion:

```bash
make validate
```

`make validate` compiles Python scripts, checks plugin mirror parity, and runs the smoke suite.

## Docs Authority

- `docs/README.md` is the docs index.
- `docs/USAGE.md` is the user workflow reference.
- `docs/INSTALL.md` is the install/update reference.
- `docs/HARNESS_ENGINEERING_SOURCE_SYNTHESIS.md` records source concepts and synthesis.
