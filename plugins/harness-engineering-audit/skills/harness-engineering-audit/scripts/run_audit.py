#!/usr/bin/env python3
"""Run a full harness-engineering audit and write reports by default."""
from __future__ import annotations

import argparse
from pathlib import Path

from harness_inventory import collect_inventory
from harness_score import score_inventory
from recommend_tools import generate_recommendations
from render_report import write_reports
from stack_detect import detect_stack
from tool_inventory import inventory_tools


def main() -> None:
    parser = argparse.ArgumentParser(description="Run harness-engineering audit and write report artifacts.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to audit")
    parser.add_argument("--out", default=None, help="Report directory. Defaults to <repo>/.codex/reports/harness-engineering-audit")
    parser.add_argument("--force", action="store_true", help="Allow overwrite of custom output directory")
    parser.add_argument("--no-recommend-tools", action="store_true", help="Disable upgrade recommendation generation")
    parser.add_argument("--no-web", action="store_true", help="Do not request follow-up web verification queue entries")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve() if args.out else repo / ".codex" / "reports" / "harness-engineering-audit"

    inventory = collect_inventory(repo)
    stack_inventory = detect_stack(repo, inventory)
    tool_inventory = inventory_tools(repo, inventory, stack_inventory)
    upgrade_recommendations = generate_recommendations(
        stack_inventory,
        tool_inventory,
        recommend_tools=not args.no_recommend_tools,
        web_requested=not args.no_web,
    )
    scorecard = score_inventory(inventory)
    write_reports(
        inventory,
        scorecard,
        out,
        force=args.force,
        stack_inventory=stack_inventory,
        tool_inventory=tool_inventory,
        upgrade_recommendations=upgrade_recommendations,
    )

    print(f"Harness-engineering audit complete.")
    print(f"Repo: {repo}")
    print(f"Report: {out / 'report.md'}")
    print(f"Next step: {out / 'next-step.md'}")
    print(f"Upgrade recommendations: {out / 'upgrade-recommendations.md'}")
    print(f"Web verification queue: {out / 'web-verification-queue.json'}")
    print(f"AGENTS priority: {out / 'agents-priority.md'}")
    print("Default OMX next stage: plan auto-approved fixes (AGENTS.md first)")
    print("Minimal OMX resume: $harness-engineering-audit continue")
    print(f"Overall score: {scorecard['overall_score']}/10 ({scorecard['overall_status']})")


if __name__ == "__main__":
    main()
