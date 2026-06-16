from __future__ import annotations

from oag_mcp.llm_config import LLMConfig
from oag_mcp.oag_v2_planner import OAGV2Planner
from oag_task_planner_helpers import CatalogRepository, DOMAIN, SchemaGraphRepository, frame, retrieve


def test_candidate_fact_pool_can_be_generated():
    result = retrieve(frame(raw_question="分析000001近一年表现", intent="performance_overview"))

    assert result["oag_version"] == "v2"
    assert result["candidate_fact_pool"]
    assert result["selected_facts"]
    assert result["skill_bindings"]


def test_mock_selector_rejects_fact_id_outside_candidate_pool():
    result = service_plan(
        frame(mentioned_attributes=["return_rate"]),
        selector_mode="mock",
        planning_options={"selected_fact_ids": ["not_in_candidate_pool"]},
    )

    assert result["status"] == "error"
    assert result["validation_result"]["illegal_fact_ids"] == ["not_in_candidate_pool"]
    assert any(item["diagnostic_code"] == "ILLEGAL_FACT_ID_REJECTED" for item in result["diagnostics"])


def test_mentioned_attributes_have_highest_priority():
    result = retrieve(frame(intent="performance_overview", mentioned_attributes=["max_drawdown"]))
    pool = result["candidate_fact_pool"]
    drawdown = next(item for item in pool if item.get("attribute_name") == "max_drawdown")

    assert drawdown["priority"] == "required"
    assert drawdown["selection_priority"] == 100
    assert result["selected_facts"][0]["attribute_name"] == "max_drawdown"


def test_benchmark_metrics_trigger_has_benchmark_dependency_completion():
    for attribute in ("benchmark_return", "excess_return"):
        result = retrieve(frame(intent=None, mentioned_attributes=[attribute]))

        dependencies = result["dependency_completion"]["completed_facts"]
        assert any(item.get("predicate") == "has_benchmark" for item in dependencies)


def test_peer_rank_triggers_belongs_to_category_dependency_completion():
    result = retrieve(frame(intent=None, mentioned_attributes=["rank"]))

    dependencies = result["dependency_completion"]["completed_facts"]
    assert any(item.get("predicate") == "belongs_to_category" for item in dependencies)


def test_skill_binder_deterministically_binds_metric_skill():
    result = retrieve(frame(intent=None, mentioned_attributes=["return_rate"]))

    bindings = result["skill_bindings"]
    assert any(item["skill_id"] == "get_fund_metric_values" for item in bindings)
    metric = next(item for item in bindings if item["skill_id"] == "get_fund_metric_values")
    assert metric["covers_fact_ids"]
    assert metric["coverage_reason_zh"]


def test_missing_period_outputs_missing_params():
    item = frame(intent=None, mentioned_attributes=["return_rate"], constraints={})
    result = retrieve(item)

    assert any("period" in row["missing_params"] for row in result["missing_params"])
    assert result["agent_plan"]["execution"]["execution_status"] == "blocked_missing_params"


def test_rule_selector_does_not_require_external_api(monkeypatch):
    monkeypatch.delenv("OAG_LLM_API_KEY", raising=False)

    result = retrieve(frame(intent=None, mentioned_attributes=["return_rate"]))

    assert result["status"] == "success"
    assert result["selection_trace"]["selector"] == "rule_selector"


def test_llm_selector_without_api_key_returns_clear_error():
    planner = OAGV2Planner(
        ontology_repository=CatalogRepository(),
        graph_repository=SchemaGraphRepository(),
        llm_config=LLMConfig(
            provider="bailian",
            model="qwen3.7-max-2026-06-08",
            api_key="",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            timeout_seconds=60,
            temperature=0.1,
            enabled=True,
        ),
    )
    result = planner.plan(
        semantic_frame=frame(intent=None, mentioned_attributes=["return_rate"]),
        selector_mode="llm",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["status"] == "error"
    assert result["error_code"] == "LLM_API_KEY_MISSING"
    assert "OAG_LLM_API_KEY" in result["message_zh"]


def service_plan(semantic_frame, selector_mode="rule", planning_options=None):
    return OAGV2Planner(
        ontology_repository=CatalogRepository(),
        graph_repository=SchemaGraphRepository(),
    ).plan(
        semantic_frame=semantic_frame,
        selector_mode=selector_mode,
        planning_options=planning_options or {},
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )
