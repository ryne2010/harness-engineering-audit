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
        (repo / ".codex" / "config.toml").write_text("model = 'gpt-5.5'\n", encoding="utf-8")
        (repo / ".agents" / "skills").mkdir(parents=True)
        (repo / "package.json").write_text(json.dumps({"scripts": {"test": "echo ok"}}, indent=2), encoding="utf-8")

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
        expected = ["inventory.json", "scorecard.json", "report.md", "findings.md", "recommended-fixes.md", "omx-handoff.md"]
        missing = [name for name in expected if not (out / name).exists()]
        if missing:
            print(f"missing reports: {missing}", file=sys.stderr)
            return 1

        score = json.loads((out / "scorecard.json").read_text(encoding="utf-8"))
        if "overall_score" not in score:
            print("scorecard missing overall_score", file=sys.stderr)
            return 1

        print("smoke passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
