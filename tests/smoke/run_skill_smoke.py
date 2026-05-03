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
        (repo / "docs").mkdir()
        (repo / "docs" / "GLOSSARY.md").write_text(
            "# Glossary\n\nCanonical term: smoke repo. Avoid: demo repo.\n",
            encoding="utf-8",
        )
        (repo / "docs" / "REVIEW.md").write_text(
            "# Review\n\nAutomated checks are deterministic. Human review reads the diff.\n",
            encoding="utf-8",
        )
        (repo / "docs" / "index.md").write_text(
            "# Docs Index\n\nCatalog of source-of-truth docs and generated knowledge pages.\n",
            encoding="utf-8",
        )
        (repo / "docs" / "log.md").write_text(
            "# Docs Log\n\n## [2026-05-02] ingest | Smoke source\n\nAppend-only docs maintenance log.\n",
            encoding="utf-8",
        )
        (repo / "docs" / "GARDENING.md").write_text(
            "# Doc Gardening\n\nRaw sources are immutable. Generated synthesis pages are refreshed during ingest/query/lint docs workflows. Check for stale claims, contradictions, orphan pages, broken links, missing cross-references, and docs search coverage.\n",
            encoding="utf-8",
        )
        (repo / "raw").mkdir()
        (repo / "docs" / "knowledge").mkdir()
        (repo / "internal" / "adr").mkdir(parents=True)
        (repo / "internal" / "adr" / "0001-smoke.md").write_text(
            "# ADR 0001\n\nContradicts ADR notes should be surfaced explicitly.\n",
            encoding="utf-8",
        )
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
        if score.get("score_schema_version") != "2":
            print(f"scorecard missing score_schema_version=2: {score.get('score_schema_version')}", file=sys.stderr)
            return 1
        if score.get("lifecycle", {}).get("classification") not in {"greenfield-bootstrap", "brownfield-cleanup", "mature-audit"}:
            print(f"scorecard missing lifecycle classification: {score.get('lifecycle')}", file=sys.stderr)
            return 1
        if score.get("readiness_registry", {}).get("schema") != "harness-engineering-audit.readiness-registry.v1":
            print("scorecard missing readiness registry", file=sys.stderr)
            return 1
        dimension_names = {d.get("name") for d in score.get("dimensions", [])}
        if "Vocabulary / Domain Language Control" not in dimension_names:
            print("scorecard missing Vocabulary / Domain Language Control dimension", file=sys.stderr)
            return 1
        if "Doc Gardening / Knowledge Base Readiness" not in dimension_names:
            print("scorecard missing Doc Gardening / Knowledge Base Readiness dimension", file=sys.stderr)
            return 1
        if "Symphony Orchestration Readiness" not in dimension_names:
            print("scorecard missing Symphony Orchestration Readiness dimension", file=sys.stderr)
            return 1
        inventory = json.loads((out / "inventory.json").read_text(encoding="utf-8"))
        if inventory.get("lifecycle", {}).get("classification") not in {"greenfield-bootstrap", "brownfield-cleanup", "mature-audit"}:
            print(f"inventory missing lifecycle classification: {inventory.get('lifecycle')}", file=sys.stderr)
            return 1
        if inventory.get("readiness_registry", {}).get("schema") != "harness-engineering-audit.readiness-registry.v1":
            print("inventory missing readiness_registry", file=sys.stderr)
            return 1
        if "vocabulary_readiness" not in inventory:
            print("inventory missing vocabulary_readiness", file=sys.stderr)
            return 1
        if "doc_gardening_readiness" not in inventory:
            print("inventory missing doc_gardening_readiness", file=sys.stderr)
            return 1
        if "symphony_readiness" not in inventory:
            print("inventory missing symphony_readiness", file=sys.stderr)
            return 1
        report_text = (out / "report.md").read_text(encoding="utf-8")
        if "Vocabulary / Domain Language Control" not in report_text:
            print("report missing Vocabulary / Domain Language Control section", file=sys.stderr)
            return 1
        if "Doc Gardening / Knowledge Base Readiness" not in report_text:
            print("report missing Doc Gardening / Knowledge Base Readiness section", file=sys.stderr)
            return 1
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
        for stage_name in {"safe-setup", "force-ideal-harness", "symphony-repo-local", "symphony-live-handoff"}:
            if stage_name not in stages:
                print(f"next-step missing {stage_name} stage", file=sys.stderr)
                return 1
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

        template_dir = REPO_ROOT / "skills" / "harness-engineering-audit" / "assets" / "templates"
        required_templates = {
            "AGENTS.md",
            "docs-index.md",
            "validation-matrix.md",
            "doc-gardening.md",
            "task-contract.md",
            "agent-role-topology.md",
            "symphony-readiness.md",
            "task-state-schema.md",
            "observability-proof-schema.md",
            "recovery-reconciliation.md",
            "source-trust-policy.md",
            "evaluation-regression-harness.md",
            "release-merge-governance.md",
            "queue-capacity-policy.md",
            "artifact-provenance-policy.md",
            "cleanup-plan.md",
            "symphony-setup-handoff.md",
            "symphony-live-handoff.md",
        }
        missing_templates = [name for name in sorted(required_templates) if not (template_dir / name).exists()]
        if missing_templates:
            print(f"missing bundled templates: {missing_templates}", file=sys.stderr)
            return 1

        minimal = Path(td) / "minimal"
        minimal.mkdir()
        audit_minimal = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(minimal), "--mode", "audit", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if audit_minimal.returncode != 0:
            print(audit_minimal.stdout)
            print(audit_minimal.stderr, file=sys.stderr)
            return audit_minimal.returncode
        minimal_out = minimal / ".codex" / "reports" / "harness-engineering-audit"
        minimal_inventory = json.loads((minimal_out / "inventory.json").read_text(encoding="utf-8"))
        minimal_score = json.loads((minimal_out / "scorecard.json").read_text(encoding="utf-8"))
        minimal_next = json.loads((minimal_out / "next-step.json").read_text(encoding="utf-8"))
        if minimal_inventory.get("lifecycle", {}).get("classification") != "greenfield-bootstrap":
            print(f"minimal repo should be greenfield-bootstrap: {minimal_inventory.get('lifecycle')}", file=sys.stderr)
            return 1
        if minimal_score.get("lifecycle", {}).get("classification") != "greenfield-bootstrap":
            print(f"minimal score lifecycle mismatch: {minimal_score.get('lifecycle')}", file=sys.stderr)
            return 1
        if minimal_next.get("default_stage") != "safe-setup":
            print(f"minimal repo default_stage should be safe-setup: {minimal_next}", file=sys.stderr)
            return 1
        if (minimal / "AGENTS.md").exists() or (minimal / "docs").exists():
            print("audit mode must not create source harness files", file=sys.stderr)
            return 1

        setup_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(minimal), "--mode", "safe-setup", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if setup_result.returncode != 0:
            print(setup_result.stdout)
            print(setup_result.stderr, file=sys.stderr)
            return setup_result.returncode
        setup_manifest_path = minimal_out / "setup-rollback-manifest.json"
        if not setup_manifest_path.exists():
            print("safe-setup missing setup rollback manifest", file=sys.stderr)
            return 1
        setup_manifest = json.loads(setup_manifest_path.read_text(encoding="utf-8"))
        for key in {"schema", "mode", "generated_at", "created", "modified", "deprecated", "collisions", "skipped"}:
            if key not in setup_manifest:
                print(f"setup manifest missing {key}: {setup_manifest}", file=sys.stderr)
                return 1
        if setup_manifest.get("mode") != "safe-setup" or setup_manifest.get("schema") != "harness-engineering-audit.setup-rollback.v1":
            print(f"unexpected setup manifest metadata: {setup_manifest}", file=sys.stderr)
            return 1
        if not (minimal / "AGENTS.md").exists() or not (minimal / "docs" / "harness" / "task-contract.md").exists():
            print("safe-setup did not create expected harness files", file=sys.stderr)
            return 1
        if "Generated by harness-engineering-audit" not in (minimal / "AGENTS.md").read_text(encoding="utf-8"):
            print("generated AGENTS missing provenance marker", file=sys.stderr)
            return 1
        second_setup = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(minimal), "--mode", "safe-setup", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if second_setup.returncode != 0:
            print(second_setup.stdout)
            print(second_setup.stderr, file=sys.stderr)
            return second_setup.returncode
        second_manifest = json.loads(setup_manifest_path.read_text(encoding="utf-8"))
        if second_manifest.get("created"):
            print(f"safe-setup rerun should be idempotent, saw created: {second_manifest}", file=sys.stderr)
            return 1

        score_registry_categories = set(minimal_score.get("readiness_registry", {}).get("categories", {}))
        inventory_registry_categories = set(minimal_inventory.get("readiness_registry", {}).get("categories", {}))
        for required_category in {
            "vocabulary_domain_language_control",
            "doc_gardening_knowledge_base_readiness",
            "task_contract_ticket_quality",
            "agent_role_topology_isolation",
            "state_machine_reconciliation",
            "observability_depth",
            "environment_reproducibility",
            "safety_trust_boundaries",
            "evaluation_regression_harness",
            "cost_context_token_budgeting",
            "release_merge_governance",
            "queueing_capacity_backpressure",
            "artifact_provenance_lifecycle",
            "symphony_orchestration_readiness",
        }:
            if required_category not in score_registry_categories:
                print(f"score readiness registry missing {required_category}: {sorted(score_registry_categories)}", file=sys.stderr)
                return 1
            if required_category not in inventory_registry_categories:
                print(f"inventory readiness registry missing {required_category}: {sorted(inventory_registry_categories)}", file=sys.stderr)
                return 1

        repo_local_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(minimal), "--mode", "symphony-repo-local", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if repo_local_result.returncode != 0:
            print(repo_local_result.stdout)
            print(repo_local_result.stderr, file=sys.stderr)
            return repo_local_result.returncode
        repo_local_handoff = minimal_out / "symphony-repo-local-handoff.md"
        if not repo_local_handoff.exists() or "Approval Required" not in repo_local_handoff.read_text(encoding="utf-8"):
            print("symphony-repo-local missing inert install/config handoff", file=sys.stderr)
            return 1
        repo_local_doc_handoff = minimal / "docs" / "harness" / "symphony-setup-handoff.md"
        if not repo_local_doc_handoff.exists() or "Install command: approval required" not in repo_local_doc_handoff.read_text(encoding="utf-8"):
            print("symphony-repo-local missing repo-local inert setup handoff", file=sys.stderr)
            return 1

        symphony_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(minimal), "--mode", "symphony-live-handoff", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if symphony_result.returncode != 0:
            print(symphony_result.stdout)
            print(symphony_result.stderr, file=sys.stderr)
            return symphony_result.returncode
        live_handoff = minimal_out / "symphony-live-handoff.md"
        if not live_handoff.exists() or "Approval Required" not in live_handoff.read_text(encoding="utf-8"):
            print("symphony-live-handoff missing inert approval-gated handoff", file=sys.stderr)
            return 1

        print("smoke passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
