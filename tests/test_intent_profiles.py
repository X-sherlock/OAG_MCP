from __future__ import annotations

from typing import Any

from oag_ontology_loader.loader import load_ontology
from oag_mcp.service import OAGContextService


DOMAIN = "finance_market"


class CatalogOntologyRepository:
    def __init__(self) -> None:
        self.catalog = load_ontology("ontology")
        self.attributes = {
            item["attribute_name"]: item for item in self.catalog.attributes
        }

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


class IntentTextRepository:
    def ping(self) -> None:
        return None

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return []

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        if "最大回撤" not in question:
            return []
        return [
            {
                "object_type": "RiskMetric",
                "attribute_name": "max_drawdown",
                "attribute_name_zh": "最大回撤",
                "aliases": ["最大回撤", "回撤"],
                "_score": 4.0,
            }
        ]


class IntentGraphRepository:
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
                "edges": [
                    edge
                    for edge in _schema_edges()
                    if edge["relation_type"] in {"reads_from", "mapped_to_field"}
                ][:2],
                "score": 0.95,
            }
        ][:top_k]


def service() -> OAGContextService:
    return OAGContextService(
        ontology_repository=CatalogOntologyRepository(),
        text_repository=IntentTextRepository(),
        graph_repository=IntentGraphRepository(),
    )


def _schema_edges() -> list[dict[str, Any]]:
    edges = [
        _edge("QueryCapability:fund_perf_interval_query", "targets_object_type", "ObjectType:Fund"),
        _edge("QueryCapability:fund_perf_interval_query", "reads_from", "DataTable:dws_fund_perf_1y"),
        _edge("QueryCapability:fund_perf_interval_query", "requires_param", "Parameter:fund_code"),
        _edge("QueryCapability:fund_perf_interval_query", "requires_param", "Parameter:period"),
        _edge("QueryCapability:fund_perf_interval_query", "returns_attribute", "Attribute:return_rate"),
        _edge("QueryCapability:fund_perf_interval_query", "returns_attribute", "Attribute:max_drawdown"),
        _edge("Attribute:return_rate", "mapped_to_field", "DataField:dws_fund_perf_1y.return_rate"),
        _edge("Attribute:max_drawdown", "mapped_to_field", "DataField:dws_fund_risk_ret_1y.max_drawdown"),
        _edge("DataTable:dws_fund_perf_1y", "has_field", "DataField:dws_fund_perf_1y.return_rate"),
        _edge("QueryCapability:fund_risk_interval_query", "reads_from", "DataTable:dws_fund_risk_ret_1y"),
        _edge("QueryCapability:fund_risk_interval_query", "returns_attribute", "Attribute:volatility"),
        _edge("QueryCapability:fund_risk_interval_query", "returns_attribute", "Attribute:sharpe_ratio"),
        _edge("QueryCapability:fund_benchmark_compare_query", "reads_from", "DataTable:dws_bm_perf_1y"),
        _edge("QueryCapability:fund_benchmark_compare_query", "returns_attribute", "Attribute:benchmark_return"),
        _edge("QueryCapability:fund_benchmark_compare_query", "returns_attribute", "Attribute:excess_return"),
        _edge("QueryCapability:fund_peer_ranking_query", "reads_from", "DataTable:DWD_FUND_NAV_GRTH"),
        _edge("QueryCapability:fund_peer_ranking_query", "returns_attribute", "Attribute:rank"),
        _edge("QueryCapability:fund_peer_ranking_query", "returns_attribute", "Attribute:percentile"),
    ]
    return edges


def _edge(from_node: str, relation_type: str, to_node: str) -> dict[str, Any]:
    return {
        "from": from_node,
        "relation_type": relation_type,
        "to": to_node,
        "score": 0.95,
    }


def _skill_priorities(result: dict[str, Any]) -> dict[str, str]:
    return {
        item["skill_id"]: item["priority"]
        for item in result["candidate_invocations"]
        if item.get("capability_type") == "skill"
    }


def _attribute_reasons(result: dict[str, Any]) -> dict[str, str]:
    return {
        item["attribute_name"]: item["match_reason"]
        for item in result["matched_attributes"]
    }


def _node_ids(result: dict[str, Any]) -> set[str]:
    return {item["node_id"] for item in result["relation_subgraph"]["nodes"]}


def _edge_types(result: dict[str, Any]) -> set[str]:
    return {item["relation_type"] for item in result["relation_subgraph"]["edges"]}


def test_performance_overview_infers_attributes_and_skill_priorities():
    result = service().retrieve_context(
        question="分析000001近一年的表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["resolved_params"]["fund_code"] == "000001"
    assert result["resolved_params"]["period"] == "1y"
    assert result["matched_objects"][0]["object_id"] == "Fund"
    assert {item["intent_name"] for item in result["matched_intents"]} >= {
        "performance_overview"
    }
    attribute_names = {item["attribute_name"] for item in result["matched_attributes"]}
    assert {"return_rate", "max_drawdown"}.issubset(attribute_names)
    priorities = _skill_priorities(result)
    assert priorities["get_fund_metric_values"] == "primary"
    assert priorities["get_fund_benchmark_facts"] == "secondary"
    assert priorities["get_fund_peer_ranking_facts"] == "optional"
    full = service().retrieve_context(
        question="分析000001近一年的表现",
        user_context={"permission_scopes": ["fund_public_data:read"], "detail_level": "full", "debug": True},
    )
    assert {"Attribute:return_rate", "Attribute:max_drawdown", "DataTable:dws_fund_perf_1y"}.issubset(
        _node_ids(full)
    )
    assert {"mapped_to_field", "reads_from"}.issubset(_edge_types(full))


def test_risk_overview_prioritizes_risk_skill():
    result = service().retrieve_context(
        question="分析000001近一年的风险表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["matched_intents"][0]["intent_name"] == "risk_overview"
    attribute_names = {item["attribute_name"] for item in result["matched_attributes"]}
    assert {"max_drawdown", "volatility", "sharpe_ratio"}.issubset(attribute_names)
    assert _skill_priorities(result)["get_fund_metric_values"] == "primary"


def test_benchmark_comparison_prioritizes_benchmark_skill():
    result = service().retrieve_context(
        question="000001近一年有没有跑赢基准",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["matched_intents"][0]["intent_name"] == "benchmark_comparison"
    attribute_names = {item["attribute_name"] for item in result["matched_attributes"]}
    assert {"excess_return", "benchmark_return"}.issubset(attribute_names)
    assert _skill_priorities(result)["get_fund_benchmark_facts"] == "primary"


def test_peer_comparison_prioritizes_peer_skill():
    result = service().retrieve_context(
        question="000001近一年同类排名怎么样",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["matched_intents"][0]["intent_name"] == "peer_comparison"
    attribute_names = {item["attribute_name"] for item in result["matched_attributes"]}
    assert {"rank", "percentile"}.intersection(attribute_names)
    assert _skill_priorities(result)["get_fund_peer_ranking_facts"] == "primary"


def test_explicit_attribute_match_reason_is_not_overwritten_by_intent():
    result = service().retrieve_context(
        question="分析000001近一年最大回撤",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    reasons = _attribute_reasons(result)
    assert reasons["max_drawdown"] == "alias_matched"
    assert _skill_priorities(result)["get_fund_metric_values"] == "primary"
