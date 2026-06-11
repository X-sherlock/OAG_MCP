from __future__ import annotations

import hashlib
from collections import Counter, deque
from typing import Any

from .yaml_store import read_all

CORE_NODE_TYPES = {
    "ObjectType",
    "Attribute",
    "QueryCapability",
    "SkillCapability",
    "IntentProfile",
    "DataSource",
    "DataTable",
}
VIEW_NODE_TYPES = {
    "overview": {"ObjectType", "IntentProfile", "SkillCapability", "QueryCapability"},
    "requirement": {"IntentProfile", "ObjectType", "Attribute", "SkillCapability", "QueryCapability"},
    "skill": {"SkillCapability", "Attribute", "QueryCapability", "ObjectType", "DataTable"},
    "object_attribute": {"ObjectType", "Attribute", "SkillCapability", "QueryCapability"},
    "table_mapping": {"Attribute", "DataTable", "DataField"},
    "full": set(NODE_TYPE_ORDER := (
        "ObjectType",
        "Attribute",
        "RelationType",
        "QueryCapability",
        "SkillCapability",
        "IntentProfile",
        "DataSource",
        "DataTable",
        "DataField",
        "PeriodVariant",
        "InstanceRule",
        "Parameter",
    )),
}
VIEW_EDGE_TYPES = {
    "overview": {
        "targets_object_type",
        "uses_query",
        "related_query",
        "has_query",
        "has_skill",
        "recommends_skill",
    },
    "requirement": {
        "requires_attribute",
        "recommends_skill",
        "has_attribute",
        "supports_attribute",
        "provides_attribute",
        "outputs_attribute",
        "targets_object_type",
        "has_skill",
        "related_query",
        "uses_query",
    },
    "skill": {
        "supports_attribute",
        "provides_attribute",
        "outputs_attribute",
        "related_query",
        "uses_query",
        "targets_object_type",
        "has_skill",
        "has_query",
        "uses_table",
    },
    "object_attribute": {
        "has_attribute",
        "has_skill",
        "has_query",
        "supports_attribute",
        "provides_attribute",
        "outputs_attribute",
        "related_query",
    },
    "table_mapping": {
        "maps_to_field",
        "mapped_to_field",
        "maps_to_attribute",
        "has_field",
        "sourced_from_table",
        "stored_in_table",
    },
    "full": set(),
}
VIEW_MODE_ALIASES = {"focus": "requirement", "lineage": "table_mapping"}
DEFAULT_VIEW_MODE = "requirement"
OVERVIEW_EDGE_TYPES = {
    "sourced_from_table",
    "stored_in_table",
    "targets_object_type",
    "uses_query",
    "outputs_attribute",
    "returns_attribute",
    "has_attribute",
    "has_query",
    "has_skill",
    "provides_attribute",
    "supports_attribute",
    "requires_attribute",
    "recommends_skill",
    "uses_table",
    "contains_table",
    "related_query",
}
FIELD_EDGE_TYPES = {"has_field", "maps_to_field", "mapped_to_field", "maps_to_attribute"}
NOISY_EDGE_TYPES = {"joins_on", "has_field"}
LINEAGE_EDGE_TYPES = {
    "sourced_from_table",
    "stored_in_table",
    "reads_from",
    "uses_table",
    "contains_table",
    "maps_to_field",
    "mapped_to_field",
    "maps_to_attribute",
    "has_field",
    "joins_on",
}
DEFAULT_FOCUS_NODE_TYPES = CORE_NODE_TYPES | {"Parameter"}
NODE_SOURCE_FILES = {
    "ObjectType": "object_types.yaml",
    "Attribute": "attributes.yaml",
    "RelationType": "relation_types.yaml",
    "QueryCapability": "queries.yaml",
    "SkillCapability": "skills.yaml",
    "IntentProfile": "intent_profiles.yaml",
    "DataSource": "data_sources.yaml",
    "DataTable": "table_schemas.yaml",
    "DataField": "table_schemas.yaml",
    "PeriodVariant": "period_variants.yaml",
    "InstanceRule": "instance_rules.yaml",
    "Parameter": "queries.yaml / skills.yaml",
}


def build_graph() -> dict[str, Any]:
    sections = read_all()
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    for item in as_list(sections.get("object_types")):
        object_type = item.get("object_type")
        if object_type:
            add_node(nodes, "ObjectType", object_type, item.get("object_type_zh") or object_type, item)
    for item in as_list(sections.get("attributes")):
        name = item.get("attribute_name")
        if name:
            add_node(nodes, "Attribute", name, item.get("attribute_name_zh") or name, item)
    for item in as_list(sections.get("relation_types")):
        name = item.get("relation_type")
        if name:
            add_node(nodes, "RelationType", name, name, item)
    for item in as_list(sections.get("queries")):
        query_id = item.get("query_id")
        if query_id:
            add_node(nodes, "QueryCapability", query_id, item.get("query_name") or query_id, item)
        for parameter in as_list(item.get("required_params")) + as_list(item.get("optional_params")):
            add_node(nodes, "Parameter", parameter, parameter, {"parameter_name": parameter})
    for item in as_list(sections.get("skills")):
        skill_id = item.get("skill_id")
        if skill_id:
            add_node(nodes, "SkillCapability", skill_id, item.get("skill_name") or skill_id, item)
        for parameter in as_list(item.get("input_params")):
            add_node(nodes, "Parameter", parameter, parameter, {"parameter_name": parameter})
    for item in as_list(sections.get("intent_profiles")):
        name = item.get("intent_name")
        if name:
            add_node(nodes, "IntentProfile", name, item.get("intent_name_zh") or name, item)
    for item in as_list(sections.get("data_sources")):
        source_id = item.get("source_id")
        if source_id:
            add_node(nodes, "DataSource", source_id, source_id, item)
    for table in as_list(sections.get("table_schemas")):
        table_name = table.get("table_name")
        if not table_name:
            continue
        add_node(nodes, "DataTable", table_name, table.get("table_name_zh") or table_name, table)
        for field in as_list(table.get("fields")):
            field_name = field.get("field_name")
            if field_name:
                raw = {**field, "table_name": table_name}
                add_node(
                    nodes,
                    "DataField",
                    f"{table_name}.{field_name}",
                    field.get("field_name_zh") or field_name,
                    raw,
                )
    for item in as_list((sections.get("period_variants") or {}).get("periods")):
        code = item.get("code")
        if code:
            add_node(nodes, "PeriodVariant", code, item.get("name_zh") or code, item)
    for item in as_list(sections.get("instance_rules")):
        rule_id = item.get("rule_id")
        if rule_id:
            add_node(nodes, "InstanceRule", rule_id, rule_id, item)

    for item in as_list(sections.get("schema_graph_edges")):
        source = item.get("from") or item.get("source")
        target = item.get("to") or item.get("target")
        relation_type = item.get("relation_type")
        if source and target and relation_type:
            edge_id = item.get("edge_id") or stable_edge_id(source, target, relation_type, "explicit")
            add_edge(edges, edge_id, source, target, relation_type, item, explicit=True)

    infer_edges(sections, nodes, edges)
    apply_degrees(nodes, edges)
    return {
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
        "summary": {"node_count": len(nodes), "edge_count": len(edges)},
    }


def build_graph_view(
    *,
    mode: str = "focus",
    view_mode: str | None = None,
    q: str | None = None,
    node_id: str | None = None,
    focus_id: str | None = None,
    depth: int = 2,
    include_fields: bool = False,
    include_inferred: bool = False,
    aggregate_edges: bool = False,
) -> dict[str, Any]:
    graph = build_graph()
    all_nodes = {node["data"]["id"]: node for node in graph["nodes"]}
    all_edges = graph["edges"]
    requested_mode = view_mode or mode or DEFAULT_VIEW_MODE
    legacy_query_focus = requested_mode in {"focus", "lineage"} and bool(q) and not (focus_id or node_id)
    mode = normalize_view_mode(requested_mode)
    focus_id = focus_id or node_id
    depth = max(1, min(depth, 2))
    requested_include_fields = include_fields
    include_fields = include_fields and (mode == "full" or bool(focus_id) or legacy_query_focus)

    allowed_node_types = VIEW_NODE_TYPES[mode]
    allowed_edge_types = VIEW_EDGE_TYPES[mode]
    visible_nodes = {
        item_id
        for item_id, node in all_nodes.items()
        if mode == "full" or node["data"].get("type") in allowed_node_types
    }
    visible_edges = [
        edge
        for edge in all_edges
        if (mode == "full" or edge["data"].get("type") in allowed_edge_types)
        and edge["data"].get("source") in visible_nodes
        and edge["data"].get("target") in visible_nodes
        and (include_inferred or edge["data"].get("origin") != "inferred")
    ]

    if not include_fields:
        visible_nodes = {
            item_id for item_id in visible_nodes if all_nodes[item_id]["data"].get("type") != "DataField"
        }
        visible_edges = [
            edge
            for edge in visible_edges
            if edge["data"].get("type") not in FIELD_EDGE_TYPES
            and not str(edge["data"].get("source", "")).startswith("DataField:")
            and not str(edge["data"].get("target", "")).startswith("DataField:")
        ]

    if mode != "full" and not focus_id and not legacy_query_focus:
        visible_nodes = {
            item_id for item_id in visible_nodes if all_nodes[item_id]["data"].get("enabled", True) is not False
        }
        visible_edges = [
            edge
            for edge in visible_edges
            if all_nodes[edge["data"]["source"]]["data"].get("enabled", True) is not False
            and all_nodes[edge["data"]["target"]]["data"].get("enabled", True) is not False
        ]

    if legacy_query_focus:
        seeds = seed_node_ids(
            all_nodes,
            q=q,
            node_id=None,
            fallback_types={"IntentProfile", "ObjectType", "SkillCapability", "Attribute"},
        )
        visible_nodes = focus_subgraph_nodes(seeds, visible_nodes, visible_edges, depth=depth)
    elif focus_id:
        seeds = {focus_id} if focus_id in all_nodes else set()
        visible_nodes = focus_subgraph_nodes(seeds, visible_nodes, visible_edges, depth=depth)

    visible_edges = [
        edge
        for edge in visible_edges
        if edge["data"].get("source") in visible_nodes and edge["data"].get("target") in visible_nodes
    ]
    nodes = [with_view_metadata(all_nodes[node_id], all_edges) for node_id in sorted(visible_nodes, key=node_sort_key(all_nodes))]
    edges = sorted(visible_edges, key=lambda edge: (edge["data"].get("type", ""), edge["data"].get("id", "")))
    if aggregate_edges:
        edges = aggregate_edge_list(edges)
    hidden = hidden_counts(graph, nodes, edges)
    summary = {
        "view_mode": mode,
        "focus_id": focus_id,
        "mode": mode,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "total_node_count": graph["summary"]["node_count"],
        "total_edge_count": graph["summary"]["edge_count"],
        "hidden_field_count": hidden["data_fields"],
        "hidden_inferred_edge_count": hidden["inferred_edges"],
    }
    return {
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "search_results": search_results(graph, q, include_fields=requested_include_fields) if q else [],
        "hidden_counts": hidden,
        "relation_groups": relation_groups(edges),
    }


def aggregate_edge_list(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for edge in edges:
        data = edge["data"]
        key = (data.get("source", ""), data.get("target", ""), data.get("type", ""))
        grouped.setdefault(key, []).append(edge)

    result: list[dict[str, Any]] = []
    for (source, target, relation_type), group in grouped.items():
        if len(group) == 1:
            result.append(group[0])
            continue
        first = group[0]["data"]
        bundle_id = f"bundle:{stable_edge_id(source, target, relation_type, 'bundle')}"
        result.append(
            {
                "data": {
                    **first,
                    "id": bundle_id,
                    "label": f"{relation_type} × {len(group)}",
                    "is_bundle": True,
                    "bundle_count": len(group),
                    "bundled_edges": [edge["data"] for edge in group],
                    "origin": "bundle",
                    "editable": False,
                }
            }
        )
    return result


def normalize_view_mode(mode: str | None) -> str:
    normalized = (mode or DEFAULT_VIEW_MODE).strip()
    normalized = VIEW_MODE_ALIASES.get(normalized, normalized)
    if normalized not in VIEW_NODE_TYPES:
        return DEFAULT_VIEW_MODE
    return normalized


def focus_subgraph_nodes(
    seeds: set[str],
    visible_nodes: set[str],
    visible_edges: list[dict[str, Any]],
    *,
    depth: int,
) -> set[str]:
    if not seeds:
        return set()
    seeds = seeds & visible_nodes
    if not seeds:
        return set()
    adjacency = build_adjacency(visible_edges)
    focused: set[str] = set()
    queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds)
    while queue:
        current, distance = queue.popleft()
        if current in focused or current not in visible_nodes:
            continue
        focused.add(current)
        if distance >= depth:
            continue
        for _edge, neighbor_id in adjacency.get(current, []):
            if neighbor_id in visible_nodes:
                queue.append((neighbor_id, distance + 1))
    return focused


def short_label(label: str | None, *, node_id: str, max_len: int = 18) -> str:
    value = str(label or node_id)
    if len(value) <= max_len:
        return value
    return f"{value[:16]}…"


def search_results(graph: dict[str, Any], q: str | None, *, include_fields: bool, limit: int = 80) -> list[dict[str, Any]]:
    query = (q or "").strip().casefold()
    if not query:
        return []
    results = []
    for node in graph["nodes"]:
        data = node["data"]
        if data.get("type") == "DataField" and not include_fields:
            continue
        matched_field = matched_search_field(data, query)
        if matched_field:
            results.append(
                {
                    "id": data["id"],
                    "type": data.get("type", ""),
                    "label": data.get("label") or data["id"],
                    "short_label": data.get("short_label") or short_label(data.get("label"), node_id=data["id"]),
                    "matched_field": matched_field,
                }
            )
        if len(results) >= limit:
            break
    return results


def matched_search_field(data: dict[str, Any], query: str) -> str:
    checks = [
        ("id", data.get("id", "")),
        ("label", data.get("label", "")),
        ("identity", data.get("identity", "")),
    ]
    raw = data.get("raw", {})
    if isinstance(raw, dict):
        checks.extend((str(key), value) for key, value in raw.items())
    for field, value in checks:
        if query in " ".join(flatten_values(value)).casefold():
            return field
    return ""


def add_node(
    nodes: dict[str, dict[str, Any]],
    node_type: str,
    identity: str,
    label: str,
    raw: dict[str, Any],
) -> None:
    node_id = f"{node_type}:{identity}"
    label_text = str(label or node_id)
    nodes[node_id] = {
        "data": {
            "id": node_id,
            "label": label_text,
            "short_label": short_label(label_text, node_id=node_id),
            "type": node_type,
            "identity": identity,
            "enabled": raw.get("enabled", True),
            "raw": raw,
            "source_file": NODE_SOURCE_FILES.get(node_type, ""),
            "degree": 1,
        }
    }


def add_edge(
    edges: dict[str, dict[str, Any]],
    edge_id: str,
    source: str,
    target: str,
    relation_type: str,
    raw: dict[str, Any],
    *,
    explicit: bool,
) -> None:
    if source == target:
        return
    normalized_id = edge_id or stable_edge_id(source, target, relation_type, "explicit" if explicit else "inferred")
    if normalized_id in edges:
        return
    edges[normalized_id] = {
        "data": {
            "id": normalized_id,
            "source": source,
            "target": target,
            "label": relation_type,
            "type": relation_type,
            "raw": raw,
            "origin": "explicit" if explicit else "inferred",
            "editable": explicit,
        }
    }


def infer_edges(
    sections: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
) -> None:
    node_ids = set(nodes)

    for table in as_list(sections.get("table_schemas")):
        table_name = table.get("table_name")
        table_id = f"DataTable:{table_name}"
        for field in as_list(table.get("fields")):
            field_name = field.get("field_name")
            field_id = f"DataField:{table_name}.{field_name}"
            add_inferred(edges, node_ids, table_id, field_id, "has_field", {"from_file": "table_schemas.yaml"})
            mapped = field.get("maps_to_attribute")
            if mapped:
                add_inferred(
                    edges,
                    node_ids,
                    field_id,
                    f"Attribute:{mapped}",
                    "maps_to_attribute",
                    {"from_file": "table_schemas.yaml", "field": field_name},
                )

    for attr in as_list(sections.get("attributes")):
        attr_name = attr.get("attribute_name")
        attr_id = f"Attribute:{attr_name}"
        for object_type in as_list(attr.get("object_types")):
            add_inferred(
                edges,
                node_ids,
                f"ObjectType:{object_type}",
                attr_id,
                "has_attribute",
                {"from_file": "attributes.yaml", "attribute_name": attr_name},
            )
        source_fields = set(str(x) for x in as_list(attr.get("source_fields")))
        for table_name in as_list(attr.get("source_tables")):
            if not source_fields:
                continue
            for table in as_list(sections.get("table_schemas")):
                if table.get("table_name") != table_name:
                    continue
                for field in as_list(table.get("fields")):
                    field_name = str(field.get("field_name"))
                    if field_name in source_fields:
                        add_inferred(
                            edges,
                            node_ids,
                            attr_id,
                            f"DataField:{table_name}.{field_name}",
                            "maps_to_field",
                            {"from_file": "attributes.yaml", "attribute_name": attr_name},
                        )

    for query in as_list(sections.get("queries")):
        query_id = query.get("query_id")
        query_node = f"QueryCapability:{query_id}"
        if query.get("target_object_type"):
            add_inferred(
                edges,
                node_ids,
                f"ObjectType:{query.get('target_object_type')}",
                query_node,
                "has_query",
                {"from_file": "queries.yaml", "query_id": query_id},
            )
        for attr in as_list(query.get("output_attributes")):
            add_inferred(edges, node_ids, query_node, f"Attribute:{attr}", "outputs_attribute", {"from_file": "queries.yaml"})
        for table_name in as_list(query.get("source_tables")):
            add_inferred(edges, node_ids, query_node, f"DataTable:{table_name}", "uses_table", {"from_file": "queries.yaml"})

    for skill in as_list(sections.get("skills")):
        skill_id = skill.get("skill_id")
        skill_node = f"SkillCapability:{skill_id}"
        if skill.get("target_object_type"):
            add_inferred(
                edges,
                node_ids,
                f"ObjectType:{skill.get('target_object_type')}",
                skill_node,
                "has_skill",
                {"from_file": "skills.yaml", "skill_id": skill_id},
            )
        for attr in as_list(skill.get("output_attributes")):
            add_inferred(edges, node_ids, skill_node, f"Attribute:{attr}", "provides_attribute", {"from_file": "skills.yaml"})
        for attr in as_list(skill.get("supported_attributes")):
            add_inferred(edges, node_ids, skill_node, f"Attribute:{attr}", "supports_attribute", {"from_file": "skills.yaml"})
        for query_id in as_list(skill.get("related_queries")):
            add_inferred(edges, node_ids, skill_node, f"QueryCapability:{query_id}", "related_query", {"from_file": "skills.yaml"})

    for profile in as_list(sections.get("intent_profiles")):
        intent = profile.get("intent_name")
        intent_node = f"IntentProfile:{intent}"
        for attr in as_list(profile.get("default_attributes")):
            add_inferred(edges, node_ids, intent_node, f"Attribute:{attr}", "requires_attribute", {"from_file": "intent_profiles.yaml"})
        for field in ("primary_skills", "secondary_skills", "optional_skills", "skill_priorities"):
            values = profile.get(field)
            if isinstance(values, dict):
                skill_ids = values.keys()
            else:
                skill_ids = as_list(values)
            for skill_id in skill_ids:
                add_inferred(edges, node_ids, intent_node, f"SkillCapability:{skill_id}", "recommends_skill", {"from_file": "intent_profiles.yaml"})

    for source in as_list(sections.get("data_sources")):
        source_id = source.get("source_id")
        for table_name in as_list(source.get("tables")):
            add_inferred(edges, node_ids, f"DataSource:{source_id}", f"DataTable:{table_name}", "contains_table", {"from_file": "data_sources.yaml"})


def add_inferred(
    edges: dict[str, dict[str, Any]],
    node_ids: set[str],
    source: str,
    target: str,
    relation_type: str,
    raw: dict[str, Any],
) -> None:
    if source not in node_ids or target not in node_ids:
        return
    edge_id = stable_edge_id(source, target, relation_type, "inferred")
    add_edge(edges, edge_id, source, target, relation_type, raw, explicit=False)


def apply_degrees(nodes: dict[str, dict[str, Any]], edges: dict[str, dict[str, Any]]) -> None:
    counts = {node_id: 0 for node_id in nodes}
    for edge in edges.values():
        data = edge["data"]
        if data["source"] in counts:
            counts[data["source"]] += 1
        if data["target"] in counts:
            counts[data["target"]] += 1
    for node_id, count in counts.items():
        nodes[node_id]["data"]["degree"] = count


def stable_edge_id(source: str, target: str, relation_type: str, origin: str) -> str:
    seed = f"{origin}:{source}:{relation_type}:{target}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"{origin}:{digest}"


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def seed_node_ids(
    nodes: dict[str, dict[str, Any]],
    *,
    q: str | None,
    node_id: str | None,
    fallback_types: set[str],
) -> set[str]:
    if node_id and node_id in nodes:
        return {node_id}
    query = (q or "").strip().casefold()
    if query:
        matches = [
            node_id
            for node_id, node in nodes.items()
            if node["data"].get("type") != "DataField" and query_matches(node["data"], query)
        ]
        if matches:
            return set(matches[:40])
    return {
        node_id
        for node_id, node in nodes.items()
        if node["data"].get("type") in fallback_types and node["data"].get("enabled", True) is not False
    }


def expand_from_seeds(
    seeds: set[str],
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    depth: int,
    allowed_node_types: set[str],
    allowed_edge_types: set[str] | None = None,
    blocked_edge_types: set[str] | None = None,
    seed_only_edge_types: set[str] | None = None,
    include_fields: bool,
    include_inferred: bool,
) -> set[str]:
    visible: set[str] = set()
    queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds if seed in nodes)
    adjacency = build_adjacency(edges)
    blocked_edge_types = blocked_edge_types or set()
    seed_only_edge_types = seed_only_edge_types or set()

    while queue:
        current, distance = queue.popleft()
        if current in visible:
            continue
        node_type = nodes[current]["data"].get("type")
        if node_type not in allowed_node_types:
            continue
        if node_type == "DataField" and not include_fields:
            continue
        visible.add(current)
        if distance >= depth:
            continue
        for edge, neighbor_id in adjacency.get(current, []):
            edge_type = edge["data"].get("type")
            if allowed_edge_types is not None and edge_type not in allowed_edge_types:
                continue
            if edge_type in seed_only_edge_types and current not in seeds:
                continue
            if edge_type in blocked_edge_types:
                continue
            if not include_inferred and edge["data"].get("origin") == "inferred":
                continue
            if neighbor_id not in nodes:
                continue
            neighbor_type = nodes[neighbor_id]["data"].get("type")
            if neighbor_type == "DataField" and not include_fields:
                continue
            if neighbor_type in allowed_node_types:
                queue.append((neighbor_id, distance + 1))
    return visible


def build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[tuple[dict[str, Any], str]]]:
    adjacency: dict[str, list[tuple[dict[str, Any], str]]] = {}
    for edge in edges:
        source = edge["data"].get("source")
        target = edge["data"].get("target")
        adjacency.setdefault(source, []).append((edge, target))
        adjacency.setdefault(target, []).append((edge, source))
    return adjacency


def directly_connected_fields(node_id: str, edges: list[dict[str, Any]]) -> set[str]:
    fields = set()
    for edge in edges:
        data = edge["data"]
        if data.get("type") != "has_field":
            continue
        if data.get("source") == node_id and str(data.get("target", "")).startswith("DataField:"):
            fields.add(data["target"])
        if data.get("target") == node_id and str(data.get("source", "")).startswith("DataField:"):
            fields.add(data["source"])
    return fields


def edges_between(
    edges: list[dict[str, Any]],
    visible_nodes: set[str],
    *,
    include_inferred: bool,
) -> list[dict[str, Any]]:
    return [
        edge
        for edge in edges
        if edge["data"].get("source") in visible_nodes
        and edge["data"].get("target") in visible_nodes
        and (include_inferred or edge["data"].get("origin") != "inferred")
    ]


def with_view_metadata(node: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    data = dict(node["data"])
    data["short_label"] = data.get("short_label") or short_label(data.get("label"), node_id=data["id"])
    if data.get("type") == "DataTable":
        field_count = 0
        for edge in edges:
            edge_data = edge["data"]
            if edge_data.get("type") == "has_field" and edge_data.get("source") == data["id"]:
                field_count += 1
        data["field_count"] = field_count
    return {"data": data}


def hidden_counts(graph: dict[str, Any], nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    visible_node_ids = {node["data"]["id"] for node in nodes}
    visible_edge_ids = {edge["data"]["id"] for edge in edges}
    all_field_ids = {node["data"]["id"] for node in graph["nodes"] if node["data"].get("type") == "DataField"}
    all_join_ids = {edge["data"]["id"] for edge in graph["edges"] if edge["data"].get("type") == "joins_on"}
    inferred_ids = {edge["data"]["id"] for edge in graph["edges"] if edge["data"].get("origin") == "inferred"}
    return {
        "nodes": graph["summary"]["node_count"] - len(visible_node_ids),
        "edges": graph["summary"]["edge_count"] - len(visible_edge_ids),
        "data_fields": len(all_field_ids - visible_node_ids),
        "joins_on": len(all_join_ids - visible_edge_ids),
        "inferred_edges": len(inferred_ids - visible_edge_ids),
    }


def relation_groups(edges: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(edge["data"].get("type", "unknown") for edge in edges)
    return dict(sorted(counts.items()))


def node_sort_key(nodes: dict[str, dict[str, Any]]):
    order = {
        "IntentProfile": 0,
        "ObjectType": 1,
        "SkillCapability": 2,
        "QueryCapability": 3,
        "Attribute": 4,
        "DataSource": 5,
        "DataTable": 6,
        "DataField": 7,
        "Parameter": 8,
    }

    def sort_key(node_id: str) -> tuple[int, str]:
        node_type = nodes[node_id]["data"].get("type")
        return (order.get(node_type, 99), node_id)

    return sort_key


def query_matches(data: dict[str, Any], query: str) -> bool:
    haystack = " ".join(
        [
            str(data.get("id", "")),
            str(data.get("label", "")),
            str(data.get("identity", "")),
            *flatten_values(data.get("raw", {})),
        ]
    ).casefold()
    return query in haystack


def flatten_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.append(str(key))
            out.extend(flatten_values(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(flatten_values(item))
        return out
    if value is None:
        return []
    return [str(value)]
