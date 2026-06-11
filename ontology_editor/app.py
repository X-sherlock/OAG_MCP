from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ontology_editor.graph_builder import build_graph, build_graph_view
    from ontology_editor.seed_runner import run_seed
    from ontology_editor.validator import validate_ontology
    from ontology_editor.yaml_store import (
        PROJECT_ROOT,
        SUPPORTED_FILES,
        StoreError,
        allowed_path,
        delete_node_payload,
        file_infos,
        read_all,
        read_yaml_file,
        upsert_node_payload,
        write_yaml_file,
    )
else:
    from .graph_builder import build_graph, build_graph_view
    from .seed_runner import run_seed
    from .validator import validate_ontology
    from .yaml_store import (
        PROJECT_ROOT,
        SUPPORTED_FILES,
        StoreError,
        allowed_path,
        delete_node_payload,
        file_infos,
        read_all,
        read_yaml_file,
        upsert_node_payload,
        write_yaml_file,
    )


STATIC_DIR = Path(__file__).resolve().parent / "static"
MODELING_RELATION_TYPES = {
    "supports_attribute",
    "outputs_attribute",
    "provides_attribute",
    "related_query",
    "uses_query",
    "has_query",
    "has_skill",
    "recommends_skill",
    "has_attribute",
    "requires_attribute",
    "returns_attribute",
    "targets_object_type",
    "uses_table",
    "maps_to_field",
    "mapped_to_field",
    "maps_to_attribute",
}

app = FastAPI(title="OAG Ontology Editor", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(Exception)
async def api_unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "error": str(exc) or exc.__class__.__name__,
                "exception_type": exc.__class__.__name__,
            }
        },
    )


class NodePayload(BaseModel):
    node_type: str
    node_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class EdgePayload(BaseModel):
    edge_id: str | None = None
    source: str
    target: str
    relation_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/files")
def api_files() -> dict[str, Any]:
    return {"files": file_infos(), "ontology_root": str((PROJECT_ROOT / "ontology").resolve())}


@app.get("/api/yaml/{file_name}")
def api_get_yaml(file_name: str) -> dict[str, Any]:
    try:
        return {"file": file_name, "data": read_yaml_file(file_name)}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.put("/api/yaml/{file_name}")
def api_put_yaml(file_name: str, payload: Any = Body(...)) -> dict[str, Any]:
    try:
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        result = write_yaml_file(file_name, data)
        validation = validate_ontology()
        return {"ok": True, "write": result, "validation": validation}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/graph")
def api_graph(
    view_mode: str = Query("requirement", pattern="^(overview|requirement|skill|object_attribute|table_mapping|full)$"),
    focus_id: str | None = None,
    depth: int = Query(1, ge=1, le=2),
    include_fields: bool = False,
    include_inferred: bool = False,
    aggregate_edges: bool = False,
    q: str | None = None,
) -> dict[str, Any]:
    try:
        return build_graph_view(
            view_mode=view_mode,
            focus_id=focus_id,
            depth=depth,
            include_fields=include_fields,
            include_inferred=include_inferred,
            aggregate_edges=aggregate_edges,
            q=q,
        )
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/graph/view")
def api_graph_view(
    mode: str = Query("requirement", pattern="^(overview|requirement|skill|object_attribute|table_mapping|full|focus|lineage)$"),
    q: str | None = None,
    node_id: str | None = None,
    focus_id: str | None = None,
    depth: int = Query(1, ge=1, le=2),
    include_fields: bool = False,
    include_inferred: bool = False,
    aggregate_edges: bool = False,
) -> dict[str, Any]:
    try:
        return build_graph_view(
            mode=mode,
            q=q,
            node_id=node_id,
            focus_id=focus_id,
            depth=depth,
            include_fields=include_fields,
            include_inferred=include_inferred,
            aggregate_edges=aggregate_edges,
        )
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/options")
def api_options() -> dict[str, Any]:
    try:
        sections = read_all()
        return {
            "object_types": option_rows(sections.get("object_types"), "ObjectType", "object_type", "object_type_zh"),
            "attributes": option_rows(sections.get("attributes"), "Attribute", "attribute_name", "attribute_name_zh"),
            "skills": option_rows(sections.get("skills"), "SkillCapability", "skill_id", "skill_name"),
            "queries": option_rows(sections.get("queries"), "QueryCapability", "query_id", "query_name"),
            "relation_types": option_rows(sections.get("relation_types"), "RelationType", "relation_type", "relation_name_zh"),
            "data_tables": option_rows(sections.get("table_schemas"), "DataTable", "table_name", "table_name_zh"),
        }
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/diagnostics")
def api_diagnostics() -> dict[str, Any]:
    try:
        return build_diagnostics()
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/mapping-matrix")
def api_mapping_matrix() -> dict[str, Any]:
    try:
        sections = read_all()
        return build_mapping_matrix(sections)
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/node-context/{node_id:path}")
def api_node_context(node_id: str, include_inferred: bool = True) -> dict[str, Any]:
    graph = build_graph()
    nodes = {node["data"]["id"]: node["data"] for node in graph["nodes"]}
    if node_id not in nodes:
        raise http_error(404, f"Node not found: {node_id}")
    edges = [
        edge["data"]
        for edge in graph["edges"]
        if include_inferred or edge["data"].get("origin") != "inferred"
    ]
    incoming = [edge for edge in edges if edge.get("target") == node_id]
    outgoing = [edge for edge in edges if edge.get("source") == node_id]
    incident = incoming + outgoing
    explicit = [edge for edge in incident if edge.get("origin") == "explicit"]

    def related(node_type: str) -> list[dict[str, Any]]:
        ids = {
            edge["source"] if edge.get("target") == node_id else edge["target"]
            for edge in incident
            if nodes.get(edge["source" if edge.get("target") == node_id else "target"], {}).get("type") == node_type
        }
        return [context_node(nodes[item]) for item in sorted(ids)]

    return {
        "node_id": node_id,
        "incoming": incoming[:100],
        "outgoing": outgoing[:100],
        "used_by_intents": related("IntentProfile"),
        "used_by_skills": related("SkillCapability"),
        "related_attributes": related("Attribute"),
        "related_queries": related("QueryCapability"),
        "related_tables": related("DataTable"),
        "explicit_edge_count": len(explicit),
        "inferred_edge_count": len([edge for edge in incident if edge.get("origin") == "inferred"]),
        "delete_blockers": explicit[:100],
        "primary_key_reference_hint": primary_key_reference_hint(node_id, incoming, outgoing),
    }


@app.post("/api/graph/node")
def api_upsert_node(payload: NodePayload) -> dict[str, Any]:
    try:
        result = upsert_node_payload(payload.node_type, payload.node_id, payload.data)
        validation = validate_ontology()
        return {"ok": True, "write": result, "validation": validation, "graph": build_graph()["summary"]}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.delete("/api/graph/node/{node_id:path}")
def api_delete_node(node_id: str, force: bool = False) -> dict[str, Any]:
    graph = build_graph()
    incident = [
        edge["data"]
        for edge in graph["edges"]
        if edge["data"]["source"] == node_id or edge["data"]["target"] == node_id
    ]
    if incident and not force:
        raise http_error(
            409,
            f"Node has {len(incident)} associated edges. Re-run with force=true to delete explicit schema edges.",
            {"incident_edges": incident[:50], "incident_edge_count": len(incident)},
        )
    try:
        node_type = node_id.split(":", 1)[0]
        removed_edges = []
        if force:
            removed_edges = delete_explicit_edges_for_node(node_id)
        result = delete_node_payload(node_type, node_id)
        return {
            "ok": True,
            "deleted_node": result,
            "deleted_schema_edges": removed_edges,
            "remaining_inferred_edge_count": len([edge for edge in incident if edge.get("origin") == "inferred"]),
            "validation": validate_ontology(),
        }
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.post("/api/graph/edge")
def api_upsert_edge(payload: EdgePayload) -> dict[str, Any]:
    try:
        graph = build_graph()
        node_ids = {node["data"]["id"] for node in graph["nodes"]}
        relation_types = {
            item.get("relation_type")
            for item in read_yaml_file("relation_types.yaml")
            if isinstance(item, dict)
        }
        relation_types.update(MODELING_RELATION_TYPES)
        if payload.source not in node_ids:
            raise StoreError(f"source does not exist: {payload.source}")
        if payload.target not in node_ids:
            raise StoreError(f"target does not exist: {payload.target}")
        if payload.relation_type not in relation_types:
            raise StoreError(f"relation_type does not exist in relation_types.yaml: {payload.relation_type}")

        rows = read_yaml_file("schema_graph_edges.yaml")
        if not isinstance(rows, list):
            raise StoreError("schema_graph_edges.yaml must contain a list")
        edge_id = payload.edge_id or f"{payload.source}__{payload.relation_type}__{payload.target}"
        edge = {
            "edge_id": edge_id,
            "from": payload.source,
            "to": payload.target,
            "relation_type": payload.relation_type,
            **payload.properties,
        }
        existing = next((item for item in rows if item.get("edge_id") == edge_id), None)
        action = "updated"
        if existing:
            existing.clear()
            existing.update(edge)
        else:
            rows.append(edge)
            action = "created"
        result = write_yaml_file("schema_graph_edges.yaml", rows)
        validation = validate_ontology()
        return {"ok": True, "action": action, "edge": edge, "write": result, "validation": validation}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.delete("/api/graph/edge/{edge_id:path}")
def api_delete_edge(edge_id: str) -> dict[str, Any]:
    try:
        rows = read_yaml_file("schema_graph_edges.yaml")
        if not isinstance(rows, list):
            raise StoreError("schema_graph_edges.yaml must contain a list")
        for index, item in enumerate(rows):
            if item.get("edge_id") == edge_id:
                deleted = rows.pop(index)
                result = write_yaml_file("schema_graph_edges.yaml", rows)
                return {"ok": True, "deleted": deleted, "write": result, "validation": validate_ontology()}
        raise StoreError(f"Explicit schema edge not found: {edge_id}")
    except StoreError as exc:
        raise http_error(404, str(exc)) from exc


@app.post("/api/validate")
def api_validate() -> dict[str, Any]:
    validation = validate_ontology()
    return {"ok": not validation["errors"], **validation}


@app.post("/api/seed")
def api_seed() -> dict[str, Any]:
    return run_seed()


@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1)) -> dict[str, Any]:
    query = q.casefold()
    graph = build_graph()
    matches = []
    for node in graph["nodes"]:
        data = node["data"]
        haystack = " ".join(flatten_values(data.get("raw", {}))).casefold()
        if query in data["id"].casefold() or query in data["label"].casefold() or query in haystack:
            matches.append(data)
    for edge in graph["edges"]:
        data = edge["data"]
        haystack = " ".join(flatten_values(data.get("raw", {}))).casefold()
        if query in data["id"].casefold() or query in data["label"].casefold() or query in haystack:
            matches.append(data)
    return {"q": q, "count": len(matches), "results": matches[:100]}


@app.get("/api/export")
def api_export() -> StreamingResponse:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_name in SUPPORTED_FILES:
            path = allowed_path(file_name)
            if path.exists():
                archive.write(path, arcname=f"ontology/{file_name}")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="ontology_yaml_export.zip"'},
    )


def option_rows(rows: Any, node_type: str, key: str, label_key: str) -> list[dict[str, Any]]:
    result = []
    for item in rows if isinstance(rows, list) else []:
        if not isinstance(item, dict) or not item.get(key):
            continue
        identity = str(item[key])
        label = str(item.get(label_key) or item.get("description") or identity)
        result.append({"id": f"{node_type}:{identity}", "value": identity, "label": label, "type": node_type})
    return result


def context_node(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id"),
        "type": data.get("type"),
        "label": data.get("label"),
        "enabled": data.get("enabled", True),
    }


def primary_key_reference_hint(node_id: str, incoming: list[dict[str, Any]], outgoing: list[dict[str, Any]]) -> list[str]:
    node_type = node_id.split(":", 1)[0]
    hints = {
        "Attribute": [
            "skills.yaml supported_attributes/output_attributes",
            "queries.yaml output_attributes",
            "intent_profiles.yaml default_attributes",
            "table_schemas.yaml fields.maps_to_attribute",
        ],
        "SkillCapability": ["intent_profiles.yaml primary/secondary/optional skills or skill_priorities"],
        "QueryCapability": ["skills.yaml related_queries"],
        "ObjectType": ["attributes.yaml object_types", "skills.yaml/queries.yaml target_object_type"],
        "DataTable": ["queries.yaml source_tables", "attributes.yaml source_tables"],
    }
    if not incoming and not outgoing:
        return hints.get(node_type, [])
    return hints.get(node_type, []) + ["schema_graph_edges.yaml explicit from/to references"]


def build_diagnostics() -> dict[str, Any]:
    sections = read_all()
    graph = build_graph()
    nodes = {node["data"]["id"]: node["data"] for node in graph["nodes"]}
    edges = [edge["data"] for edge in graph["edges"]]
    explicit_edges = [edge for edge in edges if edge.get("origin") == "explicit"]
    degree = {node_id: 0 for node_id in nodes}
    for edge in edges:
        if edge.get("source") in degree:
            degree[edge["source"]] += 1
        if edge.get("target") in degree:
            degree[edge["target"]] += 1

    items: list[dict[str, Any]] = []
    for node_id, count in degree.items():
        if count == 0 and nodes[node_id].get("type") not in {"Parameter", "DataField"}:
            items.append(
                diagnostic_item(
                    "orphan_nodes",
                    "warning",
                    node_id,
                    f"{node_id} has no incoming or outgoing edges",
                    "确认是否需要补充引用关系，或删除未使用节点。",
                )
            )

    supported_attrs: set[str] = set()
    referenced_skills: set[str] = set()
    disabled_skills: set[str] = set()
    for skill in list_rows(sections.get("skills")):
        skill_id = skill.get("skill_id")
        if not skill_id:
            continue
        attrs = set(list_field(skill, "supported_attributes")) | set(list_field(skill, "output_attributes"))
        supported_attrs.update(str(attr) for attr in attrs)
        if not attrs:
            items.append(
                diagnostic_item(
                    "skills_without_attributes",
                    "warning",
                    f"SkillCapability:{skill_id}",
                    f"Skill {skill_id} has no supported_attributes or output_attributes",
                    "为该 Skill 关联 supported_attributes 或确认它只承担编排能力。",
                    "skills.yaml",
                )
            )
        if skill.get("enabled") is False:
            disabled_skills.add(str(skill_id))

    mapped_attrs = {
        str(edge.get("target", "")).split(":", 1)[1]
        for edge in edges
        if edge.get("type") == "maps_to_attribute" and str(edge.get("target", "")).startswith("Attribute:")
    }
    mapped_attrs.update(
        str(edge.get("source", "")).split(":", 1)[1]
        for edge in edges
        if edge.get("type") == "maps_to_field" and str(edge.get("source", "")).startswith("Attribute:")
    )
    for attr in list_rows(sections.get("attributes")):
        attr_name = attr.get("attribute_name")
        if not attr_name:
            continue
        if str(attr_name) not in supported_attrs:
            items.append(
                diagnostic_item(
                    "attributes_without_skill",
                    "warning",
                    f"Attribute:{attr_name}",
                    f"Attribute {attr_name} is not covered by any Skill supported/output attributes",
                    "为该属性关联 Skill，或确认其仅用于表映射。",
                    "attributes.yaml",
                )
            )
        if str(attr_name) not in mapped_attrs:
            items.append(
                diagnostic_item(
                    "attributes_without_table_mapping",
                    "warning",
                    f"Attribute:{attr_name}",
                    f"Attribute {attr_name} has no DataField mapping",
                    "补充 source_fields/source_tables 或 table_schemas fields.maps_to_attribute。",
                    "attributes.yaml",
                )
            )

    for profile in list_rows(sections.get("intent_profiles")):
        intent = profile.get("intent_name")
        skills = set()
        for field in ("primary_skills", "secondary_skills", "optional_skills"):
            skills.update(str(item) for item in list_field(profile, field))
        priorities = profile.get("skill_priorities")
        if isinstance(priorities, dict):
            skills.update(str(item) for item in priorities)
        elif isinstance(priorities, list):
            skills.update(str(item) for item in priorities)
        referenced_skills.update(skills)
        if not skills:
            items.append(
                diagnostic_item(
                    "intents_without_skill",
                    "warning",
                    f"IntentProfile:{intent}",
                    f"Intent {intent} has no configured Skill",
                    "为该 Intent 设置 primary_skills 或 skill_priorities。",
                    "intent_profiles.yaml",
                )
            )

    used_relation_types = {str(edge.get("type")) for edge in explicit_edges if edge.get("type")}
    for relation in list_rows(sections.get("relation_types")):
        relation_type = relation.get("relation_type")
        if relation_type and str(relation_type) not in used_relation_types:
            items.append(
                diagnostic_item(
                    "relation_types_unused",
                    "warning",
                    f"RelationType:{relation_type}",
                    f"RelationType {relation_type} is not used by explicit schema edges",
                    "确认是否作为 inferred 关系保留，或删除未使用定义。",
                    "relation_types.yaml",
                )
            )

    for skill_id in sorted(disabled_skills & referenced_skills):
        items.append(
            diagnostic_item(
                "disabled_skills_referenced",
                "error",
                f"SkillCapability:{skill_id}",
                f"Disabled Skill {skill_id} is referenced by an Intent",
                "启用该 Skill，或从 Intent 编排中移除引用。",
                "skills.yaml",
            )
        )

    summary = {
        "error_count": len([item for item in items if item["severity"] == "error"]),
        "warning_count": len([item for item in items if item["severity"] == "warning"]),
        "item_count": len(items),
    }
    return {"items": items, "summary": summary}


def diagnostic_item(
    item_type: str,
    severity: str,
    node_id: str,
    message: str,
    suggested_action: str,
    file_name: str | None = None,
) -> dict[str, Any]:
    node_type = node_id.split(":", 1)[0] if ":" in node_id else ""
    action_by_type = {
        "orphan_nodes": "focus_node",
        "skills_without_attributes": "edit_skill_attributes",
        "attributes_without_skill": "link_skill",
        "attributes_without_table_mapping": "open_mapping",
        "intents_without_skill": "edit_intent_skills",
        "relation_types_unused": "review_relation_type",
        "disabled_skills_referenced": "enable_or_unlink_skill",
    }
    return {
        "type": item_type,
        "severity": severity,
        "node_id": node_id,
        "node_type": node_type,
        "action_kind": action_by_type.get(item_type, "inspect"),
        "message": message,
        "file": file_name,
        "suggested_action": suggested_action,
    }


def build_mapping_matrix(sections: dict[str, Any]) -> dict[str, Any]:
    field_map: dict[str, list[dict[str, Any]]] = {}
    for table in list_rows(sections.get("table_schemas")):
        table_name = table.get("table_name")
        table_label = table.get("table_name_zh") or table_name
        for field in list_field(table, "fields"):
            mapped_attr = field.get("maps_to_attribute")
            if not mapped_attr:
                continue
            field_map.setdefault(str(mapped_attr), []).append(
                {
                    "table_name": table_name,
                    "table_label": table_label,
                    "field_name": field.get("field_name"),
                    "field_label": field.get("field_name_zh") or field.get("field_name"),
                    "node_id": f"DataField:{table_name}.{field.get('field_name')}",
                }
            )

    rows_out = []
    status_counts = {"mapped": 0, "missing": 0, "multi_mapped": 0}
    for attr in list_rows(sections.get("attributes")):
        attr_name = attr.get("attribute_name")
        if not attr_name:
            continue
        explicit_fields = []
        for table_name in list_field(attr, "source_tables"):
            for field_name in list_field(attr, "source_fields"):
                explicit_fields.append(
                    {
                        "table_name": table_name,
                        "table_label": table_name,
                        "field_name": field_name,
                        "field_label": field_name,
                        "node_id": f"DataField:{table_name}.{field_name}",
                    }
                )
        fields = field_map.get(str(attr_name), []) + explicit_fields
        seen = set()
        deduped = []
        for item in fields:
            key = (item.get("table_name"), item.get("field_name"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        table_names = sorted({str(item.get("table_name")) for item in deduped if item.get("table_name")})
        status = "missing" if not deduped else "multi_mapped" if len(deduped) > 1 else "mapped"
        status_counts[status] += 1
        rows_out.append(
            {
                "attribute_id": f"Attribute:{attr_name}",
                "attribute_name": attr_name,
                "attribute_label": attr.get("attribute_name_zh") or attr_name,
                "object_types": list_field(attr, "object_types"),
                "field_count": len(deduped),
                "tables": table_names,
                "fields": deduped[:30],
                "status": status,
            }
        )

    return {
        "rows": sorted(rows_out, key=lambda row: (row["status"] != "missing", str(row["attribute_name"]))),
        "summary": {
            "attribute_count": len(rows_out),
            **status_counts,
        },
    }


def list_rows(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def list_field(item: dict[str, Any], field: str) -> list[Any]:
    value = item.get(field)
    return value if isinstance(value, list) else []


def delete_explicit_edges_for_node(node_id: str) -> list[dict[str, Any]]:
    rows = read_yaml_file("schema_graph_edges.yaml")
    if not isinstance(rows, list):
        raise StoreError("schema_graph_edges.yaml must contain a list")
    kept = []
    removed = []
    for item in rows:
        if item.get("from") == node_id or item.get("to") == node_id:
            removed.append(item)
        else:
            kept.append(item)
    if removed:
        write_yaml_file("schema_graph_edges.yaml", kept)
    return removed


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


def http_error(status_code: int, message: str, extra: dict[str, Any] | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": message, **(extra or {})})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ontology_editor.app:app", host="127.0.0.1", port=8010, reload=False)
