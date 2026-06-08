from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from oag_mcp.config import TDSQLConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, PROJECT_ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_ontology_main_writes_mysql_metadata_aliases_and_graph(monkeypatch, capsys):
    seed_ontology = _load_script("seed_ontology")
    calls: list[tuple[str, Any]] = []
    config = SimpleNamespace(
        tdsql=TDSQLConfig("127.0.0.1", 3306, "oag", "oag_password", "oag_meta"),
        domain="finance_market",
    )
    payloads = {"domain": "finance_market", "graph": {"nodes": [], "edges": []}}

    monkeypatch.setattr(seed_ontology, "load_config", lambda: config)
    monkeypatch.setattr(seed_ontology, "load_seed_payloads", lambda **kwargs: payloads)
    monkeypatch.setattr(
        seed_ontology,
        "seed_mysql",
        lambda payloads, config: calls.append(("mysql", payloads, config)),
    )

    seed_ontology.main()

    assert calls == [("mysql", payloads, config.tdsql)]
    output = capsys.readouterr().out
    assert (
        "Seeded OAG schema-level ontology data from ontology/*.yaml into MySQL metadata, "
        "aliases, and graph tables."
    ) in output
    assert "objects=0" in output


def test_seed_demo_data_is_deprecated_forwarder(monkeypatch, capsys):
    seed_demo_data = _load_script("seed_demo_data")
    calls: list[list[str]] = []

    monkeypatch.setattr(seed_demo_data, "seed_ontology_main", lambda argv=None: calls.append(argv or []))

    seed_demo_data.main(["--include-sample"])

    assert calls == [["--include-sample"]]
    assert "Deprecated: scripts/seed_demo_data.py has been renamed" in capsys.readouterr().out
