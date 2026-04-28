# Plugin Distribution

The primary distribution path is `gh skill install`.

This repo also includes an optional Codex plugin wrapper at:

```text
plugins/harness-engineering-audit/
```

The marketplace file is at:

```text
.agents/plugins/marketplace.json
```

For local plugin testing, a marketplace entry may use:

```json
{
  "source": {
    "source": "local",
    "path": "./plugins/harness-engineering-audit"
  }
}
```

For published distribution, prefer a Git-backed source:

```json
{
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/ryne2010/harness-engineering-audit.git",
    "path": "./plugins/harness-engineering-audit",
    "ref": "v0.1.1"
  }
}
```

Add the marketplace from a clone or Git source using Codex plugin marketplace commands when available.
