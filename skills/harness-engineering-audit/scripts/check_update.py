#!/usr/bin/env python3
"""Check and explicitly update the harness-engineering-audit Codex skill.

Default behavior is report-only: this script never mutates skill files unless
`--self-update` is provided.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

REPO = "ryne2010/harness-engineering-audit"
SKILL_PATH = "skills/harness-engineering-audit"
STATUSES = {"current", "available", "unknown", "tooling_missing", "error"}


def update_command(scope: str) -> list[str]:
    return [
        "gh",
        "skill",
        "install",
        REPO,
        SKILL_PATH,
        "--agent",
        "codex",
        "--scope",
        scope,
        "--force",
    ]


def command_text(scope: str) -> str:
    return " ".join(update_command(scope))


def multiline_command(scope: str) -> str:
    return (
        f"gh skill install {REPO} \\\n"
        f"  {SKILL_PATH} \\\n"
        "  --agent codex \\\n"
        f"  --scope {scope} \\\n"
        "  --force"
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: Dict[str, str] = {}
    for raw in text[4:end].splitlines():
        if ":" not in raw or raw.lstrip().startswith("#"):
            continue
        key, value = raw.split(":", 1)
        data[key.strip()] = value.strip().strip('"\'')
    return data


def parse_simple_yaml_value(path: Path, key: str) -> Optional[str]:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*['\"]?([^'\"#\n]+)")
    for line in read_text(path).splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return None


def parse_pyproject_version(path: Path) -> Optional[str]:
    in_project = False
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
            continue
        if in_project and stripped.startswith("version") and "=" in stripped:
            return stripped.split("=", 1)[1].strip().strip('"\'')
    return None


def candidate_skill_dirs(repo_or_skill: Path) -> Iterable[Path]:
    script_skill_dir = Path(__file__).resolve().parents[1]
    yield script_skill_dir
    path = repo_or_skill.resolve()
    yield path
    yield path / SKILL_PATH
    yield path / ".agents" / "skills" / "harness-engineering-audit"
    yield Path.home() / ".codex" / "skills" / "harness-engineering-audit"


def detect_installed_version(repo_or_skill: Path) -> tuple[Optional[str], Dict[str, Any]]:
    seen: set[Path] = set()
    details: Dict[str, Any] = {"sources_checked": []}
    for skill_dir in candidate_skill_dirs(repo_or_skill):
        skill_dir = skill_dir.resolve()
        if skill_dir in seen:
            continue
        seen.add(skill_dir)
        skill_md = skill_dir / "SKILL.md"
        yaml_path = skill_dir / "agents" / "openai.yaml"
        details["sources_checked"].append(str(skill_md))
        frontmatter = parse_frontmatter(read_text(skill_md)) if skill_md.exists() else {}
        if frontmatter.get("version"):
            details["version_source"] = str(skill_md)
            return frontmatter["version"], details
        yaml_version = parse_simple_yaml_value(yaml_path, "version") if yaml_path.exists() else None
        if yaml_version:
            details["version_source"] = str(yaml_path)
            return yaml_version, details
    return None, details


def detect_package_version(repo_or_skill: Path) -> tuple[Optional[str], Optional[str]]:
    starts = [repo_or_skill.resolve(), Path(__file__).resolve()]
    for start in starts:
        for parent in [start, *start.parents]:
            pyproject = parent / "pyproject.toml"
            if pyproject.exists():
                version = parse_pyproject_version(pyproject)
                if version:
                    return version, str(pyproject)
    return None, None


def which_gh() -> Optional[str]:
    return shutil.which("gh")


def run_gh(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def gh_skill_available() -> tuple[bool, str]:
    try:
        result = run_gh(["skill", "--help"], timeout=10)
    except Exception as exc:  # pragma: no cover - defensive around local CLI state
        return False, str(exc)
    return result.returncode == 0, (result.stderr or result.stdout).strip()


def latest_release_tag() -> tuple[Optional[str], Optional[str]]:
    try:
        result = run_gh(["release", "view", "--repo", REPO, "--json", "tagName"], timeout=20)
    except Exception as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip()
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return None, f"failed to parse gh release JSON: {exc}"
    tag = data.get("tagName")
    return (str(tag), None) if tag else (None, "gh release response did not include tagName")


def normalize_version(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lstrip("v")


def version_parts(value: Optional[str]) -> tuple[int, ...]:
    normalized = normalize_version(value)
    if not normalized:
        return ()
    parts = []
    for raw in normalized.split("."):
        if not raw.isdigit():
            break
        parts.append(int(raw))
    return tuple(parts)


def compare_versions(installed: Optional[str], latest: Optional[str]) -> Optional[int]:
    installed_parts = version_parts(installed)
    latest_parts = version_parts(latest)
    if not installed_parts or not latest_parts:
        return None
    width = max(len(installed_parts), len(latest_parts))
    installed_padded = installed_parts + (0,) * (width - len(installed_parts))
    latest_padded = latest_parts + (0,) * (width - len(latest_parts))
    if installed_padded == latest_padded:
        return 0
    return 1 if installed_padded > latest_padded else -1


def infer_scope(repo_or_skill: Path) -> tuple[Optional[str], str]:
    resolved = Path(__file__).resolve()
    text = str(resolved)
    repo_text = str(repo_or_skill.resolve())
    if "/.codex/skills/harness-engineering-audit/" in text:
        return "user", "script is running from the user Codex skill directory"
    if "/.agents/skills/harness-engineering-audit/" in text or "/.agents/skills/harness-engineering-audit" in repo_text:
        return "project", "script is running from a project-scoped skill directory"
    return None, "auto scope is ambiguous outside an installed .codex/.agents skill directory; specify --update-scope user or project"


def base_result(repo_or_skill: Path) -> Dict[str, Any]:
    installed_version, installed_details = detect_installed_version(repo_or_skill)
    package_version, package_source = detect_package_version(repo_or_skill)
    return {
        "schema": "harness-engineering-audit.update-status.v1",
        "status": "unknown",
        "installed_version": installed_version,
        "latest_version": None,
        "script_package_version": package_version,
        "script_package_version_source": package_source,
        "installed_version_source": installed_details.get("version_source"),
        "action_taken": "none",
        "human_approval_required": True,
        "mutates_by_default": False,
        "repository": REPO,
        "skill_path": SKILL_PATH,
        "recommended_scope": "user",
        "recommended_update_command": command_text("user"),
        "recommended_project_update_command": command_text("project"),
        "recommended_update_command_multiline": multiline_command("user"),
        "recommended_project_update_command_multiline": multiline_command("project"),
        "warnings": [
            "Normal audit runs never self-update silently.",
            "Avoid `gh skill update --all` for this skill because system/manual skills may lack GitHub metadata.",
            "Project-scoped installs should generally be updated intentionally through a repository PR.",
            "Newer patch tags are reported as available because release tags may include material skill changes.",
        ],
        "messages": [],
        "errors": [],
    }


def check_update(repo_or_skill: Path) -> Dict[str, Any]:
    result = base_result(repo_or_skill)
    gh_path = which_gh()
    result["gh_path"] = gh_path
    if not gh_path:
        result["status"] = "tooling_missing"
        result["errors"].append("GitHub CLI `gh` was not found on PATH.")
        return result
    skill_ok, skill_detail = gh_skill_available()
    result["gh_skill_available"] = skill_ok
    if not skill_ok:
        result["status"] = "tooling_missing"
        result["errors"].append("GitHub CLI `gh skill` command is unavailable.")
        if skill_detail:
            result["messages"].append(skill_detail)
        return result
    tag, error = latest_release_tag()
    if error:
        result["status"] = "unknown"
        result["errors"].append(error)
        return result
    result["latest_version"] = normalize_version(tag)
    installed = normalize_version(result.get("installed_version")) or normalize_version(result.get("script_package_version"))
    latest = normalize_version(result.get("latest_version"))
    if not latest:
        result["status"] = "unknown"
    elif not installed:
        result["status"] = "unknown"
        result["messages"].append("Installed version could not be detected locally.")
    elif installed == latest:
        result["status"] = "current"
        result["version_match_strategy"] = "exact"
    else:
        comparison = compare_versions(installed, latest)
        if comparison is not None and comparison >= 0:
            result["status"] = "current"
            result["version_match_strategy"] = "numeric-equivalent" if comparison == 0 else "local-newer-than-latest"
            if comparison > 0:
                result["messages"].append(
                    f"Installed version {installed} is newer than latest release tag {latest}."
                )
        else:
            result["status"] = "available"
            result["version_match_strategy"] = "newer-release-available" if comparison == -1 else "version-mismatch"
            result["messages"].append(
                f"Latest release tag {latest} differs from installed version {installed}; update explicitly if you want this skill refreshed."
            )
    return result


def project_update_cwd(repo_or_skill: Path) -> tuple[Optional[str], Optional[str]]:
    target = repo_or_skill.resolve()
    if target.is_file():
        target = target.parent
    if not target.exists() or not target.is_dir():
        return None, f"project update target is not an existing directory: {target}"
    return str(target), None


def self_update(repo_or_skill: Path, scope: str) -> Dict[str, Any]:
    result = check_update(repo_or_skill)
    if result["status"] == "tooling_missing":
        result["action_taken"] = "self-update-failed"
        return result
    chosen_scope = scope
    if scope == "auto":
        inferred, reason = infer_scope(repo_or_skill)
        result["auto_scope_reason"] = reason
        if not inferred:
            result["status"] = "error"
            result["action_taken"] = "self-update-failed"
            result["errors"].append(reason)
            return result
        chosen_scope = inferred
    if chosen_scope not in {"user", "project"}:
        result["status"] = "error"
        result["action_taken"] = "self-update-failed"
        result["errors"].append("update scope must be user, project, or auto")
        return result
    result["requested_update_scope"] = scope
    result["effective_update_scope"] = chosen_scope
    cmd = update_command(chosen_scope)
    result["executed_command"] = " ".join(cmd)
    cwd = None
    if chosen_scope == "project":
        cwd, cwd_error = project_update_cwd(repo_or_skill)
        if cwd_error:
            result["status"] = "error"
            result["action_taken"] = "self-update-failed"
            result["errors"].append(cwd_error)
            return result
        result["self_update_cwd"] = cwd
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
    except Exception as exc:
        result["status"] = "error"
        result["action_taken"] = "self-update-failed"
        result["errors"].append(str(exc))
        return result
    result["self_update_returncode"] = proc.returncode
    result["self_update_stdout"] = proc.stdout.strip()
    result["self_update_stderr"] = proc.stderr.strip()
    if proc.returncode == 0:
        result["action_taken"] = "self-update"
        result["messages"].append("Skill updated. Restart Codex / rerun the audit to use the updated files.")
    else:
        result["status"] = "error"
        result["action_taken"] = "self-update-failed"
        if proc.stderr.strip():
            result["errors"].append(proc.stderr.strip())
    return result


def print_human(result: Dict[str, Any]) -> None:
    print("Harness Engineering Audit skill update status")
    print(f"Status: {result.get('status')}")
    print(f"Installed version: {result.get('installed_version') or 'unknown'}")
    print(f"Latest version: {result.get('latest_version') or 'unknown'}")
    if result.get("script_package_version"):
        print(f"Script/package version: {result.get('script_package_version')}")
    print(f"Action taken: {result.get('action_taken', 'none')}")
    print("Human approval required: yes")
    print("Recommended user-scope update command:")
    print(multiline_command("user"))
    print("Recommended project-scope update command:")
    print(multiline_command("project"))
    for message in result.get("messages", []):
        print(f"Note: {message}")
    for error in result.get("errors", []):
        print(f"Warning: {error}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check or explicitly update the harness-engineering-audit skill.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository or installed skill path used for local version detection")
    parser.add_argument("--json", action="store_true", help="Write machine-readable status JSON")
    parser.add_argument("--self-update", action="store_true", help="Explicitly update this skill, then exit")
    parser.add_argument("--update-scope", choices=["user", "project", "auto"], default="auto", help="Install scope for --self-update")
    args = parser.parse_args(argv)

    repo_or_skill = Path(args.repo).resolve()
    result = self_update(repo_or_skill, args.update_scope) if args.self_update else check_update(repo_or_skill)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_human(result)
    if result.get("action_taken") == "self-update":
        if not args.json:
            print("Skill updated. Restart Codex / rerun the audit to use the updated files.")
        return 0
    if args.self_update and result.get("action_taken") != "self-update":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
