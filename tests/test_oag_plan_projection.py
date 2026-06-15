from __future__ import annotations

from fastapi.testclient import TestClient

from ontology_editor.app import app
from oag_task_planner_helpers import frame, retrieve, service


client = TestClient(app)


def holding_frame(*, report_date: str | None = None) -> dict:
    constraints = {"period": "1y"}
    if report_date:
        constraints["report_date"] = report_date
    return frame(
        raw_question="000001当前持仓和资产配置如何",
        task_type="query",
        intent="holding_analysis",
        constraints=constraints,
        mentioned_attributes=[],
    )


def agent_plan(*, semantic_frame: dict | None = None) -> dict:
    return service().retrieve_context(
        semantic_frame=semantic_frame or holding_frame(),
        user_context={"permission_scopes": ["fund_public_data:read"], "debug": True},
        output_view="agent",
    )


def test_agent_plan_projection_holding_case():
    result = agent_plan()

    assert {"task", "targets", "facts", "skill_calls", "coverage", "execution"}.issubset(result)
    assert "task_graph" not in result
    assert "debug_evidence" not in result
    assert "normalized_semantic_frame" not in result
    assert result["task"]["raw_question"] == "000001当前持仓和资产配置如何"
    assert result["task"]["task_type"] == "query"
    assert result["task"]["intent"] == "holding_analysis"
    assert result["task"]["constraints"]["period"] == "1y"
    assert result["targets"][0]["instance_ref"]["fund_code"] == "000001"
    assert {fact["attribute"] for fact in result["facts"]} == {
        "stock_name",
        "stock_nav_ratio",
        "bond_name",
        "bond_nav_ratio",
    }
    assert all("subject" not in fact for fact in result["facts"])
    assert all(not isinstance(fact["attribute"], dict) for fact in result["facts"])
    skill_call = next(item for item in result["skill_calls"] if item["skill_id"] == "get_fund_holding_facts")
    assert skill_call["params"] == {"fund_code": "000001"}
    assert skill_call["missing_params"] == ["report_date"]
    assert skill_call["call_status"] == "blocked_missing_params"
    assert result["coverage"]["coverage_status"] == "full_coverage"
    assert result["coverage"]["required_fact_count"] == 4
    assert result["coverage"]["covered_required_fact_count"] == 4
    assert result["execution"]["execution_status"] == "blocked_missing_params"


def test_editor_plan_unchanged():
    result = retrieve(holding_frame(), debug=True, output_view="editor")

    assert result["task_graph"]["nodes"]
    assert "diagnostics" in result
    assert "debug_evidence" in result
    assert result["fact_requirements"]
    assert result["candidate_invocations"]
    assert result["coverage_summary"]["required_fact_count"] == 4


def test_mcp_default_agent_view():
    result = service().retrieve_context(
        semantic_frame=holding_frame(),
        user_context={"permission_scopes": ["fund_public_data:read"], "debug": True},
    )

    assert "skill_calls" in result
    assert "task_graph" not in result
    assert "debug_evidence" not in result
    assert "normalized_semantic_frame" not in result


def test_output_view_switch():
    editor = retrieve(holding_frame(), debug=True, output_view="editor")
    agent = retrieve(holding_frame(), debug=True, output_view="agent")

    assert "task_graph" in editor
    assert "debug_evidence" in editor
    assert "skill_calls" in agent
    assert "task_graph" not in agent
    assert "debug_evidence" not in agent


def test_api_oag_plan_output_view_switch():
    response = client.post(
        "/api/oag/plan?output_view=agent",
        json={
            "semantic_frame": holding_frame(),
            "user_context": {"permission_scopes": ["fund_public_data:read"], "debug": True},
        },
    )

    assert response.status_code == 200
    plan = response.json()["task_plan"]
    assert "skill_calls" in plan
    assert "task_graph" not in plan
    assert "debug_evidence" not in plan


def test_no_duplicate_issues():
    result = agent_plan()

    assert result["skill_calls"][0]["missing_params"] == ["report_date"]
    assert result["execution"]["blocking_issues"] == [
        {
            "code": "SKILL_PARAMS_MISSING",
            "skill_id": "get_fund_holding_facts",
            "skill_name_zh": "获取基金持仓与配置事实",
            "missing_params": ["report_date"],
            "message_zh": "调用该 Skill 前需要补充参数：report_date",
        }
    ]
    assert all(issue["code"] != "SKILL_PARAMS_MISSING" for issue in result["issues"])
    issue_keys = [
        (issue.get("code"), issue.get("skill_id"), issue.get("fact_id"), issue.get("message_zh"))
        for issue in result["issues"]
    ]
    assert len(issue_keys) == len(set(issue_keys))


def test_execution_status_ready():
    result = agent_plan(semantic_frame=holding_frame(report_date="2026-03-31"))

    assert result["skill_calls"]
    assert all(item["call_status"] == "ready" for item in result["skill_calls"])
    assert result["execution"]["execution_status"] == "ready"
    assert result["execution"]["ready_skill_count"] == len(result["skill_calls"])
    assert result["execution"]["blocked_skill_count"] == 0
