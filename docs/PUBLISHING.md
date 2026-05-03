# Publishing

## Validate

```bash
make validate
gh skill publish --dry-run
```

## Publish a release

```bash
gh skill publish --tag v0.2.0
```

The release workflow computes the next `v0.2.x` tag and stamps
`skills/harness-engineering-audit/release.json` plus the plugin mirror copy before
`gh skill publish`. That package-local metadata lets installed skills distinguish
the exact release tag from the static development version in `SKILL.md`.

## Test install

```bash
mkdir -p /tmp/harness-skill-test
cd /tmp/harness-skill-test
git init
echo "# test" > README.md
git add README.md
git commit -m "init"

gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@v0.2.0 \
  --agent codex \
  --scope project

python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

## Release hardening

- Keep release immutability enabled in GitHub settings.
- Keep tag protection/versioning rules enabled for `v*` tags.
- Keep code scanning enabled because the skill ships Python scripts.
