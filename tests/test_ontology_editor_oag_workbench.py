from __future__ import annotations

import json
from copy import deepcopy

from fastapi.testclient import TestClient

from ontology_editor import app as app_module
from ontology_editor.app import app


client = TestClient(app)


def test_oag_planning_examples_cover_scenario_matrix():
    source = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "app.js").read_text(encoding="utf-8")
    index = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "index.html").read_text(encoding="utf-8")

    for label in [
        "分析某基金近一年表现",
        "查询某基金最大回撤和夏普",
        "查询某基金经理",
        "查询某基金公司",
        "查询某基金业绩基准",
        "比较两只基金收益",
        "推荐收益高、回撤低的基金",
        "筛选最大回撤低于10%的基金",
        "查询同类排名",
        "查询费率",
        "查询分红",
        "查询持仓配置",
    ]:
        assert label in source
    for element_id in ["oagTargets", "oagRelationQueries", "oagComparison", "oagOptions"]:
        assert element_id in source
    assert "sent_semantic_frame" in source
    assert "renderPlanViewSplit" in source
    assert "renderInvocationOverview" in source
    assert "renderRelationExpansionPaths" in source
    assert "renderYamlGovernanceEntry" in source
    assert "inferSemanticFrameFromQuestion" in source
    assert 'priority: node.priority || ""' in source
    assert 'priority-${escapeHtml(priorityClass(item.priority))}' in source
    assert 'node[origin = "task_graph"][type = "FactRequirement"][priority = "required"]' in source
    assert "oag-ui-20260630-priority" in index
    assert "自动语义草稿" in source
    assert "结构化草稿（可选校正）" in source
    assert "使用下方结构化草稿覆盖自动识别结果" in source
    assert "补充语义" not in source
    assert "高级结构" not in source


def test_oag_plan_returns_fact_plan_with_chinese_task_graph():
    response = client.post(
        "/api/oag/plan",
        json={
            "semantic_frame": {
                "raw_question": "分析000001近一年的表现",
                "domain": "finance_market",
                "task_type": "analyze",
                "intent": "performance_overview",
                "target_objects": [
                    {
                        "object_type": "Fund",
                        "instance_ref": {"fund_code": "000001"},
                        "role": "analysis_subject",
                    }
                ],
                "constraints": {"period": "1y"},
                "mentioned_attributes": [],
                "debug": True,
            },
            "user_context": {"permission_scopes": ["fund_public_data:read"], "debug": True},
        },
    )

    assert response.status_code == 200
    data = response.json()
    plan = data["task_plan"]
    assert data["editor_plan"]["task_graph"]["nodes"]
    assert data["agent_plan"]["skill_calls"]
    assert data["agent_plan"]["execution"]["message_zh"]
    assert data["plan_views"]["editor"]["label_zh"] == "Editor 调试计划"
    assert data["plan_views"]["agent"]["label_zh"] == "Agent 执行计划"
    assert plan["fact_requirements"]
    assert plan["candidate_invocations"]
    assert plan["task_graph"]["nodes"]
    assert plan["task_graph"]["edges"]
    assert plan["coverage_summary"]["required_fact_count"] > 0
    assert all(item["label_zh"] and item["reason_zh"] for item in plan["fact_requirements"])
    assert all(node["label_zh"] for node in plan["task_graph"]["nodes"])
    assert all(edge["label_zh"] and edge["reason_zh"] for edge in plan["task_graph"]["edges"])


def test_oag_peer_ranking_plan_keeps_required_facts_covered():
    frame_response = client.post(
        "/api/oag/semantic-frame",
        json={"question": "003095近一年同类排名怎么样"},
    )
    assert frame_response.status_code == 200

    response = client.post(
        "/api/oag/plan",
        json={
            "semantic_frame": frame_response.json()["semantic_frame"],
            "user_context": {"permission_scopes": ["fund_public_data:read"], "debug": True},
            "output_view": "editor",
        },
    )

    assert response.status_code == 200
    plan = response.json()["editor_plan"]
    coverage = plan["coverage_summary"]
    assert coverage["required_fact_count"] == coverage["covered_required_fact_count"]
    assert coverage["uncovered_required_facts"] == []
    assert any(
        item["attribute_name"] == "rank" and item["fact_type"] == "peer_rank"
        for item in plan["fact_requirements"]
    )
    assert any(
        item["skill_id"] == "get_fund_peer_ranking_facts" and item["covers_required_count"] >= 1
        for item in plan["candidate_invocations"]
    )


def test_oag_semantic_frame_api_matches_workflow_case_builder_snapshot():
    cases_path = app_module.PROJECT_ROOT / "outputs" / "workflow_full_test_20260630" / "workflow_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    selected_case_numbers = {1, 2, 11, 31, 71, 91, 111, 131, 151, 171, 201, 204, 205, 231}

    for case in cases:
        if case["case_no"] not in selected_case_numbers:
            continue
        response = client.post(
            "/api/oag/semantic-frame",
            json={"question": case["question"]},
        )

        assert response.status_code == 200
        assert response.json()["semantic_frame"] == case["semantic_frame"]


def test_oag_options_returns_chinese_display_fields():
    response = client.get("/api/oag/options")

    assert response.status_code == 200
    data = response.json()
    for key in ("task_types", "intents", "attributes", "fact_types", "skills", "relation_types"):
        assert data[key]
        assert "label_zh" in data[key][0]
    assert any(item["label_zh"] == "分析" for item in data["task_types"])
    assert any(item["value"] == "fund_code" and item["label_zh"] == "基金代码" for item in data["input_params"])
    assert any(item["value"] == "period" and item["label_zh"] == "统计周期" for item in data["input_params"])
    assert data["fact_requirements"]
    first_fact = data["fact_requirements"][0]
    for key in ("value", "intent_name", "fact_type", "priority_zh", "reason_zh"):
        assert key in first_fact


def test_new_intent_template_ui_is_fact_requirement_first():
    source = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'on("taskNewIntentBtn", "click", () => openIntentTemplateEditor({}));' in source
    assert 'if (initialType === "IntentProfile")' in source
    assert "新增意图模板" in source
    assert "这个意图默认需要哪些事实" in source
    assert "事实类型" in source
    assert "事实名称" in source
    assert "是否必须查询" in source
    assert "用户会怎么说" in source
    assert 'openAddNodeDialog("IntentProfile"' not in source


def test_new_skill_ui_links_to_fact_requirements():
    source = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "app.js").read_text(encoding="utf-8")

    assert 'on("taskNewSkillBtn", "click", () => openSkillCoverageEditor({}));' in source
    assert 'if (initialType === "SkillCapability")' in source
    assert "这个 Skill 能满足哪些事实需求" in source
    assert 'ensureOagOptions(["fact_requirements", "input_params"])' in source
    assert "missingRequiredFields" in source
    assert "skillInputParamCheckboxList" in source
    assert 'checkedValues("skillInputParams")' in source
    assert "请至少选择一个输入参数" in source
    assert "supported_fact_requirements" in source
    assert "deriveSkillCoverageFromFacts" in source
    assert "请至少关联一个事实需求" in source
    assert 'id="skillInputs"' not in source
    assert 'openAddNodeDialog("SkillCapability"' not in source


def test_diagnostics_api_returns_chinese_messages_and_actions():
    response = client.get("/api/diagnostics")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        assert all(item["diagnostic_message_zh"] for item in data["items"])
        assert all(item["suggested_action_zh"] for item in data["items"])


def test_intent_profile_save_writes_yaml_and_returns_backup(monkeypatch):
    rows = [
        {
            "intent_name": "performance_overview",
            "intent_name_zh": "基金综合表现分析",
            "fact_requirements_template": [],
        }
    ]
    writes = []

    monkeypatch.setattr(app_module, "read_yaml_file", lambda file_name: deepcopy(rows))
    monkeypatch.setattr(app_module, "validate_ontology", lambda: {"errors": [], "warnings": []})

    def fake_write(file_name, data):
        writes.append((file_name, data))
        return {"file": file_name, "backup_path": "ontology/.backups/intent_profiles.test.yaml"}

    monkeypatch.setattr(app_module, "write_yaml_file", fake_write)

    response = client.put(
        "/api/intent-profiles/performance_overview",
        json={
            "data": {
                "intent_name_zh": "基金综合表现分析",
                "fact_requirements_template": [
                    {
                        "fact_type": "metric_value",
                        "attribute_name": "return_rate",
                        "priority": "required",
                        "reason_zh": "综合表现分析需要收益率事实。",
                    }
                ],
            }
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["write"]["backup_path"]
    assert writes[0][0] == "intent_profiles.yaml"
    assert writes[0][1][0]["fact_requirements_template"][0]["reason_zh"]


def test_intent_profile_create_writes_fact_template(monkeypatch):
    rows: list[dict] = []
    writes = []

    monkeypatch.setattr(app_module, "read_yaml_file", lambda file_name: deepcopy(rows))
    monkeypatch.setattr(app_module, "validate_ontology", lambda: {"errors": [], "warnings": []})

    def fake_write(file_name, data):
        writes.append((file_name, deepcopy(data)))
        return {"file": file_name, "backup_path": "ontology/.backups/intent_profiles.create.test.yaml"}

    monkeypatch.setattr(app_module, "write_yaml_file", fake_write)

    response = client.put(
        "/api/intent-profiles/new_performance_review",
        json={
            "data": {
                "intent_name": "new_performance_review",
                "intent_name_zh": "新增表现复盘",
                "trigger_aliases": ["复盘表现"],
                "target_object_types": ["Fund"],
                "fact_requirements_template": [
                    {
                        "fact_type": "metric_value",
                        "attribute_name": "return_rate",
                        "priority": "required",
                        "reason_zh": "表现复盘需要先查询收益率事实。",
                    }
                ],
            }
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "created"
    assert data["write"]["backup_path"]
    assert writes[0][0] == "intent_profiles.yaml"
    assert writes[0][1][0]["intent_name"] == "new_performance_review"
    assert writes[0][1][0]["fact_requirements_template"][0]["attribute_name"] == "return_rate"


def test_skill_save_writes_yaml_and_returns_backup(monkeypatch):
    rows = [{"skill_id": "get_fund_metric_values", "skill_name": "获取基金指标值"}]
    writes = []

    monkeypatch.setattr(app_module, "read_yaml_file", lambda file_name: deepcopy(rows))
    monkeypatch.setattr(app_module, "validate_ontology", lambda: {"errors": [], "warnings": []})

    def fake_write(file_name, data):
        writes.append((file_name, data))
        return {"file": file_name, "backup_path": "ontology/.backups/skills.test.yaml"}

    monkeypatch.setattr(app_module, "write_yaml_file", fake_write)

    response = client.put(
        "/api/skills/get_fund_metric_values",
        json={
            "data": {
                "skill_name": "获取基金指标值",
                "provides_fact_types": ["metric_value"],
                "supported_subject_types": ["Fund"],
                "supported_attributes": ["return_rate"],
                "permission_scope": "fund_public_data:read",
            }
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["write"]["backup_path"]
    assert writes[0][0] == "skills.yaml"
    assert writes[0][1][0]["provides_fact_types"] == ["metric_value"]


def test_skill_create_writes_fact_requirement_link_and_coverage(monkeypatch):
    rows: list[dict] = []
    writes = []

    monkeypatch.setattr(app_module, "read_yaml_file", lambda file_name: deepcopy(rows))
    monkeypatch.setattr(app_module, "validate_ontology", lambda: {"errors": [], "warnings": []})

    def fake_write(file_name, data):
        writes.append((file_name, deepcopy(data)))
        return {"file": file_name, "backup_path": "ontology/.backups/skills.create.test.yaml"}

    monkeypatch.setattr(app_module, "write_yaml_file", fake_write)

    response = client.put(
        "/api/skills/get_new_fact_skill",
        json={
            "data": {
                "skill_id": "get_new_fact_skill",
                "skill_name": "获取新增事实",
                "target_object_type": "Fund",
                "input_params": ["fund_code", "period", "attributes"],
                "permission_scope": "fund_public_data:read",
                "supported_fact_requirements": ["performance_overview:metric_value:return_rate"],
                "provides_fact_types": ["metric_value"],
                "supported_subject_types": ["Fund"],
                "supported_attributes": ["return_rate"],
                "output_attributes": ["return_rate"],
            }
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "created"
    assert data["write"]["backup_path"]
    assert writes[0][0] == "skills.yaml"
    saved = writes[0][1][0]
    assert saved["supported_fact_requirements"] == ["performance_overview:metric_value:return_rate"]
    assert saved["provides_fact_types"] == ["metric_value"]
    assert saved["supported_attributes"] == ["return_rate"]


def test_semantic_relation_create_update_delete_writes_yaml_and_returns_backup(monkeypatch):
    rows: list[dict] = []
    relation_types = [{"relation_type": "compared_with"}]
    graph = {
        "nodes": [
            {"data": {"id": "Attribute:return_rate"}},
            {"data": {"id": "Attribute:benchmark_return"}},
        ],
        "edges": [],
    }

    def fake_read(file_name):
        if file_name == "schema_graph_edges.yaml":
            return deepcopy(rows)
        if file_name == "relation_types.yaml":
            return deepcopy(relation_types)
        return []

    def fake_write(file_name, data):
        rows[:] = deepcopy(data)
        return {"file": file_name, "backup_path": f"ontology/.backups/{file_name}.test"}

    monkeypatch.setattr(app_module, "read_yaml_file", fake_read)
    monkeypatch.setattr(app_module, "write_yaml_file", fake_write)
    monkeypatch.setattr(app_module, "build_graph", lambda: graph)
    monkeypatch.setattr(app_module, "validate_ontology", lambda: {"errors": [], "warnings": []})

    payload = {
        "source": "Attribute:return_rate",
        "target": "Attribute:benchmark_return",
        "relation_type": "compared_with",
        "properties": {"reason_zh": "收益率分析需要对比基准收益率。", "weight": 0.9},
    }
    created = client.post("/api/semantic-relations", json=payload)
    assert created.status_code == 200
    edge_id = created.json()["edge"]["edge_id"]
    assert created.json()["write"]["backup_path"]

    updated = client.put(
        f"/api/semantic-relations/{edge_id}",
        json={**payload, "properties": {**payload["properties"], "weight": 0.95}},
    )
    assert updated.status_code == 200
    assert rows[0]["weight"] == 0.95

    deleted = client.delete(f"/api/semantic-relations/{edge_id}")
    assert deleted.status_code == 200
    assert rows == []
