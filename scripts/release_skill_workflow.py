#!/usr/bin/env python3
"""Release workflow helpers for the harness-engineering-audit skill repo."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

RELEVANT_PATH_RE = re.compile(
    r"^("
    r"skills/"
    r"|plugins/"
    r"|\.agents/plugins/"
    r"|docs/"
    r"|scripts/release_skill_workflow\.py$"
    r"|README\.md$"
    r"|LICENSE$"
    r"|CHANGELOG\.md$"
    r"|pyproject\.toml$"
    r"|tests/"
    r"|\.github/workflows/release-skill\.yml$"
    r"|\.github/workflows/codeql\.yml$"
    r"|\.github/workflows/validate\.yml$"
    r")"
)

RELEASE_JSON_PATHS = [
    Path("skills/harness-engineering-audit/release.json"),
    Path("plugins/harness-engineering-audit/skills/harness-engineering-audit/release.json"),
]


def run_git(repo: Path, args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def parse_skill_version(path: Path) -> str | None:
    in_frontmatter = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if in_frontmatter and stripped.startswith("version:"):
            return stripped.split(":", 1)[1].strip().strip("\"'")
    return None


def parse_pyproject_version(path: Path) -> str | None:
    in_project = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if in_project and stripped.startswith("version") and "=" in stripped:
            return stripped.split("=", 1)[1].strip().strip("\"'")
    return None


def release_train_from_version(version: str) -> str:
    match = re.match(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:[-+].*)?$", version)
    if not match:
        raise SystemExit(f"Unsupported release version format: {version}")
    return f"v{match.group(1)}.{match.group(2)}"


def resolve_release_train(repo: Path) -> dict[str, str]:
    candidates = [
        (Path("skills/harness-engineering-audit/SKILL.md"), parse_skill_version),
        (Path("pyproject.toml"), parse_pyproject_version),
    ]
    for rel_path, parser in candidates:
        path = repo / rel_path
        if not path.exists():
            continue
        version = parser(path)
        if version:
            return {
                "metadata_version": version,
                "metadata_source": str(rel_path),
                "base_minor": release_train_from_version(version),
            }
    raise SystemExit("Could not resolve release version from skill or project metadata.")


def latest_release_tag(repo: Path, base_minor: str) -> str:
    output = run_git(repo, ["tag", "-l", f"{base_minor}.*", "--sort=-v:refname"])
    return output.splitlines()[0] if output else ""


def git_commit_exists(repo: Path, ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", f"{ref}^{{commit}}"],
        cwd=repo,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def changed_files_for_release(repo: Path, head_sha: str, base_minor: str) -> tuple[list[str], str]:
    latest = latest_release_tag(repo, base_minor)
    if latest and git_commit_exists(repo, latest):
        changed = run_git(repo, ["diff", "--name-only", latest, head_sha])
        return [line for line in changed.splitlines() if line], latest
    if git_commit_exists(repo, head_sha):
        changed = run_git(repo, ["ls-tree", "-r", "--name-only", head_sha])
        return [line for line in changed.splitlines() if line], "full-tree"
    raise SystemExit(f"Could not resolve workflow head SHA: {head_sha}")


def is_release_relevant(paths: Iterable[str]) -> bool:
    return any(RELEVANT_PATH_RE.search(path) for path in paths)


def next_release_tag(repo: Path, base_minor: str) -> str:
    latest = latest_release_tag(repo, base_minor)
    if not latest:
        return f"{base_minor}.0"
    patch = latest.rsplit(".", 1)[-1]
    if not patch.isdigit():
        raise SystemExit(f"Latest tag {latest} does not end in a numeric patch version.")
    return f"{base_minor}.{int(patch) + 1}"


def stamp_release_metadata(repo: Path, tag: str) -> None:
    version = tag.lstrip("v")
    payload = {
        "schema": "harness-engineering-audit.release.v1",
        "version": version,
        "tag": tag,
    }
    for rel_path in RELEASE_JSON_PATHS:
        path = repo / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_outputs(outputs: dict[str, str], github_output: str | None) -> None:
    lines = [f"{key}={value}" for key, value in outputs.items()]
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")
    else:
        for line in lines:
            print(line)


def cmd_resolve_base(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    outputs = resolve_release_train(repo)
    print(f"Release metadata source: {outputs['metadata_source']}")
    print(f"Release metadata version: {outputs['metadata_version']}")
    print(f"Release base minor: {outputs['base_minor']}")
    write_outputs(outputs, args.github_output)


def cmd_check_changes(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    changed, diff_base = changed_files_for_release(repo, args.head_sha, args.base_minor)
    if diff_base == "full-tree":
        print(f"No {args.base_minor}.x release tag found; considering all files at {args.head_sha}.")
    else:
        print(f"Diff base: latest release tag {diff_base}")
    print("Changed files considered for release:")
    for path in changed:
        print(path)
    release_relevant = is_release_relevant(changed)
    if not release_relevant:
        print("No release-relevant changes detected; skipping publish.")
    write_outputs(
        {
            "release_relevant": "true" if release_relevant else "false",
            "diff_base": diff_base,
            "changed_file_count": str(len(changed)),
        },
        args.github_output,
    )


def cmd_next_tag(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    tag = next_release_tag(repo, args.base_minor)
    print(f"Next release tag: {tag}")
    write_outputs({"tag": tag}, args.github_output)


def cmd_stamp_release(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    stamp_release_metadata(repo, args.tag)
    print(f"Stamped release metadata for {args.tag}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release workflow helper for harness-engineering-audit.")
    sub = parser.add_subparsers(dest="command", required=True)

    common_repo = argparse.ArgumentParser(add_help=False)
    common_repo.add_argument("--repo", default=".", help="Repository root")
    common_output = argparse.ArgumentParser(add_help=False)
    common_output.add_argument("--github-output", default=None, help="GITHUB_OUTPUT path")

    p = sub.add_parser("resolve-base", parents=[common_repo, common_output])
    p.set_defaults(func=cmd_resolve_base)

    p = sub.add_parser("check-changes", parents=[common_repo, common_output])
    p.add_argument("--head-sha", required=True)
    p.add_argument("--base-minor", required=True)
    p.set_defaults(func=cmd_check_changes)

    p = sub.add_parser("next-tag", parents=[common_repo, common_output])
    p.add_argument("--base-minor", required=True)
    p.set_defaults(func=cmd_next_tag)

    p = sub.add_parser("stamp-release", parents=[common_repo])
    p.add_argument("--tag", required=True)
    p.set_defaults(func=cmd_stamp_release)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
