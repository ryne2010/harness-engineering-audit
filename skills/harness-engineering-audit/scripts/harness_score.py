#!/usr/bin/env python3
"""Score a harness-engineering inventory."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

DIMENSIONS = [
    "Agent Legibility",
    "Instruction Hygiene",
    "Docs Authority",
    "Vocabulary / Domain Language Control",
    "Doc Gardening / Knowledge Base Readiness",
    "Validation Truth",
    "Harness Feedback Loops",
    "Codex Config Readiness",
    "Skills Readiness",
    "MCP Readiness",
    "Hooks / Rules Safety",
    "Subagent / OMX Workflow",
    "Cross-Agent Compatibility",
    "Entropy / Scaffolding Control",
    "Production Readiness",
    "Symphony Orchestration Readiness",
]

RISK_DEFAULTS = {
    "low": ("auto-approved", True, "auto-approved-follow-up"),
    "medium": ("review-required", False, "plan-before-execution"),
    "high": ("explicit-approval-required", False, "explicit-human-approval"),
}


def clamp(score: int) -> int:
    return max(0, min(10, int(score)))


def status(score: int) -> str:
    if score >= 9:
        return "excellent"
    if score >= 7:
        return "strong"
    if score >= 5:
        return "partial"
    if score >= 3:
        return "weak"
    return "missing"


def slugify(value: Any, max_len: int = 96) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return (text or "item")[:max_len].strip("-") or "item"


def unique_items(items: List[Any]) -> List[Any]:
    seen = set()
    output = []
    for item in items:
        marker = json.dumps(item, sort_keys=True, default=str) if isinstance(item, (dict, list)) else str(item)
        if marker in seen:
            continue
        seen.add(marker)
        output.append(item)
    return output


def recommendation_id(rec: Dict[str, Any]) -> str:
    if rec.get("id"):
        return slugify(rec["id"], max_len=128)
    basis = "|".join(
        str(rec.get(key, ""))
        for key in ["risk", "category", "title", "detail"]
        if rec.get(key) is not None
    )
    return f"rec-{slugify(basis, max_len=140)}"


def normalize_evidence(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def merged_values(*values: Any) -> List[str]:
    merged: List[str] = []
    for value in values:
        merged.extend(normalize_evidence(value))
    return unique_items(merged)


def normalize_recommendation(
    rec: Dict[str, Any],
    *,
    default_dimension: str = "General",
    source: str = "scorecard",
    evidence: List[str] | None = None,
) -> Dict[str, Any]:
    out = dict(rec)
    risk = str(out.get("risk", "medium")).lower()
    if risk not in {"low", "medium", "high"}:
        risk = "medium"
    out["risk"] = risk
    out["dimension"] = str(out.get("dimension") or default_dimension)
    out["title"] = str(out.get("title") or "Recommendation")
    out["detail"] = str(out.get("detail") or "")
    out["source"] = str(out.get("source") or source)

    combined_evidence = normalize_evidence(out.get("evidence")) + normalize_evidence(evidence)
    if combined_evidence:
        out["evidence"] = unique_items(combined_evidence)[:10]

    approval, auto_approved, actionability = RISK_DEFAULTS[risk]
    out["auto_approved"] = auto_approved
    out["approval"] = approval
    out.setdefault("actionability", actionability)

    out["id"] = recommendation_id(out)
    return out


def priority_rank(value: Any) -> int:
    ranks = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
    return ranks.get(str(value or "p9").lower(), 9)


def recommendation_sort_key(rec: Dict[str, Any]) -> tuple[int, str, str, str]:
    return (
        priority_rank(rec.get("priority")),
        str(rec.get("source", "")),
        str(rec.get("dimension", "")),
        str(rec.get("title", "")),
    )


def merge_duplicate_recommendation(existing: Dict[str, Any], new: Dict[str, Any]) -> None:
    merged_sources = merged_values(
        existing.get("sources") or existing.get("source"),
        new.get("sources") or new.get("source"),
    )
    existing["source"] = merged_sources[0] if merged_sources else existing.get("source", "scorecard")
    if len(merged_sources) > 1:
        existing["sources"] = merged_sources

    merged_dimensions = merged_values(
        existing.get("related_dimensions") or existing.get("dimension"),
        new.get("related_dimensions") or new.get("dimension"),
    )
    existing["dimension"] = merged_dimensions[0] if merged_dimensions else existing.get("dimension", "General")
    if len(merged_dimensions) > 1:
        existing["related_dimensions"] = merged_dimensions

    evidence = merged_values(existing.get("evidence"), new.get("evidence"))
    if evidence:
        existing["evidence"] = evidence[:10]

    if priority_rank(new.get("priority")) < priority_rank(existing.get("priority")):
        existing["priority"] = new.get("priority")


def dedupe_recommendations(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for rec in recs:
        normalized = normalize_recommendation(rec)
        rec_id = normalized["id"]
        if rec_id in by_id:
            merge_duplicate_recommendation(by_id[rec_id], normalized)
        else:
            by_id[rec_id] = normalized
    return sorted(by_id.values(), key=recommendation_sort_key)


def summarize_recommendations(
    low_risk: List[Dict[str, Any]],
    medium_risk: List[Dict[str, Any]],
    high_risk: List[Dict[str, Any]],
) -> Dict[str, Any]:
    all_recs = low_risk + medium_risk + high_risk
    return {
        "schema": "harness-engineering-audit.recommendation-summary.v1",
        "low_risk": len(low_risk),
        "medium_risk": len(medium_risk),
        "high_risk": len(high_risk),
        "total": len(all_recs),
        "auto_approved": sum(1 for rec in all_recs if rec.get("auto_approved")),
        "review_required": sum(1 for rec in all_recs if rec.get("approval") == "review-required"),
        "explicit_approval_required": sum(1 for rec in all_recs if rec.get("approval") == "explicit-approval-required"),
        "p0": sum(1 for rec in all_recs if str(rec.get("priority", "")).lower() == "p0"),
        "dedupe_policy": "stable recommendation IDs derived from risk/category/title/detail; duplicate sources, dimensions, and evidence are merged.",
    }


def add(score: int, points: int, evidence: List[str], text: str) -> int:
    evidence.append(text)
    return score + points


def dim(name: str, score: int, evidence: List[str], gaps: List[str], recs: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "name": name,
        "score": clamp(score),
        "status": status(clamp(score)),
        "evidence": evidence,
        "gaps": gaps,
        "recommendations": recs,
    }


def any_script(manifests: List[Dict[str, Any]], keywords: List[str]) -> bool:
    for m in manifests:
        scripts = m.get("scripts") or {}
        for name, cmd in scripts.items():
            low = f"{name} {cmd}".lower()
            if any(k in low for k in keywords):
                return True
    return False


def script_names(manifests: List[Dict[str, Any]], keywords: List[str]) -> List[str]:
    found = []
    for m in manifests:
        scripts = m.get("scripts") or {}
        for name, cmd in scripts.items():
            low = f"{name} {cmd}".lower()
            if any(k in low for k in keywords):
                found.append(f"{m.get('path')}::{name}")
    return sorted(found)


def score_inventory(inv: Dict[str, Any]) -> Dict[str, Any]:
    dims: List[Dict[str, Any]] = []
    manifests = inv.get("manifests", [])
    docs = inv.get("docs", {})
    vocabulary = inv.get("vocabulary_readiness", {})
    doc_gardening = inv.get("doc_gardening_readiness", {})
    instructions = inv.get("instruction_files", [])
    codex = inv.get("codex", {})
    skills = inv.get("skills", {})
    omx = inv.get("omx", {})
    ci = inv.get("ci", {})
    markers = inv.get("markers", {})
    gen = inv.get("generated_artifacts", {})
    lifecycle = inv.get("lifecycle", {})
    readiness_registry = inv.get("readiness_registry", {})
    lane_pack_registry = inv.get("lane_pack_registry", {})

    # 1 Agent Legibility
    evidence: List[str] = []
    gaps: List[str] = []
    recs: List[Dict[str, str]] = []
    s = 0
    if instructions:
        s = add(s, 2, evidence, f"Found {len(instructions)} AGENTS instruction file(s).")
    else:
        gaps.append("No AGENTS.md files found.")
        recs.append({
            "risk": "low",
            "priority": "p0",
            "title": "Add concise root AGENTS.md",
            "detail": "Create a map-like root AGENTS.md with commands, constraints, docs pointers, and scoped instruction rules as the first harness fix.",
        })
    if docs.get("exists"):
        s = add(s, 2, evidence, f"docs/ exists with {len(docs.get('files', []))} markdown file(s).")
    else:
        gaps.append("No docs/ directory found.")
    if docs.get("indexes"):
        s = add(s, 2, evidence, f"Found docs index candidates: {', '.join(docs.get('indexes', [])[:5])}")
    else:
        gaps.append("No obvious docs index found.")
        recs.append({"risk": "low", "title": "Add docs index", "detail": "Add docs/README.md or docs/pack/SPEC_INDEX.md as the docs entry point."})
    if manifests:
        s = add(s, 1, evidence, f"Found {len(manifests)} manifest/build entry file(s).")
    if any_script(manifests, ["test", "lint", "build", "validate", "typecheck", "smoke"]):
        s = add(s, 2, evidence, "Validation/build scripts are discoverable from manifests.")
    else:
        gaps.append("No obvious validation/build scripts found in manifests.")
    dims.append(dim("Agent Legibility", s, evidence, gaps, recs))

    # 2 Instruction Hygiene
    evidence, gaps, recs = [], [], []
    s = 6 if instructions else 2
    root_agents = [x for x in instructions if x.get("path") == "AGENTS.md"]
    if root_agents:
        root = root_agents[0]
        root_gaps = []
        if not root.get("has_commands"):
            root_gaps.append("validation/build commands")
        if not root.get("mentions_docs"):
            root_gaps.append("docs/source-of-truth pointers")
        if not root.get("mentions_validation"):
            root_gaps.append("validation expectations")
        if root_gaps:
            gaps.append(f"Root AGENTS.md is missing: {', '.join(root_gaps)}.")
            recs.append({
                "risk": "low",
                "priority": "p0",
                "title": "Refresh root AGENTS.md operating map",
                "detail": "Auto-approved first pass: update root AGENTS.md with repo purpose, authoritative docs, validation commands, constraints, and nested AGENTS scope rules without duplicating long-form docs.",
            })
        if root.get("bytes", 0) <= 16_384:
            s = add(s, 2, evidence, "Root AGENTS.md is within the strict 16 KiB target.")
        elif root.get("bytes", 0) <= 32_768:
            s = add(s, 1, evidence, "Root AGENTS.md is under 32 KiB but may be too heavy for hot-path use.")
            gaps.append("Root AGENTS.md exceeds strict 16 KiB map-like target.")
            recs.append({
                "risk": "low",
                "priority": "p0",
                "title": "Trim root AGENTS.md",
                "detail": "Auto-approved first pass: move detailed role/process content into docs and keep root AGENTS as a routing map.",
            })
        else:
            gaps.append("Root AGENTS.md is larger than 32 KiB and likely too large for hot-path guidance.")
            recs.append({
                "risk": "low",
                "priority": "p0",
                "title": "Shrink root AGENTS.md",
                "detail": "Auto-approved first pass: convert root AGENTS.md into a concise map and move details to docs.",
            })
            s -= 2
    else:
        gaps.append("No root AGENTS.md found.")
        recs.append({
            "risk": "low",
            "priority": "p0",
            "title": "Create root AGENTS.md operating map",
            "detail": "Auto-approved first pass: add a concise root AGENTS.md that points to authoritative docs, validation commands, constraints, and nested instruction scope rules.",
        })
    duplicate_big = [x for x in instructions if x.get("bytes", 0) > 32_768]
    if not duplicate_big:
        s = add(s, 1, evidence, "No AGENTS files exceed 32 KiB.")
    else:
        gaps.append(f"Large AGENTS files: {', '.join(x['path'] for x in duplicate_big)}")
    nested = [x for x in instructions if x.get("path") != "AGENTS.md"]
    if nested:
        s = add(s, 1, evidence, f"Found scoped nested instruction file(s): {', '.join(x['path'] for x in nested[:5])}")
    else:
        gaps.append("No nested AGENTS.md files detected; verify whether subtrees need scoped instructions.")
    dims.append(dim("Instruction Hygiene", s, evidence, gaps, recs))

    # 3 Docs Authority
    evidence, gaps, recs = [], [], []
    s = 0
    if docs.get("exists"):
        s = add(s, 2, evidence, "docs/ exists.")
    if docs.get("indexes"):
        s = add(s, 2, evidence, "Docs index candidates exist.")
    else:
        gaps.append("No docs index candidates found.")
    if docs.get("authority_docs"):
        s = add(s, 2, evidence, f"Authority/canonical docs detected: {', '.join(docs.get('authority_docs', [])[:5])}")
    else:
        gaps.append("No docs authority/source-of-truth guidance detected.")
        recs.append({"risk": "low", "title": "Add docs authority map", "detail": "Document which docs are source-of-truth, generated, archived, or supporting."})
    if docs.get("generated_policy_docs"):
        s = add(s, 2, evidence, "Generated artifact policy candidates detected.")
    else:
        gaps.append("No generated artifact lifecycle policy detected.")
    if inv.get("validation_docs"):
        s = add(s, 1, evidence, f"Validation-related docs detected: {len(inv.get('validation_docs', []))}.")
    dims.append(dim("Docs Authority", s, evidence, gaps, recs))

    # 4 Vocabulary / Domain Language Control
    evidence, gaps, recs = [], [], []
    categories = vocabulary.get("categories", {}) if isinstance(vocabulary, dict) else {}
    category_status = vocabulary.get("category_status", {}) if isinstance(vocabulary, dict) else {}
    s = 0
    vocab_checks = [
        ("glossary_or_terms", "Project glossary or canonical vocabulary surfaces are discoverable."),
        ("adr_or_decision_records", "ADR or decision-record surfaces are discoverable."),
        ("conflict_guidance", "Guidance exists for surfacing conflicts with canonical docs or ADRs."),
        ("progressive_disclosure_guidance", "Progressive-disclosure or context-budget guidance is discoverable."),
    ]
    for key, message in vocab_checks:
        paths = categories.get(key, []) if isinstance(categories, dict) else []
        if category_status.get(key) or paths:
            s += 2
            evidence.append(f"{message} Examples: {', '.join(paths[:5])}")
        else:
            gaps.append(f"Missing vocabulary readiness signal: {key.replace('_', ' ')}.")
    if s >= 6:
        s += 1
    if gaps:
        recs.append({
            "risk": "low",
            "title": "Add domain vocabulary guidance",
            "detail": "Add or link a concise glossary/domain-language surface, including canonical terms, terms to avoid, ADR conflict rules, and which detailed docs should be loaded only when relevant.",
        })
    if not categories:
        gaps.append("No vocabulary readiness inventory was collected.")
    dims.append(dim("Vocabulary / Domain Language Control", s, evidence, gaps, recs))

    # 5 Doc Gardening / Knowledge Base Readiness
    evidence, gaps, recs = [], [], []
    garden_categories = doc_gardening.get("categories", {}) if isinstance(doc_gardening, dict) else {}
    garden_status = doc_gardening.get("category_status", {}) if isinstance(doc_gardening, dict) else {}
    s = 0
    garden_checks = [
        ("source_boundaries", "Raw source / source-of-truth boundaries are discoverable."),
        ("generated_knowledge_layer", "Generated or synthesized knowledge layer signals are discoverable."),
        ("maintenance_workflows", "Doc maintenance workflows are discoverable."),
        ("indexes_and_logs", "Docs indexes or chronological logs are discoverable."),
        ("health_checks", "Doc health-check signals exist for contradictions, stale claims, or orphaned pages."),
        ("navigation_search", "Navigation or search support for larger docs corpora is discoverable."),
    ]
    for key, message in garden_checks:
        paths = garden_categories.get(key, []) if isinstance(garden_categories, dict) else []
        if garden_status.get(key) or paths:
            s += 1
            evidence.append(f"{message} Examples: {', '.join(paths[:5])}")
        else:
            gaps.append(f"Missing doc gardening signal: {key.replace('_', ' ')}.")
    # Scale six static categories to a 10-point dimension.
    s = round((s / len(garden_checks)) * 10) if garden_checks else 0
    if gaps:
        recs.append({
            "risk": "low",
            "title": "Add doc gardening workflow",
            "detail": "Document source boundaries, generated/synthesized docs ownership, ingest/query/lint workflows, indexes/logs, and recurring checks for stale claims, contradictions, orphan pages, missing cross-references, and broken links.",
        })
    if not garden_categories:
        gaps.append("No doc gardening readiness inventory was collected.")
    dims.append(dim("Doc Gardening / Knowledge Base Readiness", s, evidence, gaps, recs))

    # 6 Validation Truth
    evidence, gaps, recs = [], [], []
    s = 0
    validations = script_names(manifests, ["test", "lint", "typecheck", "build", "validate", "smoke", "e2e", "check"])
    if validations:
        s = add(s, 4, evidence, f"Found validation scripts: {', '.join(validations[:10])}")
    else:
        gaps.append("No validation scripts found.")
        recs.append({"risk": "low", "title": "Create validation matrix", "detail": "Inventory real lint/test/typecheck/build/smoke commands and document when to run them."})
    if ci.get("workflows"):
        s = add(s, 2, evidence, f"Found CI workflows: {len(ci.get('workflows', []))}.")
    else:
        gaps.append("No CI workflows detected.")
    if ci.get("validation_mentions"):
        s = add(s, 2, evidence, "CI workflows appear to run validation commands.")
    if inv.get("validation_docs"):
        s = add(s, 1, evidence, "Validation commands are mentioned in docs/manifests.")
    dims.append(dim("Validation Truth", s, evidence, gaps, recs))

    # 7 Harness Feedback Loops
    evidence, gaps, recs = [], [], []
    s = 0
    tools_dev = [m for m in manifests if m.get("path", "").startswith("tools/") or "tools/dev" in m.get("path", "")]
    generated_dirs = gen.get("candidate_dirs", [])
    if generated_dirs:
        s = add(s, 2, evidence, f"Generated/golden/report artifact dirs detected: {len(generated_dirs)}.")
    else:
        gaps.append("No generated/golden/report artifact directories detected.")
    if any_script(manifests, ["preflight", "smoke", "e2e", "validate"]):
        s = add(s, 3, evidence, "Deterministic preflight/smoke/e2e/validate checks detected.")
    else:
        gaps.append("No obvious preflight/smoke/e2e validation loop detected.")
    if ci.get("workflows"):
        s = add(s, 2, evidence, "CI exists as a feedback loop.")
    if tools_dev:
        s = add(s, 1, evidence, "tools/dev manifest-like files detected.")
    if docs.get("generated_policy_docs"):
        s = add(s, 1, evidence, "Generated artifact policy exists.")
    review_docs = [
        p for p in docs.get("files", [])
        if any(term in p.lower() for term in ["review", "pr", "pull_request", "quality"])
    ]
    if review_docs:
        s = add(s, 1, evidence, f"Review guidance candidates detected: {', '.join(review_docs[:5])}.")
    else:
        gaps.append("No obvious guidance separating deterministic checks from judgment-based automated/human review.")
        recs.append({
            "risk": "low",
            "title": "Clarify check versus review loops",
            "detail": "Document which feedback loops are deterministic automated checks and which are judgment-based automated or human reviews, so agents know what can be self-corrected from pass/fail output.",
        })
    dims.append(dim("Harness Feedback Loops", s, evidence, gaps, recs))

    # 8 Codex Config
    evidence, gaps, recs = [], [], []
    s = 5
    if codex.get("exists"):
        s = add(s, 1, evidence, ".codex/ exists.")
    if codex.get("config"):
        s = add(s, 2, evidence, f"Codex config present: {codex.get('config')}")
    else:
        gaps.append("No repo-local .codex/config.toml detected.")
    if codex.get("mcp_servers"):
        s = add(s, 1, evidence, f"MCP servers configured: {', '.join(codex.get('mcp_servers', []))}")
    if codex.get("hooks"):
        s = add(s, 1, evidence, "Codex hooks config present.")
    dims.append(dim("Codex Config Readiness", s, evidence, gaps, recs))

    # 9 Skills
    evidence, gaps, recs = [], [], []
    s = 4
    repo_skills = skills.get("repo_skills", [])
    codex_skills = skills.get("codex_skills", [])
    if repo_skills:
        s = add(s, 3, evidence, f"Repo-scoped skills detected: {', '.join(x['name'] for x in repo_skills[:10])}")
    else:
        gaps.append("No repo-scoped skills detected.")
    if codex_skills:
        s = add(s, 1, evidence, f".codex/skills detected: {len(codex_skills)}.")
    if skills.get("duplicate_names"):
        gaps.append("Duplicate skill names detected.")
        recs.append({"risk": "low", "title": "Resolve duplicate skill names", "detail": "Codex does not merge same-name skills; keep one authoritative skill per name."})
        s -= 2
    else:
        s = add(s, 1, evidence, "No duplicate skill names detected.")
    dims.append(dim("Skills Readiness", s, evidence, gaps, recs))

    # 10 MCP
    evidence, gaps, recs = [], [], []
    mcp = codex.get("mcp_servers", [])
    s = 6
    if mcp:
        s = add(s, 3, evidence, f"MCP servers configured: {', '.join(mcp)}")
    else:
        gaps.append("No MCP servers configured. This is acceptable if no external context/tools are needed.")
        s = 7
    if docs.get("files") and mcp:
        docs_text_signal = any("mcp" in p.lower() for p in docs.get("files", []))
        if docs_text_signal:
            s = add(s, 1, evidence, "MCP-related docs/file names detected.")
        else:
            gaps.append("MCP servers exist but no obvious MCP documentation file name detected.")
            recs.append({"risk": "low", "title": "Document MCP purpose", "detail": "Document MCP server purpose, expected availability, auth/secrets, and failure mode."})
    dims.append(dim("MCP Readiness", s, evidence, gaps, recs))

    # 11 Hooks/rules
    evidence, gaps, recs = [], [], []
    s = 7
    if codex.get("hooks"):
        s = add(s, 2, evidence, "Hooks config detected.")
    else:
        evidence.append("No hooks config detected; absence is safe if hooks are not needed.")
    if codex.get("rules"):
        s = add(s, 1, evidence, f"Codex rules detected: {len(codex.get('rules', []))} files.")
    dims.append(dim("Hooks / Rules Safety", s, evidence, gaps, recs))

    # 12 OMX
    evidence, gaps, recs = [], [], []
    s = 3
    if omx.get("exists"):
        s = add(s, 2, evidence, ".omx/ exists.")
    else:
        gaps.append("No .omx/ workflow artifacts detected.")
    if omx.get("contexts"):
        s = add(s, 2, evidence, f"OMX context files: {len(omx.get('contexts', []))}.")
    if omx.get("plans"):
        s = add(s, 2, evidence, f"OMX plan files: {len(omx.get('plans', []))}.")
    if docs.get("files") and any("worktree" in p.lower() or "agent" in p.lower() for p in docs.get("files", [])):
        s = add(s, 1, evidence, "Agent/worktree workflow docs detected.")
    dims.append(dim("Subagent / OMX Workflow", s, evidence, gaps, recs))

    # 13 Cross-agent compatibility
    evidence, gaps, recs = [], [], []
    cross = inv.get("cross_agent", {}).get("surfaces", [])
    s = 7
    if cross:
        s = add(s, 1, evidence, f"Cross-agent surfaces detected: {', '.join(x['path'] for x in cross)}")
        gaps.append("Cross-agent files should be checked for conflicts with Codex/OMX guidance.")
        recs.append({"risk": "low", "title": "Audit cross-agent instructions", "detail": "Ensure Claude/Cursor/etc. guidance does not conflict with Codex/OMX rules."})
    else:
        evidence.append("No cross-agent instruction surfaces detected.")
    dims.append(dim("Cross-Agent Compatibility", s, evidence, gaps, recs))

    # 14 Entropy/scaffolding
    evidence, gaps, recs = [], [], []
    counts = markers.get("counts", {})
    total_markers = sum(int(v) for v in counts.values()) if counts else 0
    s = 8
    if total_markers == 0:
        s = add(s, 1, evidence, "No scaffold/legacy marker hits detected.")
    elif total_markers < 50:
        evidence.append(f"Detected {total_markers} scaffold/legacy marker hits.")
        s -= 1
    elif total_markers < 250:
        evidence.append(f"Detected {total_markers} scaffold/legacy marker hits.")
        gaps.append("Moderate scaffold/legacy marker entropy detected.")
        s -= 3
    else:
        evidence.append(f"Detected {total_markers} scaffold/legacy marker hits.")
        gaps.append("High scaffold/legacy marker entropy detected.")
        s -= 5
    if docs.get("generated_policy_docs"):
        s = add(s, 1, evidence, "Generated artifact lifecycle guidance detected.")
    else:
        gaps.append("No generated artifact lifecycle policy detected.")
        recs.append({"risk": "low", "title": "Add generated artifact policy", "detail": "Classify checked-in reports/golden data/generated outputs as active evidence, generated on demand, archive, or delete."})
    dims.append(dim("Entropy / Scaffolding Control", s, evidence, gaps, recs))

    # 15 Production readiness
    evidence, gaps, recs = [], [], []
    s = 0
    # Aggregate selected dimensions.
    partial_scores = {d["name"]: d["score"] for d in dims}
    selected = [
        "Agent Legibility", "Instruction Hygiene", "Docs Authority", "Validation Truth",
        "Vocabulary / Domain Language Control", "Doc Gardening / Knowledge Base Readiness",
        "Harness Feedback Loops", "Entropy / Scaffolding Control"
    ]
    avg = round(sum(partial_scores.get(x, 0) for x in selected) / len(selected)) if selected else 0
    s = avg
    evidence.append(f"Production readiness derived from core readiness average: {avg}/10.")
    if avg < 7:
        gaps.append("Core harness readiness dimensions are not yet consistently strong.")
    if any_script(manifests, ["validate", "test", "build"]):
        evidence.append("Build/test/validate commands are present.")
    else:
        gaps.append("No clear build/test/validate command surface detected.")
    dims.append(dim("Production Readiness", s, evidence, gaps, recs))



    # 16 Symphony orchestration readiness
    evidence, gaps, recs = [], [], []
    symphony = inv.get("symphony_readiness", {})
    categories = symphony.get("categories", {}) if isinstance(symphony, dict) else {}
    category_status = symphony.get("category_status", {}) if isinstance(symphony, dict) else {}
    s = 0
    checks = [
        ("workflow_contracts", "Workflow / agent contracts are discoverable."),
        ("task_state_surfaces", "Task-state or control-plane surfaces are discoverable."),
        ("workspace_isolation", "Workspace isolation guidance is discoverable."),
        ("agent_runner_guidance", "Agent runner / CLI guidance is discoverable."),
        ("observability", "Observability or evidence-reporting surfaces are discoverable."),
        ("validation_guardrails", "Validation / CI guardrails are discoverable."),
        ("recovery_guardrails", "Recovery / resume / rollback guardrails are discoverable."),
    ]
    for key, message in checks:
        paths = categories.get(key, []) if isinstance(categories, dict) else []
        if category_status.get(key) or paths:
            s += 1
            evidence.append(f"{message} Examples: {', '.join(paths[:5])}")
        else:
            gaps.append(f"Missing Symphony readiness signal: {key.replace('_', ' ')}.")
    # Scale seven static categories to a 10-point dimension, preserving strictness.
    s = round((s / len(checks)) * 10) if checks else 0
    if gaps:
        recs.append({
            "risk": "low",
            "title": "Plan Symphony readiness improvements",
            "detail": "Use the Symphony readiness findings to add missing workflow contracts, task-state handoffs, workspace isolation guidance, observability, validation, and recovery guardrails before adopting a live orchestrator.",
        })
    if not categories:
        gaps.append("No Symphony readiness inventory was collected.")
    dims.append(dim("Symphony Orchestration Readiness", s, evidence, gaps, recs))

    overall = round(sum(d["score"] for d in dims) / len(dims), 2)
    verdict = "excellent" if overall >= 9 else "strong" if overall >= 7 else "partial" if overall >= 5 else "weak" if overall >= 3 else "missing"

    low_risk = []
    medium_risk = []
    high_risk = []
    recommendation_buckets = {"low": low_risk, "medium": medium_risk, "high": high_risk}
    for d in dims:
        normalized_recs = []
        for raw_rec in d.get("recommendations", []):
            rec = dict(raw_rec)
            if "AGENTS" in f"{rec.get('title', '')} {rec.get('detail', '')}" or d["name"] == "Instruction Hygiene":
                rec.setdefault("priority", "p0")
            normalized = normalize_recommendation(
                rec,
                default_dimension=d["name"],
                source=f"dimension:{slugify(d['name'])}",
                evidence=(d.get("evidence", []) + d.get("gaps", []))[:4],
            )
            normalized_recs.append(normalized)
            recommendation_buckets[normalized["risk"]].append(normalized)
        d["recommendations"] = normalized_recs

    # Always include a conservative set of potential next steps if weak areas exist.
    if overall < 8 and not low_risk:
        low_risk.append(normalize_recommendation(
            {
                "risk": "low",
                "priority": "p1",
                "dimension": "General",
                "title": "Create harness-engineering improvement plan",
                "detail": "Use this audit as input to an OMX ralplan pass, then execute auto-approved low-risk changes without asking for another approval.",
            },
            source="fallback",
        ))

    lifecycle_classification = lifecycle.get("classification", "brownfield-cleanup")
    readiness_categories = readiness_registry.get("categories", {}) if isinstance(readiness_registry, dict) else {}
    readiness_status = readiness_registry.get("category_status", {}) if isinstance(readiness_registry, dict) else {}
    readiness_recommendations = []
    for key, paths in readiness_categories.items():
        if not readiness_status.get(key):
            readiness_recommendations.append(normalize_recommendation(
                {
                    "category": key,
                    "risk": "low",
                    "dimension": "Lifecycle Harness Readiness Registry",
                    "title": f"Add {key.replace('_', ' ')} guidance",
                    "detail": "Create compact, progressively disclosed harness guidance or templates for this missing readiness category.",
                },
                source="readiness-registry",
                evidence=paths[:5] if isinstance(paths, list) else [],
            ))

    if lifecycle_classification == "greenfield-bootstrap":
        low_risk.append(normalize_recommendation(
            {
                "risk": "low",
                "priority": "p0",
                "dimension": "Lifecycle",
                "title": "Run safe setup for production-ready harness skeleton",
                "detail": "Create compact low-risk harness docs/templates for a minimal repo using progressive disclosure and provenance markers.",
            },
            source="lifecycle",
            evidence=[f"Lifecycle classification: {lifecycle_classification}"],
        ))
    elif lifecycle_classification == "brownfield-cleanup" and readiness_recommendations:
        low_risk.append(normalize_recommendation(
            {
                "risk": "low",
                "priority": "p1",
                "dimension": "Lifecycle",
                "title": "Plan safe harness consolidation",
                "detail": "Add missing low-risk readiness surfaces and produce a cleanup plan for medium/high-risk degraded harness pieces.",
            },
            source="lifecycle",
            evidence=[f"Missing readiness categories: {len(readiness_recommendations)}"],
        ))

    lane_recommendations = []
    lane_payload = lane_pack_registry.get("lanes", {}) if isinstance(lane_pack_registry, dict) else {}
    for lane_id, lane in sorted(lane_payload.items()):
        if not isinstance(lane, dict) or lane.get("status") not in {"missing", "recommended"}:
            continue
        risk = str(lane.get("risk", "low"))
        lane_evidence = unique_items(
            normalize_evidence(lane.get("evidence_paths"))
            + normalize_evidence(lane.get("activation_evidence_paths"))
            + normalize_evidence(lane.get("recommendation_reason"))
        )
        rec = normalize_recommendation({
            "category": lane_id,
            "risk": risk,
            "dimension": "Lane Packs / Grounded Source Of Truth",
            "title": f"Add {lane.get('title', lane_id)} lane pack",
            "detail": (
                f"Create grounded source-of-truth docs for `{lane_id}`. "
                "Safe setup writes docs-only lane surfaces; full orchestration is required for custom-agent TOML."
            ),
            "actionability": "safe-setup-docs-only" if risk == "low" else "plan-before-execution",
        }, source="lane-pack-registry", evidence=lane_evidence[:10])
        lane_recommendations.append(rec)
        recommendation_buckets[rec["risk"]].append(dict(rec))

    low_risk = dedupe_recommendations(low_risk)
    medium_risk = dedupe_recommendations(medium_risk)
    high_risk = dedupe_recommendations(high_risk)
    readiness_recommendations = dedupe_recommendations(readiness_recommendations)
    lane_recommendations = dedupe_recommendations(lane_recommendations)
    recommendation_summary = summarize_recommendations(low_risk, medium_risk, high_risk)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "score_schema_version": "2",
        "overall_score": overall,
        "overall_status": verdict,
        "lifecycle": {
            "classification": lifecycle_classification,
            "score_modifier": (
                "setup-needed" if lifecycle_classification == "greenfield-bootstrap"
                else "cleanup-needed" if lifecycle_classification == "brownfield-cleanup"
                else "none"
            ),
        },
        "readiness_registry": {
            "schema": "harness-engineering-audit.readiness-registry.v1",
            "categories": {
                key: {
                    "status": "present" if readiness_status.get(key) else "missing",
                    "evidence": paths[:10] if isinstance(paths, list) else [],
                }
                for key, paths in readiness_categories.items()
            },
            "recommendations": readiness_recommendations,
        },
        "lane_pack_registry": {
            "schema": lane_pack_registry.get("schema", "harness-engineering-audit.lane-pack-registry.v1") if isinstance(lane_pack_registry, dict) else "harness-engineering-audit.lane-pack-registry.v1",
            "mode_safety": lane_pack_registry.get("mode_safety", {}) if isinstance(lane_pack_registry, dict) else {},
            "active_lane_ids": lane_pack_registry.get("active_lane_ids", []) if isinstance(lane_pack_registry, dict) else [],
            "missing_required_lane_ids": lane_pack_registry.get("missing_required_lane_ids", []) if isinstance(lane_pack_registry, dict) else [],
            "recommended_lane_ids": lane_pack_registry.get("recommended_lane_ids", []) if isinstance(lane_pack_registry, dict) else [],
            "custom_agent_policy": lane_pack_registry.get("custom_agent_policy", {}) if isinstance(lane_pack_registry, dict) else {},
            "lanes": {
                key: {
                    "title": value.get("title", key),
                    "status": value.get("status", "missing"),
                    "activation": value.get("activation", "not_activated"),
                    "risk": value.get("risk", "low"),
                    "activation_confidence": value.get("activation_confidence", "none"),
                    "activation_reason": value.get("activation_reason", ""),
                    "activation_evidence": value.get("activation_evidence_paths", [])[:10],
                    "recommendation_policy": value.get("recommendation_policy", "not-applicable"),
                    "recommendation_reason": value.get("recommendation_reason", ""),
                    "evidence": value.get("evidence_paths", [])[:10],
                    "safe_setup_targets": value.get("safe_setup_targets", []),
                    "full_orchestration_targets": value.get("full_orchestration_targets", []),
                    "custom_agent_names": value.get("custom_agent_names", []),
                }
                for key, value in lane_payload.items()
                if isinstance(value, dict)
            },
            "recommendations": lane_recommendations,
        },
        "dimensions": dims,
        "auto_approval_policy": {
            "enabled": True,
            "scope": "low-risk recommendations only",
            "agents_priority": "AGENTS.md recommendations are P0 and should be handled before other low-risk fixes.",
            "excluded": "Medium-risk and high-risk recommendations still require explicit approval.",
        },
        "recommendation_summary": recommendation_summary,
        "recommendations": {
            "low_risk": low_risk,
            "medium_risk": medium_risk,
            "high_risk": high_risk,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a harness-engineering inventory JSON file.")
    parser.add_argument("inventory", help="Path to inventory JSON")
    parser.add_argument("--out", help="Write scorecard JSON to this file")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    scorecard = score_inventory(inventory)
    text = json.dumps(scorecard, indent=2 if args.pretty else None, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
