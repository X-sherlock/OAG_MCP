from __future__ import annotations

from ontology_editor.graph_builder import build_graph, build_graph_view


def test_focus_view_is_smaller_than_full_graph_and_hides_noisy_details():
    full = build_graph()
    view = build_graph_view(mode="focus", q="return_rate")

    assert view["summary"]["node_count"] < full["summary"]["node_count"]
    assert view["summary"]["edge_count"] < full["summary"]["edge_count"]
    assert all(node["data"]["type"] != "DataField" for node in view["nodes"])
    assert all(edge["data"]["type"] not in {"has_field", "joins_on"} for edge in view["edges"])


def test_focus_view_keeps_relevant_business_nodes_for_query():
    view = build_graph_view(mode="focus", q="fund_performance_analysis")
    node_ids = {node["data"]["id"] for node in view["nodes"]}

    assert "SkillCapability:fund_performance_analysis" in node_ids
    assert any(node_id.startswith("ObjectType:") for node_id in node_ids)
    assert any(node_id.startswith("Attribute:") for node_id in node_ids)


def test_requirement_view_hides_data_fields_by_default():
    view = build_graph_view(view_mode="requirement")

    assert all(node["data"]["type"] != "DataField" for node in view["nodes"])


def test_skill_focus_view_returns_focused_subgraph():
    full = build_graph()
    skill = next(node for node in full["nodes"] if node["data"]["type"] == "SkillCapability")
    view = build_graph_view(view_mode="skill", focus_id=skill["data"]["id"], include_inferred=True)
    node_ids = {node["data"]["id"] for node in view["nodes"]}

    assert skill["data"]["id"] in node_ids
    assert view["summary"]["node_count"] <= full["summary"]["node_count"]


def test_skill_view_can_include_inferred_edges():
    view = build_graph_view(view_mode="skill", include_inferred=True)

    assert any(edge["data"].get("origin") == "inferred" for edge in view["edges"])


def test_aggregate_edges_keeps_cytoscape_edge_shape():
    view = build_graph_view(view_mode="full", include_fields=True, include_inferred=True, aggregate_edges=True)

    assert "edges" in view
    assert all("data" in edge and "source" in edge["data"] and "target" in edge["data"] for edge in view["edges"])


def test_table_field_expansion_is_local_to_selected_table():
    full = build_graph()
    table = next(node for node in full["nodes"] if node["data"]["type"] == "DataTable" and node["data"]["raw"].get("fields"))
    view = build_graph_view(mode="lineage", node_id=table["data"]["id"], include_fields=True, include_inferred=True)
    field_nodes = [node for node in view["nodes"] if node["data"]["type"] == "DataField"]

    assert field_nodes
    assert len(field_nodes) < len([node for node in full["nodes"] if node["data"]["type"] == "DataField"])
    assert all(node["data"]["id"].startswith(f"DataField:{table['data']['identity']}.") for node in field_nodes)
