# Publishing

## Validate

```bash
make validate
gh skill publish --dry-run
```

## Normal release path

Releases are normally automated by `.github/workflows/release-skill.yml`.
After the required main-branch workflow succeeds, the release workflow:

1. Derives the release train from skill/project metadata.
2. Finds the latest matching `vX.Y.x` tag.
3. Checks release-relevant changes from that tag to the workflow head SHA.
4. Runs the canonical `make validate` target.
5. Stamps `release.json` in the source skill and plugin mirror copy.
6. Rechecks mirror parity, validates the package, and publishes the next patch tag.

This keeps patch releases moving without manually editing the workflow for every
patch and prevents a multi-commit push from being skipped just because the final
commit was not release-relevant.

The workflow delegates release decisions to `scripts/release_skill_workflow.py`.
`tests/smoke/run_release_workflow_smoke.py` creates temporary git histories with
tags and verifies the same helper used by GitHub Actions.

Release validation should not run `harness-engineering-audit` against this source
repo as its own quality signal. Use the fixture-based smoke tests in
`make validate`, then use `gh skill publish --dry-run` for package validation.

The hosted release job upgrades the bundled runner GitHub CLI from the official
`cli/cli` release before publishing, because `gh skill` is a preview surface and
can lag on runner images. The workflow still checks `gh skill --help` after
provisioning and fails with a clear precondition error if the selected CLI
release does not provide the command.

## Manual fallback

```bash
gh skill publish --tag vX.Y.Z
```

Use manual publishing only when intentionally bypassing or repairing the
automated workflow. The package-local `release.json` metadata lets installed
skills distinguish the exact published tag from the static development version
in `SKILL.md`.

## Test install

```bash
mkdir -p /tmp/harness-skill-test
cd /tmp/harness-skill-test
git init
echo "# test" > README.md
git add README.md
git commit -m "init"

gh skill install ryne2010/harness-engineering-audit \
  skills/harness-engineering-audit@vX.Y.Z \
  --agent codex \
  --scope project

python3 .agents/skills/harness-engineering-audit/scripts/run_audit.py .
```

## Release hardening

- Keep release immutability enabled in GitHub settings.
- Keep tag protection/versioning rules enabled for `v*` tags.
- Keep code scanning enabled because the skill ships Python scripts.
- Keep the official GitHub CLI provisioning step narrow: download from
  `cli/cli`, install the Linux `.deb`, then verify `gh skill --help` before
  package validation or publishing.
