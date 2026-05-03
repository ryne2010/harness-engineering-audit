#!/usr/bin/env python3
"""Smoke-test release workflow helper behavior against real git histories."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER = REPO_ROOT / "scripts" / "release_skill_workflow.py"


def run(cmd: list[str], cwd: Path, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )


def git(repo: Path, *args: str) -> str:
    return run(["git", *args], repo).stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(repo, "commit", "--no-gpg-sign", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def init_repo(root: Path, version: str = "0.3.0") -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "ci@example.test")
    git(repo, "config", "user.name", "CI")
    write(
        repo / "skills" / "harness-engineering-audit" / "SKILL.md",
        f"---\nname: harness-engineering-audit\nversion: {version}\n---\n# Skill\n",
    )
    write(repo / "pyproject.toml", f"[project]\nname = 'fixture'\nversion = '{version}'\n")
    write(repo / "README.md", "# Fixture\n")
    write(repo / "plugins" / "harness-engineering-audit" / "skills" / "harness-engineering-audit" / "release.json", "{}\n")
    write(repo / "skills" / "harness-engineering-audit" / "release.json", "{}\n")
    commit(repo, "initial")
    return repo


def helper(repo: Path, *args: str, github_output: Path | None = None) -> tuple[str, dict[str, str]]:
    cmd = [sys.executable, str(HELPER), *args, "--repo", str(repo)]
    if github_output is not None:
        cmd.extend(["--github-output", str(github_output)])
    result = run(cmd, REPO_ROOT)
    outputs: dict[str, str] = {}
    if github_output and github_output.exists():
        for line in github_output.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                outputs[key] = value
    return result.stdout, outputs


def assert_resolve_base() -> bool:
    with tempfile.TemporaryDirectory(prefix="release-helper-base-") as td:
        repo = init_repo(Path(td), "0.3.4")
        out = Path(td) / "github-output.txt"
        _, outputs = helper(repo, "resolve-base", github_output=out)
        if outputs.get("metadata_version") != "0.3.4" or outputs.get("base_minor") != "v0.3":
            print(f"resolve-base output mismatch: {outputs}", file=sys.stderr)
            return False
    return True


def assert_multi_commit_release_relevance() -> bool:
    with tempfile.TemporaryDirectory(prefix="release-helper-history-") as td:
        repo = init_repo(Path(td))
        git(repo, "tag", "v0.3.0")
        write(repo / "notes" / "local.txt", "not release relevant\n")
        commit(repo, "non release before")
        write(repo / "docs" / "USAGE.md", "# Usage\n")
        commit(repo, "release relevant middle")
        write(repo / "notes" / "after.txt", "head is not release relevant\n")
        head = commit(repo, "non release head")

        out = Path(td) / "github-output.txt"
        stdout, outputs = helper(repo, "check-changes", "--head-sha", head, "--base-minor", "v0.3", github_output=out)
        if outputs.get("release_relevant") != "true" or outputs.get("diff_base") != "v0.3.0":
            print(f"multi-commit relevance output mismatch: {outputs}", file=sys.stderr)
            return False
        if "docs/USAGE.md" not in stdout or "notes/after.txt" not in stdout:
            print(f"multi-commit changed file list incomplete:\n{stdout}", file=sys.stderr)
            return False
    return True


def assert_non_release_changes_skip_publish() -> bool:
    with tempfile.TemporaryDirectory(prefix="release-helper-skip-") as td:
        repo = init_repo(Path(td))
        git(repo, "tag", "v0.3.0")
        write(repo / "notes" / "local.txt", "not release relevant\n")
        head = commit(repo, "non release only")

        out = Path(td) / "github-output.txt"
        _, outputs = helper(repo, "check-changes", "--head-sha", head, "--base-minor", "v0.3", github_output=out)
        if outputs.get("release_relevant") != "false":
            print(f"non-release changes should skip publish: {outputs}", file=sys.stderr)
            return False
    return True


def assert_next_tag_and_stamp() -> bool:
    with tempfile.TemporaryDirectory(prefix="release-helper-tag-") as td:
        repo = init_repo(Path(td))
        git(repo, "tag", "v0.3.0")
        git(repo, "tag", "v0.3.2")

        out = Path(td) / "github-output.txt"
        _, outputs = helper(repo, "next-tag", "--base-minor", "v0.3", github_output=out)
        if outputs.get("tag") != "v0.3.3":
            print(f"next-tag output mismatch: {outputs}", file=sys.stderr)
            return False

        helper(repo, "stamp-release", "--tag", "v0.3.3")
        expected = {
            "schema": "harness-engineering-audit.release.v1",
            "version": "0.3.3",
            "tag": "v0.3.3",
        }
        for rel in [
            "skills/harness-engineering-audit/release.json",
            "plugins/harness-engineering-audit/skills/harness-engineering-audit/release.json",
        ]:
            data = json.loads((repo / rel).read_text(encoding="utf-8"))
            if data != expected:
                print(f"stamped metadata mismatch for {rel}: {data}", file=sys.stderr)
                return False
    return True


def main() -> int:
    if not HELPER.exists():
        print(f"missing release helper: {HELPER}", file=sys.stderr)
        return 1
    checks = [
        assert_resolve_base,
        assert_multi_commit_release_relevance,
        assert_non_release_changes_skip_publish,
        assert_next_tag_and_stamp,
    ]
    for check in checks:
        if not check():
            return 1
    print("release workflow smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
