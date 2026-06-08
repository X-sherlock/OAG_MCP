from __future__ import annotations

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


class NoisyTextRepository:
    def ping(self) -> None:
        return None

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return [
            {
                "domain": domain,
                "object_type": "DataField",
                "object_id": "DWS FUND RISK xx.年",
                "object_name": "年",
                "aliases": ["年"],
                "_score": 10.0,
                "params": {},
            }
        ]

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return []


class NoisyGraphRepository:
    def ping(self) -> None:
        return None

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        return _noisy_edges()[:top_k]

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        paths = [
            {
                "path": [
                    "ObjectType:Fund",
                    "QueryCapability:fund_perf_interval_query",
                    "DataTable:dws_fund_perf_xx",
                    "DataField:dws_fund_perf_xx.区间回报（近xx)",
                ],
                "edges": [
                    _edge("QueryCapability:fund_perf_interval_query", "reads_from", "DataTable:dws_fund_perf_xx"),
                    _edge("Attribute:return_rate", "mapped_to_field", "DataField:dws_fund_perf_xx.区间回报（近xx)"),
                ],
                "score": 0.98,
            }
        ]
        for field in _period_noise_fields() + _enum_noise_fields():
            paths.append(
                {
                    "path": ["ObjectType:Fund", "DataTable:dim_fund_info", field],
                    "edges": [
                        _edge("ObjectType:Fund", "sourced_from_table", "DataTable:dim_fund_info"),
                        _edge("DataTable:dim_fund_info", "has_field", field),
                    ],
                    "score": 0.7,
                }
            )
        for idx in range(40):
            paths.append(
                {
                    "path": [
                        "Attribute:return_rate",
                        f"DataField:DWD_FUND_NAV_GRTH.收益率(一周)-{idx}",
                    ],
                    "edges": [
                        _edge(
                            "Attribute:return_rate",
                            "mapped_to_field",
                            f"DataField:DWD_FUND_NAV_GRTH.收益率(一周)-{idx}",
                        )
                    ],
                    "score": 0.6,
                }
            )
        return paths[:top_k]


def service() -> OAGContextService:
    return OAGContextService(
        ontology_repository=CatalogRepository(),
        text_repository=NoisyTextRepository(),
        graph_repository=NoisyGraphRepository(),
    )


def result(user_context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = {"permission_scopes": ["fund_public_data:read"], **(user_context or {})}
    return service().retrieve_context("分析000001近一年的表现", context)


def test_compact_output_budget():
    item = result()

    assert "matched_relations" not in item
    assert "relation_paths" not in item
    assert "relation_subgraph" not in item
    assert "candidate_queries" not in item
    assert item["fact_requirements"]
    assert "truncation" in item


def test_no_datafield_in_matched_objects():
    item = result()

    assert all(obj["object_type"] != "DataField" for obj in item["matched_objects"])
    assert all("DWS FUND RISK xx.年" not in obj["object_id"] for obj in item["matched_objects"])


def test_period_aware_field_filter():
    item = result({"detail_level": "full", "debug": True})
    fields = [
        node["object_id"]
        for node in item["relation_subgraph"]["nodes"]
        if node["object_type"] == "DataField"
    ]

    assert any(("近xx" in field or "一年" in field or "近一年" in field) for field in fields)
    assert fields


def test_relation_paths_budget():
    item = result({"detail_level": "full", "debug": True})

    assert len(item["relation_paths"]) <= 80


def test_retrieval_summary():
    summary = result()["retrieval_summary"]

    assert "Fund" in summary["main_object_types"]
    assert "return_rate" in summary["main_attributes"]
    assert "max_drawdown" in summary["main_attributes"]
    assert "metric_value" in summary["main_fact_types"]
    assert "get_fund_metric_values" in summary["main_skills"]
    assert "main_tables" not in summary
    assert summary["period"] == "1y"
    assert summary["fund_code"] == "000001"


def test_standard_and_full_modes():
    compact = result()
    standard = result({"detail_level": "standard"})
    full = result({"detail_level": "full", "debug": True})

    assert "matched_relations" not in compact
    assert "schema_evidence_summary" in standard
    assert standard["schema_evidence_summary"]["matched_relation_count"] <= 80
    assert len(full["matched_relations"]) >= standard["schema_evidence_summary"]["matched_relation_count"]
    assert "debug_info" in full
    assert all(obj["object_type"] != "DataField" for obj in full["matched_objects"])


def test_candidate_invocation_dedup():
    item = result()
    keys = [
        (
            invocation.get("skill_id"),
            tuple(
                sorted(
                    (
                        key,
                        tuple(value) if isinstance(value, list) else value,
                    )
                    for key, value in (invocation.get("params") or {}).items()
                )
            ),
        )
        for invocation in item["candidate_invocations"]
        if invocation.get("capability_type") == "skill"
    ]

    assert len(keys) == len(set(keys))
    assert len(item["candidate_invocations"]) <= 6


def _noisy_edges() -> list[dict[str, Any]]:
    edges = [
        _edge("QueryCapability:fund_perf_interval_query", "targets_object_type", "ObjectType:Fund"),
        _edge("QueryCapability:fund_perf_interval_query", "returns_attribute", "Attribute:return_rate"),
        _edge("QueryCapability:fund_perf_interval_query", "returns_attribute", "Attribute:max_drawdown"),
        _edge("QueryCapability:fund_perf_interval_query", "returns_attribute", "Attribute:benchmark_return"),
        _edge("QueryCapability:fund_perf_interval_query", "returns_attribute", "Attribute:excess_return"),
        _edge("QueryCapability:fund_perf_interval_query", "reads_from", "DataTable:dws_fund_perf_xx"),
        _edge("QueryCapability:fund_risk_interval_query", "reads_from", "DataTable:dws_fund_risk retxx"),
        _edge("QueryCapability:fund_benchmark_compare_query", "reads_from", "DataTable:dwd_fund_bm_grth_rate"),
        _edge("SkillCapability:fund_performance_analysis", "uses_query", "QueryCapability:fund_perf_interval_query"),
        _edge("SkillCapability:fund_risk_analysis", "uses_query", "QueryCapability:fund_risk_interval_query"),
        _edge("SkillCapability:fund_benchmark_compare", "uses_query", "QueryCapability:fund_benchmark_compare_query"),
        _edge("SkillCapability:fund_peer_comparison", "uses_query", "QueryCapability:fund_peer_ranking_query"),
        _edge("Attribute:return_rate", "mapped_to_field", "DataField:dws_fund_perf_xx.区间回报（近xx)"),
        _edge("Attribute:return_rate", "mapped_to_field", "DataField:DWD_FUND_NAV_GRTH.收益率(一年)"),
        _edge("Attribute:max_drawdown", "mapped_to_field", "DataField:dws_fund_perf_xx.最大回撤（近xx）"),
        _edge("Attribute:benchmark_return", "mapped_to_field", "DataField:dwd_fund_bm_grth_rate.区间收益率（近xx)"),
        _edge("Attribute:excess_return", "mapped_to_field", "DataField:dws_fund_perf_xx.净值超越基准收益率（近xx）"),
        _edge("DataTable:dws_fund_perf_xx", "has_field", "DataField:dws_fund_perf_xx.区间回报（近xx)"),
    ]
    for field in _period_noise_fields() + _enum_noise_fields():
        edges.append(_edge("DataTable:dim_fund_info", "has_field", field, score=0.9))
    for idx in range(80):
        edges.append(
            _edge(
                "Attribute:return_rate",
                "mapped_to_field",
                f"DataField:DWD_FUND_NAV_GRTH.收益率(一周)-{idx}",
                score=0.8,
            )
        )
        edges.append(
            _edge(
                "DataTable:dws_fund_perf_xx",
                "joins_on",
                f"DataTable:unrelated_table_{idx}",
                score=0.6,
            )
        )
    return edges


def _period_noise_fields() -> list[str]:
    return [
        "DataField:DWD_FUND_NAV_GRTH.收益率(一周)",
        "DataField:DWD_FUND_NAV_GRTH.收益率(一月)",
        "DataField:DWD_FUND_NAV_GRTH.收益率(三个月)",
        "DataField:DWD_FUND_NAV_GRTH.收益率(六个月)",
        "DataField:DWD_FUND_NAV_GRTH.收益率(三年)",
        "DataField:DWD_FUND_NAV_GRTH.收益率(成立以来)",
    ]


def _enum_noise_fields() -> list[str]:
    return [
        "DataField:dim_fund_info.0-非ETF",
        "DataField:dim_fund_info.1-ETF",
        "DataField:dim_fund_info.0：否；1:是",
        "DataField:dim_fund_info.1：不可售",
    ]


def _edge(from_node: str, relation_type: str, to_node: str, score: float = 0.95) -> dict[str, Any]:
    return {
        "edge_id": f"{from_node}__{relation_type}__{to_node}",
        "from": from_node,
        "relation_type": relation_type,
        "to": to_node,
        "score": score,
    }
