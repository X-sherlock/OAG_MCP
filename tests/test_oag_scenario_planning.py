from __future__ import annotations

from oag_mcp.fact_planner import FactPlanner
from oag_task_planner_helpers import CatalogRepository, SchemaGraphRepository, DOMAIN, frame, retrieve


def attrs(result):
    return {item.get("attribute_name") for item in result["fact_requirements"]}


def fact_types(result):
    return {item.get("fact_type") for item in result["fact_requirements"]}


def skill_ids(result):
    return {item.get("skill_id") for item in result["candidate_invocations"]}


def fundset_frame(**overrides):
    item = frame(
        raw_question="近一年收益率最高的基金有哪些",
        task_type="rank",
        intent="fund_ranking",
        object_type="FundSet",
        instance_ref={"fund_universe": "all_funds"},
        role="candidate_set",
        mentioned_attributes=[],
        ranking=[{"attribute": "return_rate", "direction": "desc"}],
        limit=10,
    )
    item.update(overrides)
    return item


def test_single_fund_metric_query():
    result = retrieve(
        frame(
            raw_question="查询000001近一年最大回撤和夏普",
            task_type="query",
            intent=None,
            mentioned_attributes=["max_drawdown", "sharpe_ratio"],
        )
    )

    required = {item["attribute_name"] for item in result["fact_requirements"] if item["priority"] == "required"}
    assert {"max_drawdown", "sharpe_ratio"}.issubset(required)
    assert "get_fund_metric_values" in skill_ids(result)


def test_single_fund_overview_analysis():
    result = retrieve(frame(raw_question="分析000001近一年表现", task_type="analyze", intent="performance_overview"))

    assert {"return_rate", "benchmark_return", "excess_return", "max_drawdown"}.issubset(attrs(result))
    assert {"get_fund_metric_values", "get_fund_benchmark_facts"}.issubset(skill_ids(result))


def test_benchmark_comparison():
    result = retrieve(frame(raw_question="000001近一年有没有跑赢基准", task_type="compare", intent="benchmark_comparison"))

    assert {"return_rate", "benchmark_return", "excess_return"}.issubset(attrs(result))
    assert any(item.get("predicate") == "has_benchmark" for item in result["fact_requirements"])


def test_peer_comparison():
    result = retrieve(frame(raw_question="000001近一年同类排名怎么样", task_type="compare", intent="peer_comparison"))

    assert {"rank", "percentile"}.issubset(attrs(result))
    assert any(item.get("predicate") == "belongs_to_category" for item in result["fact_requirements"])
    assert "get_fund_peer_ranking_facts" in skill_ids(result)


def test_relation_queries_for_manager_company_and_benchmark():
    cases = [
        ("查询000001的基金经理", [{"relation_type": "managed_by", "target_object_type": "FundManager"}]),
        ("查询000001的基金公司", [{"relation_type": "issued_by", "target_object_type": "FundCompany"}]),
        ("查询000001的业绩比较基准", [{"relation_type": "has_benchmark", "target_object_type": "Benchmark"}]),
    ]
    for raw_question, relation_queries in cases:
        result = retrieve(frame(raw_question=raw_question, task_type="query", intent=None, relation_queries=relation_queries))
        predicates = {item.get("predicate") for item in result["fact_requirements"]}
        assert relation_queries[0]["relation_type"] in predicates
        assert "get_fund_profile_facts" in skill_ids(result)


def test_multi_fund_comparison_keeps_all_targets():
    item = frame(raw_question="比较000001和000002近一年收益", task_type="compare", intent="fund_comparison", mentioned_attributes=["return_rate"])
    item["target_objects"] = [
        {"object_type": "Fund", "instance_ref": {"fund_code": "000001"}, "role": "comparison_subject"},
        {"object_type": "Fund", "instance_ref": {"fund_code": "000002"}, "role": "comparison_subject"},
    ]
    item["comparison"] = {"mode": "side_by_side", "attributes": ["return_rate"], "target_object_policy": "all_targets"}

    result = retrieve(item)
    subjects = {fact["subject"]["subject_id"] for fact in result["fact_requirements"] if fact.get("attribute_name") == "return_rate"}
    graph_targets = {node.get("instance_ref", {}).get("fund_code") for node in result["task_graph"]["nodes"] if node.get("node_type") == "TargetInstance"}

    assert {"Fund:000001", "Fund:000002"}.issubset(subjects)
    assert {"000001", "000002"}.issubset(graph_targets)
    assert "comparison_result" in fact_types(result)


def test_fundset_ranking_screening_and_recommendation():
    ranking = retrieve(fundset_frame())
    screening = retrieve(
        fundset_frame(
            raw_question="筛选近一年最大回撤低于10%的基金",
            task_type="screen",
            intent="fund_screening",
            ranking=[],
            filters=[{"attribute": "max_drawdown", "operator": "<=", "value": 0.1}],
        )
    )
    recommendation = retrieve(
        fundset_frame(
            raw_question="推荐近一年收益高、回撤低的基金",
            task_type="recommend",
            intent="fund_recommendation",
            ranking=[{"attribute": "return_rate", "direction": "desc"}, {"attribute": "max_drawdown", "direction": "asc"}],
            filters=[{"attribute": "max_drawdown", "operator": "<=", "value": 0.1}],
        )
    )

    assert "metric_ranking" in fact_types(ranking)
    assert "rank_funds_by_metric" in skill_ids(ranking)
    assert "filter_condition" in fact_types(screening)
    assert "screen_funds_by_metric_condition" in skill_ids(screening)
    assert {"entity_set", "metric_ranking", "filter_condition"}.issubset(fact_types(recommendation))
    assert "recommend_funds_by_risk_return" in skill_ids(recommendation)


def test_profile_fee_dividend_holding_and_allocation_queries():
    cases = [
        ("000001的基本信息", "profile", "fund_profile", "object_profile", "get_fund_profile_facts", {}),
        ("000001费率是多少", "query", "fee_analysis", "fee_fact", "get_fund_fee_facts", {}),
        ("000001分红情况", "query", "dividend_analysis", "dividend_fact", "get_fund_dividend_facts", {}),
        ("000001当前持仓如何", "query", "holding_analysis", "holding_fact", "get_fund_holding_facts", {"report_date": "latest"}),
        ("000001资产配置怎么样", "query", "asset_allocation_analysis", "allocation_fact", "get_fund_holding_facts", {"report_date": "latest"}),
    ]
    for raw_question, task_type, intent, fact_type, skill_id, extra_constraints in cases:
        item = frame(raw_question=raw_question, task_type=task_type, intent=intent)
        item["constraints"].update(extra_constraints)
        result = retrieve(item)
        assert fact_type in fact_types(result)
        assert skill_id in skill_ids(result)


def test_unknown_intent_with_explicit_attribute_still_plans():
    result = retrieve(frame(intent="unknown_intent", mentioned_attributes=["return_rate"]))

    assert result["status"] == "success"
    assert "return_rate" in attrs(result)
    assert "get_fund_metric_values" in skill_ids(result)


def test_unknown_intent_without_attribute_needs_clarification():
    result = retrieve(frame(intent="unknown_intent", mentioned_attributes=[]))

    assert result["status"] == "need_clarification"
    assert result["coverage_summary"]["coverage_status"] == "need_clarification"


def test_compare_with_one_target_returns_chinese_diagnostic():
    result = retrieve(frame(raw_question="比较000001近一年收益", task_type="compare", intent="fund_comparison", mentioned_attributes=["return_rate"]))

    assert any(item["diagnostic_code"] == "COMPARE_TARGET_TOO_FEW" for item in result["diagnostics"])
    assert all(item["message_zh"] and item["suggestion_zh"] for item in result["diagnostics"])


def test_fundset_task_without_fundset_returns_diagnostic():
    result = retrieve(frame(raw_question="近一年收益率最高的基金有哪些", task_type="rank", intent="fund_ranking", mentioned_attributes=[], ranking=[{"attribute": "return_rate", "direction": "desc"}]))

    assert any(item["diagnostic_code"] == "FUNDSET_TARGET_MISSING" for item in result["diagnostics"])


def test_no_skill_coverage_returns_uncovered_facts_and_diagnostic():
    planner = FactPlanner(
        ontology_repository=CatalogRepository(),
        graph_repository=SchemaGraphRepository(),
        skills=[
            {
                "skill_id": "unrelated_skill",
                "skill_name": "无关 Skill",
                "description": "不覆盖基金事实。",
                "provides_fact_types": ["document_fact"],
                "supported_subject_types": ["ResearchReport"],
                "supported_attributes": [],
                "input_params": [],
                "permission_scope": "fund_public_data:read",
                "enabled": True,
            }
        ],
    )
    result = planner.plan(
        semantic_frame=frame(mentioned_attributes=["return_rate"]),
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["coverage_summary"]["coverage_status"] == "no_coverage"
    assert result["coverage_summary"]["uncovered_required_facts"]
    assert any(item["diagnostic_code"] == "CANDIDATE_INVOCATIONS_EMPTY" for item in result["diagnostics"])


def test_task_graph_chinese_fields_complete_for_fundset():
    result = retrieve(fundset_frame())

    assert all(node.get("label_zh") and node.get("role") for node in result["task_graph"]["nodes"])
    assert all(edge.get("label_zh") and edge.get("reason_zh") for edge in result["task_graph"]["edges"])
    assert not {"DataTable", "DataField", "QueryCapability"} & {node.get("node_type") for node in result["task_graph"]["nodes"]}
