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

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from oag_mcp.fact_planner import FactPlanner
from oag_mcp.ontology_diagnostics import diagnose_ontology
from oag_mcp.plan_projector import project_plan
from oag_mcp.semantic_frame_builder import semantic_frame_for
from oag_ontology_loader.loader import load_ontology

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


class OAGPlanPayload(BaseModel):
    semantic_frame: dict[str, Any]
    user_context: dict[str, Any] = Field(default_factory=dict)
    output_view: str = "editor"


class OAGSemanticFramePayload(BaseModel):
    question: str
    category: str = ""


class IntentProfilePayload(BaseModel):
    data: dict[str, Any]


class SkillPayload(BaseModel):
    data: dict[str, Any]


class SemanticRelationPayload(BaseModel):
    edge_id: str | None = None
    source: str | None = None
    target: str | None = None
    relation_type: str | None = None
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
            "fact_types": option_rows(sections.get("fact_types"), "FactType", "fact_type", "fact_type_name_zh"),
            "skills": option_rows(sections.get("skills"), "SkillCapability", "skill_id", "skill_name"),
            "queries": option_rows(sections.get("queries"), "QueryCapability", "query_id", "query_name"),
            "relation_types": option_rows(sections.get("relation_types"), "RelationType", "relation_type", "relation_name_zh"),
            "data_tables": option_rows(sections.get("table_schemas"), "DataTable", "table_name", "table_name_zh"),
        }
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/oag/options")
def api_oag_options() -> dict[str, Any]:
    try:
        sections = read_all()
        return build_oag_options(sections)
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.post("/api/oag/semantic-frame")
def api_oag_semantic_frame(payload: OAGSemanticFramePayload) -> dict[str, Any]:
    question = payload.question.strip()
    if not question:
        raise http_error(400, "question must not be empty")
    frame = semantic_frame_for(question, payload.category)
    return {"ok": True, "semantic_frame": frame}


@app.post("/api/oag/plan")
def api_oag_plan(payload: OAGPlanPayload, output_view: str | None = Query(None)) -> dict[str, Any]:
    try:
        planner = FactPlanner(
            ontology_repository=EditorCatalogRepository(),
            graph_repository=EditorSchemaGraphRepository(),
        )
        result = planner.plan(
            semantic_frame=payload.semantic_frame,
            user_context=payload.user_context,
        )
        selected_view = output_view or payload.output_view or "editor"
        editor_plan = project_plan(result, "editor")
        agent_plan = project_plan(result, "agent")
        selected_plan = project_plan(result, selected_view)
        return {
            **selected_plan,
            "ok": editor_plan.get("status") in {"success", "need_clarification"},
            "output_view": selected_view,
            "task_plan": selected_plan,
            "editor_plan": editor_plan,
            "agent_plan": agent_plan,
            "plan_views": {
                "editor": {
                    "label_zh": "Editor 调试计划",
                    "description_zh": "面向 OAG Editor 展示完整 task_graph、诊断、关系扩展证据和调试信息。",
                },
                "agent": {
                    "label_zh": "Agent 执行计划",
                    "description_zh": "面向后续智能体执行 Skill 调用，只保留目标、事实、Skill 调用、覆盖和执行状态。",
                },
            },
        }
    except (StoreError, ValueError) as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/diagnostics")
def api_diagnostics() -> dict[str, Any]:
    try:
        return build_oag_diagnostics()
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/intent-profiles")
def api_intent_profiles() -> dict[str, Any]:
    rows = read_yaml_file("intent_profiles.yaml")
    return {"items": enrich_intent_profiles(rows if isinstance(rows, list) else [])}


@app.put("/api/intent-profiles/{intent_name:path}")
def api_put_intent_profile(intent_name: str, payload: IntentProfilePayload) -> dict[str, Any]:
    try:
        result = upsert_named_yaml_item(
            file_name="intent_profiles.yaml",
            key="intent_name",
            identity=intent_name,
            payload=normalize_intent_profile_payload(intent_name, payload.data),
        )
        return {"ok": True, **result, "validation": validate_ontology()}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/skills")
def api_skills() -> dict[str, Any]:
    rows = read_yaml_file("skills.yaml")
    return {"items": enrich_skills(rows if isinstance(rows, list) else [])}


@app.put("/api/skills/{skill_id:path}")
def api_put_skill(skill_id: str, payload: SkillPayload) -> dict[str, Any]:
    try:
        result = upsert_named_yaml_item(
            file_name="skills.yaml",
            key="skill_id",
            identity=skill_id,
            payload=normalize_skill_payload(skill_id, payload.data),
        )
        return {"ok": True, **result, "validation": validate_ontology()}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/semantic-relations")
def api_semantic_relations() -> dict[str, Any]:
    rows = read_yaml_file("schema_graph_edges.yaml")
    edges = [enrich_semantic_relation(row) for row in rows if isinstance(row, dict) and is_governed_relation(row)]
    return {
        "items": edges,
        "summary": {
            "edge_count": len(edges),
            "attribute_expansion_count": len([edge for edge in edges if edge.get("group") == "attribute_expansion"]),
            "object_relation_count": len([edge for edge in edges if edge.get("group") == "object_relation"]),
        },
    }


@app.post("/api/semantic-relations")
def api_create_semantic_relation(payload: SemanticRelationPayload) -> dict[str, Any]:
    try:
        edge = semantic_relation_payload_to_edge(payload)
        result = upsert_schema_edge(edge)
        return {"ok": True, **result, "validation": validate_ontology()}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.put("/api/semantic-relations/{edge_id:path}")
def api_put_semantic_relation(edge_id: str, payload: SemanticRelationPayload) -> dict[str, Any]:
    try:
        edge = semantic_relation_payload_to_edge(payload, fallback_edge_id=edge_id)
        result = upsert_schema_edge(edge)
        return {"ok": True, **result, "validation": validate_ontology()}
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.delete("/api/semantic-relations/{edge_id:path}")
def api_delete_semantic_relation(edge_id: str) -> dict[str, Any]:
    try:
        rows = read_yaml_file("schema_graph_edges.yaml")
        if not isinstance(rows, list):
            raise StoreError("schema_graph_edges.yaml must contain a list")
        for index, item in enumerate(rows):
            if isinstance(item, dict) and item.get("edge_id") == edge_id:
                deleted = rows.pop(index)
                result = write_yaml_file("schema_graph_edges.yaml", rows)
                return {"ok": True, "deleted": deleted, "write": result, "validation": validate_ontology()}
        raise StoreError(f"找不到要删除的显式语义关系边：{edge_id}")
    except StoreError as exc:
        raise http_error(404, str(exc)) from exc


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


class EditorCatalogRepository:
    def __init__(self) -> None:
        self.catalog = load_ontology(PROJECT_ROOT / "ontology")
        self.objects = {item["object_type"]: item for item in self.catalog.object_types}
        self.attributes = {item["attribute_name"]: item for item in self.catalog.attributes}

    def ping(self) -> None:
        return None

    def domain_enabled(self, domain: str) -> bool:
        return domain == "finance_market"

    def get_objects_by_ids(self, domain: str, object_ids: list[str]) -> list[dict[str, Any]]:
        del domain
        rows = []
        for object_id in object_ids:
            item = self.objects.get(object_id)
            if not item:
                continue
            rows.append(
                {
                    "object_type": "ObjectType",
                    "object_id": object_id,
                    "object_name": item.get("object_type_zh") or object_id,
                    "aliases": [object_id, item.get("object_type_zh") or object_id],
                    "params": {
                        "description": item.get("description", ""),
                        "source_tables": item.get("source_tables", []),
                    },
                }
            )
        return rows

    def get_attributes_by_names(self, domain: str, names: list[str]) -> list[dict[str, Any]]:
        del domain
        rows = []
        for name in names:
            item = self.attributes.get(name)
            if not item:
                continue
            rows.append(
                {
                    "object_type": (item.get("object_types") or [""])[0],
                    "attribute_name": item["attribute_name"],
                    "attribute_name_zh": item.get("attribute_name_zh") or item["attribute_name"],
                    "description": item.get("description", ""),
                    "aliases": item.get("aliases", []),
                    "default_fact_type": item.get("default_fact_type"),
                    "relation_query": item.get("relation_query"),
                    "data_capability_status": item.get("data_capability_status"),
                    "unsupported_reason_code": item.get("unsupported_reason_code"),
                    "params": {
                        "default_fact_type": item.get("default_fact_type"),
                        "relation_query": item.get("relation_query"),
                        "data_capability_status": item.get("data_capability_status"),
                        "unsupported_reason_code": item.get("unsupported_reason_code"),
                    },
                }
            )
        return rows

    def get_fact_types(self, domain: str) -> list[dict[str, Any]]:
        del domain
        return list(self.catalog.fact_types)

    def get_query_capabilities(self, domain: str) -> list[dict[str, Any]]:
        del domain
        return [item for item in self.catalog.queries if item.get("enabled", True)]

    def get_skill_capabilities(self, domain: str) -> list[dict[str, Any]]:
        del domain
        return [item for item in self.catalog.skills if item.get("enabled", True)]

    def get_intent_profiles(self, domain: str) -> list[dict[str, Any]]:
        del domain
        return [item for item in self.catalog.intent_profiles if item.get("enabled", True)]


class EditorSchemaGraphRepository:
    def __init__(self) -> None:
        self.edges = load_ontology(PROJECT_ROOT / "ontology").schema_graph_edges

    def ping(self) -> None:
        return None

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        del domain, max_hops
        starts = {f"{item.get('object_type')}:{item.get('object_id')}" for item in entities}
        return [
            dict(edge)
            for edge in self.edges
            if edge.get("from") in starts or edge.get("to") in starts
        ][:top_k]

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        del domain, entities, max_hops, top_k
        return []


def build_oag_options(sections: dict[str, Any]) -> dict[str, Any]:
    attributes = [
        zh_option(item, "attribute_name", "attribute_name_zh", "指标属性")
        for item in list_rows(sections.get("attributes"))
    ]
    fact_types = [
        zh_option(item, "fact_type", "fact_type_name_zh", "事实类型")
        for item in list_rows(sections.get("fact_types"))
    ]
    relation_types = [
        zh_option(item, "relation_type", "relation_name_zh", "关系类型")
        for item in list_rows(sections.get("relation_types"))
    ]
    intents = [
        zh_option(item, "intent_name", "intent_name_zh", "宽泛意图")
        for item in list_rows(sections.get("intent_profiles"))
        if item.get("enabled", True)
    ]
    return {
        "task_types": [
            {"value": "analyze", "label_zh": "分析"},
            {"value": "compare", "label_zh": "比较"},
            {"value": "rank", "label_zh": "排序"},
            {"value": "screen", "label_zh": "筛选"},
            {"value": "recommend", "label_zh": "推荐"},
            {"value": "explain", "label_zh": "解释"},
            {"value": "query", "label_zh": "查询"},
        ],
        "intents": intents,
        "object_types": [
            zh_option(item, "object_type", "object_type_zh", "目标对象类型")
            for item in list_rows(sections.get("object_types"))
        ],
        "attributes": attributes,
        "fact_types": fact_types,
        "skills": [
            zh_option(item, "skill_id", "skill_name", "Skill 能力")
            for item in list_rows(sections.get("skills"))
            if item.get("enabled", True)
        ],
        "relation_types": relation_types,
        "input_params": build_input_param_options(sections, attributes),
        "fact_requirements": build_fact_requirement_options(
            list_rows(sections.get("intent_profiles")),
            attributes,
            fact_types,
            relation_types,
        ),
        "periods": [
            {"value": "1w", "label_zh": "近一周"},
            {"value": "1m", "label_zh": "近一月"},
            {"value": "3m", "label_zh": "近三个月"},
            {"value": "6m", "label_zh": "近六月"},
            {"value": "1y", "label_zh": "近一年"},
            {"value": "3y", "label_zh": "近三年"},
            {"value": "5y", "label_zh": "近五年"},
            {"value": "ytd", "label_zh": "今年以来"},
            {"value": "si", "label_zh": "成立以来"},
        ],
    }


def build_fact_requirement_options(
    intent_profiles: list[dict[str, Any]],
    attributes: list[dict[str, Any]],
    fact_types: list[dict[str, Any]],
    relation_types: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    attr_labels = {item["value"]: item["label_zh"] for item in attributes}
    fact_labels = {item["value"]: item["label_zh"] for item in fact_types}
    relation_labels = {item["value"]: item["label_zh"] for item in relation_types}
    rows: list[dict[str, Any]] = []
    for intent in intent_profiles:
        if not intent.get("enabled", True):
            continue
        intent_name = str(intent.get("intent_name") or "")
        intent_label = str(intent.get("intent_name_zh") or intent_name)
        subject_types = list_field(intent, "target_object_types") or ["Fund"]
        for index, fact in enumerate(list_field(intent, "fact_requirements_template")):
            if not isinstance(fact, dict):
                continue
            fact_type = str(fact.get("fact_type") or "")
            attribute_name = str(fact.get("attribute_name") or "")
            relation_type = str(fact.get("relation_type") or fact.get("predicate") or "")
            value = f"{intent_name}:{fact_type}:{attribute_name or relation_type or index}"
            fact_label = fact_labels.get(fact_type, fact_type or "事实")
            target_label = attr_labels.get(attribute_name) or relation_labels.get(relation_type) or attribute_name or relation_type or "未命名事实"
            priority = str(fact.get("priority") or "required")
            rows.append(
                {
                    "value": value,
                    "label_zh": f"{intent_label} / {target_label}",
                    "label": f"{intent_label} / {target_label}",
                    "group_zh": intent_label,
                    "intent_name": intent_name,
                    "intent_name_zh": intent_label,
                    "fact_type": fact_type,
                    "fact_type_zh": fact_label,
                    "attribute_name": attribute_name,
                    "attribute_name_zh": attr_labels.get(attribute_name, attribute_name),
                    "relation_type": relation_type,
                    "relation_type_zh": relation_labels.get(relation_type, relation_type),
                    "subject_types": subject_types,
                    "priority": priority,
                    "priority_zh": "必须查询" if priority == "required" else "辅助参考",
                    "reason_zh": fact.get("reason_zh") or "该事实用于支撑当前意图回答。",
                }
            )
    return rows


def build_input_param_options(
    sections: dict[str, Any], attributes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    attr_labels = {item["value"]: item["label_zh"] for item in attributes}
    known_labels = {
        "fund_code": "基金代码",
        "fund_codes": "多只基金代码",
        "fund_universe": "基金池",
        "period": "统计周期",
        "attributes": "事实名称/指标列表",
        "attribute": "单个事实名称",
        "report_date": "报告日期",
        "date": "日期",
        "date_range": "日期范围",
        "date_or_date_range": "日期或日期范围",
        "report_date_or_date_range": "报告日期或日期范围",
        "start_date": "开始日期",
        "end_date": "结束日期",
        "benchmark_code": "基准代码",
        "index_code": "指数代码",
        "fee_type": "费率类型",
        "limit": "返回数量",
        "ranking": "排序规则",
        "filters": "筛选条件",
        "policy_topic": "政策主题",
        "relation_type": "关系类型",
        "target_object_type": "目标对象类型",
    }
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    def add_param(value: Any, source_label: str) -> None:
        text = str(value or "").strip()
        if not text or text in seen:
            return
        seen.add(text)
        label = attr_labels.get(text) or known_labels.get(text) or text.replace("_", " ")
        rows.append(
            {
                "value": text,
                "label_zh": label,
                "label": label,
                "group_zh": source_label,
                "description_zh": f"{source_label}中已经使用的输入参数。",
            }
        )

    for skill in list_rows(sections.get("skills")):
        for param in list_field(skill, "input_params"):
            add_param(param, "Skill 参数")
    for query in list_rows(sections.get("queries")):
        for field in ("required_params", "optional_params"):
            for param in list_field(query, field):
                add_param(param, "查询参数")
    for intent in list_rows(sections.get("intent_profiles")):
        for param in list_field(intent, "required_params"):
            add_param(param, "意图参数")

    return rows


def zh_option(item: dict[str, Any], value_key: str, label_key: str, group: str) -> dict[str, Any]:
    value = str(item.get(value_key) or "")
    label = str(item.get(label_key) or item.get("description_zh") or item.get("description") or value)
    return {
        "value": value,
        "label_zh": label,
        "label": label,
        "group_zh": group,
        "description_zh": item.get("description_zh") or item.get("description") or "",
    }


def build_oag_diagnostics() -> dict[str, Any]:
    catalog = load_ontology(PROJECT_ROOT / "ontology")
    oag_items = [normalize_diagnostic_row(item) for item in diagnose_ontology(catalog)]
    legacy_items = [normalize_diagnostic_row(item) for item in build_diagnostics()["items"]]
    items = dedupe_diagnostics([*oag_items, *legacy_items])
    summary = {
        "error_count": len([item for item in items if item["severity"] == "error"]),
        "warning_count": len([item for item in items if item["severity"] == "warning"]),
        "info_count": len([item for item in items if item["severity"] == "info"]),
        "suggestion_count": len([item for item in items if item["severity"] not in {"error", "warning", "info"}]),
        "item_count": len(items),
    }
    return {"items": items, "summary": summary}


def normalize_diagnostic_row(item: dict[str, Any]) -> dict[str, Any]:
    item_type = item.get("diagnostic_type") or item.get("type") or "ontology_check"
    message = chinese_diagnostic_message(item_type, item)
    action = chinese_diagnostic_action(item_type) or item.get("suggested_action_zh") or item.get("suggested_action")
    node_id = item.get("node_id") or ""
    edge_id = item.get("edge_id") or ""
    target_id = node_id or edge_id
    return {
        **item,
        "diagnostic_type": item_type,
        "type": item_type,
        "severity": item.get("severity") or "warning",
        "node_id": node_id,
        "edge_id": edge_id,
        "target_id": target_id,
        "node_type": item.get("node_type") or (node_id.split(":", 1)[0] if ":" in node_id else ""),
        "action_kind": item.get("action_kind") or diagnostic_action_kind(item_type),
        "diagnostic_message_zh": message,
        "suggested_action_zh": action,
        "message": message,
        "suggested_action": action,
    }


def dedupe_diagnostics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (str(item.get("diagnostic_type")), str(item.get("node_id")), str(item.get("edge_id")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return rows


def chinese_diagnostic_message(item_type: str, item: dict[str, Any]) -> str:
    node_id = item.get("node_id") or item.get("edge_id") or "相关配置"
    messages = {
        "intent_missing_fact_requirements_template": f"{node_id} 缺少事实需求模板，宽泛意图命中后无法稳定生成默认事实。",
        "skill_missing_provides_fact_types": f"{node_id} 没有声明能提供哪些事实类型，OAG 无法可靠判断它能覆盖哪些事实。",
        "skill_missing_supported_attributes": f"{node_id} 没有声明支持哪些属性，OAG 无法可靠判断它支持哪些指标。",
        "skill_missing_supported_subject_types": f"{node_id} 没有声明支持哪些主体对象，OAG 无法可靠判断适用对象。",
        "attribute_without_skill_coverage": f"{node_id} 当前没有任何启用 Skill 声明覆盖。",
        "semantic_edge_missing_reason_zh": f"{node_id} 缺少中文原因，前端无法解释为什么需要这条关系扩展。",
        "semantic_edge_missing_applicability": f"{node_id} 缺少适用任务或适用意图，扩展范围不够可控。",
        "planning_edge_missing_planning_role": f"{node_id} 缺少 planning_role，无法解释该关系在规划中的角色。",
        "planning_edge_missing_auto_expand_mode": f"{node_id} 缺少 auto_expand_mode，无法区分自动扩展、显式查询或依赖关系。",
        "object_profile_relation_auto_expands_always": f"{node_id} 是对象画像关系，但配置为 always 自动扩展，普通指标查询可能被背景对象污染。",
        "relation_edge_unknown_node": f"{node_id} 引用了不存在的节点，关系规划可能跳过该边。",
        "required_fact_without_skill_coverage": f"{node_id} 没有任何 Skill 覆盖，必须补充能力或调整事实优先级。",
        "orphan_nodes": f"{node_id} 当前没有任何入边或出边，可能未参与事实规划。",
        "skills_without_attributes": f"{node_id} 没有声明支持或输出的属性，无法稳定参与事实覆盖匹配。",
        "attributes_without_skill": f"{node_id} 当前没有任何 Skill 声明覆盖。",
        "attributes_without_table_mapping": f"{node_id} 没有配置到表字段的映射，落地查询时可能缺少数据来源。",
        "intents_without_skill": f"{node_id} 没有配置候选 Skill，意图命中后无法推荐执行能力。",
        "relation_types_unused": f"{node_id} 未被显式关系边使用。",
        "disabled_skills_referenced": f"{node_id} 已停用但仍被意图引用。",
    }
    return messages.get(item_type, str(item.get("message") or "本体配置存在需要确认的问题。"))


def chinese_diagnostic_action(item_type: str) -> str:
    actions = {
        "intent_missing_fact_requirements_template": "为该意图补充默认事实需求，并填写事实类型、属性、优先级和中文原因。",
        "skill_missing_provides_fact_types": "为该 Skill 补充能提供的事实类型，例如指标值事实、对象关系事实或对象基础事实。",
        "skill_missing_supported_attributes": "为该 Skill 补充支持属性，或确认它只按对象关系覆盖。",
        "skill_missing_supported_subject_types": "为该 Skill 补充支持对象类型，例如基金或基金集合。",
        "attribute_without_skill_coverage": "补充支持该属性的 Skill 能力声明，或确认该属性暂不参与事实规划。",
        "semantic_edge_missing_reason_zh": "为该关系边补充中文原因，用于解释事实扩展来源。",
        "semantic_edge_missing_applicability": "补充适用任务和适用意图，限制关系扩展生效范围。",
        "planning_edge_missing_planning_role": "补充 planning_role，例如 metric_context、benchmark_context、peer_context 或 profile_context。",
        "planning_edge_missing_auto_expand_mode": "补充 auto_expand_mode，例如 contextual、explicit_only、dependency_only 或 debug_only。",
        "object_profile_relation_auto_expands_always": "将对象画像关系改为 explicit_only，或改为 contextual 并补充严格 trigger_policy。",
        "relation_edge_unknown_node": "检查关系边的起点和终点是否与对象、属性、事实类型或能力节点一致。",
        "required_fact_without_skill_coverage": "补充可覆盖该事实类型、主体对象和属性的 Skill，或调整事实需求优先级。",
        "orphan_nodes": "确认该节点是否需要补充关系，或删除未使用配置。",
        "skills_without_attributes": "为该 Skill 补充支持属性、输出属性或支持关系。",
        "attributes_without_skill": "补充能覆盖该属性的 Skill，或确认该属性暂不参与 OAG 事实规划。",
        "attributes_without_table_mapping": "补充属性的数据来源字段映射，或确认该属性由计算能力生成。",
        "intents_without_skill": "为该 Intent 配置主 Skill、辅助 Skill 或事实需求模板。",
        "relation_types_unused": "确认该关系类型是否作为备用类型保留，或补充对应显式边。",
        "disabled_skills_referenced": "启用该 Skill，或从相关 Intent 中移除引用。",
    }
    return actions.get(item_type, "根据定位对象打开对应治理视图，补齐缺失配置。")


def diagnostic_action_kind(item_type: str) -> str:
    mapping = {
        "intent_missing_fact_requirements_template": "edit_intent_template",
        "skill_missing_provides_fact_types": "edit_skill_coverage",
        "skill_missing_supported_attributes": "edit_skill_coverage",
        "skill_missing_supported_subject_types": "edit_skill_coverage",
        "attribute_without_skill_coverage": "edit_skill_coverage",
        "semantic_edge_missing_reason_zh": "edit_relation",
        "semantic_edge_missing_applicability": "edit_relation",
        "planning_edge_missing_planning_role": "edit_relation",
        "planning_edge_missing_auto_expand_mode": "edit_relation",
        "object_profile_relation_auto_expands_always": "edit_relation",
        "relation_edge_unknown_node": "edit_relation",
        "required_fact_without_skill_coverage": "edit_skill_coverage",
    }
    return mapping.get(item_type, "inspect")


def enrich_intent_profiles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "display_name_zh": item.get("intent_name_zh") or item.get("intent_name"),
            "fact_template_count": len(item.get("fact_requirements_template") or []),
            "enabled_zh": "已启用" if item.get("enabled", True) else "已停用",
        }
        for item in rows
        if isinstance(item, dict)
    ]


def enrich_skills(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "display_name_zh": item.get("skill_name") or item.get("skill_id"),
            "fact_type_count": len(item.get("provides_fact_types") or []),
            "supported_attribute_count": len(item.get("supported_attributes") or item.get("output_attributes") or []),
            "enabled_zh": "已启用" if item.get("enabled", True) else "已停用",
        }
        for item in rows
        if isinstance(item, dict)
    ]


def normalize_intent_profile_payload(intent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = dict(payload)
    item["intent_name"] = intent_name
    item.setdefault("intent_name_zh", intent_name)
    item.setdefault("trigger_aliases", [])
    item.setdefault("default_attributes", [])
    item.setdefault("fact_requirements_template", [])
    for fact in item["fact_requirements_template"]:
        if isinstance(fact, dict):
            fact.setdefault("priority", "required")
            fact.setdefault("reason_zh", "该事实用于支撑当前意图的回答。")
    return item


def normalize_skill_payload(skill_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = dict(payload)
    item["skill_id"] = skill_id
    item.setdefault("skill_name", skill_id)
    item.setdefault("input_params", [])
    item.setdefault("output_attributes", [])
    item.setdefault("supported_attributes", [])
    item.setdefault("supported_subject_types", [item.get("target_object_type") or "Fund"])
    item.setdefault("provides_fact_types", [])
    item.setdefault("supported_fact_requirements", [])
    item.setdefault("related_queries", [])
    item.setdefault("permission_scope", "fund_public_data:read")
    item.setdefault("enabled", True)
    return item


def upsert_named_yaml_item(file_name: str, key: str, identity: str, payload: dict[str, Any]) -> dict[str, Any]:
    rows = read_yaml_file(file_name)
    if not isinstance(rows, list):
        raise StoreError(f"{file_name} must contain a list")
    existing = next((item for item in rows if isinstance(item, dict) and str(item.get(key)) == identity), None)
    action = "updated"
    if existing:
        existing.clear()
        existing.update(payload)
    else:
        rows.append(payload)
        action = "created"
    result = write_yaml_file(file_name, rows)
    return {"action": action, "item": payload, "write": result}


SEMANTIC_RELATION_TYPES = {
    "compared_with",
    "derives",
    "ranked_by_peer",
    "risk_companion",
    "return_companion",
    "benchmark_metric_of",
    "peer_metric_of",
}
OBJECT_RELATION_TYPES = {
    "managed_by",
    "issued_by",
    "managed_by_company",
    "has_benchmark",
    "tracks_index",
    "belongs_to_category",
    "has_dividend",
    "has_fee",
    "has_asset_allocation",
    "has_position",
    "holds_asset",
}


def is_governed_relation(edge: dict[str, Any]) -> bool:
    relation_type = edge.get("relation_type")
    source = str(edge.get("from") or "")
    target = str(edge.get("to") or "")
    return (
        relation_type in SEMANTIC_RELATION_TYPES
        or relation_type in OBJECT_RELATION_TYPES
        or (source.startswith("Attribute:") and target.startswith("Attribute:"))
        or (source.startswith("ObjectType:") and target.startswith("ObjectType:"))
    )


def enrich_semantic_relation(edge: dict[str, Any]) -> dict[str, Any]:
    group = "attribute_expansion" if str(edge.get("from", "")).startswith("Attribute:") else "object_relation"
    return {
        **edge,
        "source": edge.get("from"),
        "target": edge.get("to"),
        "group": group,
        "group_zh": "属性语义扩展关系" if group == "attribute_expansion" else "对象关系",
        "display_name_zh": edge.get("relation_name_zh") or relation_type_label_zh(edge.get("relation_type")),
        "reason_status_zh": "已填写原因" if edge.get("reason_zh") else "缺少中文原因",
    }


def semantic_relation_payload_to_edge(
    payload: SemanticRelationPayload,
    fallback_edge_id: str | None = None,
) -> dict[str, Any]:
    source = payload.source or payload.properties.get("from")
    target = payload.target or payload.properties.get("to")
    relation_type = payload.relation_type or payload.properties.get("relation_type")
    if not source or not target or not relation_type:
        raise StoreError("起点节点、终点节点、关系类型都不能为空")
    edge_id = payload.edge_id or fallback_edge_id or f"{source}__{relation_type}__{target}"
    props = dict(payload.properties)
    for key in ("edge_id", "source", "target", "from", "to", "relation_type"):
        props.pop(key, None)
    return {"edge_id": edge_id, "from": source, "to": target, "relation_type": relation_type, **props}


def upsert_schema_edge(edge: dict[str, Any]) -> dict[str, Any]:
    validate_schema_edge_endpoints(edge)
    rows = read_yaml_file("schema_graph_edges.yaml")
    if not isinstance(rows, list):
        raise StoreError("schema_graph_edges.yaml must contain a list")
    existing = next((item for item in rows if isinstance(item, dict) and item.get("edge_id") == edge["edge_id"]), None)
    action = "updated"
    if existing:
        existing.clear()
        existing.update(edge)
    else:
        rows.append(edge)
        action = "created"
    result = write_yaml_file("schema_graph_edges.yaml", rows)
    return {"action": action, "edge": edge, "write": result}


def validate_schema_edge_endpoints(edge: dict[str, Any]) -> None:
    graph = build_graph()
    node_ids = {node["data"]["id"] for node in graph["nodes"]}
    if edge["from"] not in node_ids:
        raise StoreError(f"起点节点不存在：{edge['from']}")
    if edge["to"] not in node_ids:
        raise StoreError(f"终点节点不存在：{edge['to']}")
    relation_types = {item.get("relation_type") for item in list_rows(read_yaml_file("relation_types.yaml"))}
    relation_types.update(MODELING_RELATION_TYPES)
    relation_types.update(SEMANTIC_RELATION_TYPES)
    relation_types.update(OBJECT_RELATION_TYPES)
    if edge["relation_type"] not in relation_types:
        raise StoreError(f"关系类型不存在：{edge['relation_type']}")


def relation_type_label_zh(relation_type: Any) -> str:
    labels = {
        "compared_with": "对比指标",
        "derives": "派生指标",
        "ranked_by_peer": "扩展为同类排名",
        "risk_companion": "风险伴随指标",
        "return_companion": "收益伴随指标",
        "benchmark_metric_of": "基准相关指标",
        "peer_metric_of": "同类比较相关指标",
        "managed_by": "管理关系",
        "issued_by": "基金公司发行或管理",
        "managed_by_company": "基金公司管理",
        "has_benchmark": "业绩基准关系",
        "tracks_index": "跟踪指数",
        "belongs_to_category": "基金分类",
    }
    return labels.get(str(relation_type or ""), str(relation_type or "关系"))


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
