from __future__ import annotations

from fastapi.testclient import TestClient

from ontology_editor import app as app_module
from ontology_editor.app import app


client = TestClient(app)


def test_diagnostics_returns_summary_and_items():
    response = client.get("/api/diagnostics")
    assert response.status_code == 200
    data = response.json()

    assert "summary" in data
    assert "items" in data
    assert "error_count" in data["summary"]
    assert "warning_count" in data["summary"]
    assert isinstance(data["items"], list)
    if data["items"]:
        assert "node_type" in data["items"][0]
        assert "action_kind" in data["items"][0]


def test_diagnostics_detects_expected_check_types(monkeypatch):
    sections = {
        "attributes": [{"attribute_name": "return_rate"}],
        "skills": [{"skill_id": "empty_skill"}],
        "intent_profiles": [{"intent_name": "empty_intent"}],
        "relation_types": [{"relation_type": "unused_relation"}],
        "schema_graph_edges": [],
        "object_types": [],
        "queries": [],
        "table_schemas": [],
    }
    graph = {
        "nodes": [
            {"data": {"id": "Attribute:return_rate", "type": "Attribute"}},
            {"data": {"id": "SkillCapability:empty_skill", "type": "SkillCapability"}},
            {"data": {"id": "IntentProfile:empty_intent", "type": "IntentProfile"}},
            {"data": {"id": "RelationType:unused_relation", "type": "RelationType"}},
        ],
        "edges": [],
        "summary": {"node_count": 4, "edge_count": 0},
    }

    monkeypatch.setattr(app_module, "read_all", lambda: sections)
    monkeypatch.setattr(app_module, "build_graph", lambda: graph)
    item_types = {item["type"] for item in app_module.build_diagnostics()["items"]}

    assert "attributes_without_skill" in item_types
    assert "skills_without_attributes" in item_types
    assert "intents_without_skill" in item_types
    assert "relation_types_unused" in item_types


def test_mapping_matrix_returns_attribute_mapping_rows():
    response = client.get("/api/mapping-matrix")
    assert response.status_code == 200
    data = response.json()

    assert "summary" in data
    assert "rows" in data
    assert data["rows"]
    first = data["rows"][0]
    assert "attribute_id" in first
    assert "field_count" in first
    assert "status" in first
