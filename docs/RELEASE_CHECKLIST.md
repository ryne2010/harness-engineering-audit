# Release Checklist

1. Update version references if needed.
2. Run:

```bash
make validate
gh skill publish --dry-run
```

3. Commit changes:

```bash
git add -A
git commit -m "Release vX.Y.Z"
git push
```

4. Publish:

```bash
gh skill publish --tag vX.Y.Z
```

5. Test install in a clean repo.
6. Confirm generated report artifacts are created.
