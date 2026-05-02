#!/usr/bin/env python3
"""Stack profile detection for harness-engineering audits.

This module is intentionally static and stdlib-only. It infers stack tags from
repo-local evidence and never installs, configures, or contacts external services.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCHEMA = "harness.stack-inventory.v1"


def _manifest_paths(inventory: Dict[str, Any]) -> set[str]:
    return {str(item.get("path", "")) for item in inventory.get("manifests", [])}


def _all_paths(inventory: Dict[str, Any]) -> List[str]:
    paths: List[str] = []
    for key in ["instruction_files", "manifests", "validation_docs"]:
        value = inventory.get(key, [])
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("path"):
                    paths.append(str(item["path"]))
                elif isinstance(item, str):
                    paths.append(item)
    for section in ["codex", "omx", "ci", "docs", "skills", "generated_artifacts"]:
        value = inventory.get(section, {})
        if isinstance(value, dict):
            for sub in value.values():
                if isinstance(sub, str):
                    paths.append(sub)
                elif isinstance(sub, list):
                    for item in sub:
                        if isinstance(item, str):
                            paths.append(item)
                        elif isinstance(item, dict) and item.get("path"):
                            paths.append(str(item["path"]))
    return sorted(set(paths))


def _package_data(root: Path) -> Dict[str, Any]:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _deps(package: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        value = package.get(key, {})
        if isinstance(value, dict):
            out.update({str(k).lower(): str(v) for k, v in value.items()})
    return out


def _add(tags: Dict[str, Dict[str, Any]], tag: str, evidence: Iterable[str], confidence: str) -> None:
    current = tags.setdefault(tag, {"tag": tag, "evidence_paths": [], "confidence": confidence})
    merged = set(current.get("evidence_paths", []))
    merged.update(e for e in evidence if e)
    current["evidence_paths"] = sorted(merged)[:20]
    order = {"low": 0, "medium": 1, "high": 2}
    if order.get(confidence, 0) > order.get(str(current.get("confidence", "low")), 0):
        current["confidence"] = confidence


def detect_stack(repo: str | Path, inventory: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(repo).resolve()
    manifests = _manifest_paths(inventory)
    paths = _all_paths(inventory)
    lower_paths = [p.lower() for p in paths]
    package = _package_data(root)
    deps = _deps(package)
    tags: Dict[str, Dict[str, Any]] = {}
    openapi_files = [name for name in ["openapi.yaml", "openapi.yml", "openapi.json"] if (root / name).exists()]

    if "pyproject.toml" in manifests or any(p.endswith("requirements.txt") for p in manifests):
        _add(tags, "python", ["pyproject.toml" if "pyproject.toml" in manifests else "requirements.txt"], "high")
    if "package.json" in manifests:
        _add(tags, "node-js-ts", ["package.json"], "high")
        if any(name in deps for name in ["typescript", "ts-node", "tsx"]):
            _add(tags, "typescript", ["package.json"], "high")
    if "go.mod" in manifests:
        _add(tags, "go", ["go.mod"], "high")
    if "Cargo.toml" in manifests:
        _add(tags, "rust", ["Cargo.toml"], "high")
    if "Makefile" in manifests or any(p.endswith((".sh", ".bash", ".zsh")) for p in lower_paths):
        _add(tags, "shell-cli", [p for p in paths if p == "Makefile" or p.endswith((".sh", ".bash", ".zsh"))], "medium")
    if any(name in deps for name in ["react", "next", "vue", "svelte", "@angular/core"]):
        _add(tags, "frontend-web", ["package.json"], "high")
    if "react" in deps:
        _add(tags, "react-app", ["package.json"], "high")
    if "next" in deps:
        _add(tags, "nextjs-app", ["package.json"], "high")
    if "vue" in deps:
        _add(tags, "vue-app", ["package.json"], "high")
    if "svelte" in deps:
        _add(tags, "svelte-app", ["package.json"], "high")
    if "@angular/core" in deps:
        _add(tags, "angular-app", ["package.json"], "high")
    if "tailwindcss" in deps or any("tailwind" in p for p in lower_paths):
        _add(tags, "tailwind", ["package.json"] + [p for p in paths if "tailwind" in p.lower()], "high")
    if any("shadcn" in p for p in lower_paths) or "shadcn" in deps:
        _add(tags, "shadcn-ui", [p for p in paths if "shadcn" in p.lower()] or ["package.json"], "medium")
    if any("figma" in p for p in lower_paths):
        _add(tags, "figma-driven", [p for p in paths if "figma" in p.lower()], "medium")
    if "@playwright/test" in deps or "playwright" in deps or any("playwright" in p for p in lower_paths):
        _add(tags, "playwright", ["package.json"] + [p for p in paths if "playwright" in p.lower()], "high")
    if "cypress" in deps or any("cypress" in p for p in lower_paths):
        _add(tags, "cypress", ["package.json"] + [p for p in paths if "cypress" in p.lower()], "high")
    if openapi_files or any(p.endswith(("openapi.yaml", "openapi.yml", "openapi.json")) or "openapi" in p for p in lower_paths):
        _add(tags, "openapi", openapi_files + [p for p in paths if "openapi" in p.lower()], "high")
    if "graphql" in deps or any("graphql" in p for p in lower_paths):
        _add(tags, "graphql", ["package.json"] + [p for p in paths if "graphql" in p.lower()], "medium")
    if "trpc" in " ".join(deps) or any("trpc" in p for p in lower_paths):
        _add(tags, "trpc", ["package.json"] + [p for p in paths if "trpc" in p.lower()], "medium")
    if any(p.lower().endswith(("dockerfile", "docker-compose.yml", "docker-compose.yaml")) for p in manifests):
        _add(tags, "docker", [p for p in manifests if "docker" in p.lower()], "high")
    if any("terraform" in p or p.endswith(".tf") for p in lower_paths):
        _add(tags, "infra-terraform", [p for p in paths if "terraform" in p.lower() or p.endswith(".tf")], "medium")
    if any("kubernetes" in p or "k8s" in p for p in lower_paths):
        _add(tags, "kubernetes", [p for p in paths if "kubernetes" in p.lower() or "k8s" in p.lower()], "medium")
    if inventory.get("codex", {}).get("exists"):
        _add(tags, "codex-ready", [inventory.get("codex", {}).get("config") or ".codex"], "high")
    if inventory.get("omx", {}).get("exists"):
        _add(tags, "omx-enabled", [".omx"], "high")
    if inventory.get("skills", {}).get("repo_skills") or "skills/harness-engineering-audit/SKILL.md" in paths:
        _add(tags, "codex-skill-repo", ["skills/harness-engineering-audit/SKILL.md"], "high")
    if any(".codex-plugin" in p or "plugins/" in p for p in lower_paths):
        _add(tags, "codex-plugin-repo", [p for p in paths if ".codex-plugin" in p or p.startswith("plugins/")], "medium")
    if any("mcp" in p for p in lower_paths) or inventory.get("codex", {}).get("mcp_servers"):
        _add(tags, "mcp-server-or-client", [p for p in paths if "mcp" in p.lower()], "medium")
    if inventory.get("docs", {}).get("files"):
        _add(tags, "docs-heavy", inventory.get("docs", {}).get("files", [])[:10], "medium")
    if any(p in manifests for p in ["pnpm-workspace.yaml", "yarn.lock"]) or any("workspace" in str(package.get(k, "")) for k in ["workspaces"]):
        _add(tags, "monorepo", ["package.json"], "medium")
    if (root / "LICENSE").exists() or (root / "CHANGELOG.md").exists():
        _add(tags, "open-source-package", [p for p in ["LICENSE", "CHANGELOG.md"] if (root / p).exists()], "medium")

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "stack_tags": sorted(tags.values(), key=lambda item: item["tag"]),
        "profile_groups": {
            "codex_omx_native": [t for t in tags if t.startswith("codex") or t.startswith("omx") or "mcp" in t],
            "language_runtime": [t for t in tags if t in {"python", "node-js-ts", "typescript", "go", "rust", "shell-cli"}],
            "frontend_design": [t for t in tags if t in {"frontend-web", "react-app", "nextjs-app", "vue-app", "svelte-app", "angular-app", "tailwind", "shadcn-ui", "figma-driven", "playwright", "cypress"}],
            "backend_api_data": [t for t in tags if t in {"openapi", "graphql", "trpc"}],
            "infra_deployment": [t for t in tags if t in {"docker", "infra-terraform", "kubernetes"}],
            "specialized_gated_leads": [t for t in tags if t in {"codex-skill-repo", "codex-plugin-repo", "mcp-server-or-client"}],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect stack tags for a repository inventory.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--out")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    result = detect_stack(args.repo, inventory)
    text = json.dumps(result, indent=2 if args.pretty else None, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
