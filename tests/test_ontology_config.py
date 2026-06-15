from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from oag_ontology_loader.loader import load_ontology
from oag_ontology_loader.validator import OntologyValidationError, validate_section


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ontology_yaml_loads_and_sections_are_not_empty():
    # 本体目录的所有分区都必须可加载且非空，这是服务启动的最低前置条件。
    catalog = load_ontology(PROJECT_ROOT / "ontology")

    assert catalog.object_types
    assert catalog.attributes
    assert catalog.relation_types
    assert catalog.fact_types
    assert catalog.queries
    assert catalog.skills
    assert catalog.data_sources
    assert catalog.instance_rules
    assert catalog.table_schemas
    assert catalog.schema_graph_edges
    assert catalog.intent_profiles
    assert catalog.sample_instances
    assert catalog.sample_graph_edges
    assert catalog.demo_instances == catalog.sample_instances
    assert catalog.demo_graph_edges == catalog.sample_graph_edges


def test_validator_reports_missing_required_fields_clearly():
    # 缺字段错误要包含分区、条目标识和字段名，方便维护者修复 YAML。
    with pytest.raises(OntologyValidationError) as exc:
        validate_section("attributes", [{"attribute_name": "return_rate"}])

    message = str(exc.value)
    assert "attributes.yaml item return_rate missing required fields" in message
    assert "attribute_name_zh" in message


def test_attribute_catalog_contains_required_business_attributes():
    # 这些基金分析核心属性必须存在，否则示例问题无法匹配到查询输出。
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    names = {item["attribute_name"] for item in catalog.attributes}

    assert {"return_rate", "max_drawdown", "sharpe_ratio", "fund_size", "holding_industry"}.issubset(names)
    assert {"rank", "percentile", "downside_deviation"}.issubset(names)


def test_intent_profile_catalog_contains_required_profiles():
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    profiles = {item["intent_name"]: item for item in catalog.intent_profiles}

    assert {
        "performance_overview",
        "risk_overview",
        "benchmark_comparison",
        "peer_comparison",
    }.issubset(profiles)
    assert "表现" in profiles["performance_overview"]["trigger_aliases"]
    assert "return_rate" in profiles["performance_overview"]["default_attributes"]
    assert profiles["performance_overview"]["primary_skills"] == ["get_fund_metric_values"]


def test_relation_catalog_contains_required_relations():
    # 关系类型是图召回的基础，缺失会导致 relation_subgraph 不完整。
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    names = {item["relation_type"] for item in catalog.relation_types}

    assert {
        "managed_by",
        "compared_with",
        "derives",
        "ranked_by_peer",
        "risk_companion",
        "has_benchmark",
        "has_performance_metric",
        "has_risk_metric",
        "holds_industry",
        "has_asset_allocation",
    }.issubset(names)


def test_query_catalog_contains_required_queries():
    # 结构化查询能力决定 candidate_queries 是否能覆盖主要基金分析场景。
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    query_ids = {item["query_id"] for item in catalog.queries}

    assert {
        "fund_perf_interval_query",
        "fund_risk_interval_query",
        "fund_industry_allocation_query",
        "fund_asset_allocation_query",
    }.issubset(query_ids)


def test_disabled_unstructured_queries_and_skills_load_but_are_not_enabled():
    # 未接入的数据能力仍应能加载到目录，但不能出现在 enabled_* 结果中。
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    disabled_queries = {item["query_id"] for item in catalog.queries if not item["enabled"]}
    disabled_skills = {item["skill_id"] for item in catalog.skills if not item["enabled"]}

    assert {"fund_related_report_query", "fund_related_news_query", "policy_impact_query"}.issubset(disabled_queries)
    assert {"fund_report_summary", "fund_news_impact_analysis", "policy_impact_analysis"}.issubset(disabled_skills)
    assert disabled_queries.isdisjoint({item["query_id"] for item in catalog.enabled_queries()})
    assert disabled_skills.isdisjoint({item["skill_id"] for item in catalog.enabled_skills()})


def test_seed_ontology_uses_ontology_payloads_without_hardcoded_catalog_lists():
    # 种子脚本必须从 ontology 文件读取目录，避免源码里重新维护一份硬编码清单。
    source = (PROJECT_ROOT / "scripts" / "seed_ontology.py").read_text(encoding="utf-8")
    assert "OBJECTS = [" not in source
    assert "ATTRIBUTES = [" not in source
    assert "QUERIES = [" not in source
    assert "SKILLS = [" not in source
    assert "GRAPH = {" not in source

    spec = importlib.util.spec_from_file_location(
        "seed_ontology", PROJECT_ROOT / "scripts" / "seed_ontology.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    payloads = module.load_seed_payloads(PROJECT_ROOT / "ontology")
    assert payloads["objects"]
    object_ids = {item["object_id"] for item in payloads["objects"]}
    assert {
        "Fund",
        "FundCompany",
        "FundManager",
        "PerformanceMetric",
        "RiskMetric",
    }.issubset(object_ids)
    assert all(item["object_type"] == "ObjectType" for item in payloads["objects"])
    assert "003095" not in object_ids
    assert payloads["attributes"]
    assert payloads["queries"]
    assert payloads["skills"]
    assert payloads["intent_profiles"]
    assert payloads["graph"]["nodes"]
    assert payloads["graph"]["edges"]
    assert len(payloads["graph"]["nodes"]) > 12
    assert len(payloads["graph"]["edges"]) > 10
    node_ids = {item["id"] for item in payloads["graph"]["nodes"]}
    edge_ids = {item["edge_id"] for item in payloads["graph"]["edges"]}
    assert "FactType:metric_value" in node_ids
    assert "Fund:003095" not in node_ids
    assert not any("Fund:003095" in edge_id for edge_id in edge_ids)
    assert {
        "DataTable:dim_fund_info",
        "DataTable:DWD_FUND_NAV",
        "DataTable:dws_fund_perf_1y",
        "DataTable:DWD_FUND_ASET_ALLOC",
        "Attribute:return_rate",
        "Attribute:max_drawdown",
    }.issubset(node_ids)
    assert "DataTable:dws_fund_perf_xx" not in node_ids
    assert "DataTable:DWD_FUND_NAV__has_field__DataField:DWD_FUND_NAV.基金单位净值" in edge_ids
    disabled = [item for item in payloads["queries"] if item["query_id"] == "fund_related_report_query"]
    assert disabled and disabled[0]["enabled"] is False

    with_sample = module.load_seed_payloads(PROJECT_ROOT / "ontology", include_sample=True)
    assert with_sample["objects"]
    assert "Fund:003095" in {item["id"] for item in with_sample["graph"]["nodes"]}
