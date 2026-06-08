from __future__ import annotations

import json
from typing import Any

from oag_ontology_loader.loader import load_ontology
from oag_mcp.service import OAGContextService


DOMAIN = "finance_market"


class CatalogRepository:
    def __init__(self) -> None:
        self.catalog = load_ontology("ontology")
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
            if not item:
                continue
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


class SchemaGraphRepository:
    def ping(self) -> None:
        return None

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        return _schema_edges()[:top_k]

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        return [
            {
                "path": [
                    "ObjectType:Fund",
                    "QueryCapability:fund_perf_interval_query",
                    "DataTable:dws_fund_perf_1y",
                    "DataField:dws_fund_perf_1y.return_rate",
                ],
                "edges": _schema_edges()[:3],
                "score": 0.95,
            }
        ][:top_k]


def service() -> OAGContextService:
    return OAGContextService(
        ontology_repository=CatalogRepository(),
        text_repository=EmptyTextRepository(),
        graph_repository=SchemaGraphRepository(),
    )


def retrieve(question: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    user_context = {"permission_scopes": ["fund_public_data:read"], **(context or {})}
    return service().retrieve_context(question, user_context)


def test_compact_fact_requirements_for_performance_overview():
    result = retrieve("分析000001近一年的表现")

    assert result["status"] == "success"
    assert result["resolved_params"]["fund_code"] == "000001"
    assert result["resolved_params"]["period"] == "1y"
    assert result["target_instances"][0]["object_type"] == "Fund"
    assert result["target_instances"][0]["instance_ref"] == {"fund_code": "000001"}

    requirement_ids = {item["fact_requirement_id"] for item in result["fact_requirements"]}
    assert {
        "fr_return_rate_1y",
        "fr_benchmark_return_1y",
        "fr_excess_return_1y",
        "fr_max_drawdown_1y",
        "fr_volatility_1y",
        "fr_sharpe_ratio_1y",
        "fr_rank_1y",
    }.issubset(requirement_ids)
    for requirement in result["fact_requirements"]:
        assert requirement["fact_type"]
        assert requirement["subject"]
        assert requirement["predicate"]
        assert requirement["attribute"]
        assert requirement["constraints"]["period"] == "1y"
        assert requirement["priority"]
        assert requirement["reason"]


def test_candidate_invocations_cover_fact_requirements():
    result = retrieve("分析000001近一年的表现")
    requirement_ids = {item["fact_requirement_id"] for item in result["fact_requirements"]}
    required_ids = {
        item["fact_requirement_id"]
        for item in result["fact_requirements"]
        if item["priority"] == "required"
    }
    invocations = result["candidate_invocations"]

    assert {item["skill_id"] for item in invocations} >= {
        "get_fund_metric_values",
        "get_fund_benchmark_facts",
        "get_fund_peer_ranking_facts",
    }
    covered_ids = set()
    for invocation in invocations:
        assert invocation["covers_fact_requirements"]
        assert set(invocation["covers_fact_requirements"]).issubset(requirement_ids)
        covered_ids.update(invocation["covers_fact_requirements"])
    assert required_ids.issubset(covered_ids)


def test_compact_output_no_table_field_evidence():
    result = retrieve("分析000001近一年的表现")
    text = json.dumps(result, ensure_ascii=False)

    assert "matched_relations" not in result
    assert "relation_paths" not in result
    assert "relation_subgraph" not in result
    assert "candidate_queries" not in result
    assert "main_tables" not in result["retrieval_summary"]
    assert "DataTable:" not in text
    assert "DataField:" not in text
    assert "source_tables" not in text


def test_full_debug_keeps_schema_evidence():
    result = retrieve(
        "分析000001近一年的表现",
        {"detail_level": "full", "debug": True},
    )

    assert "schema_evidence" in result
    assert result["relation_subgraph"]["nodes"]
    assert any(
        node["object_type"] in {"DataTable", "DataField"}
        for node in result["relation_subgraph"]["nodes"]
    )
    assert result["matched_relations"]
    assert result["relation_paths"]


def test_missing_fund_code_fact_requirements():
    result = retrieve("分析这只基金近一年的表现")

    assert result["fact_requirements"]
    assert result["target_instances"] == []
    assert any("fund_code" in item["missing_params"] for item in result["missing_params"])
    assert all(
        "fund_code" in invocation["missing_params"]
        for invocation in result["candidate_invocations"]
        if invocation["covers_fact_requirements"]
    )
    assert "fund_code" not in result["resolved_params"]


def test_risk_overview_fact_requirements():
    result = retrieve("分析000001近一年的风险表现")

    assert result["matched_intents"][0]["intent_name"] == "risk_overview"
    required_attrs = {
        item["attribute"]["attribute_name"]
        for item in result["fact_requirements"]
        if item["priority"] == "required"
    }
    assert {"max_drawdown", "volatility", "sharpe_ratio"}.issubset(required_attrs)
    metric_invocation = next(
        item for item in result["candidate_invocations"] if item["skill_id"] == "get_fund_metric_values"
    )
    assert {"max_drawdown", "volatility", "sharpe_ratio"}.issubset(
        set(metric_invocation["params"]["attributes"])
    )


def test_benchmark_comparison_fact_requirements():
    result = retrieve("000001近一年有没有跑赢基准")
    attrs = {item["attribute"]["attribute_name"] for item in result["fact_requirements"]}

    assert {"return_rate", "benchmark_return", "excess_return"}.issubset(attrs)
    assert any(
        item["skill_id"] == "get_fund_benchmark_facts"
        for item in result["candidate_invocations"]
    )


def test_peer_comparison_fact_requirements():
    result = retrieve("000001近一年同类排名怎么样")
    attrs = {item["attribute"]["attribute_name"] for item in result["fact_requirements"]}

    assert "rank" in attrs
    assert any(
        item["skill_id"] == "get_fund_peer_ranking_facts"
        for item in result["candidate_invocations"]
    )


def _schema_edges() -> list[dict[str, Any]]:
    return [
        _edge("QueryCapability:fund_perf_interval_query", "targets_object_type", "ObjectType:Fund"),
        _edge("QueryCapability:fund_perf_interval_query", "reads_from", "DataTable:dws_fund_perf_1y"),
        _edge("Attribute:return_rate", "mapped_to_field", "DataField:dws_fund_perf_1y.return_rate"),
        _edge("QueryCapability:fund_benchmark_compare_query", "reads_from", "DataTable:dws_bm_perf_1y"),
        _edge("QueryCapability:fund_peer_ranking_query", "reads_from", "DataTable:dwd_fund_nav_grth"),
    ]


def _edge(from_node: str, relation_type: str, to_node: str) -> dict[str, Any]:
    return {
        "edge_id": f"{from_node}__{relation_type}__{to_node}",
        "from": from_node,
        "relation_type": relation_type,
        "to": to_node,
        "score": 0.95,
    }
