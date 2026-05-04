#!/usr/bin/env python3
"""Run a full harness-engineering audit and write reports by default."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness_inventory import collect_inventory
from harness_score import score_inventory
from check_update import check_update, self_update
from recommend_tools import generate_recommendations
from render_report import write_reports
from setup_writer import run_setup
from stack_detect import detect_stack
from tool_inventory import inventory_tools
from lane_packs import build_lane_pack_registry, load_lane_pack_catalog

AUDIT_LEVELS = [
    {
        "key": "minimal",
        "mode": "audit",
        "label": "Minimal audit",
        "description": "report-only inventory, scoring, recommendations, and handoff artifacts",
    },
    {
        "key": "audit",
        "mode": "audit",
        "label": "Audit",
        "description": "same report-only mode as minimal; useful for script compatibility",
    },
    {
        "key": "safe-setup",
        "mode": "safe-setup",
        "label": "Safe setup",
        "description": "create missing low-risk docs/templates only",
    },
    {
        "key": "force-ideal-harness",
        "mode": "force-ideal-harness",
        "label": "Force ideal harness",
        "description": "stronger low-risk consolidation; no deletes or CI/config/hooks/security changes",
    },
    {
        "key": "symphony-repo-local",
        "mode": "symphony-repo-local",
        "label": "Symphony repo-local",
        "description": "repo-local Symphony contracts/templates and inert handoff text",
    },
    {
        "key": "symphony-live-handoff",
        "mode": "symphony-live-handoff",
        "label": "Symphony live handoff",
        "description": "approval-gated handoff text only; no install/config mutation",
    },
    {
        "key": "full-orchestration",
        "mode": "full-orchestration",
        "label": "Full orchestration",
        "description": "explicit opt-in lane-pack orchestration contracts and harness custom-agent TOML",
    },
]
AUDIT_LEVEL_BY_KEY = {level["key"]: level for level in AUDIT_LEVELS}
AUDIT_MODE_CHOICES = list(AUDIT_LEVEL_BY_KEY)


def mode_from_audit_level(value: str) -> str:
    return AUDIT_LEVEL_BY_KEY[value]["mode"]


def prompt_for_audit_mode() -> str:
    print("Select harness-engineering audit level:")
    selectable = [level for level in AUDIT_LEVELS if level["key"] != "audit"]
    for index, level in enumerate(selectable, start=1):
        default_marker = " (default)" if index == 1 else ""
        print(f"  {index}. {level['key']} - {level['description']}{default_marker}")
    print("Press Enter for minimal report-only audit.")
    while True:
        choice = input("Audit level: ").strip()
        if not choice:
            return "audit"
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(selectable):
                return selectable[index - 1]["mode"]
        normalized = choice.lower()
        if normalized in AUDIT_LEVEL_BY_KEY:
            return mode_from_audit_level(normalized)
        valid = ", ".join(level["key"] for level in selectable)
        print(f"Unrecognized audit level. Choose a number or one of: {valid}.", file=sys.stderr)


def resolve_audit_mode(requested_mode: str | None) -> str:
    if requested_mode:
        return mode_from_audit_level(requested_mode)
    if sys.stdin.isatty() and sys.stdout.isatty():
        return prompt_for_audit_mode()
    return "audit"



def main() -> None:
    parser = argparse.ArgumentParser(description="Run harness-engineering audit and write report artifacts.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository path to audit")
    parser.add_argument("--out", default=None, help="Report directory. Defaults to <repo>/.codex/reports/harness-engineering-audit")
    parser.add_argument("--force", action="store_true", help="Allow overwrite of custom output directory")
    parser.add_argument(
        "--mode",
        choices=AUDIT_MODE_CHOICES,
        default=None,
        help="Audit level/execution mode. In an interactive TTY, omitted mode prompts for a level; non-interactive runs default to minimal report-only audit.",
    )
    parser.add_argument("--no-recommend-tools", action="store_true", help="Disable upgrade recommendation generation")
    parser.add_argument("--no-web", action="store_true", help="Do not request follow-up web verification queue entries")
    parser.add_argument("--check-update", dest="check_update", action="store_true", default=True, help="Check this skill for updates and include status in reports (default)")
    parser.add_argument("--no-check-update", dest="check_update", action="store_false", help="Disable non-mutating skill update check")
    parser.add_argument("--self-update", action="store_true", help="Explicitly update this skill installation and exit")
    parser.add_argument("--update-scope", choices=["user", "project", "auto"], default="auto", help="Install scope for --self-update")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve() if args.out else repo / ".codex" / "reports" / "harness-engineering-audit"
    mode = resolve_audit_mode(args.mode) if not args.self_update else "audit"

    if args.self_update:
        update_status = self_update(repo, args.update_scope)
        for message in update_status.get("messages", []):
            print(message)
        for error in update_status.get("errors", []):
            print(f"Self-update error: {error}")
        if update_status.get("action_taken") == "self-update":
            if not update_status.get("messages"):
                print("Skill updated. Restart Codex / rerun the audit to use the updated files.")
            return
        raise SystemExit(1)

    if args.check_update:
        try:
            update_status = check_update(repo)
        except Exception as exc:  # normal audits must not fail because update awareness is unavailable
            update_status = {
                "schema": "harness-engineering-audit.update-status.v1",
                "status": "error",
                "installed_version": None,
                "latest_version": None,
                "action_taken": "none",
                "human_approval_required": True,
                "recommended_update_command": "gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user --force",
                "recommended_project_update_command": "gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope project --force",
                "errors": [str(exc)],
            }
    else:
        update_status = {
            "schema": "harness-engineering-audit.update-status.v1",
            "status": "unknown",
            "installed_version": None,
            "latest_version": None,
            "action_taken": "none",
            "human_approval_required": True,
            "check_enabled": False,
            "messages": ["Update check disabled by --no-check-update."],
            "recommended_update_command": "gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope user --force",
            "recommended_project_update_command": "gh skill install ryne2010/harness-engineering-audit skills/harness-engineering-audit --agent codex --scope project --force",
        }

    inventory = collect_inventory(repo)
    stack_inventory = detect_stack(repo, inventory)
    lane_registry = build_lane_pack_registry(repo, inventory, stack_inventory, load_lane_pack_catalog())
    inventory["lane_pack_registry"] = lane_registry
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
        update_status=update_status,
        mode=mode,
    )
    setup_manifest = run_setup(repo, out, mode, lane_registry=lane_registry)

    print(f"Harness-engineering audit complete.")
    print(f"Mode: {mode}")
    print(f"Repo: {repo}")
    print(f"Report: {out / 'report.md'}")
    print(f"Next step: {out / 'next-step.md'}")
    print(f"Upgrade recommendations: {out / 'upgrade-recommendations.md'}")
    print(f"Skill update status: {out / 'update-status.json'}")
    print(f"Web verification queue: {out / 'web-verification-queue.json'}")
    print(f"AGENTS priority: {out / 'agents-priority.md'}")
    if mode != "audit":
        print(f"Setup rollback manifest: {out / 'setup-rollback-manifest.json'}")
        print(f"Setup created: {len(setup_manifest.get('created', []))}")
        print(f"Setup modified: {len(setup_manifest.get('modified', []))}")
        print(f"Setup collisions: {len(setup_manifest.get('collisions', []))}")
    try:
        next_step = json.loads((out / "next-step.json").read_text(encoding="utf-8"))
        print(f"Default OMX next stage: {next_step.get('default_stage', 'ralplan')}")
    except Exception:
        print("Default OMX next stage: ralplan")
    print("Minimal OMX resume: $harness-engineering-audit continue")
    print(f"Overall score: {scorecard['overall_score']}/10 ({scorecard['overall_status']})")


if __name__ == "__main__":
    main()
