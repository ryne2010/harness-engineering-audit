# Cross-Agent Surfaces

This skill is tailored for Codex and OMX. Other agent surfaces should be audited only to detect conflicts or duplicate instruction systems.

Check when present:

- `CLAUDE.md`
- `.claude/**`
- `.cursor/**`
- `.windsurf/**`
- `.cline/**`
- `.gemini/**`
- `.github/copilot-instructions.md`
- `.continue/**`
- `.aider*`
- custom `rules/` or `.rules/` directories

Questions:

- Do these files contradict `AGENTS.md`?
- Do they point to stale commands?
- Do they duplicate repo guidance?
- Are they scoped to their agent, or do they pretend to be general authority?
- Do they create conflicting hooks or MCP behavior?
- Should they be kept, archived, or summarized in a cross-agent policy?

Do not make non-Codex tools normative for this skill. Codex/OpenAI guidance is the authority.
