#!/usr/bin/env python3
"""Approval-gated tooling recommendations for harness-engineering audits."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCHEMA = "harness.upgrade-recommendations.v1"
QUEUE_SCHEMA = "harness.web-verification-queue.v1"
DEFAULT_POLICY = {
    "recommend_tools": True,
    "web_requested": True,
    "install_config_mutation": False,
    "approval_gate": "required",
    "write_reports": True,
}

SOURCE_TRUST_POLICY = {
    "tier0-official": "Official vendor, framework, OpenAI/Codex/OMX, or package-manager source.",
    "tier1-high-trust": "Mature ecosystem project with clear ownership, license, releases, and docs.",
    "tier2-discovery": "Community discovery only; must be primary-source verified before action.",
    "tier3-unverified": "Unverified lead; warning required and not actionable by default.",
    "blocked": "Unsafe or blocked source; do not recommend.",
}
NATIVE_SUPPRESSIBLE_IDS = {"codex-mcp", "omx-native-workflows", "codex-agents-md"}

SEED_CATALOG = [
    {
        "id": "codex-agents-md",
        "name": "AGENTS.md guidance",
        "capabilities": ["agent instructions", "repo guidance"],
        "stack_tags": ["codex-ready", "docs-heavy"],
        "source_url": "https://developers.openai.com/codex/guides/agents-md",
        "source_owner": "OpenAI",
        "trust_tier": "tier0-official",
        "last_reviewed": "2026-05-02",
        "license_hint": None,
        "install_commands": [],
        "config_commands": ["Edit AGENTS.md after approval; keep it concise and map-like."],
        "validation_commands": ["Review generated harness audit report and run documented repo validation."],
        "rollback_commands": ["git checkout -- AGENTS.md"],
    },
    {
        "id": "codex-mcp",
        "name": "Codex MCP integration",
        "capabilities": ["external context", "tool integration"],
        "stack_tags": ["codex-ready", "mcp-server-or-client"],
        "source_url": "https://developers.openai.com/codex/mcp",
        "source_owner": "OpenAI",
        "trust_tier": "tier0-official",
        "last_reviewed": "2026-05-02",
        "license_hint": None,
        "install_commands": [],
        "config_commands": ["Add scoped MCP config only after purpose, owner, auth, and rollback are approved."],
        "validation_commands": ["codex mcp list || true"],
        "rollback_commands": ["Remove the approved MCP entry from .codex/config.toml"],
    },
    {
        "id": "omx-native-workflows",
        "name": "OMX native workflows",
        "capabilities": ["planning", "team orchestration", "verification", "trace", "memory"],
        "stack_tags": ["omx-enabled"],
        "source_url": "https://github.com/ryne2010/oh-my-codex",
        "source_owner": "oh-my-codex",
        "trust_tier": "tier1-high-trust",
        "last_reviewed": "2026-05-02",
        "license_hint": None,
        "install_commands": [],
        "config_commands": ["Prefer existing OMX workflows before adding external orchestration tooling."],
        "validation_commands": ["omx status || true"],
        "rollback_commands": ["No repo mutation required for recommendation-only use."],
    },
    {
        "id": "pytest",
        "name": "pytest",
        "capabilities": ["python tests", "test discovery"],
        "stack_tags": ["python"],
        "source_url": "https://docs.pytest.org/",
        "source_owner": "pytest-dev",
        "trust_tier": "tier1-high-trust",
        "last_reviewed": "2026-05-02",
        "license_hint": "MIT",
        "install_commands": ["python -m pip install pytest"],
        "config_commands": ["Add pytest configuration only after approval."],
        "validation_commands": ["python -m pytest"],
        "rollback_commands": ["python -m pip uninstall pytest"],
    },
    {
        "id": "playwright",
        "name": "Playwright",
        "capabilities": ["browser e2e", "frontend runtime validation"],
        "stack_tags": ["frontend-web", "react-app", "nextjs-app", "vue-app", "svelte-app", "angular-app"],
        "source_url": "https://playwright.dev/",
        "source_owner": "Microsoft Playwright",
        "trust_tier": "tier1-high-trust",
        "last_reviewed": "2026-05-02",
        "license_hint": "Apache-2.0",
        "install_commands": ["npm init playwright@latest"],
        "config_commands": ["Add Playwright config and tests only after approval."],
        "validation_commands": ["npx playwright test"],
        "rollback_commands": ["Remove Playwright config/tests and package entries from the approved diff."],
    },
    {
        "id": "shadcn-ui",
        "name": "shadcn/ui",
        "capabilities": ["ui component workflow", "design-system scaffolding"],
        "stack_tags": ["shadcn-ui", "tailwind", "react-app", "nextjs-app"],
        "source_url": "https://ui.shadcn.com/",
        "source_owner": "shadcn",
        "trust_tier": "tier1-high-trust",
        "last_reviewed": "2026-05-02",
        "license_hint": "MIT",
        "install_commands": ["npx shadcn@latest init"],
        "config_commands": ["Run shadcn init/add only after approval because it mutates source/config."],
        "validation_commands": ["npm run lint", "npm test"],
        "rollback_commands": ["Revert generated components/config from the approved diff."],
    },
    {
        "id": "figma-mcp",
        "name": "Figma MCP/server integration",
        "capabilities": ["design-source integration", "design context"],
        "stack_tags": ["figma-driven", "design-system"],
        "source_url": "https://help.figma.com/",
        "source_owner": "Figma",
        "trust_tier": "tier0-official",
        "last_reviewed": "2026-05-02",
        "license_hint": None,
        "install_commands": [],
        "config_commands": ["Add Figma integration only after token scope and MCP trust review."],
        "validation_commands": ["Confirm Figma MCP/tool access with least-privilege credentials."],
        "rollback_commands": ["Remove Figma MCP config and revoke related tokens."],
    },
    {
        "id": "openapi-generator",
        "name": "OpenAPI Generator",
        "capabilities": ["api client/server generation", "contract workflow"],
        "stack_tags": ["openapi"],
        "source_url": "https://openapi-generator.tech/",
        "source_owner": "OpenAPI Generator",
        "trust_tier": "tier1-high-trust",
        "last_reviewed": "2026-05-02",
        "license_hint": "Apache-2.0",
        "install_commands": ["Use an approved package-manager or container invocation for openapi-generator."],
        "config_commands": ["Add generation config only after approving generated artifact lifecycle."],
        "validation_commands": ["Run existing API/client tests after generation."],
        "rollback_commands": ["Remove generated files/config from the approved diff."],
    },
    {
        "id": "docker-official",
        "name": "Docker official tooling",
        "capabilities": ["container validation", "runtime parity"],
        "stack_tags": ["docker"],
        "source_url": "https://docs.docker.com/",
        "source_owner": "Docker",
        "trust_tier": "tier0-official",
        "last_reviewed": "2026-05-02",
        "license_hint": None,
        "install_commands": [],
        "config_commands": ["Add/modify Docker files only after runtime ownership approval."],
        "validation_commands": ["docker build ."],
        "rollback_commands": ["Revert Dockerfile/compose changes from the approved diff."],
    },
]


def _tag_set(stack_inventory: Dict[str, Any]) -> set[str]:
    return {str(item.get("tag")) for item in stack_inventory.get("stack_tags", [])}


def _capability_covered(tool_inventory: Dict[str, Any], capability: str) -> Dict[str, Any] | None:
    cap_low = capability.lower()
    for native in tool_inventory.get("native_capabilities", []):
        haystack = f"{native.get('id', '')} {native.get('capability', '')}".lower()
        if any(word in haystack for word in cap_low.split()):
            return native
    return None


def _base_source(entry: Dict[str, Any], web_requested: bool) -> Dict[str, Any]:
    return {
        "source_url": entry.get("source_url"),
        "source_owner": entry.get("source_owner"),
        "trust_tier": entry.get("trust_tier"),
        "last_reviewed": entry.get("last_reviewed"),
        "verification_mode": "static-catalog",
        "web_requested": web_requested,
        "web_verified": False,
        "license_hint": entry.get("license_hint"),
        "freshness_status": "review-needed",
    }


def generate_recommendations(
    stack_inventory: Dict[str, Any],
    tool_inventory: Dict[str, Any],
    recommend_tools: bool = True,
    web_requested: bool = True,
) -> Dict[str, Any]:
    tags = _tag_set(stack_inventory)
    recommendations: List[Dict[str, Any]] = []
    suppressions: List[Dict[str, Any]] = []
    queue: List[Dict[str, Any]] = []

    if recommend_tools:
        for entry in SEED_CATALOG:
            if not tags.intersection(set(entry.get("stack_tags", []))):
                continue
            source = _base_source(entry, web_requested=web_requested)
            primary_capability = str((entry.get("capabilities") or [entry.get("name")])[0])
            covered = _capability_covered(tool_inventory, primary_capability)
            common = {
                "id": entry["id"],
                "title": entry["name"],
                "detected_evidence": sorted(tags.intersection(set(entry.get("stack_tags", [])))),
                "stack_tags": sorted(set(entry.get("stack_tags", [])).intersection(tags)),
                "capability_gap": primary_capability,
                "expected_material_benefit": f"Improves {primary_capability} for agentic development workflows.",
                "risk": "medium" if entry.get("install_commands") else "low",
                "confidence": "medium" if source["freshness_status"] == "review-needed" else "high",
                "approval_required": True,
                "tooling_action_human_approval_required": True,
                "audit_fix_auto_approved": False,
                "install_config_mutation": False,
                "install_commands": entry.get("install_commands", []),
                "config_commands": entry.get("config_commands", []),
                "validation_commands": entry.get("validation_commands", []),
                "rollback_commands": entry.get("rollback_commands", []),
                **source,
            }
            queue.append({
                "id": entry["id"],
                "source_url": entry.get("source_url"),
                "trust_tier": entry.get("trust_tier"),
                "web_requested": web_requested,
                "web_verified": False,
                "verification_mode": "static-catalog",
                "reason": "Confirm current official/high-trust installation and rollback guidance before action.",
            })
            if covered and entry["id"] in NATIVE_SUPPRESSIBLE_IDS:
                suppressions.append({
                    **common,
                    "suppressed": True,
                    "suppression_reason": "Native Codex/OMX capability already covers this gap.",
                    "covered_by": [covered.get("id")],
                    "evidence_paths": covered.get("evidence_paths", []),
                    "unsuppress_if": "Native coverage is absent, unhealthy, or insufficient for the target repo's explicit need.",
                })
            else:
                recommendations.append({
                    **common,
                    "suppressed": False,
                    "suppression_reason": None,
                    "covered_by": [],
                })

    if not recommendations and recommend_tools:
        recommendations.append({
            "id": "custom-harness-tooling-proposal",
            "title": "Custom harness tooling proposal",
            "detected_evidence": [],
            "stack_tags": sorted(tags),
            "capability_gap": "No official/high-trust catalog fit was selected.",
            "expected_material_benefit": "Create a narrowly scoped custom Codex skill, MCP adapter, or hook only when existing official/high-trust tools do not fit.",
            "source_url": None,
            "source_owner": "local proposal",
            "trust_tier": "tier2-discovery",
            "risk": "medium",
            "confidence": "low",
            "approval_required": True,
            "tooling_action_human_approval_required": True,
            "audit_fix_auto_approved": False,
            "install_config_mutation": False,
            "web_requested": web_requested,
            "web_verified": False,
            "verification_mode": "repo-local-only",
            "install_commands": [],
            "config_commands": ["Draft a custom skill/MCP/hook design and seek approval before implementation."],
            "validation_commands": ["Run the repo validation suite after approved implementation."],
            "rollback_commands": ["Revert the approved custom tooling diff."],
            "suppressed": False,
            "suppression_reason": None,
            "covered_by": [],
        })

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": dict(DEFAULT_POLICY, recommend_tools=recommend_tools, web_requested=web_requested),
        "source_trust_policy": SOURCE_TRUST_POLICY,
        "catalog_last_reviewed": max(entry["last_reviewed"] for entry in SEED_CATALOG),
        "recommendations": recommendations,
        "suppressions": suppressions,
        "web_verification_queue": {
            "schema": QUEUE_SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "web_requested": web_requested,
            "web_verified": False,
            "verification_mode": "static-catalog",
            "entries": queue,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate approval-gated upgrade recommendations.")
    parser.add_argument("--stack", required=True)
    parser.add_argument("--tools", required=True)
    parser.add_argument("--out")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--no-recommend-tools", action="store_true")
    parser.add_argument("--no-web", action="store_true")
    args = parser.parse_args()
    stack = json.loads(Path(args.stack).read_text(encoding="utf-8"))
    tools = json.loads(Path(args.tools).read_text(encoding="utf-8"))
    result = generate_recommendations(
        stack,
        tools,
        recommend_tools=not args.no_recommend_tools,
        web_requested=not args.no_web,
    )
    text = json.dumps(result, indent=2 if args.pretty else None, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
