from __future__ import annotations

from fastapi.testclient import TestClient

from ontology_editor.app import app


client = TestClient(app)


def test_options_returns_modeling_select_sources():
    response = client.get("/api/options")
    assert response.status_code == 200
    data = response.json()

    assert data["object_types"]
    assert data["attributes"]
    assert data["skills"]
    assert data["queries"]
    assert data["relation_types"]
    assert data["data_tables"]
