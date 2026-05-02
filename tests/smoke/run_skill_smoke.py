#!/usr/bin/env python3
"""Smoke-test the harness-engineering-audit skill against a temporary repo."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_AUDIT = REPO_ROOT / "skills" / "harness-engineering-audit" / "scripts" / "run_audit.py"


def main() -> int:
    if not RUN_AUDIT.exists():
        print(f"missing run_audit.py at {RUN_AUDIT}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="harness-audit-smoke-") as td:
        repo = Path(td) / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "AGENTS.md").write_text("# AGENTS.md\n\nRun tests before merge.\n", encoding="utf-8")
        (repo / "README.md").write_text("# Smoke repo\n", encoding="utf-8")
        (repo / ".codex").mkdir()
        (repo / ".codex" / "config.toml").write_text(
            "model = 'gpt-5.5'\n[mcp_servers.docs]\ncommand = 'docs-mcp'\n",
            encoding="utf-8",
        )
        (repo / ".omx" / "context").mkdir(parents=True)
        (repo / ".omx" / "context" / "example.md").write_text("# Context\n", encoding="utf-8")
        (repo / ".agents" / "skills" / "example").mkdir(parents=True)
        (repo / ".agents" / "skills" / "example" / "SKILL.md").write_text(
            "---\nname: example\n---\n# Example skill\n",
            encoding="utf-8",
        )
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / "validate.yml").write_text(
            "name: validate\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npm test\n",
            encoding="utf-8",
        )
        (repo / "pyproject.toml").write_text("[project]\nname = 'smoke'\nversion = '0.0.0'\n", encoding="utf-8")
        (repo / "package.json").write_text(
            json.dumps(
                {
                    "scripts": {"test": "echo ok", "lint": "echo lint"},
                    "dependencies": {"react": "^19.0.0", "next": "^15.0.0"},
                    "devDependencies": {"typescript": "^5.0.0", "tailwindcss": "^4.0.0"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (repo / "openapi.yaml").write_text("openapi: 3.1.0\ninfo:\n  title: Smoke\n  version: 0.0.0\npaths: {}\n", encoding="utf-8")
        (repo / "Dockerfile").write_text("FROM node:22-alpine\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(repo)],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            return result.returncode

        out = repo / ".codex" / "reports" / "harness-engineering-audit"
        expected = [
            "inventory.json",
            "scorecard.json",
            "report.md",
            "findings.md",
            "recommended-fixes.md",
            "agents-priority.md",
            "omx-handoff.md",
            "next-step.md",
            "next-step.json",
            "stack-inventory.json",
            "tool-inventory.json",
            "upgrade-recommendations.json",
            "upgrade-recommendations.md",
            "web-verification-queue.json",
            "source-trust-policy.md",
            "prompts/deep-interview.md",
            "prompts/ralplan.md",
            "prompts/team.md",
            "prompts/ralph.md",
            "prompts/symphony-adoption.md",
            "prompts/tool-upgrade-ralplan.md",
        ]
        missing = [name for name in expected if not (out / name).exists()]
        if missing:
            print(f"missing reports: {missing}", file=sys.stderr)
            return 1

        score = json.loads((out / "scorecard.json").read_text(encoding="utf-8"))
        if "overall_score" not in score:
            print("scorecard missing overall_score", file=sys.stderr)
            return 1
        dimension_names = {d.get("name") for d in score.get("dimensions", [])}
        if "Symphony Orchestration Readiness" not in dimension_names:
            print("scorecard missing Symphony Orchestration Readiness dimension", file=sys.stderr)
            return 1
        inventory = json.loads((out / "inventory.json").read_text(encoding="utf-8"))
        if "symphony_readiness" not in inventory:
            print("inventory missing symphony_readiness", file=sys.stderr)
            return 1
        report_text = (out / "report.md").read_text(encoding="utf-8")
        if "Symphony Orchestration Readiness" not in report_text:
            print("report missing Symphony readiness section", file=sys.stderr)
            return 1

        next_step = json.loads((out / "next-step.json").read_text(encoding="utf-8"))
        if next_step.get("default_stage") != "ralplan":
            print("next-step default_stage should be ralplan", file=sys.stderr)
            return 1
        if not next_step.get("agents_priority"):
            print("next-step missing agents_priority", file=sys.stderr)
            return 1
        stages = {stage.get("stage") for stage in next_step.get("stages", [])}
        if "symphony-adoption" not in stages:
            print("next-step missing symphony-adoption stage", file=sys.stderr)
            return 1
        if "tool-upgrade-ralplan" not in stages:
            print("next-step missing tool-upgrade-ralplan stage", file=sys.stderr)
            return 1

        stack = json.loads((out / "stack-inventory.json").read_text(encoding="utf-8"))
        stack_tags = {item.get("tag") for item in stack.get("stack_tags", [])}
        for required_tag in {"python", "node-js-ts", "frontend-web", "openapi", "docker", "codex-ready", "omx-enabled"}:
            if required_tag not in stack_tags:
                print(f"stack inventory missing {required_tag}: {sorted(stack_tags)}", file=sys.stderr)
                return 1

        tools = json.loads((out / "tool-inventory.json").read_text(encoding="utf-8"))
        native_ids = {item.get("id") for item in tools.get("native_capabilities", [])}
        if not {"codex-project-config", "codex-mcp", "repo-codex-skills", "omx-runtime-artifacts"} <= native_ids:
            print(f"tool inventory missing native capabilities: {sorted(native_ids)}", file=sys.stderr)
            return 1

        upgrades = json.loads((out / "upgrade-recommendations.json").read_text(encoding="utf-8"))
        policy = upgrades.get("policy", {})
        if not (policy.get("recommend_tools") and policy.get("web_requested")):
            print("upgrade policy should recommend tools and request web verification by default", file=sys.stderr)
            return 1
        if policy.get("install_config_mutation") is not False or policy.get("approval_gate") != "required":
            print("upgrade policy should require approval and forbid audit-side mutation", file=sys.stderr)
            return 1
        queue = json.loads((out / "web-verification-queue.json").read_text(encoding="utf-8"))
        if queue.get("web_verified") is not False or queue.get("verification_mode") != "static-catalog":
            print("web verification queue must honestly report static, unverified status", file=sys.stderr)
            return 1
        if not upgrades.get("recommendations"):
            print("expected at least one actionable high-trust recommendation", file=sys.stderr)
            return 1
        if not all(r.get("approval_required") and not r.get("audit_fix_auto_approved") for r in upgrades.get("recommendations", [])):
            print("upgrade recommendations must require approval and not be auto-approved", file=sys.stderr)
            return 1
        if any(r.get("trust_tier") in {"tier3-unverified", "blocked"} for r in upgrades.get("recommendations", [])):
            print("unverified or blocked recommendations must not be actionable", file=sys.stderr)
            return 1
        if not upgrades.get("suppressions"):
            print("expected Codex/OMX-covered recommendations to be suppressed", file=sys.stderr)
            return 1
        upgrade_text = (out / "upgrade-recommendations.md").read_text(encoding="utf-8")
        if "Generated commands are inert" not in upgrade_text or "Approval required" not in upgrade_text:
            print("upgrade recommendations markdown missing approval/inert command language", file=sys.stderr)
            return 1
        trust_text = (out / "source-trust-policy.md").read_text(encoding="utf-8")
        if "unverified community tools" not in trust_text.lower() or "web_verified: false" not in trust_text:
            print("source trust policy missing trust/web honesty language", file=sys.stderr)
            return 1

        agent_recs = [
            r
            for r in score.get("recommendations", {}).get("low_risk", [])
            if "AGENTS" in f"{r.get('title', '')} {r.get('detail', '')}"
        ]
        if not agent_recs or not all(r.get("auto_approved") for r in agent_recs):
            print("AGENTS low-risk recommendations should be auto-approved", file=sys.stderr)
            return 1

        print("smoke passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
