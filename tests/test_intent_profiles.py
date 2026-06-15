from __future__ import annotations

from oag_task_planner_helpers import frame, retrieve


def _required_attrs(result: dict) -> set[str]:
    return {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "required" and item.get("attribute_name")
    }


def test_performance_overview_profile_generates_template_facts():
    result = retrieve(frame(intent="performance_overview"))

    assert {"return_rate", "benchmark_return", "excess_return", "max_drawdown"} == _required_attrs(result)
    optional = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "optional" and item.get("attribute_name")
    }
    assert {"volatility", "sharpe_ratio", "rank"}.issubset(optional)
    assert result["semantic_frame_summary"]["intent"] == "performance_overview"


def test_risk_overview_profile_generates_risk_facts():
    result = retrieve(frame(raw_question="分析000001近一年的风险表现", intent="risk_overview"))

    assert {"max_drawdown", "volatility"} == _required_attrs(result)
    optional = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "optional" and item.get("attribute_name")
    }
    assert {"sharpe_ratio", "calmar_ratio", "downside_risk", "var", "cvar", "peer_drawdown_rank", "peer_sharpe_rank"}.issubset(optional)


def test_benchmark_comparison_profile_generates_relative_facts():
    result = retrieve(frame(raw_question="000001近一年有没有跑赢基准", intent="benchmark_comparison"))

    assert {"return_rate", "benchmark_return", "excess_return"}.issubset(_required_attrs(result))
    assert any(item["skill_id"] == "get_fund_benchmark_facts" for item in result["candidate_invocations"])


def test_peer_comparison_profile_generates_rank_facts():
    result = retrieve(frame(raw_question="000001近一年同类排名怎么样", intent="peer_comparison"))

    assert {"rank", "percentile"} == _required_attrs(result)
    optional = {
        item["attribute_name"]
        for item in result["fact_requirements"]
        if item.get("priority") == "optional" and item.get("attribute_name")
    }
    assert {"return_rate", "max_drawdown", "sharpe_ratio"}.issubset(optional)
    assert any(item["skill_id"] == "get_fund_peer_ranking_facts" for item in result["candidate_invocations"])


def test_explicit_attribute_does_not_expand_full_intent_template():
    result = retrieve(
        frame(
            raw_question="分析000001近一年最大回撤",
            intent="risk_overview",
            mentioned_attributes=["max_drawdown"],
        )
    )

    required = _required_attrs(result)
    assert required == {"max_drawdown"}
    assert "downside_deviation" not in required
