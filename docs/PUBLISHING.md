# Publishing

## Validate

```bash
python3 -m py_compile skills/harness-engineering-audit/scripts/*.py tests/smoke/run_skill_smoke.py
python3 tests/smoke/run_skill_smoke.py
gh skill publish --dry-run
```

## Publish a release

```bash
gh skill publish --tag v0.2.0
```

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
