# Source Trust Policy

The upgrade recommendation layer is stack-agnostic and Codex/OMX-first.

- Prefer native Codex/OMX capabilities before recommending external tools.
- Prefer official vendor, framework, OpenAI/Codex/OMX, or package-manager sources.
- Allow mature high-trust ecosystem projects only when ownership, license, releases, and docs are clear.
- Treat community discovery as non-actionable until primary-source verification is complete.
- Do not recommend unverified or blocked tools as installable actions.
- Keep local-script web verification honest: Python report generation writes `web_verified: false` and queues sources for later verification.
- Require human approval before install/config/source mutation.
- Generate validation and rollback commands as inert handoff text; do not execute them during audit.
