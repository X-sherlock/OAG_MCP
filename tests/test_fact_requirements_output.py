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


def test_missing_fund_code_is_blocked_before_skill_selection():
    item = frame()
    item["target_objects"][0]["instance_ref"] = {}
    result = retrieve(item)

    assert result["status"] == "blocked_missing_params"
    assert result["fact_requirements"] == []
    assert result["candidate_invocations"] == []
    assert result["missing_params"]
    assert result["missing_params"][0]["missing_params"] == ["fund_code"]
    assert result["missing_params"][0]["message_zh"]


def test_benchmark_and_peer_profiles_use_expected_skills():
    benchmark = retrieve(frame(intent="benchmark_comparison"))
    peer = retrieve(frame(raw_question="000001近一年同类排名怎么样", intent="peer_comparison"))

    assert any(item["skill_id"] == "get_fund_benchmark_facts" for item in benchmark["candidate_invocations"])
    assert any(item["skill_id"] == "get_fund_peer_ranking_facts" for item in peer["candidate_invocations"])


def test_optional_facts_are_covered_when_skill_capability_exists():
    benchmark = retrieve(frame(raw_question="000001近一年收益怎么样", intent="performance_overview", mentioned_attributes=["return_rate"]))
    risk = retrieve(
        frame(
            raw_question="分析000001近一年收益率和最大回撤表现",
            intent="risk_overview",
            mentioned_attributes=["return_rate", "max_drawdown"],
        )
    )

    def covered_optional_attrs(result: dict) -> set[str]:
        covered_ids = {
            fact_id
            for invocation in result["candidate_invocations"]
            for fact_id in invocation["covers_fact_requirements"]
        }
        return {
            item["attribute_name"]
            for item in result["fact_requirements"]
            if item.get("priority") == "optional"
            and item.get("fact_requirement_id") in covered_ids
            and item.get("attribute_name")
        }

    assert {"benchmark_return", "excess_return"}.issubset(covered_optional_attrs(benchmark))
    assert {"peer_drawdown_rank", "peer_sharpe_rank", "calmar_ratio"}.issubset(covered_optional_attrs(risk))
    assert any(item["skill_id"] == "get_fund_benchmark_facts" for item in benchmark["candidate_invocations"])
    assert any(item["skill_id"] == "get_fund_peer_ranking_facts" for item in risk["candidate_invocations"])
    assert any(item["skill_id"] == "get_fund_risk_facts" for item in risk["candidate_invocations"])
