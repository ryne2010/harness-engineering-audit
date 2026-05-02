# Install

## Project-scope Codex install

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit \
  --agent codex \
  --scope project
```

## Pinned install

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@v0.2.0 \
  --agent codex \
  --scope project
```

## User-scope install

```bash
gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@v0.2.0 \
  --agent codex \
  --scope user
```

## Manual install

Download the release ZIP from GitHub, unzip it, then copy the skill folder into the target repo:

```bash
mkdir -p .agents/skills
cp -R /path/to/harness-engineering-audit/skills/harness-engineering-audit \
  .agents/skills/harness-engineering-audit
```
