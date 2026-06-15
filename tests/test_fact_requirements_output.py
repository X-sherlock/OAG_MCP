from __future__ import annotations

from oag_task_planner_helpers import frame, retrieve


def test_fact_requirements_have_chinese_display_fields():
    result = retrieve(frame())

    for requirement in result["fact_requirements"]:
        assert requirement["label_zh"]
        assert requirement["description_zh"]
        assert requirement["reason_zh"]
        assert requirement["fact_type_zh"]
        assert requirement["priority_zh"]
        assert requirement["source_zh"]


def test_candidate_invocations_cover_required_facts():
    result = retrieve(frame())
    required_ids = {
        item["fact_requirement_id"]
        for item in result["fact_requirements"]
        if item["priority"] == "required"
    }
    covered_ids = {
        fact_id
        for invocation in result["candidate_invocations"]
        for fact_id in invocation["covers_fact_requirements"]
    }

    assert required_ids.issubset(covered_ids)
    assert result["coverage_summary"]["required_fact_count"] == len(required_ids)
    assert result["coverage_summary"]["covered_required_fact_count"] == len(required_ids)


def test_task_graph_is_derived_task_subgraph():
    result = retrieve(frame())
    node_types = {node["node_type"] for node in result["task_graph"]["nodes"]}
    edge_types = {edge["relation_type"] for edge in result["task_graph"]["edges"]}

    assert {"SemanticFrame", "TaskType", "IntentProfile", "TargetInstance"}.issubset(node_types)
    assert {"requires_fact", "covered_by_skill", "has_attribute"}.issubset(edge_types)
    assert {"DataTable", "DataField", "QueryCapability"}.isdisjoint(node_types)


def test_missing_fund_code_is_reported_as_missing_skill_param():
    item = frame()
    item["target_objects"][0]["instance_ref"] = {}
    result = retrieve(item)

    assert result["fact_requirements"]
    assert result["missing_params"]
    assert any("fund_code" in row["missing_params"] for row in result["missing_params"])
    assert all(row["message_zh"] for row in result["missing_params"])


def test_benchmark_and_peer_profiles_use_expected_skills():
    benchmark = retrieve(frame(intent="benchmark_comparison"))
    peer = retrieve(frame(raw_question="000001近一年同类排名怎么样", intent="peer_comparison"))

    assert any(item["skill_id"] == "get_fund_benchmark_facts" for item in benchmark["candidate_invocations"])
    assert any(item["skill_id"] == "get_fund_peer_ranking_facts" for item in peer["candidate_invocations"])
