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
LANE_CATALOG = REPO_ROOT / "skills" / "harness-engineering-audit" / "assets" / "lane-packs.json"
SKILL_SCRIPTS = REPO_ROOT / "skills" / "harness-engineering-audit" / "scripts"


def assert_recommendation_helper_edges() -> bool:
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    from harness_score import dedupe_recommendations, normalize_recommendation, summarize_recommendations  # noqa: PLC0415

    invalid_risk = normalize_recommendation({"risk": "surprising", "title": "Odd", "detail": "Fallback"})
    if invalid_risk.get("risk") != "medium" or invalid_risk.get("approval") != "review-required" or invalid_risk.get("auto_approved"):
        print(f"invalid risk should normalize to review-required medium: {invalid_risk}", file=sys.stderr)
        return False

    deduped = dedupe_recommendations([
        {
            "risk": "low",
            "category": "same",
            "title": "Same title",
            "detail": "Same detail",
            "dimension": "Dimension A",
            "source": "source-a",
            "evidence": ["one"],
            "priority": "p2",
        },
        {
            "risk": "low",
            "category": "same",
            "title": "Same title",
            "detail": "Same detail",
            "dimension": "Dimension B",
            "source": "source-b",
            "evidence": ["one", "two"],
            "priority": "p0",
        },
    ])
    if len(deduped) != 1:
        print(f"duplicate recommendations should merge: {deduped}", file=sys.stderr)
        return False
    merged = deduped[0]
    if merged.get("priority") != "p0":
        print(f"duplicate merge should keep highest priority: {merged}", file=sys.stderr)
        return False
    if set(merged.get("sources", [])) != {"source-a", "source-b"}:
        print(f"duplicate merge should keep sources: {merged}", file=sys.stderr)
        return False
    if set(merged.get("related_dimensions", [])) != {"Dimension A", "Dimension B"}:
        print(f"duplicate merge should keep dimensions: {merged}", file=sys.stderr)
        return False
    if set(merged.get("evidence", [])) != {"one", "two"}:
        print(f"duplicate merge should dedupe evidence: {merged}", file=sys.stderr)
        return False

    summary = summarize_recommendations(deduped, [invalid_risk], [])
    if summary.get("low_risk") != 1 or summary.get("medium_risk") != 1 or summary.get("auto_approved") != 1 or summary.get("review_required") != 1:
        print(f"recommendation summary helper edge mismatch: {summary}", file=sys.stderr)
        return False
    return True


def assert_tool_catalog_loader() -> bool:
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    from recommend_tools import load_tool_catalog  # noqa: PLC0415

    entries = load_tool_catalog()
    ids = {entry.get("id") for entry in entries}
    required = {"codex-agents-md", "codex-mcp", "omx-native-workflows"}
    if not required <= ids:
        print(f"tool catalog loader missing required entries: {sorted(ids)}", file=sys.stderr)
        return False
    if not all(isinstance(entry.get("stack_tags"), list) for entry in entries):
        print(f"tool catalog entries must expose list stack_tags: {entries}", file=sys.stderr)
        return False
    return True


def assert_no_recommend_tools_skips_catalog() -> bool:
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    import recommend_tools  # noqa: PLC0415

    original_loader = recommend_tools.load_tool_catalog

    def fail_loader():
        raise RuntimeError("catalog loader should not be called when recommendations are disabled")

    recommend_tools.load_tool_catalog = fail_loader
    try:
        result = recommend_tools.generate_recommendations(
            {"stack_tags": [{"tag": "python"}]},
            {"native_capabilities": []},
            recommend_tools=False,
            web_requested=True,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return False
    finally:
        recommend_tools.load_tool_catalog = original_loader

    policy = result.get("policy", {})
    queue = result.get("web_verification_queue", {})
    if policy.get("recommend_tools") is not False:
        print(f"disabled recommendations should set policy false: {result}", file=sys.stderr)
        return False
    if result.get("catalog_last_reviewed") is not None:
        print(f"disabled recommendations should not load catalog metadata: {result}", file=sys.stderr)
        return False
    if result.get("recommendations") or result.get("suppressions") or queue.get("entries"):
        print(f"disabled recommendations should emit no recommendation work: {result}", file=sys.stderr)
        return False
    if queue.get("verification_mode") != "recommendations-disabled":
        print(f"disabled recommendations should mark queue disabled: {queue}", file=sys.stderr)
        return False
    return True


def assert_recommendation_contract(score: dict, label: str) -> bool:
    recs = score.get("recommendations", {})
    buckets = [
        ("low_risk", recs.get("low_risk", []) or []),
        ("medium_risk", recs.get("medium_risk", []) or []),
        ("high_risk", recs.get("high_risk", []) or []),
    ]
    seen_ids = set()
    for bucket_name, bucket in buckets:
        for rec in bucket:
            missing = [
                key
                for key in {"id", "source", "dimension", "title", "detail", "risk", "approval", "actionability", "auto_approved"}
                if key not in rec
            ]
            if missing:
                print(f"{label} recommendation in {bucket_name} missing {missing}: {rec}", file=sys.stderr)
                return False
            if rec["id"] in seen_ids:
                print(f"{label} duplicate recommendation id: {rec['id']}", file=sys.stderr)
                return False
            seen_ids.add(rec["id"])
            if bucket_name == "low_risk" and (rec.get("risk") != "low" or rec.get("approval") != "auto-approved" or not rec.get("auto_approved")):
                print(f"{label} low-risk recommendation contract invalid: {rec}", file=sys.stderr)
                return False
            if bucket_name == "medium_risk" and (rec.get("risk") != "medium" or rec.get("approval") != "review-required" or rec.get("auto_approved")):
                print(f"{label} medium-risk recommendation contract invalid: {rec}", file=sys.stderr)
                return False
            if bucket_name == "high_risk" and (rec.get("risk") != "high" or rec.get("approval") != "explicit-approval-required" or rec.get("auto_approved")):
                print(f"{label} high-risk recommendation contract invalid: {rec}", file=sys.stderr)
                return False
    summary = score.get("recommendation_summary", {})
    expected_counts = {
        "low_risk": len(recs.get("low_risk", []) or []),
        "medium_risk": len(recs.get("medium_risk", []) or []),
        "high_risk": len(recs.get("high_risk", []) or []),
    }
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            print(f"{label} recommendation summary {key} mismatch: {summary} expected {expected}", file=sys.stderr)
            return False
    if summary.get("total") != sum(expected_counts.values()):
        print(f"{label} recommendation summary total mismatch: {summary}", file=sys.stderr)
        return False
    if summary.get("auto_approved") != expected_counts["low_risk"]:
        print(f"{label} recommendation summary auto-approved mismatch: {summary}", file=sys.stderr)
        return False
    if summary.get("schema") != "harness-engineering-audit.recommendation-summary.v1":
        print(f"{label} recommendation summary schema invalid: {summary}", file=sys.stderr)
        return False
    return True


def assert_handoff_default(out: Path, label: str) -> bool:
    next_step = json.loads((out / "next-step.json").read_text(encoding="utf-8"))
    handoff = (out / "omx-handoff.md").read_text(encoding="utf-8")
    default_stage = next_step.get("default_stage")
    stage = next((item for item in next_step.get("stages", []) if item.get("stage") == default_stage), None)
    if not stage:
        print(f"{label} missing default stage entry: {next_step}", file=sys.stderr)
        return False
    expected_label = stage.get("label")
    expected_command = stage.get("command")
    if f"Default next stage: **{expected_label}**." not in handoff:
        print(f"{label} handoff default label mismatch: {expected_label}", file=sys.stderr)
        return False
    if f"## Suggested default: {expected_label}" not in handoff:
        print(f"{label} handoff missing dynamic default heading: {expected_label}", file=sys.stderr)
        return False
    if expected_command not in handoff:
        print(f"{label} handoff missing default command: {expected_command}", file=sys.stderr)
        return False
    if "## Suggested `$ralplan` (default)" in handoff:
        print(f"{label} handoff contains stale hard-coded ralplan default", file=sys.stderr)
        return False
    return True


def main() -> int:
    if not RUN_AUDIT.exists():
        print(f"missing run_audit.py at {RUN_AUDIT}", file=sys.stderr)
        return 1
    if not CHECK_UPDATE.exists():
        print(f"missing check_update.py at {CHECK_UPDATE}", file=sys.stderr)
        return 1
    if not assert_recommendation_helper_edges():
        return 1
    if not assert_tool_catalog_loader():
        return 1
    if not assert_no_recommend_tools_skips_catalog():
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
                    "dependencies": {
                        "react": "^19.0.0",
                        "next": "^15.0.0",
                        "electron": "^33.0.0",
                        "bullmq": "^5.0.0",
                    },
                    "devDependencies": {
                        "typescript": "^5.0.0",
                        "tailwindcss": "^4.0.0",
                        "vite": "^7.0.0",
                        "@storybook/react": "^9.0.0",
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (repo / "manifest.json").write_text(
            json.dumps({"manifest_version": 3, "name": "Smoke Extension", "version": "0.0.0"}, indent=2),
            encoding="utf-8",
        )
        (repo / "src" / "components").mkdir(parents=True)
        (repo / "src" / "components" / "Button.tsx").write_text("export function Button() { return null }\n", encoding="utf-8")
        (repo / "src" / "auth").mkdir(parents=True)
        (repo / "src" / "auth" / "permissions.ts").write_text("export const permissions = []\n", encoding="utf-8")
        (repo / ".storybook").mkdir()
        (repo / ".storybook" / "main.ts").write_text("export default {}\n", encoding="utf-8")
        (repo / "electron").mkdir()
        (repo / "electron" / "main.ts").write_text("export {}\n", encoding="utf-8")
        (repo / "src-tauri").mkdir()
        (repo / "src-tauri" / "tauri.conf.json").write_text("{}\n", encoding="utf-8")
        (repo / "ios" / "Smoke.xcodeproj").mkdir(parents=True)
        (repo / "ios" / "Smoke.xcodeproj" / "project.pbxproj").write_text("// fixture\n", encoding="utf-8")
        (repo / "ios" / "WatchKit Extension").mkdir(parents=True)
        (repo / "ios" / "WatchKit Extension" / "Info.plist").write_text("<plist />\n", encoding="utf-8")
        (repo / "android" / "app" / "src" / "main").mkdir(parents=True)
        (repo / "android" / "app" / "src" / "main" / "AndroidManifest.xml").write_text("<manifest />\n", encoding="utf-8")
        (repo / "workers").mkdir()
        (repo / "workers" / "queue-worker.ts").write_text("export {}\n", encoding="utf-8")
        (repo / "openapi.yaml").write_text("openapi: 3.1.0\ninfo:\n  title: Smoke\n  version: 0.0.0\npaths: {}\n", encoding="utf-8")
        (repo / "Dockerfile").write_text("FROM node:22-alpine\n", encoding="utf-8")
        (repo / "infra").mkdir()
        (repo / "infra" / "main.tf").write_text("terraform { required_version = \">= 1.6.0\" }\n", encoding="utf-8")
        (repo / "models").mkdir()
        (repo / "models" / "vision-model.onnx").write_text("placeholder model fixture\n", encoding="utf-8")
        (repo / "notebooks").mkdir()
        (repo / "notebooks" / "experiment.ipynb").write_text("{}", encoding="utf-8")


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

        dangerous_out = Path(td) / "harness-engineering-audit"
        dangerous_out.mkdir()
        sentinel = dangerous_out / "sentinel.txt"
        sentinel.write_text("custom output must not be deleted\n", encoding="utf-8")
        custom_out_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(repo), "--out", str(dangerous_out), "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if custom_out_result.returncode == 0:
            print("audit should refuse an unmarked custom output directory", file=sys.stderr)
            return 1
        if not sentinel.exists():
            print("audit deleted an unmarked custom output directory", file=sys.stderr)
            return 1
        if "Refusing to overwrite unmarked output directory" not in custom_out_result.stderr:
            print(f"unexpected custom output refusal: {custom_out_result.stderr}", file=sys.stderr)
            return 1

        default_out = repo / ".codex" / "reports" / "harness-engineering-audit"
        default_out.mkdir(parents=True)
        legacy_default_file = default_out / "legacy.txt"
        legacy_default_file.write_text("default report directory may be regenerated\n", encoding="utf-8")
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
        if legacy_default_file.exists():
            print("audit did not regenerate the default report directory", file=sys.stderr)
            return 1
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
        if not assert_recommendation_contract(score, "main fixture"):
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
        lane_registry = inventory.get("lane_pack_registry", {})
        if lane_registry.get("schema") != "harness-engineering-audit.lane-pack-registry.v1":
            print(f"inventory missing lane_pack_registry: {lane_registry}", file=sys.stderr)
            return 1
        mode_safety = lane_registry.get("mode_safety", {})
        if not (mode_safety.get("audit_report_only") and mode_safety.get("safe_setup_docs_only") and mode_safety.get("custom_agents_full_orchestration_only")):
            print(f"lane registry missing mode safety flags: {mode_safety}", file=sys.stderr)
            return 1
        lanes = lane_registry.get("lanes", {})
        for lane_id in {"frontend-ui-ux", "infra-cicd-terraform", "ai-ml-cv-data-science"}:
            if lanes.get(lane_id, {}).get("activation") != "stack_detected":
                print(f"expected stack-detected lane {lane_id}: {lanes.get(lane_id)}", file=sys.stderr)
                return 1
        if "host_matrix" not in lanes.get("frontend-ui-ux", {}) or not lanes["frontend-ui-ux"]["host_matrix"].get("web"):
            print(f"frontend-ui-ux missing web host matrix: {lanes.get('frontend-ui-ux')}", file=sys.stderr)
            return 1
        host_matrix = lanes["frontend-ui-ux"]["host_matrix"]
        for host in {"web", "desktop", "mobile", "tablet", "watch", "browser_extension"}:
            if not host_matrix.get(host):
                print(f"frontend-ui-ux missing {host} host matrix: {host_matrix}", file=sys.stderr)
                return 1
        for lane_id in {"frontend-ui-ux", "mobile-native", "desktop-native", "security-trust", "performance-scalability-reliability"}:
            lane = lanes.get(lane_id, {})
            if lane.get("status") != "recommended" or lane.get("recommendation_policy") != "recommended":
                print(f"expected recommended lane policy for {lane_id}: {lane}", file=sys.stderr)
                return 1
            if lane.get("activation_confidence") not in {"medium", "high"}:
                print(f"expected medium/high confidence for {lane_id}: {lane}", file=sys.stderr)
                return 1
        score_lane_registry = score.get("lane_pack_registry", {})
        if score_lane_registry.get("schema") != "harness-engineering-audit.lane-pack-registry.v1":
            print(f"scorecard missing lane_pack_registry: {score_lane_registry}", file=sys.stderr)
            return 1
        score_frontend_lane = score_lane_registry.get("lanes", {}).get("frontend-ui-ux", {})
        if score_frontend_lane.get("activation_confidence") not in {"medium", "high"}:
            print(f"scorecard missing lane confidence: {score_frontend_lane}", file=sys.stderr)
            return 1
        if score_frontend_lane.get("recommendation_policy") != "recommended":
            print(f"scorecard missing lane recommendation policy: {score_frontend_lane}", file=sys.stderr)
            return 1
        if "frontend-ui-ux" not in score_lane_registry.get("recommended_lane_ids", []):
            print(f"scorecard should recommend missing frontend-ui-ux lane: {score_lane_registry}", file=sys.stderr)
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
        if "## Lane Pack Registry" not in report_text or "frontend-ui-ux" not in report_text or "Confidence" not in report_text:
            print("report missing lane pack registry section", file=sys.stderr)
            return 1
        if "## Skill update status" not in report_text or "gh skill update --all" not in report_text:
            print("report missing skill update status safety section", file=sys.stderr)
            return 1
        if "OMX interactive default: select **Plan auto-approved fixes**" not in report_text or "$ralplan \"Read" not in report_text:
            print("main report should show ralplan as the default manual command for brownfield fixture", file=sys.stderr)
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
        decision = next_step.get("decision", {})
        if decision.get("default_stage") != next_step.get("default_stage") or not decision.get("reason"):
            print(f"next-step decision missing or inconsistent: {next_step}", file=sys.stderr)
            return 1
        if decision.get("review_required", 0) != score.get("recommendation_summary", {}).get("review_required", 0):
            print(f"next-step decision count mismatch: {decision}", file=sys.stderr)
            return 1
        if not next_step.get("agents_priority"):
            print("next-step missing agents_priority", file=sys.stderr)
            return 1
        stages = {stage.get("stage") for stage in next_step.get("stages", [])}
        for stage_name in {"safe-setup", "force-ideal-harness", "symphony-repo-local", "symphony-live-handoff"}:
            if stage_name not in stages:
                print(f"next-step missing {stage_name} stage", file=sys.stderr)
                return 1
        if "full-orchestration" not in stages:
            print("next-step missing full-orchestration stage", file=sys.stderr)
            return 1
        full_stage = next(stage for stage in next_step.get("stages", []) if stage.get("stage") == "full-orchestration")
        if full_stage.get("recommended"):
            print("full-orchestration must not be recommended by default", file=sys.stderr)
            return 1
        if "symphony-adoption" not in stages:
            print("next-step missing symphony-adoption stage", file=sys.stderr)
            return 1
        if "tool-upgrade-ralplan" not in stages:
            print("next-step missing tool-upgrade-ralplan stage", file=sys.stderr)
            return 1
        if not assert_handoff_default(out, "main fixture"):
            return 1

        stack = json.loads((out / "stack-inventory.json").read_text(encoding="utf-8"))
        stack_tags = {item.get("tag") for item in stack.get("stack_tags", [])}
        for required_tag in {
            "python",
            "node-js-ts",
            "frontend-web",
            "openapi",
            "docker",
            "codex-ready",
            "omx-enabled",
            "browser-extension",
            "storybook",
            "vite-app",
            "mobile-native",
            "ios",
            "android",
            "watchos",
            "desktop-native",
            "electron",
            "tauri",
            "queue",
            "cache",
            "worker-service",
            "security-sensitive",
        }:
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
        if not LANE_CATALOG.exists():
            print(f"missing lane catalog: {LANE_CATALOG}", file=sys.stderr)
            return 1
        lane_catalog = json.loads(LANE_CATALOG.read_text(encoding="utf-8"))
        if lane_catalog.get("schema") != "harness-engineering-audit.lane-pack-catalog.v1":
            print(f"unexpected lane catalog schema: {lane_catalog.get('schema')}", file=sys.stderr)
            return 1
        built_in_agent_names = set(lane_catalog.get("built_in_agent_names", []))
        expected_universal_lanes = {
            "lane-registry",
            "agent-handoff-protocol",
            "workflow-library",
            "contract-boundaries",
            "runtime-evidence-standards",
            "change-taxonomy",
            "decision-memory",
            "context-budget-architecture",
            "tool-capability-registry",
            "drift-staleness-control",
        }
        expected_stack_lanes = {
            "frontend-ui-ux",
            "backend-api-contracts",
            "data-persistence",
            "security-trust",
            "performance-scalability-reliability",
            "infra-cicd-terraform",
            "ai-ml-cv-data-science",
            "mobile-native",
            "desktop-native",
            "cli-devtool",
            "observability-sre",
            "docs-gardening-knowledge",
            "qa-evaluation",
        }
        catalog_lanes = {lane.get("id"): lane for lane in lane_catalog.get("lanes", [])}
        if not expected_universal_lanes <= set(catalog_lanes) or not expected_stack_lanes <= set(catalog_lanes):
            print(f"lane catalog missing expected lanes: {sorted(set(catalog_lanes))}", file=sys.stderr)
            return 1
        custom_agent_names = []
        for lane_id, lane in catalog_lanes.items():
            for key in {"id", "activation", "risk", "safe_setup_targets", "full_orchestration_targets", "source_of_truth_expectations", "validation_expectations"}:
                if key not in lane:
                    print(f"lane {lane_id} missing {key}", file=sys.stderr)
                    return 1
            for target in lane.get("safe_setup_targets", []):
                if target.get("target", "").startswith(".codex/agents"):
                    print(f"safe setup target must not create .codex/agents: {lane_id} {target}", file=sys.stderr)
                    return 1
                if not (template_dir / target.get("template", "")).exists():
                    print(f"missing lane safe template: {lane_id} {target}", file=sys.stderr)
                    return 1
            for target in lane.get("full_orchestration_targets", []):
                if not (template_dir / target.get("template", "")).exists():
                    print(f"missing lane full template: {lane_id} {target}", file=sys.stderr)
                    return 1
                if target.get("agent_name"):
                    custom_agent_names.append(target["agent_name"])
        if len(custom_agent_names) != len(set(custom_agent_names)) or set(custom_agent_names) & built_in_agent_names:
            print(f"custom agent names must be unique and non-built-in: {custom_agent_names}", file=sys.stderr)
            return 1
        sys.path.insert(0, str(SKILL_SCRIPTS))
        from lane_packs import build_lane_pack_registry, setup_targets_for_mode, validate_lane_pack_catalog  # noqa: PLC0415

        invalid_catalog = json.loads(json.dumps(lane_catalog))
        invalid_catalog["lanes"][0]["safe_setup_targets"][0]["target"] = "../AGENTS.md"
        try:
            validate_lane_pack_catalog(invalid_catalog)
        except ValueError:
            pass
        else:
            print("lane catalog validation should reject parent-traversal targets", file=sys.stderr)
            return 1

        low_confidence_registry = build_lane_pack_registry(
            repo,
            inventory,
            {
                "stack_tags": [
                    {
                        "tag": "security-sensitive",
                        "confidence": "low",
                        "evidence_paths": ["src/auth/permissions.ts"],
                    }
                ],
                "profile_groups": {},
            },
            lane_catalog,
        )
        low_confidence_security = low_confidence_registry.get("lanes", {}).get("security-trust", {})
        if low_confidence_security.get("status") != "candidate":
            print(f"low-confidence medium-risk lane should be advisory candidate: {low_confidence_security}", file=sys.stderr)
            return 1
        if low_confidence_security.get("recommendation_policy") != "advisory-candidate":
            print(f"low-confidence medium-risk lane should not be recommended: {low_confidence_security}", file=sys.stderr)
            return 1
        if "security-trust" in low_confidence_registry.get("recommended_lane_ids", []):
            print(f"low-confidence medium-risk lane should not be in recommended ids: {low_confidence_registry}", file=sys.stderr)
            return 1
        low_confidence_targets = setup_targets_for_mode(low_confidence_registry, "full-orchestration", lane_catalog)
        if any(target.get("lane_id") == "security-trust" for target in low_confidence_targets):
            print(f"advisory candidate lane should not produce setup targets: {low_confidence_targets}", file=sys.stderr)
            return 1
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
        if not assert_recommendation_contract(minimal_score, "minimal fixture"):
            return 1
        if minimal_inventory.get("lifecycle", {}).get("classification") != "greenfield-bootstrap":
            print(f"minimal repo should be greenfield-bootstrap: {minimal_inventory.get('lifecycle')}", file=sys.stderr)
            return 1
        if minimal_score.get("lifecycle", {}).get("classification") != "greenfield-bootstrap":
            print(f"minimal score lifecycle mismatch: {minimal_score.get('lifecycle')}", file=sys.stderr)
            return 1
        if minimal_next.get("default_stage") != "safe-setup":
            print(f"minimal repo default_stage should be safe-setup: {minimal_next}", file=sys.stderr)
            return 1
        minimal_decision = minimal_next.get("decision", {})
        if minimal_decision.get("default_stage") != "safe-setup" or "Greenfield" not in minimal_decision.get("reason", ""):
            print(f"minimal next-step decision should explain safe setup: {minimal_next}", file=sys.stderr)
            return 1
        minimal_report = (minimal_out / "report.md").read_text(encoding="utf-8")
        if "OMX interactive default: select **Run safe setup**" not in minimal_report or "--mode safe-setup" not in minimal_report:
            print("minimal report should show safe-setup as the default manual command", file=sys.stderr)
            return 1
        if not assert_handoff_default(minimal_out, "minimal fixture"):
            return 1
        if (minimal / "AGENTS.md").exists() or (minimal / "docs").exists():
            print("audit mode must not create source harness files", file=sys.stderr)
            return 1
        if (minimal / ".codex" / "agents").exists():
            print("audit mode must not create .codex/agents", file=sys.stderr)
            return 1

        noise = Path(td) / "noise"
        noise.mkdir()
        (noise / "AUTHORS.md").write_text("# Authors\n\nProject maintainers.\n", encoding="utf-8")
        (noise / "app" / "models").mkdir(parents=True)
        (noise / "app" / "models" / "user.ts").write_text("export interface User {}\n", encoding="utf-8")
        noise_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(noise), "--mode", "audit", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if noise_result.returncode != 0:
            print(noise_result.stdout)
            print(noise_result.stderr, file=sys.stderr)
            return noise_result.returncode
        noise_out = noise / ".codex" / "reports" / "harness-engineering-audit"
        noise_inventory = json.loads((noise_out / "inventory.json").read_text(encoding="utf-8"))
        noise_registry = noise_inventory.get("lane_pack_registry", {})
        noise_recommended = set(noise_registry.get("recommended_lane_ids", []))
        if {"security-trust", "ai-ml-cv-data-science"} & noise_recommended:
            print(f"substring noise should not recommend security/AI lanes: {noise_registry}", file=sys.stderr)
            return 1
        noise_stack = json.loads((noise_out / "stack-inventory.json").read_text(encoding="utf-8"))
        noise_tags = {item.get("tag") for item in noise_stack.get("stack_tags", [])}
        if {"security-sensitive", "ai-ml"} & noise_tags:
            print(f"substring noise should not create security/AI stack tags: {sorted(noise_tags)}", file=sys.stderr)
            return 1

        self_noise = Path(td) / "self-noise"
        self_noise.mkdir()
        (self_noise / ".codex" / "reports" / "harness-engineering-audit").mkdir(parents=True)
        (self_noise / ".codex" / "reports" / "harness-engineering-audit" / "report.md").write_text(
            "# Generated Report\n\n"
            "Symphony control plane task-state handoff. Doc gardening knowledge base. "
            "Source of truth, validation, recovery, evidence, queue, release, artifact lifecycle.\n",
            encoding="utf-8",
        )
        (self_noise / ".omx" / "state" / "sessions" / "example").mkdir(parents=True)
        (self_noise / ".omx" / "state" / "sessions" / "example" / "autopilot-state.json").write_text(
            json.dumps(
                {
                    "mode": "autopilot",
                    "current_phase": "validation",
                    "notes": "workflow handoff control plane trace evidence reconcile retry",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (self_noise / ".omx" / "logs").mkdir(parents=True)
        (self_noise / ".omx" / "logs" / "trace.log").write_text(
            "trace evidence validation workflow handoff\n",
            encoding="utf-8",
        )
        (self_noise / ".agents" / "skills" / "harness-engineering-audit").mkdir(parents=True)
        (self_noise / ".agents" / "skills" / "harness-engineering-audit" / "SKILL.md").write_text(
            "---\nname: harness-engineering-audit\n---\n"
            "# Harness Engineering Audit\n\n"
            "AGENTS.md Codex OMX MCP Symphony doc gardening task contract role topology.\n",
            encoding="utf-8",
        )
        self_noise_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(self_noise), "--mode", "audit", "--no-check-update", "--no-recommend-tools"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self_noise_result.returncode != 0:
            print(self_noise_result.stdout)
            print(self_noise_result.stderr, file=sys.stderr)
            return self_noise_result.returncode
        self_noise_out = self_noise / ".codex" / "reports" / "harness-engineering-audit"
        self_noise_inventory = json.loads((self_noise_out / "inventory.json").read_text(encoding="utf-8"))
        if self_noise_inventory.get("file_count_scanned") != 0:
            print(f"self-owned runtime artifacts should not be scanned: {self_noise_inventory}", file=sys.stderr)
            return 1
        if self_noise_inventory.get("codex", {}).get("exists") or self_noise_inventory.get("omx", {}).get("exists"):
            print(f"generated codex/omx runtime-only dirs should not count as readiness: {self_noise_inventory}", file=sys.stderr)
            return 1
        if self_noise_inventory.get("skills", {}).get("repo_skills"):
            print(f"project-local copy of this skill should not count as a repo skill: {self_noise_inventory}", file=sys.stderr)
            return 1
        if self_noise_inventory.get("readiness_registry", {}).get("readiness_count") != 0:
            print(f"self-owned artifacts should not satisfy readiness registry: {self_noise_inventory}", file=sys.stderr)
            return 1
        if self_noise_inventory.get("symphony_readiness", {}).get("readiness_count") != 0:
            print(f"self-owned artifacts should not satisfy Symphony readiness: {self_noise_inventory}", file=sys.stderr)
            return 1
        self_noise_stack = json.loads((self_noise_out / "stack-inventory.json").read_text(encoding="utf-8"))
        if self_noise_stack.get("stack_tags"):
            print(f"self-owned artifacts should not create stack tags: {self_noise_stack}", file=sys.stderr)
            return 1
        self_noise_upgrades = json.loads((self_noise_out / "upgrade-recommendations.json").read_text(encoding="utf-8"))
        if self_noise_upgrades.get("policy", {}).get("recommend_tools") is not False:
            print(f"--no-recommend-tools should persist disabled policy: {self_noise_upgrades}", file=sys.stderr)
            return 1
        if self_noise_upgrades.get("recommendations") or self_noise_upgrades.get("web_verification_queue", {}).get("entries"):
            print(f"--no-recommend-tools should not emit tool work: {self_noise_upgrades}", file=sys.stderr)
            return 1

        present_security = Path(td) / "present-security"
        present_security.mkdir()
        (present_security / "SECURITY.md").write_text("# Security\n\nReport permission issues.\n", encoding="utf-8")
        (present_security / "src" / "auth").mkdir(parents=True)
        (present_security / "src" / "auth" / "permissions.ts").write_text("export const permissions = []\n", encoding="utf-8")
        present_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(present_security), "--mode", "audit", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if present_result.returncode != 0:
            print(present_result.stdout)
            print(present_result.stderr, file=sys.stderr)
            return present_result.returncode
        present_out = present_security / ".codex" / "reports" / "harness-engineering-audit"
        present_report = (present_out / "report.md").read_text(encoding="utf-8")
        if "SECURITY.md" not in present_report or "src/auth/permissions.ts" not in present_report:
            print("present stack lane report should include source and activation evidence", file=sys.stderr)
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
        if not (minimal / "docs" / "harness" / "lane-packs" / "lane-registry.md").exists():
            print("safe-setup missing universal lane pack docs", file=sys.stderr)
            return 1
        if (minimal / ".codex" / "agents").exists():
            print("safe-setup must not create .codex/agents", file=sys.stderr)
            return 1
        safe_lane_text = (minimal / "docs" / "harness" / "lane-packs" / "lane-registry.md").read_text(encoding="utf-8")
        if "Generated by harness-engineering-audit" not in safe_lane_text:
            print("safe lane pack missing provenance marker", file=sys.stderr)
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
        if (minimal / ".codex" / "agents").exists():
            print("safe-setup rerun must not create .codex/agents", file=sys.stderr)
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

        full_result = subprocess.run(
            [sys.executable, "-S", str(RUN_AUDIT), str(minimal), "--mode", "full-orchestration", "--no-check-update"],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if full_result.returncode != 0:
            print(full_result.stdout)
            print(full_result.stderr, file=sys.stderr)
            return full_result.returncode
        agent_dir = minimal / ".codex" / "agents"
        if not agent_dir.exists():
            print("full-orchestration should create .codex/agents", file=sys.stderr)
            return 1
        generated_agents = sorted(agent_dir.glob("*.toml"))
        if not generated_agents:
            print("full-orchestration missing generated custom-agent TOML", file=sys.stderr)
            return 1
        seen_agent_names = set()
        for agent_file in generated_agents:
            text = agent_file.read_text(encoding="utf-8")
            if "Generated by harness-engineering-audit" not in text or "explicitly invoked" not in text:
                print(f"custom agent missing provenance/explicit invocation language: {agent_file}", file=sys.stderr)
                return 1
            name_line = next((line for line in text.splitlines() if line.startswith("name = ")), "")
            name = name_line.split("=", 1)[1].strip().strip('"') if name_line else ""
            if not name or name in built_in_agent_names or name in seen_agent_names:
                print(f"custom agent name invalid: {name} from {agent_file}", file=sys.stderr)
                return 1
            seen_agent_names.add(name)
        full_manifest = json.loads(setup_manifest_path.read_text(encoding="utf-8"))
        if not any(path.startswith(".codex/agents/") for path in full_manifest.get("created", []) + full_manifest.get("modified", [])):
            print(f"full-orchestration manifest missing custom-agent files: {full_manifest}", file=sys.stderr)
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
