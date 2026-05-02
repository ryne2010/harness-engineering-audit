#!/usr/bin/env python3
"""Smoke-test the harness-engineering-audit skill against a temporary repo."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_AUDIT = REPO_ROOT / "skills" / "harness-engineering-audit" / "scripts" / "run_audit.py"
CHECK_UPDATE = REPO_ROOT / "skills" / "harness-engineering-audit" / "scripts" / "check_update.py"


def main() -> int:
    if not RUN_AUDIT.exists():
        print(f"missing run_audit.py at {RUN_AUDIT}", file=sys.stderr)
        return 1
    if not CHECK_UPDATE.exists():
        print(f"missing check_update.py at {CHECK_UPDATE}", file=sys.stderr)
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


        fake_bin = Path(td) / "bin"
        fake_bin.mkdir()
        fake_log = Path(td) / "fake-gh-log.jsonl"
        fake_gh = fake_bin / "gh"
        fake_gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "log = os.environ.get('FAKE_GH_LOG')\n"
            "if log:\n"
            "    with open(log, 'a', encoding='utf-8') as fh:\n"
            "        fh.write(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')\n"
            "args = sys.argv[1:]\n"
            "if args[:2] == ['skill', '--help']:\n"
            "    print('gh skill help')\n"
            "    raise SystemExit(0)\n"
            "if args[:2] == ['release', 'view']:\n"
            "    print(json.dumps({'tagName': 'v0.2.0'}))\n"
            "    raise SystemExit(0)\n"
            "if args[:2] == ['skill', 'install']:\n"
            "    print('installed')\n"
            "    raise SystemExit(0)\n"
            "raise SystemExit(2)\n",
            encoding="utf-8",
        )
        fake_gh.chmod(0o755)
        fake_env = dict(os.environ)
        fake_env["PATH"] = f"{fake_bin}{os.pathsep}{fake_env.get('PATH', '')}"
        fake_env["FAKE_GH_LOG"] = str(fake_log)
        self_update = subprocess.run(
            [sys.executable, "-S", str(CHECK_UPDATE), str(repo), "--self-update", "--update-scope", "project", "--json"],
            cwd=str(REPO_ROOT.parent),
            env=fake_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self_update.returncode != 0:
            print(self_update.stdout)
            print(self_update.stderr, file=sys.stderr)
            return self_update.returncode
        self_update_payload = json.loads(self_update.stdout)
        if self_update_payload.get("action_taken") != "self-update" or self_update_payload.get("effective_update_scope") != "project":
            print(f"fake self-update did not report success: {self_update_payload}", file=sys.stderr)
            return 1
        fake_calls = [json.loads(line) for line in fake_log.read_text(encoding="utf-8").splitlines()]
        install_calls = [call for call in fake_calls if call.get("argv", [])[:2] == ["skill", "install"]]
        if len(install_calls) != 1:
            print(f"expected exactly one skill install call, saw: {fake_calls}", file=sys.stderr)
            return 1
        install_call = install_calls[0]
        if install_call.get("cwd") != str(repo.resolve()):
            print(f"project self-update cwd should be target repo, saw: {install_call}", file=sys.stderr)
            return 1
        if "--all" in install_call.get("argv", []):
            print(f"self-update must not use --all: {install_call}", file=sys.stderr)
            return 1

        check_result = subprocess.run(
            [sys.executable, "-S", str(CHECK_UPDATE), str(repo), "--json"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check_result.returncode != 0:
            print(check_result.stdout)
            print(check_result.stderr, file=sys.stderr)
            return check_result.returncode
        check_payload = json.loads(check_result.stdout)
        if check_payload.get("action_taken") != "none" or check_payload.get("status") not in {"current", "available", "unknown", "tooling_missing", "error"}:
            print(f"unexpected check_update payload: {check_payload}", file=sys.stderr)
            return 1

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
            "update-status.json",
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
        if "## Skill update status" not in report_text or "gh skill update --all" not in report_text:
            print("report missing skill update status safety section", file=sys.stderr)
            return 1
        update_status = json.loads((out / "update-status.json").read_text(encoding="utf-8"))
        if update_status.get("action_taken") != "none":
            print("normal audit must not trigger self-update", file=sys.stderr)
            return 1
        if update_status.get("status") not in {"current", "available", "unknown", "tooling_missing", "error"}:
            print(f"unexpected update status: {update_status}", file=sys.stderr)
            return 1

        no_check = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(repo), "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if no_check.returncode != 0:
            print(no_check.stdout)
            print(no_check.stderr, file=sys.stderr)
            return no_check.returncode
        no_check_status = json.loads((out / "update-status.json").read_text(encoding="utf-8"))
        if no_check_status.get("check_enabled") is not False or no_check_status.get("action_taken") != "none":
            print(f"--no-check-update did not produce expected status: {no_check_status}", file=sys.stderr)
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
