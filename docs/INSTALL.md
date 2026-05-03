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


## Force-update this skill only

For a user-scoped Codex install, update only this skill with:

```bash
gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user --force
```

The audit script also exposes an explicit self-update helper:

```bash
python3 ~/.codex/skills/harness-engineering-audit/scripts/run_audit.py . --self-update --update-scope user
```

Normal audit runs only report update status. They do not auto-update. Avoid `gh skill update --all` here because system/manual skills may not have GitHub metadata and this flow should update only `harness-engineering-audit`. Project-scope installs should generally be updated through the repository and reviewed in a PR.
