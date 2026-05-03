#!/usr/bin/env python3
"""Installed tooling and native capability inventory for harness audits."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCHEMA = "harness.tool-inventory.v1"


def _stack_tags(stack_inventory: Dict[str, Any]) -> set[str]:
    return {str(item.get("tag")) for item in stack_inventory.get("stack_tags", [])}


def _script_names(inventory: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for manifest in inventory.get("manifests", []):
        scripts = manifest.get("scripts") or {}
        if isinstance(scripts, dict):
            for name in scripts:
                names.append(f"{manifest.get('path')}::{name}")
    return sorted(names)


def inventory_tools(repo: str | Path, inventory: Dict[str, Any], stack_inventory: Dict[str, Any]) -> Dict[str, Any]:
    root = Path(repo).resolve()
    tags = _stack_tags(stack_inventory)
    codex = inventory.get("codex", {})
    omx = inventory.get("omx", {})
    skills = inventory.get("skills", {})
    manifests = inventory.get("manifests", [])
    scripts = _script_names(inventory)

    native_capabilities: List[Dict[str, Any]] = []
    if codex.get("exists"):
        native_capabilities.append({
            "id": "codex-project-config",
            "capability": "codex project guidance",
            "covered": True,
            "evidence_paths": [codex.get("config") or ".codex"],
        })
    if codex.get("mcp_servers"):
        native_capabilities.append({
            "id": "codex-mcp",
            "capability": "external context/tool integration",
            "covered": True,
            "evidence_paths": [codex.get("config") or ".codex/config.toml"],
        })
    if skills.get("repo_skills"):
        native_capabilities.append({
            "id": "repo-codex-skills",
            "capability": "repeatable agent workflows",
            "covered": True,
            "evidence_paths": [item.get("path") for item in skills.get("repo_skills", []) if item.get("path")],
        })
    if omx.get("exists"):
        native_capabilities.append({
            "id": "omx-runtime-artifacts",
            "capability": "planning, team orchestration, memory/trace/session state",
            "covered": True,
            "evidence_paths": [".omx"],
        })

    installed_tools: List[Dict[str, Any]] = []
    for manifest in manifests:
        if manifest.get("name") == "package.json":
            installed_tools.append({
                "id": "package-scripts",
                "kind": "package-manager",
                "evidence_paths": [manifest.get("path")],
                "scripts": sorted((manifest.get("scripts") or {}).keys()),
            })
        elif manifest.get("scripts"):
            installed_tools.append({
                "id": f"{str(manifest.get('name', 'manifest')).lower()}-targets",
                "kind": "command-registry",
                "evidence_paths": [manifest.get("path")],
                "scripts": sorted((manifest.get("scripts") or {}).keys()),
            })
        elif manifest.get("path"):
            installed_tools.append({"id": str(manifest.get("name")), "kind": "manifest", "evidence_paths": [manifest.get("path")]})

    capability_gaps: List[Dict[str, Any]] = []
    if not scripts:
        capability_gaps.append({
            "id": "validation-command-discovery",
            "capability": "validation command registry",
            "evidence_paths": [],
            "severity": "medium",
        })
    if "frontend-web" in tags and not ({"playwright", "cypress"} & tags):
        capability_gaps.append({
            "id": "browser-e2e",
            "capability": "browser/runtime validation",
            "evidence_paths": ["package.json"],
            "severity": "medium",
        })
    if ({"openapi", "graphql", "trpc"} & tags) and not any("contract" in s.lower() for s in scripts):
        capability_gaps.append({
            "id": "api-contract-validation",
            "capability": "API contract validation",
            "evidence_paths": ["package.json"],
            "severity": "medium",
        })
    if "python" in tags and not any("pytest" in s.lower() for s in scripts):
        capability_gaps.append({
            "id": "python-test-runner",
            "capability": "Python test runner discoverability",
            "evidence_paths": ["pyproject.toml"],
            "severity": "low",
        })
    if not native_capabilities:
        capability_gaps.append({
            "id": "native-agent-harness",
            "capability": "Codex/OMX native harness surfaces",
            "evidence_paths": [],
            "severity": "medium",
        })

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "native_capabilities": native_capabilities,
        "installed_tools": installed_tools,
        "capability_gaps": capability_gaps,
        "validation_scripts": scripts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory installed harness tooling and capabilities.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--stack", required=True)
    parser.add_argument("--out")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    stack = json.loads(Path(args.stack).read_text(encoding="utf-8"))
    result = inventory_tools(args.repo, inventory, stack)
    text = json.dumps(result, indent=2 if args.pretty else None, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
