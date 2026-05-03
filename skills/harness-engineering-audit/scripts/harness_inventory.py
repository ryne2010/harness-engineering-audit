#!/usr/bin/env python3
"""Read-only repository inventory for harness-engineering audits."""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".turbo", ".cache", "target",
    "Library", "Temp", "Logs", "DerivedData", ".idea", ".vscode"
}

AUDIT_SIGNAL_EXCLUDED_PREFIXES = {
    (".codex", "reports"),
    (".omx", "cache"),
    (".omx", "state"),
    (".omx", "logs"),
    (".agents", "skills", "harness-engineering-audit"),
    (".codex", "skills", "harness-engineering-audit"),
    ("plugins", "harness-engineering-audit", "skills", "harness-engineering-audit"),
    ("skills", "harness-engineering-audit", "assets"),
}

TEXT_EXTS = {
    ".md", ".txt", ".toml", ".json", ".yaml", ".yml", ".js", ".jsx",
    ".ts", ".tsx", ".py", ".rb", ".go", ".rs", ".java", ".kt", ".cs",
    ".sh", ".bash", ".zsh", ".ps1", ".ini", ".cfg", ".xml", ".html"
}

SCAFFOLD_MARKERS = [
    "scaffold", "legacy", "deprecated", "temporary", "placeholder", "preview",
    "demo", "stage", "milestone", "bootstrap", "fallback", "spike", "generated-only",
    "host wrapper", "todo", "fixme", "hack", "for now"
]

CROSS_AGENT_PATTERNS = [
    "CLAUDE.md", ".claude", ".cursor", ".windsurf", ".cline", ".gemini",
    ".continue", ".aider", ".github/copilot-instructions.md"
]

MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "requirements-dev.txt", "pnpm-workspace.yaml", "yarn.lock", "package-lock.json",
    "pnpm-lock.yaml", "uv.lock", "poetry.lock", "Cargo.toml", "go.mod",
    "Makefile", "justfile", "Taskfile.yml", "Taskfile.yaml", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml"
}

VALIDATION_KEYWORDS = [
    "test", "lint", "typecheck", "type", "build", "validate", "smoke", "e2e",
    "check", "ci", "preflight", "format", "spec", "coverage"
]

@dataclass
class FileInfo:
    path: str
    bytes: int
    lines: int


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def is_ignored(path: Path) -> bool:
    parts = path.parts
    if any(part in IGNORE_DIRS for part in parts):
        return True
    return any(parts[:len(prefix)] == prefix for prefix in AUDIT_SIGNAL_EXCLUDED_PREFIXES)


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if is_ignored(current.relative_to(root) if current != root else Path("")):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not is_ignored((current / d).relative_to(root))]
        for filename in filenames:
            path = current / filename
            if not is_ignored(path.relative_to(root)):
                yield path


def read_text(path: Path, limit: int = 2_000_000) -> Optional[str]:
    try:
        if path.stat().st_size > limit:
            return None
        if path.suffix and path.suffix.lower() not in TEXT_EXTS and path.name not in MANIFEST_NAMES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def file_info(path: Path, root: Path) -> FileInfo:
    text = read_text(path, limit=500_000)
    return FileInfo(
        path=rel(path, root),
        bytes=path.stat().st_size if path.exists() else 0,
        lines=0 if text is None else text.count("\n") + (1 if text else 0),
    )


def find_instruction_files(root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path in iter_files(root):
        if path.name in {"AGENTS.md", "AGENTS.override.md"}:
            info = asdict(file_info(path, root))
            text = read_text(path) or ""
            info["has_commands"] = bool(re.search(r"\b(pnpm|npm|yarn|uv|pytest|ruff|mypy|pyright|go test|cargo test|make)\b", text))
            info["mentions_docs"] = "docs/" in text or "README" in text
            info["mentions_validation"] = any(k in text.lower() for k in VALIDATION_KEYWORDS)
            out.append(info)
    return sorted(out, key=lambda x: x["path"])


def find_paths(root: Path, candidates: Iterable[str]) -> List[str]:
    found = []
    for candidate in candidates:
        if is_ignored(Path(candidate)):
            continue
        p = root / candidate
        if p.exists():
            found.append(candidate)
    return found


def parse_package_scripts(path: Path) -> Dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        if isinstance(scripts, dict):
            return {str(k): str(v) for k, v in scripts.items()}
    except Exception:
        pass
    return {}


def parse_makefile_targets(path: Path) -> Dict[str, str]:
    targets: Dict[str, str] = {}
    target_pattern = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?:\s|$)")
    for raw in (read_text(path) or "").splitlines():
        if raw.startswith(("\t", " ")):
            continue
        match = target_pattern.match(raw)
        if not match:
            continue
        target = match.group(1)
        targets[target] = f"make {target}"
    return targets


def find_manifests(root: Path) -> List[Dict[str, Any]]:
    manifests: List[Dict[str, Any]] = []
    for path in iter_files(root):
        if path.name in MANIFEST_NAMES:
            item: Dict[str, Any] = {"path": rel(path, root), "name": path.name}
            if path.name == "package.json":
                scripts = parse_package_scripts(path)
                item["scripts"] = scripts
                item["validation_scripts"] = sorted([s for s in scripts if any(k in s.lower() for k in VALIDATION_KEYWORDS)])
            elif path.name == "Makefile":
                scripts = parse_makefile_targets(path)
                item["scripts"] = scripts
                item["validation_scripts"] = sorted([s for s in scripts if any(k in s.lower() for k in VALIDATION_KEYWORDS)])
                item["mentions_validation"] = bool(item["validation_scripts"])
            else:
                text = read_text(path) or ""
                item["mentions_validation"] = any(k in text.lower() for k in VALIDATION_KEYWORDS)
            manifests.append(item)
    return sorted(manifests, key=lambda x: x["path"])


def find_docs(root: Path) -> Dict[str, Any]:
    docs_dir = root / "docs"
    docs: Dict[str, Any] = {"exists": docs_dir.exists(), "files": [], "indexes": [], "authority_docs": [], "generated_policy_docs": []}
    if not docs_dir.exists():
        return docs
    for path in iter_files(docs_dir):
        if path.suffix.lower() == ".md":
            r = rel(path, root)
            docs["files"].append(r)
            low = path.name.lower()
            text = read_text(path, limit=300_000) or ""
            if "index" in low or "readme" in low or "spec_index" in low:
                docs["indexes"].append(r)
            if re.search(r"authority|source of truth|authoritative|canonical|ownership", text, re.I):
                docs["authority_docs"].append(r)
            if re.search(r"generated artifact|artifact policy|golden|snapshot|report lifecycle", text, re.I):
                docs["generated_policy_docs"].append(r)
    docs["files"] = sorted(docs["files"])
    docs["indexes"] = sorted(set(docs["indexes"]))
    docs["authority_docs"] = sorted(set(docs["authority_docs"]))
    docs["generated_policy_docs"] = sorted(set(docs["generated_policy_docs"]))
    return docs


def find_vocabulary_surfaces(root: Path) -> Dict[str, Any]:
    """Collect signals that the repo governs project vocabulary for agents.

    Vocabulary control is a harness surface: agents do better when domain terms,
    glossary files, ADR language, and "use/avoid" naming rules are easy to find.
    This intentionally inventories static evidence only.
    """
    seed_paths = find_paths(
        root,
        [
            "internal/CONTEXT.md",
            "internal/domain.md",
            "docs/GLOSSARY.md",
            "docs/glossary.md",
            "docs/TERMINOLOGY.md",
            "docs/terminology.md",
            "docs/DOMAIN.md",
            "docs/domain.md",
            "docs/ADR",
            "docs/adr",
            "internal/adr",
            "dictionary",
        ],
    )
    glossary_terms = [
        "glossary",
        "terminology",
        "vocabulary",
        "domain language",
        "ubiquitous language",
        "canonical term",
        "canonical vocabulary",
        "terms to avoid",
        "term to avoid",
    ]
    vocabulary_paths = seed_paths + find_text_signal_paths(root, glossary_terms, limit=60)
    adr_paths = []
    for candidate in ["docs/ADR", "docs/adr", "internal/adr", "adr"]:
        p = root / candidate
        if p.exists():
            if p.is_dir():
                adr_paths.extend(rel(path, root) for path in iter_files(p) if path.suffix.lower() == ".md")
            else:
                adr_paths.append(candidate)
    adr_paths.extend(find_text_signal_paths(root, ["architecture decision", "decision record", "contradicts adr"], limit=40))
    conflict_guidance = find_text_signal_paths(
        root,
        ["ADR conflict", "contradicts ADR", "conflict with ADR", "source of truth", "canonical vocabulary"],
        limit=35,
    )
    progressive_disclosure = find_text_signal_paths(
        root,
        ["progressive disclosure", "load only", "context budget", "token cost", "context window"],
        limit=35,
    )
    categories = {
        "glossary_or_terms": unique_sorted(vocabulary_paths, limit=80),
        "adr_or_decision_records": unique_sorted(adr_paths, limit=80),
        "conflict_guidance": unique_sorted(conflict_guidance, limit=60),
        "progressive_disclosure_guidance": unique_sorted(progressive_disclosure, limit=60),
    }
    category_status = {name: bool(paths) for name, paths in categories.items()}
    return {
        "schema": "harness-engineering-audit.vocabulary-readiness.v1",
        "static_only": True,
        "categories": categories,
        "category_status": category_status,
        "readiness_count": sum(1 for ready in category_status.values() if ready),
        "category_count": len(categories),
    }


def find_doc_gardening_surfaces(root: Path) -> Dict[str, Any]:
    """Collect signals for maintained documentation and knowledge-base hygiene.

    This models docs as a living harness artifact: raw sources stay distinct from
    generated/synthesized docs, agents have explicit maintenance workflows, and
    indexes/logs/health checks keep the corpus navigable as it grows.
    """
    source_boundaries = find_paths(
        root,
        [
            "raw",
            "sources",
            "docs/sources",
            "references",
            "docs/references",
            "docs/archive",
            "archive",
        ],
    )
    source_boundaries.extend(
        find_text_signal_paths(
            root,
            ["raw source", "raw sources", "source of truth", "immutable source", "citation", "citations"],
            limit=45,
        )
    )

    generated_knowledge = find_paths(
        root,
        [
            "wiki",
            "docs/wiki",
            "knowledge",
            "docs/knowledge",
            "docs/generated",
            "generated",
        ],
    )
    generated_knowledge.extend(
        find_text_signal_paths(
            root,
            ["wiki", "knowledge base", "summary page", "entity page", "concept page", "synthesis"],
            limit=45,
        )
    )

    maintenance_workflows = find_text_signal_paths(
        root,
        [
            "doc garden",
            "doc gardening",
            "docs gardening",
            "ingest",
            "query workflow",
            "lint docs",
            "docs lint",
            "documentation maintenance",
            "maintain docs",
        ],
        limit=50,
    )

    indexes_logs = find_paths(
        root,
        [
            "index.md",
            "log.md",
            "docs/index.md",
            "docs/log.md",
            "docs/README.md",
            "CHANGELOG.md",
        ],
    )
    indexes_logs.extend(find_text_signal_paths(root, ["append-only", "chronological log", "docs index", "spec index"], limit=35))

    health_checks = find_text_signal_paths(
        root,
        [
            "contradiction",
            "contradictions",
            "stale",
            "superseded",
            "orphan",
            "orphaned",
            "broken link",
            "broken links",
            "cross-reference",
            "cross references",
            "missing page",
        ],
        limit=60,
    )

    navigation_search = find_text_signal_paths(
        root,
        [
            "docs search",
            "wiki search",
            "knowledge search",
            "graph view",
            "backlink",
            "backlinks",
            "dataview",
            "full-text search",
            "markdown search",
        ],
        limit=35,
    )

    categories = {
        "source_boundaries": unique_sorted(source_boundaries, limit=80),
        "generated_knowledge_layer": unique_sorted(generated_knowledge, limit=80),
        "maintenance_workflows": unique_sorted(maintenance_workflows, limit=80),
        "indexes_and_logs": unique_sorted(indexes_logs, limit=80),
        "health_checks": unique_sorted(health_checks, limit=80),
        "navigation_search": unique_sorted(navigation_search, limit=60),
    }
    category_status = {name: bool(paths) for name, paths in categories.items()}
    return {
        "schema": "harness-engineering-audit.doc-gardening-readiness.v1",
        "static_only": True,
        "categories": categories,
        "category_status": category_status,
        "readiness_count": sum(1 for ready in category_status.values() if ready),
        "category_count": len(categories),
    }


def find_codex(root: Path) -> Dict[str, Any]:
    codex: Dict[str, Any] = {"exists": False, "config": None, "mcp_servers": [], "hooks": None, "rules": [], "prompts": [], "reports": []}
    config = root / ".codex" / "config.toml"
    if config.exists():
        text = read_text(config) or ""
        codex["config"] = rel(config, root)
        codex["mcp_servers"] = re.findall(r"^\s*\[mcp_servers\.([^\]]+)\]", text, flags=re.M)
    hooks = root / ".codex" / "hooks.json"
    if hooks.exists():
        codex["hooks"] = rel(hooks, root)
    for sub in ["rules", "prompts", "reports"]:
        d = root / ".codex" / sub
        if d.exists():
            codex[sub] = sorted(rel(p, root) for p in iter_files(d) if not is_ignored(p.relative_to(root)))[:500]
    codex["exists"] = bool(codex["config"] or codex["hooks"] or codex["rules"] or codex["prompts"])
    return codex


def find_skills(root: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"repo_skills": [], "codex_skills": [], "duplicate_names": []}
    skill_dirs = [(root / ".agents" / "skills", "repo_skills"), (root / ".codex" / "skills", "codex_skills")]
    seen: Dict[str, List[str]] = {}
    for base, key in skill_dirs:
        if not base.exists():
            continue
        for skill_md in base.glob("*/SKILL.md"):
            if is_ignored(skill_md.relative_to(root)):
                continue
            text = read_text(skill_md) or ""
            name = skill_md.parent.name
            m = re.search(r"^name:\s*([^\n]+)", text, flags=re.M)
            if m:
                name = m.group(1).strip().strip('"')
            item = {"name": name, "path": rel(skill_md, root), "bytes": skill_md.stat().st_size}
            out[key].append(item)
            seen.setdefault(name, []).append(item["path"])
    out["repo_skills"] = sorted(out["repo_skills"], key=lambda x: x["name"])
    out["codex_skills"] = sorted(out["codex_skills"], key=lambda x: x["name"])
    out["duplicate_names"] = [{"name": k, "paths": v} for k, v in seen.items() if len(v) > 1]
    return out


def find_omx(root: Path) -> Dict[str, Any]:
    omx_dir = root / ".omx"
    out: Dict[str, Any] = {"exists": False, "contexts": [], "plans": [], "other_files": []}
    if not omx_dir.exists():
        return out
    for path in iter_files(omx_dir):
        if is_ignored(path.relative_to(root)):
            continue
        r = rel(path, root)
        if ".omx/context" in r:
            out["contexts"].append(r)
        elif ".omx/plans" in r:
            out["plans"].append(r)
        else:
            out["other_files"].append(r)
    for k in ["contexts", "plans", "other_files"]:
        out[k] = sorted(out[k])[:500]
    out["exists"] = bool(out["contexts"] or out["plans"] or out["other_files"])
    return out


def find_ci(root: Path) -> Dict[str, Any]:
    workflows = root / ".github" / "workflows"
    out: Dict[str, Any] = {"workflows": [], "validation_mentions": []}
    if workflows.exists():
        for path in iter_files(workflows):
            if path.suffix.lower() in {".yml", ".yaml"}:
                r = rel(path, root)
                out["workflows"].append(r)
                text = read_text(path) or ""
                if any(k in text.lower() for k in VALIDATION_KEYWORDS):
                    out["validation_mentions"].append(r)
    return out


def find_cross_agent(root: Path) -> Dict[str, Any]:
    found = []
    for pattern in CROSS_AGENT_PATTERNS:
        p = root / pattern
        if p.exists():
            if p.is_dir():
                found.append({"path": pattern, "type": "directory", "files": len(list(iter_files(p)))})
            else:
                found.append({"path": pattern, "type": "file", "bytes": p.stat().st_size})
    return {"surfaces": found}


def marker_scan(root: Path) -> Dict[str, Any]:
    counts = {m: 0 for m in SCAFFOLD_MARKERS}
    examples: Dict[str, List[str]] = {m: [] for m in SCAFFOLD_MARKERS}
    total_files = 0
    for path in iter_files(root):
        text = read_text(path, limit=500_000)
        if not text:
            continue
        total_files += 1
        lower = text.lower()
        for marker in SCAFFOLD_MARKERS:
            c = lower.count(marker)
            if c:
                counts[marker] += c
                if len(examples[marker]) < 10:
                    examples[marker].append(rel(path, root))
    return {"counts": counts, "examples": examples, "text_files_scanned": total_files}


def generated_artifacts(root: Path) -> Dict[str, Any]:
    patterns = ["golden", "snapshot", "snapshots", "report", "reports", "generated", "artifacts", "dist", "build"]
    dirs = []
    for dirpath, dirnames, _ in os.walk(root):
        current = Path(dirpath)
        if is_ignored(current.relative_to(root) if current != root else Path("")):
            dirnames[:] = []
            continue
        name = current.name.lower()
        if any(p in name for p in patterns):
            dirs.append(rel(current, root))
        dirnames[:] = [d for d in dirnames if not is_ignored((current / d).relative_to(root))]
    return {"candidate_dirs": sorted(set(dirs))[:500]}


def validation_docs(root: Path) -> List[str]:
    candidates = []
    for path in iter_files(root):
        if path.suffix.lower() in {".md", ".toml", ".json", ".yaml", ".yml"}:
            text = read_text(path, limit=200_000) or ""
            if any(k in text.lower() for k in VALIDATION_KEYWORDS) and ("docs" in path.parts or path.name in MANIFEST_NAMES):
                candidates.append(rel(path, root))
    return sorted(set(candidates))[:500]



def unique_sorted(values: Iterable[str], limit: int = 500) -> List[str]:
    """Return deterministic unique path lists with a bounded size."""
    return sorted(set(values))[:limit]


def text_contains_any(path: Path, keywords: Iterable[str], limit: int = 300_000) -> bool:
    text = read_text(path, limit=limit)
    if not text:
        return False
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def find_text_signal_paths(root: Path, keywords: Iterable[str], limit: int = 50) -> List[str]:
    matches: List[str] = []
    for path in iter_files(root):
        if len(matches) >= limit:
            break
        if text_contains_any(path, keywords):
            matches.append(rel(path, root))
    return unique_sorted(matches, limit=limit)


def find_symphony_readiness(root: Path) -> Dict[str, Any]:
    """Collect static signals for OpenAI Symphony-style orchestration readiness.

    This is intentionally a static harness audit. It does not call Linear/GitHub APIs,
    start agent sessions, or inspect private credentials. The goal is to determine
    whether a repository exposes the contracts and guardrails a Symphony-like control
    plane would need before a later adoption plan.
    """
    workflow_contracts = find_paths(
        root,
        [
            "AGENTS.md",
            "AGENTS.override.md",
            "WORKFLOW.md",
            ".codex/config.toml",
            ".codex/hooks.json",
            "docs/OMX_WORKFLOW.md",
            "docs/USAGE.md",
            ".github/ISSUE_TEMPLATE",
            ".github/pull_request_template.md",
        ],
    )
    workflow_contracts.extend(find_text_signal_paths(root, ["workflow", "handoff", "control plane"], limit=25))

    task_state_surfaces = find_paths(
        root,
        [
            ".omx/state",
            ".omx/plans",
            ".omx/context",
            ".codex/reports",
            ".github/ISSUE_TEMPLATE",
            ".github/PULL_REQUEST_TEMPLATE.md",
        ],
    )
    task_state_surfaces.extend(
        find_text_signal_paths(root, ["linear", "issue", "ticket", "task", "status", "next-step"], limit=35)
    )

    workspace_isolation = find_text_signal_paths(
        root,
        ["workspace", "worktree", "sandbox", "isolated", "per-issue", "per issue", "tmux"],
        limit=35,
    )
    agent_runner_guidance = find_text_signal_paths(
        root,
        ["codex", "agent", "omx", "mcp", "skill", "prompt", "gh cli", "subagent"],
        limit=45,
    )
    observability = find_paths(root, [".omx/logs", ".codex/reports", "docs/TRACE.md"])
    observability.extend(find_text_signal_paths(root, ["log", "trace", "status", "hud", "report", "evidence"], limit=35))
    validation_guardrails = validation_docs(root)
    validation_guardrails.extend(find_text_signal_paths(root, VALIDATION_KEYWORDS, limit=35))
    recovery_guardrails = find_text_signal_paths(
        root,
        ["retry", "restart", "resume", "recover", "rollback", "cancel", "stale", "reconcile", "state"],
        limit=35,
    )

    categories = {
        "workflow_contracts": unique_sorted(workflow_contracts, limit=60),
        "task_state_surfaces": unique_sorted(task_state_surfaces, limit=60),
        "workspace_isolation": unique_sorted(workspace_isolation, limit=60),
        "agent_runner_guidance": unique_sorted(agent_runner_guidance, limit=80),
        "observability": unique_sorted(observability, limit=60),
        "validation_guardrails": unique_sorted(validation_guardrails, limit=80),
        "recovery_guardrails": unique_sorted(recovery_guardrails, limit=60),
    }
    category_status = {name: bool(paths) for name, paths in categories.items()}
    readiness_count = sum(1 for ready in category_status.values() if ready)
    return {
        "schema": "harness-engineering-audit.symphony-readiness.v1",
        "static_only": True,
        "non_goals": [
            "no daemon/service execution",
            "no live tracker API calls",
            "no target-repo auto-modification",
            "no reference implementation setup",
        ],
        "categories": categories,
        "category_status": category_status,
        "readiness_count": readiness_count,
        "category_count": len(categories),
    }


READINESS_CATEGORY_TERMS = {
    "vocabulary_domain_language_control": [
        "glossary", "terminology", "domain language", "canonical vocabulary", "canonical term",
    ],
    "doc_gardening_knowledge_base_readiness": [
        "doc gardening", "knowledge base", "ingest", "orphan", "stale claims", "cross-reference",
    ],
    "task_contract_ticket_quality": [
        "acceptance criteria", "task contract", "ticket", "issue template", "scope", "done criteria",
    ],
    "agent_role_topology_isolation": [
        "role topology", "frontend agent", "backend agent", "docs agent", "path ownership", "write scope",
    ],
    "state_machine_reconciliation": [
        "state machine", "queued", "claimed", "blocked", "reconcile", "lease", "stale task",
    ],
    "observability_depth": [
        "proof of work", "trace id", "trace", "decision log", "evidence", "observability",
    ],
    "environment_reproducibility": [
        "fresh clone", "bootstrap", "setup", "toolchain", "dependency install", "local parity",
    ],
    "safety_trust_boundaries": [
        "trust boundary", "prompt injection", "secret", "permission", "sandbox", "supply chain",
    ],
    "evaluation_regression_harness": [
        "eval", "evaluation", "golden task", "replay", "regression harness", "rubric",
    ],
    "cost_context_token_budgeting": [
        "context budget", "token budget", "progressive disclosure", "compaction", "AGENTS size",
    ],
    "release_merge_governance": [
        "release", "merge", "pull request", "PR template", "changelog", "rollback",
    ],
    "queueing_capacity_backpressure": [
        "queue", "capacity", "backpressure", "retry", "priority", "cancellation",
    ],
    "artifact_provenance_lifecycle": [
        "provenance", "generated artifact", "artifact lifecycle", "rollback manifest", "archive policy",
    ],
    "symphony_orchestration_readiness": [
        "symphony", "control plane", "task-state", "issue-tracker", "runner guidance", "reconciliation",
    ],
}


def find_readiness_registry(root: Path) -> Dict[str, Any]:
    categories: Dict[str, List[str]] = {}
    category_status: Dict[str, bool] = {}
    for name, terms in READINESS_CATEGORY_TERMS.items():
        paths = find_text_signal_paths(root, terms, limit=60)
        categories[name] = paths
        category_status[name] = bool(paths)
    return {
        "schema": "harness-engineering-audit.readiness-registry.v1",
        "categories": categories,
        "category_status": category_status,
        "readiness_count": sum(1 for ready in category_status.values() if ready),
        "category_count": len(category_status),
    }


def classify_lifecycle(root: Path, inventory: Dict[str, Any]) -> Dict[str, Any]:
    signals = {
        "file_count_scanned": inventory.get("file_count_scanned", 0),
        "instruction_files": len(inventory.get("instruction_files", [])),
        "docs_files": len(inventory.get("docs", {}).get("files", [])),
        "validation_docs": len(inventory.get("validation_docs", [])),
        "validation_manifests": len(inventory.get("manifests", [])),
        "omx_files": len(inventory.get("omx", {}).get("contexts", [])) + len(inventory.get("omx", {}).get("plans", [])),
        "codex_config": bool(inventory.get("codex", {}).get("config")),
        "repo_skills": len(inventory.get("skills", {}).get("repo_skills", [])),
        "readiness_signals": inventory.get("readiness_registry", {}).get("readiness_count", 0),
    }
    maturity_points = 0
    maturity_points += 2 if signals["instruction_files"] else 0
    maturity_points += 2 if signals["docs_files"] >= 3 else 1 if signals["docs_files"] else 0
    maturity_points += 2 if signals["validation_docs"] else 0
    maturity_points += 1 if signals["validation_manifests"] else 0
    maturity_points += 1 if signals["codex_config"] else 0
    maturity_points += 1 if signals["omx_files"] else 0
    maturity_points += 1 if signals["repo_skills"] else 0
    maturity_points += 2 if signals["readiness_signals"] >= 7 else 1 if signals["readiness_signals"] >= 3 else 0

    if signals["file_count_scanned"] <= 8 and maturity_points <= 2:
        classification = "greenfield-bootstrap"
    elif maturity_points >= 9:
        classification = "mature-audit"
    else:
        classification = "brownfield-cleanup"

    return {
        "schema": "harness-engineering-audit.lifecycle.v1",
        "classification": classification,
        "signals": signals,
        "rationale": [
            f"Maturity points: {maturity_points}.",
            "Greenfield requires very few scanned files and almost no harness surfaces.",
            "Mature repos require multiple instruction, docs, validation, config, workflow, or readiness signals.",
        ],
    }


def collect_inventory(repo: str | Path) -> Dict[str, Any]:
    root = Path(repo).resolve()
    files = list(iter_files(root)) if root.exists() else []
    inventory: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "file_count_scanned": len(files),
        "instruction_files": find_instruction_files(root),
        "codex": find_codex(root),
        "skills": find_skills(root),
        "omx": find_omx(root),
        "manifests": find_manifests(root),
        "docs": find_docs(root),
        "ci": find_ci(root),
        "cross_agent": find_cross_agent(root),
        "generated_artifacts": generated_artifacts(root),
        "validation_docs": validation_docs(root),
        "markers": marker_scan(root),
        "vocabulary_readiness": find_vocabulary_surfaces(root),
        "doc_gardening_readiness": find_doc_gardening_surfaces(root),
        "symphony_readiness": find_symphony_readiness(root),
    }
    inventory["readiness_registry"] = find_readiness_registry(root)
    inventory["lifecycle"] = classify_lifecycle(root, inventory)
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory a repo for harness-engineering audit evidence.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to inventory")
    parser.add_argument("--out", help="Write inventory JSON to this file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    inventory = collect_inventory(args.repo)
    text = json.dumps(inventory, indent=2 if args.pretty else None, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
