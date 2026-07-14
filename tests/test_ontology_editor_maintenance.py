from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from ontology_editor import app as app_module
from ontology_editor.app import app


client = TestClient(app)


def test_relation_candidates_recommend_and_detect_duplicate(monkeypatch):
    graph = {
        "nodes": [
            {"data": {"id": "SkillCapability:get_metric", "type": "SkillCapability", "label": "获取指标", "enabled": True}},
            {"data": {"id": "Attribute:return_rate", "type": "Attribute", "label": "收益率", "enabled": True}},
        ],
        "edges": [
            {
                "data": {
                    "id": "SkillCapability:get_metric__supports_attribute__Attribute:return_rate",
                    "source": "SkillCapability:get_metric",
                    "target": "Attribute:return_rate",
                    "type": "supports_attribute",
                    "origin": "explicit",
                    "editable": True,
                }
            }
        ],
        "summary": {"node_count": 2, "edge_count": 1},
    }

    monkeypatch.setattr(app_module, "build_graph", lambda: graph)
    monkeypatch.setattr(app_module, "read_yaml_file", lambda file_name: [{"relation_type": "supports_attribute", "relation_name_zh": "Skill 支持属性"}])

    response = client.get(
        "/api/maintenance/relation-candidates",
        params={"source": "SkillCapability:get_metric", "target": "Attribute:return_rate"},
    )

    assert response.status_code == 200
    data = response.json()
    values = {item["value"]: item for item in data["relation_options"]}
    assert "supports_attribute" in values
    assert values["supports_attribute"]["duplicate"] is True
    assert data["duplicate_edges"][0]["origin"] == "explicit"
    assert data["endpoint_status"]["can_save"] is True


def test_relation_candidates_reports_invalid_endpoint(monkeypatch):
    graph = {
        "nodes": [{"data": {"id": "Attribute:return_rate", "type": "Attribute", "label": "收益率", "enabled": True}}],
        "edges": [],
        "summary": {"node_count": 1, "edge_count": 0},
    }

    monkeypatch.setattr(app_module, "build_graph", lambda: graph)
    monkeypatch.setattr(app_module, "read_yaml_file", lambda file_name: [])

    response = client.get(
        "/api/maintenance/relation-candidates",
        params={"source": "Missing:node", "target": "Attribute:return_rate"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["endpoint_status"]["source_exists"] is False
    assert "起点节点不存在" in data["endpoint_status"]["errors"][0]


def test_maintenance_overview_groups_diagnostics(monkeypatch):
    graph = {
        "nodes": [
            {"data": {"id": "Attribute:return_rate", "type": "Attribute"}},
            {"data": {"id": "SkillCapability:get_metric", "type": "SkillCapability"}},
        ],
        "edges": [
            {"data": {"id": "e1", "source": "SkillCapability:get_metric", "target": "Attribute:return_rate", "type": "supports_attribute", "origin": "explicit"}},
            {"data": {"id": "e2", "source": "SkillCapability:get_metric", "target": "Attribute:return_rate", "type": "supports_attribute", "origin": "inferred"}},
        ],
        "summary": {"node_count": 2, "edge_count": 2},
    }
    diagnostics = {
        "items": [
            {
                "type": "attributes_without_skill",
                "severity": "warning",
                "node_id": "Attribute:return_rate",
                "action_kind": "link_skill",
                "diagnostic_message_zh": "属性没有 Skill 覆盖",
            }
        ],
        "summary": {"error_count": 0, "warning_count": 1, "info_count": 0, "item_count": 1},
    }

    monkeypatch.setattr(app_module, "build_graph", lambda: graph)
    monkeypatch.setattr(app_module, "build_oag_diagnostics", lambda: diagnostics)

    response = client.get("/api/maintenance/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["explicit_edge_count"] == 1
    assert data["summary"]["inferred_edge_count"] == 1
    assert data["diagnostic_groups"][0]["action_kind"] == "link_skill"
    assert data["diagnostic_groups"][0]["label_zh"] == "关联 Skill"


def test_editor_ontology_dir_env_is_used_by_fresh_process(tmp_path):
    env = os.environ.copy()
    env["OAG_EDITOR_ONTOLOGY_DIR"] = str(tmp_path)
    env["PYTHONPATH"] = str(Path.cwd())
    code = "from ontology_editor.app import api_files; import json; print(json.dumps(api_files()))"

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    data = json.loads(result.stdout)
    assert Path(data["ontology_root"]) == tmp_path.resolve()
