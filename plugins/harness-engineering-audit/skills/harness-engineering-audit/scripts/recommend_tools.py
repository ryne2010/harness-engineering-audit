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
TOOL_CATALOG_SCHEMA = "harness.tool-catalog.v1"
SKILL_DIR = Path(__file__).resolve().parents[1]
TOOL_CATALOG_PATH = SKILL_DIR / "assets" / "tool-catalog.json"
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
CATALOG_REQUIRED_KEYS = {
    "id",
    "name",
    "capabilities",
    "stack_tags",
    "source_url",
    "source_owner",
    "trust_tier",
    "last_reviewed",
    "install_commands",
    "config_commands",
    "validation_commands",
    "rollback_commands",
}


def load_tool_catalog(path: Path = TOOL_CATALOG_PATH) -> List[Dict[str, Any]]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("schema") != TOOL_CATALOG_SCHEMA:
        raise ValueError(f"unexpected tool catalog schema: {catalog.get('schema')}")
    entries = catalog.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("tool catalog must contain entries")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("tool catalog entries must be objects")
        missing = sorted(CATALOG_REQUIRED_KEYS - set(entry))
        if missing:
            raise ValueError(f"tool catalog entry {entry.get('id', '<unknown>')} missing keys: {missing}")
        entry_id = str(entry["id"])
        if entry_id in seen:
            raise ValueError(f"duplicate tool catalog id: {entry_id}")
        seen.add(entry_id)
        if entry["trust_tier"] not in SOURCE_TRUST_POLICY:
            raise ValueError(f"invalid trust tier for {entry_id}: {entry['trust_tier']}")
        list_fields = [
            "capabilities",
            "stack_tags",
            "install_commands",
            "config_commands",
            "validation_commands",
            "rollback_commands",
        ]
        for key in list_fields:
            if not isinstance(entry.get(key), list):
                raise ValueError(f"tool catalog entry {entry_id} field {key} must be a list")
    return entries


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
    catalog_entries: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    tags = _tag_set(stack_inventory)
    catalog_entries = list(catalog_entries) if catalog_entries is not None else load_tool_catalog()
    recommendations: List[Dict[str, Any]] = []
    suppressions: List[Dict[str, Any]] = []
    queue: List[Dict[str, Any]] = []

    if recommend_tools:
        for entry in catalog_entries:
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
        "catalog_last_reviewed": max(entry["last_reviewed"] for entry in catalog_entries),
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
