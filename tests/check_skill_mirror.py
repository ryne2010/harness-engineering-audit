#!/usr/bin/env python3
"""Validate the plugin skill mirror matches the source skill payload."""
from __future__ import annotations

import filecmp
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "skills" / "harness-engineering-audit"
MIRROR = REPO_ROOT / "plugins" / "harness-engineering-audit" / "skills" / "harness-engineering-audit"
IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def files_under(root: Path) -> set[Path]:
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not should_ignore(path.relative_to(root))
    }


def main() -> int:
    if not SOURCE.exists():
        print(f"missing source skill directory: {SOURCE}", file=sys.stderr)
        return 1
    if not MIRROR.exists():
        print(f"missing plugin mirror skill directory: {MIRROR}", file=sys.stderr)
        return 1

    source_files = files_under(SOURCE)
    mirror_files = files_under(MIRROR)
    missing_in_mirror = sorted(source_files - mirror_files)
    extra_in_mirror = sorted(mirror_files - source_files)
    changed = sorted(
        rel for rel in source_files & mirror_files if not filecmp.cmp(SOURCE / rel, MIRROR / rel, shallow=False)
    )

    if missing_in_mirror or extra_in_mirror or changed:
        if missing_in_mirror:
            print("Missing in plugin mirror:", file=sys.stderr)
            for rel in missing_in_mirror:
                print(f"- {rel}", file=sys.stderr)
        if extra_in_mirror:
            print("Extra in plugin mirror:", file=sys.stderr)
            for rel in extra_in_mirror:
                print(f"- {rel}", file=sys.stderr)
        if changed:
            print("Different files:", file=sys.stderr)
            for rel in changed:
                print(f"- {rel}", file=sys.stderr)
        return 1

    print("skill mirror parity ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
