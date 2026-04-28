#!/usr/bin/env python3
"""Run a full harness-engineering audit and write reports by default."""
from __future__ import annotations

import argparse
from pathlib import Path

from harness_inventory import collect_inventory
from harness_score import score_inventory
from render_report import write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Run harness-engineering audit and write report artifacts.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to audit")
    parser.add_argument("--out", default=None, help="Report directory. Defaults to <repo>/.codex/reports/harness-engineering-audit")
    parser.add_argument("--force", action="store_true", help="Allow overwrite of custom output directory")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve() if args.out else repo / ".codex" / "reports" / "harness-engineering-audit"

    inventory = collect_inventory(repo)
    scorecard = score_inventory(inventory)
    write_reports(inventory, scorecard, out, force=args.force)

    print(f"Harness-engineering audit complete.")
    print(f"Repo: {repo}")
    print(f"Report: {out / 'report.md'}")
    print(f"Overall score: {scorecard['overall_score']}/10 ({scorecard['overall_status']})")


if __name__ == "__main__":
    main()
