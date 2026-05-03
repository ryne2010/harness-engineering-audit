# Release Checklist

1. Update version references if needed.
2. Run:

```bash
make validate
gh skill publish --dry-run
```

`make validate` includes the release workflow smoke test, which exercises the
same helper used by `.github/workflows/release-skill.yml` against temporary git
histories.

3. Commit and push changes:

```bash
git add -A
git commit -m "Release vX.Y.Z"
git push
```

4. Confirm the release workflow runs after the required main-branch workflow succeeds.
5. Confirm the workflow selected the intended metadata-derived `vX.Y` train and next patch tag.
6. Test install in a clean repo using the published tag.
7. Confirm generated report artifacts are created, including `update-status.json`.
8. Test the documented one-skill update command; do not use `gh skill update --all` for release validation.

Manual `gh skill publish --tag vX.Y.Z` is a fallback for workflow repair only, not the normal release path.
