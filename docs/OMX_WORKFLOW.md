# OMX Workflow

The skill is audit-first. The audit script itself does not modify repo source files, but low-risk findings are auto-approved for the follow-up OMX execution pass. Root `AGENTS.md` improvements are P0 when the audit finds missing, stale, oversized, or under-informative instruction surfaces.

Interactive OMX runs should avoid copy/paste: after the audit, select **Plan auto-approved fixes** when the skill offers the next-stage choice. To resume later, type:

```text
$harness-engineering-audit continue
```

The generated prompt files keep the full handoff text out of the terminal input line:

```text
$ralplan "Read .codex/reports/harness-engineering-audit/prompts/ralplan.md and follow it."
$team "Read .codex/reports/harness-engineering-audit/prompts/team.md and follow it."
$ralph "Read .codex/reports/harness-engineering-audit/prompts/ralph.md and follow it."
$deep-interview "Read .codex/reports/harness-engineering-audit/prompts/deep-interview.md and follow it." # medium/high-risk questions only
$ralplan "Read .codex/reports/harness-engineering-audit/prompts/tool-upgrade-ralplan.md and follow it." # approval-gated tool upgrades only
```

Tool upgrade planning is always separate from auto-approved harness fixes. It must verify official/high-trust sources first, prefer native Codex/OMX coverage, and treat generated install/config/rollback commands as inert until a human approves a specific tooling action.
