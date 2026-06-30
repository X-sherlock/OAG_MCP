from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from oag_task_planner_helpers import service


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "agent_plan_examples"
CASES_FILE = OUTPUT_DIR / "semantic_frame_cases.json"
PYTHON_OUTPUT = OUTPUT_DIR / "python_agent_plans.json"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cases_file = Path(os.environ.get("OAG_AGENT_PLAN_CASES", CASES_FILE))
    output_file = Path(os.environ.get("OAG_AGENT_PLAN_PYTHON_OUTPUT", PYTHON_OUTPUT))
    examples: list[dict[str, Any]] = json.loads(cases_file.read_text(encoding="utf-8"))
    planner = service()
    rows = []
    for example in examples:
        rows.append(
            {
                "case_id": example["case_id"],
                "title": example["title"],
                "semantic_frame": example["semantic_frame"],
                "agent_plan": planner.retrieve_context(
                    semantic_frame=example["semantic_frame"],
                    user_context=example.get("user_context") or {"permission_scopes": ["fund_public_data:read"]},
                    output_view="agent",
                ),
            }
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
