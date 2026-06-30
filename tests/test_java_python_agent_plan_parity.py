from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "agent_plan_examples"
JAVA_ROOT = PROJECT_ROOT / "OAG_MCP_JAVA"


def test_java_agent_plan_matches_python_for_15_semantic_frames() -> None:
    _assert_parity(
        cases_file=OUTPUT_DIR / "semantic_frame_cases.json",
        python_output=OUTPUT_DIR / "python_agent_plans.json",
        java_output=OUTPUT_DIR / "java_agent_plans.json",
    )


def test_java_agent_plan_matches_python_for_round2_15_semantic_frames() -> None:
    _assert_parity(
        cases_file=OUTPUT_DIR / "semantic_frame_cases_round2.json",
        python_output=OUTPUT_DIR / "python_agent_plans_round2.json",
        java_output=OUTPUT_DIR / "java_agent_plans_round2.json",
    )


def _assert_parity(*, cases_file: Path, python_output: Path, java_output: Path) -> None:
    cases = json.loads(cases_file.read_text(encoding="utf-8"))
    assert len(cases) >= 15

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT / 'src'}{os.pathsep}{PROJECT_ROOT / 'tests'}"
    env["OAG_AGENT_PLAN_CASES"] = str(cases_file)
    env["OAG_AGENT_PLAN_PYTHON_OUTPUT"] = str(python_output)
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "export_agent_plan_examples.py")],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )
    mvn = shutil.which("mvn") or shutil.which("mvn.cmd") or "mvn"
    subprocess.run(
        [
            mvn,
            "-Dtest=AgentPlanExampleExportTest",
            f"-Doag.agentPlan.cases={cases_file}",
            f"-Doag.agentPlan.javaOutput={java_output}",
            "test",
        ],
        cwd=JAVA_ROOT,
        check=True,
    )

    python_rows = json.loads(python_output.read_text(encoding="utf-8"))
    java_rows = json.loads(java_output.read_text(encoding="utf-8"))

    assert [item["case_id"] for item in java_rows] == [item["case_id"] for item in python_rows]
    for python_row, java_row in zip(python_rows, java_rows):
        assert java_row["agent_plan"] == python_row["agent_plan"], python_row["case_id"]
