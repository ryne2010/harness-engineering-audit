#!/usr/bin/env python3
"""Lane-pack catalog and runtime registry helpers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

CATALOG_SCHEMA = "harness-engineering-audit.lane-pack-catalog.v1"
REGISTRY_SCHEMA = "harness-engineering-audit.lane-pack-registry.v1"
SKILL_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = SKILL_DIR / "assets" / "lane-packs.json"
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"
MODE_SAFETY = {
    "audit_report_only": True,
    "safe_setup_docs_only": True,
    "custom_agents_full_orchestration_only": True,
}
CONFIDENCE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
RISK_RECOMMENDATION_FLOOR = {"low": "low", "medium": "medium", "high": "high"}


def load_lane_pack_catalog(path: Path = CATALOG_PATH) -> Dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    validate_lane_pack_catalog(catalog)
    return catalog


def validate_lane_pack_catalog(catalog: Dict[str, Any]) -> None:
    if catalog.get("schema") != CATALOG_SCHEMA:
        raise ValueError(f"unexpected lane catalog schema: {catalog.get('schema')}")
    lanes = catalog.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("lane catalog must contain lanes")
    built_ins = set(catalog.get("built_in_agent_names", []))
    seen_ids: set[str] = set()
    seen_agent_names: set[str] = set()
    required = {
        "id", "title", "activation", "risk", "description", "safe_setup_targets",
        "full_orchestration_targets", "source_of_truth_expectations", "validation_expectations",
    }
    for lane in lanes:
        missing = sorted(required - set(lane))
        if missing:
            raise ValueError(f"lane {lane.get('id', '<unknown>')} missing keys: {missing}")
        lane_id = str(lane["id"])
        if lane_id in seen_ids:
            raise ValueError(f"duplicate lane id: {lane_id}")
        seen_ids.add(lane_id)
        if lane["activation"] not in {"universal", "stack"}:
            raise ValueError(f"invalid activation for {lane_id}: {lane['activation']}")
        if lane["risk"] not in {"low", "medium", "high"}:
            raise ValueError(f"invalid risk for {lane_id}: {lane['risk']}")
        for target in lane.get("safe_setup_targets", []):
            _validate_target(lane_id, target, allow_agent=False)
        for target in lane.get("full_orchestration_targets", []):
            _validate_target(lane_id, target, allow_agent=True)
            agent_name = target.get("agent_name")
            if agent_name:
                if agent_name in built_ins:
                    raise ValueError(f"custom agent {agent_name} collides with built-in name")
                if agent_name in seen_agent_names:
                    raise ValueError(f"duplicate custom agent name: {agent_name}")
                seen_agent_names.add(str(agent_name))


def _validate_target(lane_id: str, target: Dict[str, Any], allow_agent: bool) -> None:
    template = str(target.get("template", ""))
    target_path = str(target.get("target", ""))
    if not template or not target_path:
        raise ValueError(f"lane {lane_id} target missing template or target")
    if Path(template).is_absolute() or ".." in Path(template).parts:
        raise ValueError(f"lane {lane_id} target template must be repo-relative and bounded: {template}")
    if Path(target_path).is_absolute() or ".." in Path(target_path).parts:
        raise ValueError(f"lane {lane_id} target path must be repo-relative and bounded: {target_path}")
    if not (TEMPLATE_DIR / template).exists():
        raise ValueError(f"lane {lane_id} references missing template: {template}")
    if not allow_agent and target_path.startswith(".codex/agents"):
        raise ValueError(f"lane {lane_id} safe target must not write .codex/agents")
    if target_path.startswith(".codex/agents") and not target.get("agent_name"):
        raise ValueError(f"lane {lane_id} agent target missing agent_name")


def catalog_lanes(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(catalog.get("lanes", []))


def stack_tag_set(stack_inventory: Dict[str, Any]) -> set[str]:
    return {str(item.get("tag")) for item in stack_inventory.get("stack_tags", []) if item.get("tag")}


def stack_profile_set(stack_inventory: Dict[str, Any]) -> set[str]:
    profiles = stack_inventory.get("profile_groups", {}) or {}
    active = set()
    for name, values in profiles.items():
        if values:
            active.add(str(name))
    return active


def lane_is_active(lane: Dict[str, Any], tags: set[str], profiles: set[str]) -> Tuple[bool, str]:
    if lane.get("activation") == "universal":
        return True, "universal"
    lane_tags = set(lane.get("activation_tags", []) or [])
    lane_profiles = set(lane.get("activation_profile_groups", []) or [])
    if lane_tags & tags or lane_profiles & profiles:
        return True, "stack_detected"
    return False, "not_activated"


def confidence_at_least(value: str, floor: str) -> bool:
    return CONFIDENCE_ORDER.get(value, 0) >= CONFIDENCE_ORDER.get(floor, 0)


def stack_tag_lookup(stack_inventory: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item.get("tag")): item
        for item in stack_inventory.get("stack_tags", [])
        if isinstance(item, dict) and item.get("tag")
    }


def lane_activation_details(
    lane: Dict[str, Any],
    tags_by_name: Dict[str, Dict[str, Any]],
    profiles: set[str],
) -> Dict[str, Any]:
    if lane.get("activation") == "universal":
        return {
            "activation_confidence": "high",
            "activation_evidence_paths": [],
            "activation_reason": "Universal core lane.",
            "matched_tags": [],
            "matched_profile_groups": [],
        }

    lane_tags = set(lane.get("activation_tags", []) or [])
    lane_profiles = set(lane.get("activation_profile_groups", []) or [])
    matched_tags = sorted(lane_tags & set(tags_by_name))
    matched_profiles = sorted(lane_profiles & profiles)
    evidence: set[str] = set()
    confidence = "none"
    for tag in matched_tags:
        payload = tags_by_name.get(tag, {})
        tag_confidence = str(payload.get("confidence", "low"))
        if confidence_at_least(tag_confidence, confidence):
            confidence = tag_confidence
        evidence.update(str(item) for item in payload.get("evidence_paths", []) if item)
    if matched_profiles and confidence == "none":
        confidence = "medium"
    reason_bits = []
    if matched_tags:
        reason_bits.append("matched tags: " + ", ".join(matched_tags[:8]))
    if matched_profiles:
        reason_bits.append("matched profile groups: " + ", ".join(matched_profiles[:4]))
    return {
        "activation_confidence": confidence,
        "activation_evidence_paths": sorted(evidence)[:20],
        "activation_reason": "; ".join(reason_bits) if reason_bits else "No activation evidence detected.",
        "matched_tags": matched_tags,
        "matched_profile_groups": matched_profiles,
    }


def path_exists(repo: Path, rel_path: str) -> bool:
    return (repo / rel_path).exists()


def all_inventory_paths(inventory: Dict[str, Any]) -> List[str]:
    paths: List[str] = []
    for key in ["instruction_files", "manifests", "validation_docs"]:
        value = inventory.get(key, [])
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("path"):
                    paths.append(str(item["path"]))
                elif isinstance(item, str):
                    paths.append(item)
    for section in ["codex", "omx", "ci", "docs", "skills", "generated_artifacts", "cross_agent"]:
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


def matching_paths(repo: Path, inventory: Dict[str, Any], expectations: Iterable[str]) -> List[str]:
    known = all_inventory_paths(inventory)
    matches: set[str] = set()
    for expected in expectations:
        expected = str(expected)
        if path_exists(repo, expected):
            matches.add(expected)
        prefix = expected.rstrip("/") + "/"
        for path in known:
            lower = path.lower()
            if path == expected or path.startswith(prefix) or expected.lower() in lower:
                matches.add(path)
    return sorted(matches)[:20]


def host_matrix_for_lane(lane_id: str, tags: set[str]) -> Dict[str, bool]:
    if lane_id != "frontend-ui-ux":
        return {}
    return {
        "web": bool(tags & {"frontend-web", "react-app", "nextjs-app", "vue-app", "svelte-app", "angular-app"}),
        "desktop": bool(tags & {"desktop-native", "electron", "tauri"}),
        "mobile": bool(tags & {"mobile-native", "ios", "android", "react-native", "flutter"}),
        "tablet": bool(tags & {"mobile-native", "ios", "android", "react-native", "flutter"}),
        "watch": bool(tags & {"watchos"}),
        "tv": bool(tags & {"tvos"}),
        "embedded": bool(tags & {"embedded"}),
        "browser_extension": bool(tags & {"browser-extension"}),
    }


def build_lane_pack_registry(
    repo: str | Path,
    inventory: Dict[str, Any],
    stack_inventory: Dict[str, Any],
    catalog: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    root = Path(repo).resolve()
    catalog = catalog or load_lane_pack_catalog()
    tags = stack_tag_set(stack_inventory)
    tags_by_name = stack_tag_lookup(stack_inventory)
    profiles = stack_profile_set(stack_inventory)
    lanes: Dict[str, Any] = {}
    active_lane_ids: List[str] = []
    missing_required_lane_ids: List[str] = []
    recommended_lane_ids: List[str] = []

    for lane in catalog_lanes(catalog):
        lane_id = str(lane["id"])
        active, activation_state = lane_is_active(lane, tags, profiles)
        activation_details = lane_activation_details(lane, tags_by_name, profiles)
        safe_targets = [str(t["target"]) for t in lane.get("safe_setup_targets", [])]
        full_targets = [str(t["target"]) for t in lane.get("full_orchestration_targets", [])]
        custom_agent_names = [
            str(t["agent_name"]) for t in lane.get("full_orchestration_targets", []) if t.get("agent_name")
        ]
        evidence_paths = matching_paths(root, inventory, lane.get("source_of_truth_expectations", []))
        target_evidence = [target for target in safe_targets + full_targets if path_exists(root, target)]
        evidence_paths = sorted(set(evidence_paths + target_evidence))[:20]
        present = bool(evidence_paths)
        if active:
            active_lane_ids.append(lane_id)
        risk = str(lane.get("risk", "low"))
        recommendation_floor = RISK_RECOMMENDATION_FLOOR.get(risk, "medium")
        meets_recommendation_floor = confidence_at_least(
            str(activation_details.get("activation_confidence", "none")),
            recommendation_floor,
        )
        if present:
            status = "present"
        elif active:
            if meets_recommendation_floor:
                status = "recommended"
                recommended_lane_ids.append(lane_id)
                missing_required_lane_ids.append(lane_id)
            else:
                status = "candidate"
        else:
            status = "not_applicable"
        lanes[lane_id] = {
            "id": lane_id,
            "title": lane.get("title", lane_id),
            "status": status,
            "activation": activation_state,
            "risk": risk,
            "activation_confidence": activation_details.get("activation_confidence", "none"),
            "activation_evidence_paths": activation_details.get("activation_evidence_paths", []),
            "activation_reason": activation_details.get("activation_reason", ""),
            "matched_tags": activation_details.get("matched_tags", []),
            "matched_profile_groups": activation_details.get("matched_profile_groups", []),
            "recommendation_policy": (
                "present"
                if present else
                "recommended"
                if active and meets_recommendation_floor else
                "advisory-candidate"
                if active else
                "not-applicable"
            ),
            "recommendation_reason": (
                "Source-of-truth surface already detected."
                if present else
                f"{risk} risk lane met {recommendation_floor} confidence floor."
                if active and meets_recommendation_floor else
                f"{risk} risk lane did not meet {recommendation_floor} confidence floor; report as advisory only."
                if active else
                "Lane was not activated by current repo evidence."
            ),
            "safe_setup_targets": safe_targets,
            "full_orchestration_targets": full_targets,
            "custom_agent_names": custom_agent_names,
            "evidence_paths": evidence_paths,
            "missing_surfaces": [] if present or not active else list(lane.get("source_of_truth_expectations", [])),
            "source_of_truth_paths": list(lane.get("source_of_truth_expectations", [])),
            "host_matrix": host_matrix_for_lane(lane_id, tags),
            "recommendations": [] if present or not active else [
                f"Create {lane.get('title', lane_id)} lane source-of-truth docs and validation evidence."
            ],
            "description": lane.get("description", ""),
        }

    return {
        "schema": REGISTRY_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_schema": catalog.get("schema", CATALOG_SCHEMA),
        "catalog_version": catalog.get("version", "unknown"),
        "repo_root": str(root),
        "mode_safety": dict(MODE_SAFETY),
        "lanes": lanes,
        "active_lane_ids": sorted(active_lane_ids),
        "missing_required_lane_ids": sorted(missing_required_lane_ids),
        "recommended_lane_ids": sorted(recommended_lane_ids),
        "custom_agent_policy": {
            "safe_setup_creates_custom_agents": False,
            "full_orchestration_creates_custom_agents": True,
            "built_in_agent_names": list(catalog.get("built_in_agent_names", [])),
        },
    }


def setup_targets_for_mode(
    lane_registry: Dict[str, Any] | None,
    mode: str,
    catalog: Dict[str, Any] | None = None,
) -> List[Dict[str, str]]:
    if not lane_registry or mode == "audit":
        return []
    catalog = catalog or load_lane_pack_catalog()
    catalog_by_id = {str(lane["id"]): lane for lane in catalog_lanes(catalog)}
    out: List[Dict[str, str]] = []
    lanes = lane_registry.get("lanes", {}) if isinstance(lane_registry, dict) else {}
    eligible_ids: set[str] = set(lane_registry.get("recommended_lane_ids", []) or [])
    if mode == "full-orchestration":
        eligible_ids.update(
            str(lane_id)
            for lane_id, payload in lanes.items()
            if isinstance(payload, dict) and payload.get("status") == "present"
        )
    for lane_id in sorted(eligible_ids):
        lane = catalog_by_id.get(lane_id, {})
        for target in lane.get("safe_setup_targets", []):
            out.append({"lane_id": lane_id, "template": str(target["template"]), "target": str(target["target"])})
        if mode == "full-orchestration":
            for target in lane.get("full_orchestration_targets", []):
                out.append({"lane_id": lane_id, "template": str(target["template"]), "target": str(target["target"])})
    return out
