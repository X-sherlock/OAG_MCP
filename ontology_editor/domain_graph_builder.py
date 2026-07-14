from __future__ import annotations

from typing import Any

from .domain_store import read_domain


def build_domain_graph(domain_id: str, version_id: str | None = None) -> dict[str, Any]:
    domain = read_domain(domain_id, version_id)
    plan_metadata = domain.get("plan_metadata") if isinstance(domain.get("plan_metadata"), dict) else {}
    relation_labels = {
        item.get("relation_type"): item.get("relation_name_zh") or item.get("description_zh") or item.get("relation_type")
        for item in domain["relation_types"]
        if isinstance(item, dict)
    }
    relation_labels.setdefault("has_attribute", "拥有属性")

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()

    def add_node(node_id: str, node_type: str, label: str, identity: str, raw: dict[str, Any]) -> None:
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(
            {
                "data": {
                    "id": node_id,
                    "type": node_type,
                    "identity": identity,
                    "label": label or identity,
                    "short_label": label or identity,
                    "origin": "domain_yaml",
                    "enabled": raw.get("enabled", True),
                    "raw": raw,
                }
            }
        )

    for item in domain["object_types"]:
        identity = str(item.get("object_type") or "")
        add_node(f"ObjectType:{identity}", "ObjectType", item.get("object_type_zh") or identity, identity, item)
    for item in domain["attributes"]:
        identity = str(item.get("attribute_name") or "")
        add_node(f"Attribute:{identity}", "Attribute", item.get("attribute_name_zh") or identity, identity, item)
    for item in domain["relation_types"]:
        identity = str(item.get("relation_type") or "")
        add_node(f"RelationType:{identity}", "RelationType", item.get("relation_name_zh") or identity, identity, item)

    edge_ids: set[str] = set()

    def add_edge(edge_id: str, source: str, target: str, relation_type: str, origin: str, raw: dict[str, Any]) -> None:
        if source not in node_ids or target not in node_ids or edge_id in edge_ids:
            return
        edge_ids.add(edge_id)
        edges.append(
            {
                "data": {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "type": relation_type,
                    "label": raw.get("label_zh") or raw.get("relation_name_zh") or relation_labels.get(relation_type) or relation_type,
                    "origin": origin,
                    "editable": origin == "explicit",
                    "raw": raw,
                }
            }
        )

    for item in domain["attributes"]:
        attr = item.get("attribute_name")
        for object_type in item.get("object_types") or []:
            add_edge(
                f"ObjectType:{object_type}__has_attribute__Attribute:{attr}",
                f"ObjectType:{object_type}",
                f"Attribute:{attr}",
                "has_attribute",
                "inferred",
                {"from_file": "attributes.yaml", "attribute_name": attr},
            )
    for item in domain["schema_graph_edges"]:
        source = item.get("from") or item.get("source")
        target = item.get("to") or item.get("target")
        relation_type = item.get("relation_type") or "related_to"
        edge_id = item.get("edge_id") or f"{source}__{relation_type}__{target}"
        add_edge(edge_id, source, target, relation_type, "explicit", item)

    saved_plan = plan_metadata.get("plan") if isinstance(plan_metadata.get("plan"), dict) else {}
    plan = latest_plan_from_domain(domain, relation_labels, saved_plan)
    saved_domain_input = plan_metadata.get("domain_input") if isinstance(plan_metadata.get("domain_input"), dict) else {}
    domain_input = latest_domain_input_from_domain(domain, saved_domain_input)

    return {
        "kind": "domain_graph",
        "domain_id": domain_id,
        "version_id": domain["version_id"],
        "current_version_id": domain.get("domain_meta", {}).get("current_version_id") or domain["version_id"],
        "versions": domain.get("versions") or [],
        "domain": domain["domain"],
        "domain_input": domain_input,
        "plan": plan,
        "feedback": str(plan_metadata.get("feedback") or ""),
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "total_node_count": len(nodes),
            "total_edge_count": len(edges),
        },
        "relation_groups": count_by([edge["data"] for edge in edges], "type"),
        "hidden_counts": {"data_fields": 0, "inferred_edges": 0},
        "search_results": [],
    }


def reconstruct_plan_from_domain(domain: dict[str, Any], relation_labels: dict[str, Any]) -> dict[str, Any]:
    domain_info = domain.get("domain") if isinstance(domain.get("domain"), dict) else {}
    return {
        "summary_zh": domain_info.get("description") or f"{domain_info.get('domain_name') or '该领域'} 的本体关系图已从 YAML 还原。",
        "objects": domain["object_types"],
        "attributes": domain["attributes"],
        "relationships": relationship_rows_from_domain(domain, relation_labels),
        "open_questions": [],
        "revision_notes": ["该规划方案由已落盘 YAML 自动还原，原始规划未保存。"],
    }


def latest_plan_from_domain(domain: dict[str, Any], relation_labels: dict[str, Any], saved_plan: dict[str, Any]) -> dict[str, Any]:
    if not saved_plan:
        return reconstruct_plan_from_domain(domain, relation_labels)
    return {
        "summary_zh": saved_plan.get("summary_zh") or reconstruct_plan_from_domain(domain, relation_labels)["summary_zh"],
        "objects": domain["object_types"],
        "attributes": domain["attributes"],
        "relationships": relationship_rows_from_domain(domain, relation_labels),
        "open_questions": saved_plan.get("open_questions") if isinstance(saved_plan.get("open_questions"), list) else [],
        "revision_notes": saved_plan.get("revision_notes") if isinstance(saved_plan.get("revision_notes"), list) else [],
    }


def relationship_rows_from_domain(domain: dict[str, Any], relation_labels: dict[str, Any]) -> list[dict[str, Any]]:
    relationships = []
    for edge in domain["schema_graph_edges"]:
        if not isinstance(edge, dict):
            continue
        source = edge.get("from") or edge.get("source")
        target = edge.get("to") or edge.get("target")
        relation_type = edge.get("relation_type") or "related_to"
        relationships.append(
            {
                "source": source,
                "target": target,
                "relation_type": relation_type,
                "relation_name_zh": edge.get("relation_name_zh") or edge.get("label_zh") or relation_labels.get(relation_type) or relation_type,
                "reason_zh": edge.get("reason_zh") or edge.get("description") or "",
            }
        )
    return relationships


def reconstruct_domain_input(domain: dict[str, Any]) -> dict[str, Any]:
    return latest_domain_input_from_domain(domain, {})


def latest_domain_input_from_domain(domain: dict[str, Any], saved_domain_input: dict[str, Any]) -> dict[str, Any]:
    domain_info = domain.get("domain") if isinstance(domain.get("domain"), dict) else {}
    return {
        "domain_name": saved_domain_input.get("domain_name") or saved_domain_input.get("name") or domain_info.get("domain_name") or "",
        "description": saved_domain_input.get("description") or domain_info.get("description") or "",
        "objects": domain["object_types"],
        "attributes": domain["attributes"],
        "bulk_text": saved_domain_input.get("bulk_text") or "",
    }


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "")
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts
