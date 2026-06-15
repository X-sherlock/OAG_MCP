from __future__ import annotations

import copy
from dataclasses import replace

from oag_ontology_loader.loader import load_ontology
from oag_mcp.fact_planner import FactPlanner
from oag_mcp.ontology_diagnostics import diagnose_ontology
from oag_task_planner_helpers import PROJECT_ROOT, CatalogRepository, SchemaGraphRepository, frame, retrieve


def test_relation_expansion_policy():
    result = retrieve(
        frame(
            raw_question="000001近一年收益怎么样",
            task_type="analyze",
            intent="performance_overview",
            mentioned_attributes=["return_rate"],
        )
    )

    expanded = [item for item in result["fact_requirements"] if item["source"] == "relation_expansion"]
    expanded_attrs = {item["attribute_name"] for item in expanded}

    assert {"benchmark_return", "excess_return"}.issubset(expanded_attrs)
    assert len([item for item in expanded if item.get("expanded_from", {}).get("source_attribute") == "return_rate"]) <= 3
    assert len(expanded) <= 8
    assert all(item["reason_zh"] for item in expanded)

    screen_result = retrieve(
        frame(task_type="screen", intent="performance_overview", mentioned_attributes=["return_rate"])
    )
    screen_expanded_attrs = {
        item["attribute_name"]
        for item in screen_result["fact_requirements"]
        if item["source"] == "relation_expansion"
    }
    assert "benchmark_return" not in screen_expanded_attrs
    assert "excess_return" not in screen_expanded_attrs


def test_relation_instance_fund_manager():
    result = retrieve(
        frame(
            raw_question="查询000001的基金经理",
            task_type="query",
            intent=None,
            mentioned_attributes=["fund_manager"],
        )
    )

    relation_fact = next(item for item in result["fact_requirements"] if item["fact_type"] == "relation_instance")
    assert relation_fact["predicate"] == "managed_by"
    assert relation_fact["target_object_type"] == "FundManager"
    assert relation_fact["priority"] == "required"
    assert "基金经理" in relation_fact["reason_zh"]
    assert any(
        item["skill_id"] == "get_fund_profile_facts"
        and relation_fact["fact_requirement_id"] in item["covers_fact_requirements"]
        for item in result["candidate_invocations"]
    )
    assert any(
        edge["source"] == "ObjectType:Fund"
        and edge["target"] == "ObjectType:FundManager"
        and edge["relation_type"] == "managed_by"
        for edge in result["task_graph"]["edges"]
    )


def test_explicit_risk_metric_query_does_not_expand_profile_objects():
    result = retrieve(
        frame(
            raw_question="查询000001近一年最大回撤和夏普",
            task_type="analyze",
            intent="risk_overview",
            mentioned_attributes=["max_drawdown", "sharpe_ratio"],
        )
    )

    required = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "required"
    }
    optional = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "optional"
    }
    relation_answer_facts = [
        item
        for item in result["fact_requirements"]
        if item.get("fact_type") == "relation_instance" and item.get("answer_visibility") == "answer_fact"
    ]
    object_nodes = {node["node_id"] for node in result["task_graph"]["nodes"] if node.get("node_type") == "ObjectType"}

    assert required == {"max_drawdown", "sharpe_ratio"}
    assert {"volatility", "calmar_ratio", "peer_drawdown_rank", "peer_sharpe_rank"}.issubset(optional)
    assert not relation_answer_facts
    assert {
        "ObjectType:FundManager",
        "ObjectType:FundCompany",
        "ObjectType:FundFee",
        "ObjectType:Dividend",
        "ObjectType:FundPosition",
        "ObjectType:AssetAllocation",
    }.isdisjoint(object_nodes)


def test_benchmark_comparison_uses_benchmark_as_supporting_context():
    result = retrieve(frame(raw_question="000001近一年有没有跑赢基准", intent="benchmark_comparison"))

    required = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "required"
    }
    benchmark_relation = next(
        item for item in result["fact_requirements"] if item.get("predicate") == "has_benchmark"
    )
    object_nodes = {node["node_id"] for node in result["task_graph"]["nodes"] if node.get("node_type") == "ObjectType"}

    assert {"return_rate", "benchmark_return", "excess_return"}.issubset(required)
    assert benchmark_relation["answer_visibility"] == "supporting_context"
    assert benchmark_relation["priority"] == "supporting"
    assert {"ObjectType:FundManager", "ObjectType:FundCompany", "ObjectType:FundFee", "ObjectType:Dividend"}.isdisjoint(object_nodes)


def test_peer_comparison_uses_category_as_supporting_context():
    result = retrieve(
        frame(raw_question="000001近一年同类排名怎么样", task_type="compare", intent="peer_comparison")
    )

    required = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "required"
    }
    category_relation = next(
        item for item in result["fact_requirements"] if item.get("predicate") == "belongs_to_category"
    )
    object_nodes = {node["node_id"] for node in result["task_graph"]["nodes"] if node.get("node_type") == "ObjectType"}

    assert {"rank", "percentile"}.issubset(required)
    assert category_relation["answer_visibility"] == "supporting_context"
    assert category_relation["priority"] != "required"
    assert {"ObjectType:FundManager", "ObjectType:FundCompany"}.isdisjoint(object_nodes)


def test_relation_instance_fund_company():
    result = retrieve(
        frame(
            raw_question="000001是哪家公司管理的",
            task_type="query",
            intent=None,
            mentioned_attributes=["fund_company"],
        )
    )

    relation_fact = next(item for item in result["fact_requirements"] if item["fact_type"] == "relation_instance")
    assert relation_fact["predicate"] in {"issued_by", "managed_by_company"}
    assert relation_fact["target_object_type"] == "FundCompany"
    assert relation_fact["priority"] == "required"
    assert any(
        item["skill_id"] == "get_fund_profile_facts"
        and relation_fact["fact_requirement_id"] in item["covers_fact_requirements"]
        for item in result["candidate_invocations"]
    )


def test_profile_skill_supported_attributes_exist():
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    known_attributes = {item["attribute_name"] for item in catalog.attributes}
    profile_skill = next(item for item in catalog.skills if item["skill_id"] == "get_fund_profile_facts")

    assert set(profile_skill["supported_attributes"]).issubset(known_attributes)
    assert {"managed_by", "issued_by", "has_benchmark", "belongs_to_category", "tracks_index"}.issubset(
        set(profile_skill["supported_relations"])
    )


def test_skill_coverage_reason():
    result = retrieve(frame())

    invocation = next(item for item in result["candidate_invocations"] if item["skill_id"] == "get_fund_metric_values")
    assert isinstance(invocation["coverage_score"], float)
    assert invocation["coverage_score"] > 0
    assert invocation["coverage_reason_zh"]
    assert invocation["covers_required_count"] > 0
    assert result["coverage_summary"]["covered_required_fact_count"] == result["coverage_summary"]["required_fact_count"]


def test_coverage_summary_status():
    full = retrieve(frame())
    assert full["coverage_summary"]["coverage_status"] == "full_coverage"

    catalog = load_ontology(PROJECT_ROOT / "ontology")
    metric_skill = next(item for item in catalog.skills if item["skill_id"] == "get_fund_metric_values")
    partial = FactPlanner(
        ontology_repository=CatalogRepository(),
        graph_repository=SchemaGraphRepository(),
        skills=[metric_skill],
    ).plan(
        semantic_frame=frame(),
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )
    assert partial["coverage_summary"]["coverage_status"] == "partial_coverage"

    clarify = retrieve(frame(intent="not_configured_intent", mentioned_attributes=[]))
    assert clarify["coverage_summary"]["coverage_status"] == "need_clarification"


def test_task_graph_chinese_labels():
    result = retrieve(frame())

    assert all(node.get("label_zh") and node.get("role") for node in result["task_graph"]["nodes"])
    assert all(edge.get("label_zh") and edge.get("reason_zh") for edge in result["task_graph"]["edges"])
    assert not any(node["label_zh"] in {"analyze", "period"} for node in result["task_graph"]["nodes"])
    assert any(edge["relation_type"] == "compared_with" for edge in result["task_graph"]["edges"])
    assert any(edge["relation_type"] == "covered_by_skill" for edge in result["task_graph"]["edges"])


def test_ontology_diagnostics():
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    broken_intents = copy.deepcopy(catalog.intent_profiles)
    broken_intents.append(
        {
            "intent_name": "broken_intent",
            "trigger_aliases": [],
            "default_attributes": [],
            "primary_skills": [],
            "secondary_skills": [],
            "optional_skills": [],
            "required_params": [],
            "enabled": True,
        }
    )
    broken_skills = copy.deepcopy(catalog.skills)
    broken_skills.append(
        {
            "skill_id": "broken_skill",
            "skill_name": "破损 Skill",
            "description": "用于诊断测试。",
            "target_object_type": "Fund",
            "input_params": [],
            "output_attributes": [],
            "related_queries": [],
            "permission_scope": "fund_public_data:read",
            "enabled": True,
        }
    )
    broken_edges = copy.deepcopy(catalog.schema_graph_edges)
    broken_edges.append(
        {
            "edge_id": "Attribute:return_rate__compared_with__Attribute:not_exists",
            "from": "Attribute:return_rate",
            "to": "Attribute:not_exists",
            "relation_type": "compared_with",
            "score": 0.5,
        }
    )

    broken_catalog = replace(
        catalog,
        intent_profiles=broken_intents,
        skills=broken_skills,
        schema_graph_edges=broken_edges,
    )
    diagnostics = diagnose_ontology(broken_catalog)
    types = {item["diagnostic_type"] for item in diagnostics}

    assert "intent_missing_fact_requirements_template" in types
    assert "skill_missing_supported_attributes" in types
    assert "semantic_edge_missing_reason_zh" in types
    assert "relation_edge_unknown_node" in types
    assert all(item["diagnostic_message_zh"] and item["suggested_action_zh"] for item in diagnostics)
