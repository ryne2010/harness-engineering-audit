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
    return any(part in IGNORE_DIRS for part in path.parts)


def iter_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        if is_ignored(current.relative_to(root) if current != root else Path("")):
            continue
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


def find_manifests(root: Path) -> List[Dict[str, Any]]:
    manifests: List[Dict[str, Any]] = []
    for path in iter_files(root):
        if path.name in MANIFEST_NAMES:
            item: Dict[str, Any] = {"path": rel(path, root), "name": path.name}
            if path.name == "package.json":
                scripts = parse_package_scripts(path)
                item["scripts"] = scripts
                item["validation_scripts"] = sorted([s for s in scripts if any(k in s.lower() for k in VALIDATION_KEYWORDS)])
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


def find_codex(root: Path) -> Dict[str, Any]:
    codex: Dict[str, Any] = {"exists": (root / ".codex").exists(), "config": None, "mcp_servers": [], "hooks": None, "rules": [], "prompts": [], "reports": []}
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
            codex[sub] = sorted(rel(p, root) for p in iter_files(d))[:500]
    return codex


def find_skills(root: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"repo_skills": [], "codex_skills": [], "duplicate_names": []}
    skill_dirs = [(root / ".agents" / "skills", "repo_skills"), (root / ".codex" / "skills", "codex_skills")]
    seen: Dict[str, List[str]] = {}
    for base, key in skill_dirs:
        if not base.exists():
            continue
        for skill_md in base.glob("*/SKILL.md"):
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
    out: Dict[str, Any] = {"exists": omx_dir.exists(), "contexts": [], "plans": [], "other_files": []}
    if not omx_dir.exists():
        return out
    for path in iter_files(omx_dir):
        r = rel(path, root)
        if ".omx/context" in r:
            out["contexts"].append(r)
        elif ".omx/plans" in r:
            out["plans"].append(r)
        else:
            out["other_files"].append(r)
    for k in ["contexts", "plans", "other_files"]:
        out[k] = sorted(out[k])[:500]
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
            continue
        name = current.name.lower()
        if any(p in name for p in patterns):
            dirs.append(rel(current, root))
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
    return {"candidate_dirs": sorted(set(dirs))[:500]}


def validation_docs(root: Path) -> List[str]:
    candidates = []
    for path in iter_files(root):
        if path.suffix.lower() in {".md", ".toml", ".json", ".yaml", ".yml"}:
            text = read_text(path, limit=200_000) or ""
            if any(k in text.lower() for k in VALIDATION_KEYWORDS) and ("docs" in path.parts or path.name in MANIFEST_NAMES):
                candidates.append(rel(path, root))
    return sorted(set(candidates))[:500]


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
    }
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
