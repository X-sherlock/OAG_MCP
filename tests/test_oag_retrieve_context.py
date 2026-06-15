from __future__ import annotations

import json

from oag_mcp.service import error_response
from oag_task_planner_helpers import frame, retrieve, service


def test_semantic_frame_required():
    result = service().retrieve_context()

    assert result["status"] == "error"
    assert result["error_code"] == "SEMANTIC_FRAME_REQUIRED"
    assert "缺少前置意图识别节点输出" in result["message_zh"]


def test_performance_overview_task_plan():
    result = retrieve(frame())

    assert result["status"] == "success"
    attrs = {item["attribute_name"] for item in result["fact_requirements"]}
    assert {
        "return_rate",
        "benchmark_return",
        "excess_return",
        "max_drawdown",
        "volatility",
        "sharpe_ratio",
        "rank",
    }.issubset(attrs)
    assert {item["skill_id"] for item in result["candidate_invocations"]} >= {
        "get_fund_metric_values",
        "get_fund_benchmark_facts",
        "get_fund_peer_ranking_facts",
    }
    node_types = {item["node_type"] for item in result["task_graph"]["nodes"]}
    assert {"ObjectType", "Attribute", "FactRequirement", "SkillCapability"}.issubset(node_types)
    assert {"DataTable", "DataField", "QueryCapability"}.isdisjoint(node_types)


def test_explicit_attributes_take_priority_over_intent_template():
    result = retrieve(
        frame(
            raw_question="000001近一年最大回撤和夏普怎么样",
            intent="risk_overview",
            mentioned_attributes=["max_drawdown", "sharpe_ratio"],
        )
    )

    required = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item["priority"] == "required"
    }
    assert required == {"max_drawdown", "sharpe_ratio"}
    metric_invocation = next(
        item for item in result["candidate_invocations"] if item["skill_id"] == "get_fund_metric_values"
    )
    assert set(metric_invocation["params"]["attributes"]).issubset(
        {"max_drawdown", "sharpe_ratio", "volatility", "calmar_ratio"}
    )


def test_relation_expansion_from_return_rate():
    result = retrieve(
        frame(
            raw_question="000001近一年收益怎么样",
            intent=None,
            mentioned_attributes=["return_rate"],
        )
    )

    facts = {item["attribute_name"]: item for item in result["fact_requirements"]}
    assert facts["return_rate"]["priority"] == "required"
    assert facts["return_rate"]["source"] == "explicit_attribute"
    assert {"benchmark_return", "excess_return", "rank"}.intersection(facts)
    expanded = [item for item in result["fact_requirements"] if item["source"] == "relation_expansion"]
    assert expanded
    assert all(item["reason_zh"] for item in expanded)
    assert any(edge["relation_type"] == "expanded_by_relation" for edge in result["task_graph"]["edges"])


def test_recommend_task_generates_covered_fundset_facts_without_fund_code():
    result = retrieve(
        frame(
            raw_question="推荐近一年收益率高、回撤低的基金",
            task_type="recommend",
            intent=None,
            object_type="FundSet",
            instance_ref={"fund_universe": "all_public_funds"},
            role="recommendation_universe",
            ranking=[
                {"attribute": "return_rate", "direction": "desc"},
                {"attribute": "max_drawdown", "direction": "asc"},
            ],
            limit=10,
        )
    )

    fact_types = {item["fact_type"] for item in result["fact_requirements"]}
    assert {"entity_set", "metric_ranking"}.issubset(fact_types)
    assert any(item["skill_id"] == "recommend_funds_by_risk_return" for item in result["candidate_invocations"])
    assert result["coverage_summary"]["coverage_status"] == "full_coverage"
    assert result["coverage_summary"]["coverage_message_zh"]


def test_unknown_intent_with_explicit_attribute_warns_but_plans():
    result = retrieve(
        frame(
            intent="not_configured_intent",
            mentioned_attributes=["max_drawdown"],
        )
    )

    assert result["status"] == "success"
    assert any(warning["warning_code"] == "UNKNOWN_INTENT" for warning in result["warnings"])
    assert any(item["attribute_name"] == "max_drawdown" for item in result["fact_requirements"])
    assert result["candidate_invocations"]


def test_unknown_intent_without_attributes_needs_clarification():
    result = retrieve(frame(intent="not_configured_intent", mentioned_attributes=[]))

    assert result["status"] == "need_clarification"
    assert result["error_code"] == "FACT_REQUIREMENTS_INSUFFICIENT"
    assert "语义信息不足" in result["message_zh"]


def test_debug_evidence_is_optional():
    normal = retrieve(frame())
    debug = retrieve(frame(), debug=True)

    assert "debug_evidence" not in normal
    assert "debug_evidence" in debug
    assert debug["debug_evidence"]["message_zh"]


def test_standard_output_does_not_expose_schema_nodes():
    result = retrieve(frame())
    text = json.dumps(result, ensure_ascii=False)

    assert "DataTable:" not in text
    assert "DataField:" not in text
    assert "QueryCapability:" not in text


def test_error_response_keeps_legacy_shape_for_server_exceptions():
    result = error_response(
        domain="finance_market",
        question="",
        intent="",
        message="boom",
    )

    assert result["status"] == "error"
    assert result["relation_subgraph"] == {"nodes": [], "edges": [], "paths": []}
