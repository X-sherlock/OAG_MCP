from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from oag_ontology_loader.loader import load_ontology
from oag_mcp.service import OAGContextService
from oag_task_planner_helpers import frame, retrieve


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "finance_market"


def _load_seed_ontology():
    spec = importlib.util.spec_from_file_location(
        "seed_ontology", PROJECT_ROOT / "scripts" / "seed_ontology.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload() -> dict[str, Any]:
    return _load_seed_ontology().load_seed_payloads(PROJECT_ROOT / "ontology")


def test_xx_tables_expanded_on_seed():
    payload = _payload()
    node_ids = {node["id"] for node in payload["graph"]["nodes"]}

    assert "DataTable:dws_fund_perf_xx" not in node_ids
    assert "DataTable:dws_bm_perf_xx" not in node_ids
    assert "DataTable:dws_fund_risk retxx" not in node_ids
    assert "DataTable:DWS_FUND_RISK_PEER_xx" not in node_ids
    assert {
        "DataTable:dws_fund_perf_1y",
        "DataTable:dws_bm_perf_1y",
        "DataTable:dws_fund_risk_ret_1y",
        "DataTable:DWS_FUND_RISK_PEER_1y",
    }.issubset(node_ids)


def test_xx_fields_expanded_on_seed():
    payload = _payload()
    nodes = payload["graph"]["nodes"]
    field_nodes = [node for node in nodes if node["id"].startswith("DataField:")]

    assert not any("xx" in node["id"].lower() for node in field_nodes)
    assert not any(any(token in node["id"] for token in ("近xx", "近x")) for node in field_nodes)
    assert any("近一年" in node["id"] for node in field_nodes)
    assert any("近三年" in node["id"] for node in field_nodes)
    assert any("成立以来" in node["id"] for node in field_nodes)

    expanded = next(node for node in field_nodes if "dws_fund_perf_1y" in node["id"] and "近一年" in node["id"])
    params = expanded["params"]
    assert params["is_expanded_from_period_template"] is True
    assert params["template_source_table"]
    assert params["template_source_field"]
    assert params["period_code"] == "1y"
    assert params["period_name_zh"] == "近一年"


def test_edges_expanded():
    payload = _payload()
    edges = payload["graph"]["edges"]
    edge_ids = {edge["edge_id"] for edge in edges}

    assert any(
        edge["from"] == "Attribute:return_rate"
        and edge["relation_type"] == "mapped_to_field"
        and edge["to"].startswith("DataField:dws_fund_perf_1y.")
        for edge in edges
    )
    assert any(
        edge["from"] == "Attribute:max_drawdown"
        and edge["relation_type"] == "mapped_to_field"
        and "_1y." in edge["to"]
        for edge in edges
    )
    assert (
        "QueryCapability:fund_perf_interval_query__reads_from__DataTable:dws_fund_perf_1y"
        in edge_ids
    )
    assert (
        "QueryCapability:fund_risk_interval_query__reads_from__DataTable:dws_fund_risk_ret_1y"
        in edge_ids
    )
    assert not any("xx" in edge["edge_id"].lower() for edge in edges)
    assert not any(any(token in edge["edge_id"] for token in ("_xx", "retxx", "近xx", "近x")) for edge in edges)


def test_runtime_no_xx_in_compact_output():
    result = retrieve(frame())
    text = json.dumps(result, ensure_ascii=False)

    assert result["status"] == "success"
    assert "_xx" not in text
    assert "retxx" not in text
    assert "近xx" not in text
    assert "近x" not in text


def test_runtime_period_specific_tables():
    result = retrieve(frame(), debug=True)

    assert result["semantic_frame_summary"]["constraints"]["period"] == "1y"
    assert "debug_evidence" in result
    assert all(node["node_type"] not in {"DataTable", "DataField"} for node in result["task_graph"]["nodes"])


def test_runtime_period_3y():
    result = retrieve(
        frame(
            raw_question="分析000001近三年的表现",
            constraints={"period": "3y"},
        ),
        debug=True,
    )

    assert result["semantic_frame_summary"]["constraints"]["period"] == "3y"
    assert all(item["constraints"]["period"] == "3y" for item in result["fact_requirements"])


def test_no_unconfirmed_physical_claim():
    payload = _payload()
    table = next(node for node in payload["graph"]["nodes"] if node["id"] == "DataTable:dws_fund_perf_1y")
    field = next(node for node in payload["graph"]["nodes"] if node["id"].startswith("DataField:dws_fund_perf_1y.") and "近一年" in node["id"])

    assert table["params"]["physical_table_name"] is None
    assert table["params"]["physical_resolution_required"] is True
    assert field["params"]["physical_field_name"] is None
    assert field["params"]["physical_resolution_required"] is True


class CatalogRepository:
    def __init__(self) -> None:
        self.catalog = load_ontology(PROJECT_ROOT / "ontology")
        self.attributes = {item["attribute_name"]: item for item in self.catalog.attributes}

    def ping(self) -> None:
        return None

    def domain_enabled(self, domain: str) -> bool:
        return domain == DOMAIN

    def get_objects_by_ids(self, domain: str, object_ids: list[str]) -> list[dict[str, Any]]:
        return []

    def get_attributes_by_names(self, domain: str, names: list[str]) -> list[dict[str, Any]]:
        rows = []
        for name in names:
            item = self.attributes.get(name)
            if item:
                rows.append(
                    {
                        "object_type": (item.get("object_types") or [""])[0],
                        "attribute_name": item["attribute_name"],
                        "attribute_name_zh": item["attribute_name_zh"],
                        "aliases": item.get("aliases", []),
                    }
                )
        return rows

    def get_query_capabilities(self, domain: str) -> list[dict[str, Any]]:
        return [item for item in self.catalog.queries if item.get("enabled", True)]

    def get_skill_capabilities(self, domain: str) -> list[dict[str, Any]]:
        return [item for item in self.catalog.skills if item.get("enabled", True)]

    def get_intent_profiles(self, domain: str) -> list[dict[str, Any]]:
        return [item for item in self.catalog.intent_profiles if item.get("enabled", True)]


class EmptyTextRepository:
    def ping(self) -> None:
        return None

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return []

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return []


class PayloadGraphRepository:
    def __init__(self) -> None:
        self.edges = _payload()["graph"]["edges"]

    def ping(self) -> None:
        return None

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        del domain, max_hops
        return [dict(edge) for edge in self.edges[:top_k]] if entities else []

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        del domain, entities, max_hops, top_k
        return []


def _service() -> OAGContextService:
    return OAGContextService(
        ontology_repository=CatalogRepository(),
        text_repository=EmptyTextRepository(),
        graph_repository=PayloadGraphRepository(),
    )
