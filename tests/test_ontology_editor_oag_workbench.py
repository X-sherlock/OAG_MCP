from __future__ import annotations

import io
import json
import zipfile
from copy import deepcopy

from fastapi.testclient import TestClient

from ontology_editor import app as app_module
from ontology_editor.app import app


client = TestClient(app)


def test_oag_planning_examples_cover_scenario_matrix():
    source = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "app.js").read_text(encoding="utf-8")

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


def test_oag_workbench_returns_business_matrices_and_release_readiness():
    response = client.get("/api/oag/workbench")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["domain"] == "finance_market"
    assert data["summary"]["scenario_count"] == len(data["scenario_matrix"])
    assert data["modeling_guide"]
    assert data["scenario_matrix"]
    assert data["skill_coverage_matrix"]
    assert data["relation_strategy"]["summary"]["edge_count"] >= 0
    assert "release_readiness" in data["test_publish"]

    first_scenario = data["scenario_matrix"][0]
    for key in ("intent_name_zh", "required_fact_count", "execution_status_zh", "next_action_zh", "sample_question_zh", "semantic_frame", "fact_requirements"):
        assert key in first_scenario
    assert first_scenario["semantic_frame"]["domain"] == "finance_market"
    assert first_scenario["semantic_frame"]["intent"] == first_scenario["intent_name"]
    assert first_scenario["semantic_frame"]["target_objects"]
    assert first_scenario["fact_requirements"]
    first_scenario_fact = first_scenario["fact_requirements"][0]
    for key in ("label_zh", "covering_skill_names_zh", "execution_status_zh", "suggested_action_zh"):
        assert key in first_scenario_fact

    first_coverage = data["skill_coverage_matrix"][0]
    for key in ("label_zh", "covering_skills", "execution_status_zh", "suggested_action_zh"):
        assert key in first_coverage

    first_sample = data["test_publish"]["sample_scenarios"][0]
    assert first_sample["semantic_frame"]["intent"] == first_sample["intent_name"]
    assert first_sample["question_zh"] == first_sample["semantic_frame"]["raw_question"]

    if data["diagnostics_governance"]["top_actions"]:
        first_action = data["diagnostics_governance"]["top_actions"][0]
        for key in ("suggested_task_id", "suggested_task_title_zh", "suggested_action_zh", "diagnostic_types"):
            assert key in first_action
        assert first_action["suggested_task_id"] in {
            "intent_templates",
            "skill_coverage",
            "semantic_relations",
            "core_graph",
            "diagnostic",
        }


def test_oag_workbench_sample_plans_validate_agent_execution_status():
    response = client.get("/api/oag/workbench/sample-plans")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["sample_count"] == len(data["items"])
    assert "status_zh" in data["summary"]
    assert data["items"]
    first = data["items"][0]
    for key in (
        "question_zh",
        "status_zh",
        "execution_status_zh",
        "coverage_status_zh",
        "missing_params",
        "uncovered_facts",
    ):
        assert key in first


def test_oag_scenario_draft_generates_intent_template_and_relation_suggestions():
    response = client.post(
        "/api/oag/scenario-draft",
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
                "debug": True,
            },
            "trigger_aliases": ["分析000001近一年的表现"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent_profile_draft"]["intent_name"] == "performance_overview"
    assert data["intent_profile_draft"]["fact_requirements_template"]
    first_fact = data["intent_profile_draft"]["fact_requirements_template"][0]
    for key in ("fact_type", "priority", "reason_zh"):
        assert key in first_fact
    assert data["agent_plan"]["execution"]["message_zh"]
    assert "relation_strategy_drafts" in data
    assert all("unknown" not in item["from"] and "unknown" not in item["to"] for item in data["relation_strategy_drafts"])
    assert "skill_coverage_gaps" in data


def test_relation_strategy_drafts_apply_writes_schema_edges_once(monkeypatch):
    rows: list[dict] = []
    writes = []
    graph = {
        "nodes": [
            {"data": {"id": "ObjectType:Fund"}},
            {"data": {"id": "ObjectType:Benchmark"}},
        ],
        "edges": [],
    }

    def fake_read(file_name):
        if file_name == "schema_graph_edges.yaml":
            return deepcopy(rows)
        if file_name == "relation_types.yaml":
            return [{"relation_type": "has_benchmark"}]
        return []

    def fake_write(file_name, data):
        writes.append((file_name, deepcopy(data)))
        rows[:] = deepcopy(data)
        return {"file": file_name, "backup_path": "ontology/.backups/schema_graph_edges.bulk.test.yaml"}

    monkeypatch.setattr(app_module, "read_yaml_file", fake_read)
    monkeypatch.setattr(app_module, "write_yaml_file", fake_write)
    monkeypatch.setattr(app_module, "build_graph", lambda: graph)
    monkeypatch.setattr(app_module, "validate_ontology", lambda: {"errors": [], "warnings": []})

    response = client.post(
        "/api/oag/relation-strategy-drafts",
        json={
            "items": [
                {
                    "edge_id": "ObjectType:Fund__has_benchmark__ObjectType:Benchmark",
                    "from": "ObjectType:Fund",
                    "to": "ObjectType:Benchmark",
                    "relation_type": "has_benchmark",
                    "applicable_tasks": ["analyze"],
                    "applicable_intents": ["performance_overview"],
                    "planning_role": "benchmark_context",
                    "auto_expand_mode": "contextual",
                    "answer_visibility": "supporting_context",
                    "reason_zh": "表现分析需要业绩基准作为支撑上下文。",
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["applied_count"] == 1
    assert data["items"][0]["action"] == "created"
    assert len(writes) == 1
    saved = writes[0][1][0]
    assert saved["planning_role"] == "benchmark_context"
    assert saved["auto_expand_mode"] == "contextual"
    assert saved["reason_zh"]


def test_oag_publish_package_contains_manifest_yaml_and_agent_plan_validation():
    response = client.get("/api/oag/publish-package")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "workbench_summary.json" in names
        assert "sample_agent_plan_validation.json" in names
        assert "ontology/skills.yaml" in names
        assert "ontology/schema_graph_edges.yaml" in names

        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        validation = json.loads(archive.read("sample_agent_plan_validation.json").decode("utf-8"))

    assert manifest["package_type"] == "oag_model_publish_package"
    assert manifest["agent_plan_validation"]["sample_count"] == validation["summary"]["sample_count"]
    assert manifest["consumer_hint_zh"]


def test_workbench_home_defaults_to_business_view_with_advanced_folded_tools():
    source = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "app.js").read_text(encoding="utf-8")

    for text in [
        "面向场景的 OAG 模型工作台",
        "模型搭建向导",
        "场景矩阵",
        "Skill 覆盖矩阵",
        "场景需要的事实",
        "renderScenarioFactSummary",
        "关系策略工作台",
        "诊断治理",
        "测试发布",
        "从 0 建模动作",
        "定义领域对象",
        "导入对象属性",
        "设计事实类型",
        "注册 Skill 能力",
        "生成典型场景",
        "生成典型场景",
        "openScenarioDraftGenerator",
        "/api/oag/scenario-draft",
        "事实需求模板",
        "关系策略建议",
        "编辑并保存意图模板",
        "保存关系策略建议",
        "saveScenarioRelationDrafts",
        "/api/oag/relation-strategy-drafts",
        "配置关系策略",
        "高级功能：YAML、完整 editor_plan、任务子图和 debug 信息",
        "/api/oag/workbench",
        "openWorkbenchScenario",
        "openWorkbenchSemanticFrame",
        "已载入场景样例",
        "点击“生成事实规划”即可验证 agent_plan",
        "runWorkbenchScenarioValidation",
        "/api/oag/workbench/sample-plans",
        "运行全部样例验证",
        "agent_plan 覆盖、缺失参数和可执行状态",
        "生成 OAG 发布包",
        "/api/oag/publish-package",
        "runModelingAction",
        "openDiagnosticRepairAction",
        "diagnosticActionTask",
        "data-diagnostic-task",
        "data-diagnostic-repair-task",
        "进入修复",
        'openAddNodeDialog("ObjectType")',
        'openAddNodeDialog("Attribute")',
        'openAddNodeDialog("FactType")',
    ]:
        assert text in source


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
        assert all(item["suggested_task_id"] for item in data["items"])
        assert all(item["suggested_task_title_zh"] for item in data["items"])


def test_diagnostic_top_actions_route_to_repair_workbenches():
    actions = app_module.build_top_diagnostic_actions(
        [
            {
                "diagnostic_type": "intent_missing_fact_requirements_template",
                "action_kind": "edit_intent_template",
                "node_id": "IntentProfile:performance_overview",
                "target_id": "IntentProfile:performance_overview",
            },
            {
                "diagnostic_type": "required_fact_without_skill_coverage",
                "action_kind": "edit_skill_coverage",
                "node_id": "FactRequirement:performance_overview.return_rate",
                "target_id": "FactRequirement:performance_overview.return_rate",
            },
            {
                "diagnostic_type": "planning_edge_missing_auto_expand_mode",
                "action_kind": "edit_relation",
                "edge_id": "ObjectType:Fund__has_benchmark__ObjectType:Benchmark",
                "target_id": "ObjectType:Fund__has_benchmark__ObjectType:Benchmark",
            },
        ]
    )

    by_kind = {item["action_kind"]: item for item in actions}
    assert by_kind["edit_intent_template"]["suggested_task_id"] == "intent_templates"
    assert by_kind["edit_skill_coverage"]["suggested_task_id"] == "skill_coverage"
    assert by_kind["edit_relation"]["suggested_task_id"] == "semantic_relations"
    assert by_kind["edit_relation"]["suggested_action_zh"]
    assert by_kind["edit_skill_coverage"]["diagnostic_types"] == ["required_fact_without_skill_coverage"]


def test_diagnostic_normalization_overrides_legacy_action_kinds_with_business_routes():
    row = app_module.normalize_diagnostic_row(
        {
            "type": "attributes_without_skill",
            "action_kind": "link_skill",
            "node_id": "Attribute:return_rate",
            "severity": "warning",
        }
    )

    assert row["raw_action_kind"] == "link_skill"
    assert row["action_kind"] == "edit_skill_coverage"
    assert row["suggested_task_id"] == "skill_coverage"
    assert row["suggested_task_title_zh"] == "Skill 覆盖矩阵"


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
