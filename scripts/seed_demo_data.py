from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from seed_ontology import load_seed_payloads, main as seed_ontology_main, seed_mysql


def main(argv: list[str] | None = None) -> None:
    print(
        "Deprecated: scripts/seed_demo_data.py has been renamed to "
        "scripts/seed_ontology.py. Forwarding to the ontology seed entrypoint."
    )
    seed_ontology_main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
