from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from .validator import validate_ontology
from .yaml_store import PROJECT_ROOT


def run_seed() -> dict[str, Any]:
    validation = validate_ontology()
    if validation["errors"]:
        return {
            "ok": False,
            "blocked": True,
            "validation": validation,
            "stdout": "",
            "stderr": "Seed is blocked because ontology validation has errors.",
            "return_code": None,
        }

    script = PROJECT_ROOT / "scripts" / "seed_ontology.py"
    env = os.environ.copy()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
    )
    return {
        "ok": proc.returncode == 0,
        "blocked": False,
        "validation": validation,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "return_code": proc.returncode,
    }
