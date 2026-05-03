#!/usr/bin/env python3
"""Stack profile detection for harness-engineering audits.

This module is intentionally static and stdlib-only. It infers stack tags from
repo-local evidence and never installs, configures, or contacts external services.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

SCHEMA = "harness.stack-inventory.v1"
IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".nuxt", "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}


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


def _repo_paths(root: Path, limit: int = 4000) -> List[str]:
    paths: List[str] = []
    for path in root.rglob("*"):
        if len(paths) >= limit:
            break
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in IGNORE_DIRS for part in rel.parts):
            continue
        if path.is_file():
            paths.append(str(rel))
    return sorted(set(paths))


def _path_tokens(path: str) -> set[str]:
    tokens: set[str] = set()
    for part in Path(path).parts:
        stem = Path(part).stem
        tokens.update(token for token in re.split(r"[^a-z0-9]+", stem.lower()) if token)
    return tokens


def _has_token(path: str, expected: Iterable[str]) -> bool:
    return bool(_path_tokens(path) & set(expected))


def _package_data(root: Path) -> Dict[str, Any]:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _json_file(root: Path, rel_path: str) -> Dict[str, Any]:
    path = root / rel_path
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
    paths = sorted(set(_all_paths(inventory) + _repo_paths(root)))
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
    frontend_layout_paths = [
        p for p in paths
        if p.lower().endswith((".tsx", ".jsx", ".vue", ".svelte"))
        and (
            p.lower().startswith(("app/", "pages/", "src/app/", "src/pages/", "src/components/", "components/"))
            or "/components/" in p.lower()
        )
    ]
    if frontend_layout_paths:
        _add(tags, "frontend-web", frontend_layout_paths, "medium")
    if "react" in deps:
        _add(tags, "react-app", ["package.json"], "high")
    if "next" in deps:
        _add(tags, "nextjs-app", ["package.json"], "high")
    if "nuxt" in deps or any("nuxt.config" in p for p in lower_paths):
        _add(tags, "nuxt-app", ["package.json"] + [p for p in paths if "nuxt.config" in p.lower()], "high")
        _add(tags, "frontend-web", ["package.json"], "high")
    if any(name in deps for name in ["vite", "vitest"]) or any("vite.config" in p for p in lower_paths):
        _add(tags, "vite-app", ["package.json"] + [p for p in paths if "vite.config" in p.lower()], "medium")
        _add(tags, "frontend-web", ["package.json"], "medium")
    if "astro" in deps or any("astro.config" in p for p in lower_paths):
        _add(tags, "astro-app", ["package.json"] + [p for p in paths if "astro.config" in p.lower()], "high")
        _add(tags, "frontend-web", ["package.json"], "high")
    if any(name in deps for name in ["@remix-run/react", "@remix-run/node"]) or any("remix.config" in p for p in lower_paths):
        _add(tags, "remix-app", ["package.json"] + [p for p in paths if "remix.config" in p.lower()], "high")
        _add(tags, "frontend-web", ["package.json"], "high")
    if any("storybook" in name for name in deps) or any(".storybook/" in p for p in lower_paths):
        _add(tags, "storybook", ["package.json"] + [p for p in paths if ".storybook/" in p.lower()], "medium")
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
    root_manifest = _json_file(root, "manifest.json")
    extension_manifest = root_manifest.get("manifest_version") if isinstance(root_manifest, dict) else None
    if extension_manifest or any("extension" in p and ("manifest.json" in p or "browser" in p) for p in lower_paths):
        _add(tags, "browser-extension", [p for p in paths if "extension" in p.lower() or "manifest.json" in p.lower()], "medium")
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
    if inventory.get("ci", {}).get("workflows"):
        _add(tags, "github-actions", inventory.get("ci", {}).get("workflows", []), "high")
        _add(tags, "ci-cd", inventory.get("ci", {}).get("workflows", []), "high")
    if any(p.lower().endswith((".sql", ".dbml")) or "migration" in p.lower() or "schema.prisma" in p.lower() for p in paths):
        _add(tags, "database", [p for p in paths if p.lower().endswith((".sql", ".dbml")) or "migration" in p.lower() or "schema.prisma" in p.lower()], "medium")
    if any(name in deps for name in ["prisma", "@prisma/client"]):
        _add(tags, "prisma", ["package.json"], "high")
    if any(name in deps for name in ["drizzle-orm", "typeorm", "sequelize"]):
        _add(tags, "drizzle", ["package.json"], "medium")
    if any(name in deps for name in ["jsonwebtoken", "passport", "next-auth", "@auth/core", "oauth", "bcrypt"]):
        _add(tags, "auth", ["package.json"], "medium")
        _add(tags, "security-sensitive", ["package.json"], "medium")
    security_tokens = {"auth", "authentication", "authorization", "permission", "permissions", "rbac", "oauth", "jwt"}
    security_paths = [p for p in paths if _has_token(p, security_tokens)]
    if (root / "SECURITY.md").exists():
        security_paths.append("SECURITY.md")
    if security_paths:
        _add(tags, "security-sensitive", security_paths, "medium")
    if any("security" in p.lower() or "secret" in p.lower() or ".env" in p.lower() for p in paths):
        _add(tags, "secrets", [p for p in paths if "security" in p.lower() or "secret" in p.lower() or ".env" in p.lower()], "medium")
    if any(name in deps for name in ["autocannon", "k6", "benchmark", "tinybench"]):
        _add(tags, "benchmark", ["package.json"], "medium")
        _add(tags, "performance", ["package.json"], "medium")
    if any(name in deps for name in ["bullmq", "bull", "ioredis", "redis", "@upstash/redis"]):
        _add(tags, "queue", ["package.json"], "medium")
        _add(tags, "cache", ["package.json"], "medium")
        _add(tags, "performance", ["package.json"], "medium")
    if any("worker" in p.lower() or "queue" in p.lower() or "cache" in p.lower() for p in paths):
        _add(tags, "worker-service", [p for p in paths if any(term in p.lower() for term in ["worker", "queue", "cache"])], "medium")
    if any("load" in p.lower() or "benchmark" in p.lower() or "perf" in p.lower() for p in paths):
        _add(tags, "performance", [p for p in paths if "load" in p.lower() or "benchmark" in p.lower() or "perf" in p.lower()], "medium")
    if any(name in deps for name in ["@sentry/browser", "@sentry/node", "@opentelemetry/api", "prom-client"]):
        _add(tags, "observability", ["package.json"], "medium")
    if any("opentelemetry" in p.lower() or "prometheus" in p.lower() or "grafana" in p.lower() or "sentry" in p.lower() for p in paths):
        _add(tags, "observability", [p for p in paths if any(term in p.lower() for term in ["opentelemetry", "prometheus", "grafana", "sentry"])], "medium")
    if any(name in deps for name in ["react-native", "expo", "flutter"]):
        _add(tags, "mobile-native", ["package.json"], "medium")
        if "react-native" in deps:
            _add(tags, "react-native", ["package.json"], "medium")
        if "expo" in deps:
            _add(tags, "react-native", ["package.json"], "medium")
        if "flutter" in deps:
            _add(tags, "flutter", ["package.json"], "medium")
    mobile_paths = [
        p for p in paths
        if p.lower().endswith((".xcodeproj", ".xcworkspace"))
        or "androidmanifest.xml" in p.lower()
        or p.lower().startswith(("ios/", "android/"))
        or p.lower().endswith("pubspec.yaml")
    ]
    if mobile_paths:
        _add(tags, "mobile-native", mobile_paths, "medium")
    if any(p.lower().endswith("pubspec.yaml") for p in paths):
        _add(tags, "flutter", [p for p in paths if p.lower().endswith("pubspec.yaml")], "medium")
    if any(p.lower().startswith("ios/") or p.lower().endswith((".xcodeproj", ".xcworkspace")) for p in paths):
        _add(tags, "ios", [p for p in paths if p.lower().startswith("ios/") or p.lower().endswith((".xcodeproj", ".xcworkspace"))], "medium")
    if any(p.lower().startswith("android/") or "androidmanifest.xml" in p.lower() for p in paths):
        _add(tags, "android", [p for p in paths if p.lower().startswith("android/") or "androidmanifest.xml" in p.lower()], "medium")
    if any("watchos" in p.lower() or "watchkit" in p.lower() for p in paths):
        _add(tags, "watchos", [p for p in paths if "watchos" in p.lower() or "watchkit" in p.lower()], "medium")
    if any("tvos" in p.lower() for p in paths):
        _add(tags, "tvos", [p for p in paths if "tvos" in p.lower()], "medium")
    if any(name in deps for name in ["electron", "@tauri-apps/api"]):
        _add(tags, "desktop-native", ["package.json"], "medium")
        if "electron" in deps:
            _add(tags, "electron", ["package.json"], "medium")
        if "@tauri-apps/api" in deps:
            _add(tags, "tauri", ["package.json"], "medium")
    if any("electron" in p.lower() for p in paths):
        _add(tags, "desktop-native", [p for p in paths if "electron" in p.lower()], "medium")
        _add(tags, "electron", [p for p in paths if "electron" in p.lower()], "medium")
    if any(p.lower().startswith("src-tauri/") or "tauri.conf" in p.lower() for p in paths):
        _add(tags, "desktop-native", [p for p in paths if p.lower().startswith("src-tauri/") or "tauri.conf" in p.lower()], "medium")
        _add(tags, "tauri", [p for p in paths if p.lower().startswith("src-tauri/") or "tauri.conf" in p.lower()], "medium")
    ai_ml_tokens = {"ai", "ml", "cv", "dataset", "datasets", "notebook", "notebooks", "opencv", "inference", "training", "eval", "modelcard"}
    ai_ml_paths = [
        p for p in paths
        if p.lower().endswith((".ipynb", ".onnx", ".pt", ".pth", ".h5"))
        or _has_token(p, ai_ml_tokens)
        or "model-card" in p.lower()
    ]
    if ai_ml_paths:
        _add(tags, "ai-ml", ai_ml_paths, "medium")
    if any(name in deps for name in ["torch", "tensorflow", "opencv-python", "scikit-learn", "transformers"]):
        _add(tags, "ai-ml", ["package.json"], "medium")
        if "opencv-python" in deps:
            _add(tags, "cv", ["package.json"], "medium")
    if any(
        bool(item.get("validation_scripts")) if isinstance(item, dict) else False
        for item in inventory.get("manifests", [])
    ):
        _add(tags, "qa-validation", ["manifest validation scripts"], "medium")
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
            "frontend_design": [t for t in tags if t in {"frontend-web", "react-app", "nextjs-app", "vue-app", "svelte-app", "angular-app", "nuxt-app", "vite-app", "astro-app", "remix-app", "storybook", "tailwind", "shadcn-ui", "figma-driven", "playwright", "cypress", "browser-extension"}],
            "backend_api_data": [t for t in tags if t in {"openapi", "graphql", "trpc"}],
            "infra_deployment": [t for t in tags if t in {"docker", "infra-terraform", "kubernetes"}],
            "quality_security_data": [t for t in tags if t in {"qa-validation", "security-sensitive", "auth", "database", "ai-ml", "observability", "performance", "queue", "cache", "worker-service"}],
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
