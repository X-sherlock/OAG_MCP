from __future__ import annotations

import io
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import yaml

PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from oag_mcp.llm_config import load_llm_config
from oag_mcp.oag_v2_planner import OAGV2Planner
from oag_mcp.ontology_diagnostics import diagnose_ontology
from oag_mcp.plan_projector import project_plan
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
        dump_yaml,
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
        dump_yaml,
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
    raw_question: str | None = None
    semantic_frame: dict[str, Any]
    recognized_intents: list[dict[str, Any]] = Field(default_factory=list)
    selector_mode: str = "rule"
    planning_options: dict[str, Any] = Field(default_factory=dict)
    user_context: dict[str, Any] = Field(default_factory=dict)
    output_view: str = "editor"


class ScenarioDraftPayload(BaseModel):
    semantic_frame: dict[str, Any]
    intent_name: str | None = None
    intent_name_zh: str | None = None
    trigger_aliases: list[str] = Field(default_factory=list)
    user_context: dict[str, Any] = Field(default_factory=dict)


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


class RelationStrategyDraftsPayload(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)


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


@app.get("/api/oag/workbench")
def api_oag_workbench() -> dict[str, Any]:
    try:
        sections = read_all()
        diagnostics = build_oag_diagnostics()
        return build_oag_workbench(sections, diagnostics)
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.get("/api/oag/workbench/sample-plans")
def api_oag_workbench_sample_plans() -> dict[str, Any]:
    try:
        sections = read_all()
        diagnostics = build_oag_diagnostics()
        workbench = build_oag_workbench(sections, diagnostics)
        return build_sample_plan_validation(workbench)
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


@app.post("/api/oag/scenario-draft")
def api_oag_scenario_draft(payload: ScenarioDraftPayload) -> dict[str, Any]:
    try:
        planner = OAGV2Planner(
            ontology_repository=EditorCatalogRepository(),
            graph_repository=EditorSchemaGraphRepository(),
        )
        result = planner.plan(
            semantic_frame=payload.semantic_frame,
            selector_mode="rule",
            user_context={**payload.user_context, "debug": True},
        )
        return build_scenario_draft(payload, result)
    except (StoreError, ValueError) as exc:
        raise http_error(400, str(exc)) from exc


@app.post("/api/oag/plan")
def api_oag_plan(payload: OAGPlanPayload, output_view: str | None = Query(None)) -> dict[str, Any]:
    try:
        planner = OAGV2Planner(
            ontology_repository=EditorCatalogRepository(),
            graph_repository=EditorSchemaGraphRepository(),
        )
        result = planner.plan(
            semantic_frame=payload.semantic_frame,
            raw_question=payload.raw_question,
            recognized_intents=payload.recognized_intents,
            selector_mode=payload.selector_mode,
            planning_options=payload.planning_options,
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
            "llm_config_status": result.get("llm_config_status") or load_llm_config(PROJECT_ROOT).status(),
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


@app.get("/api/oag/llm-status")
def api_oag_llm_status() -> dict[str, Any]:
    return load_llm_config(PROJECT_ROOT).status()


@app.get("/api/oag/golden-questions")
def api_oag_golden_questions() -> dict[str, Any]:
    try:
        return run_golden_questions()
    except StoreError as exc:
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


@app.post("/api/oag/relation-strategy-drafts")
def api_apply_relation_strategy_drafts(payload: RelationStrategyDraftsPayload) -> dict[str, Any]:
    try:
        edges = [relation_strategy_draft_to_edge(item) for item in payload.items]
        if not edges:
            raise StoreError("没有可写入的关系策略建议。")
        result = upsert_schema_edges(edges)
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


@app.get("/api/oag/publish-package")
def api_oag_publish_package() -> StreamingResponse:
    try:
        sections = read_all()
        diagnostics = build_oag_diagnostics()
        workbench = build_oag_workbench(sections, diagnostics)
        sample_validation = build_sample_plan_validation(workbench)
        manifest = build_publish_manifest(workbench, sample_validation)
        buffer = build_publish_package_zip(sections, workbench, sample_validation, manifest)
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="oag_model_publish_package.zip"'},
        )
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


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
                }
            )
        return rows

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


def build_oag_workbench(sections: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    options = build_oag_options(sections)
    skills = [item for item in list_rows(sections.get("skills")) if item.get("enabled", True)]
    intent_profiles = [item for item in list_rows(sections.get("intent_profiles")) if item.get("enabled", True)]
    governed_edges = [
        enrich_semantic_relation(item)
        for item in list_rows(sections.get("schema_graph_edges"))
        if is_governed_relation(item)
    ]
    coverage_rows = build_skill_coverage_matrix(options["fact_requirements"], skills)
    scenario_rows = build_scenario_matrix(intent_profiles, coverage_rows)
    relation_strategy = build_relation_strategy_summary(governed_edges)
    diagnostic_items = diagnostics.get("items") or []
    release_readiness = build_release_readiness(diagnostics, coverage_rows, relation_strategy)
    return {
        "summary": {
            "domain_zh": "基金投研",
            "domain": "finance_market",
            "object_type_count": len(list_rows(sections.get("object_types"))),
            "attribute_count": len(list_rows(sections.get("attributes"))),
            "fact_type_count": len(list_rows(sections.get("fact_types"))),
            "scenario_count": len(scenario_rows),
            "skill_count": len(skills),
            "relation_policy_count": len(governed_edges),
            "diagnostic_count": diagnostics.get("summary", {}).get("item_count", len(diagnostic_items)),
            "publish_status_zh": release_readiness["status_zh"],
        },
        "modeling_guide": build_modeling_guide(sections, scenario_rows, coverage_rows, relation_strategy, diagnostics),
        "scenario_matrix": scenario_rows,
        "skill_coverage_matrix": coverage_rows,
        "relation_strategy": relation_strategy,
        "diagnostics_governance": {
            "summary": diagnostics.get("summary", {}),
            "items": diagnostic_items[:12],
            "top_actions": build_top_diagnostic_actions(diagnostic_items),
        },
        "test_publish": {
            "sample_scenarios": build_sample_scenarios(scenario_rows),
            "release_readiness": release_readiness,
        },
    }


def build_skill_coverage_matrix(fact_requirements: list[dict[str, Any]], skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for fact in fact_requirements:
        covering_skills = [skill for skill in skills if skill_covers_fact(skill, fact)]
        required = fact.get("priority") == "required"
        rows.append(
            {
                "fact_requirement_id": fact["value"],
                "label_zh": fact.get("label_zh") or fact["value"],
                "intent_name": fact.get("intent_name"),
                "intent_name_zh": fact.get("intent_name_zh") or fact.get("intent_name"),
                "fact_type": fact.get("fact_type"),
                "fact_type_zh": fact.get("fact_type_zh") or fact.get("fact_type"),
                "attribute_name": fact.get("attribute_name"),
                "attribute_name_zh": fact.get("attribute_name_zh") or fact.get("attribute_name"),
                "relation_type": fact.get("relation_type"),
                "relation_type_zh": fact.get("relation_type_zh") or fact.get("relation_type"),
                "priority": fact.get("priority") or "required",
                "priority_zh": fact.get("priority_zh") or ("必须查询" if required else "辅助参考"),
                "reason_zh": fact.get("reason_zh") or "该事实用于支撑当前意图回答。",
                "covering_skills": [
                    {
                        "skill_id": skill.get("skill_id"),
                        "skill_name_zh": skill.get("skill_name") or skill.get("skill_id"),
                        "input_params": list_field(skill, "input_params"),
                        "permission_scope": skill.get("permission_scope") or "",
                    }
                    for skill in covering_skills
                ],
                "covering_skill_count": len(covering_skills),
                "execution_status": "covered" if covering_skills else ("blocked_required" if required else "uncovered_optional"),
                "execution_status_zh": "已有 Skill 覆盖" if covering_skills else ("必须补 Skill" if required else "辅助事实未覆盖"),
                "suggested_action_zh": "可直接进入样例规划验证。" if covering_skills else "新增或编辑 Skill 覆盖，关联该事实需求。",
            }
        )
    return rows


def skill_covers_fact(skill: dict[str, Any], fact: dict[str, Any]) -> bool:
    explicit = set(list_field(skill, "supported_fact_requirements"))
    if fact.get("value") in explicit:
        return True
    fact_type = fact.get("fact_type")
    if fact_type and fact_type not in set(list_field(skill, "provides_fact_types")):
        return False
    subject_types = set(fact.get("subject_types") or [])
    supported_subjects = set(list_field(skill, "supported_subject_types"))
    target_type = skill.get("target_object_type")
    if target_type:
        supported_subjects.add(str(target_type))
    if subject_types and supported_subjects and subject_types.isdisjoint(supported_subjects):
        return False
    attribute_name = fact.get("attribute_name")
    if attribute_name:
        attributes = set(list_field(skill, "supported_attributes")) | set(list_field(skill, "output_attributes"))
        return attribute_name in attributes
    relation_type = fact.get("relation_type")
    if relation_type:
        return relation_type in set(list_field(skill, "supported_relations"))
    return bool(fact_type)


def build_scenario_matrix(
    intent_profiles: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_intent: dict[str, list[dict[str, Any]]] = {}
    for row in coverage_rows:
        by_intent.setdefault(str(row.get("intent_name") or ""), []).append(row)
    scenarios = []
    for intent in intent_profiles:
        intent_name = str(intent.get("intent_name") or "")
        facts = by_intent.get(intent_name, [])
        required = [item for item in facts if item.get("priority") == "required"]
        blocked = [item for item in required if not item.get("covering_skill_count")]
        optional_uncovered = [
            item for item in facts if item.get("priority") != "required" and not item.get("covering_skill_count")
        ]
        status = "ready" if facts and not blocked else ("no_template" if not facts else "blocked")
        task_type = infer_task_type_from_intent(intent_name)
        target_object_types = list_field(intent, "target_object_types") or ["Fund"]
        sample_question = build_scenario_question_zh(intent.get("intent_name_zh") or intent_name, task_type, target_object_types)
        semantic_frame = build_scenario_semantic_frame(
            intent_name=intent_name,
            task_type=task_type,
            target_object_types=target_object_types,
            sample_question=sample_question,
            facts=facts,
        )
        scenarios.append(
            {
                "intent_name": intent_name,
                "intent_name_zh": intent.get("intent_name_zh") or intent_name,
                "task_type": task_type,
                "target_object_types": target_object_types,
                "trigger_aliases": list_field(intent, "trigger_aliases")[:6],
                "sample_question_zh": sample_question,
                "semantic_frame": semantic_frame,
                "fact_count": len(facts),
                "fact_requirements": scenario_fact_requirement_details(facts),
                "required_fact_count": len(required),
                "covered_required_fact_count": len(required) - len(blocked),
                "skill_count": len({skill["skill_id"] for fact in facts for skill in fact.get("covering_skills", [])}),
                "missing_required_facts": blocked[:5],
                "optional_gap_count": len(optional_uncovered),
                "execution_status": status,
                "execution_status_zh": {
                    "ready": "可运行样例验证",
                    "blocked": "必须事实缺 Skill",
                    "no_template": "缺少事实需求模板",
                }[status],
                "next_action_zh": (
                    "进入规划调试台运行样例问题。"
                    if status == "ready"
                    else "先补齐事实需求模板或 Skill 覆盖。"
                ),
            }
        )
    return scenarios


def scenario_fact_requirement_details(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for fact in facts:
        skills = fact.get("covering_skills") or []
        rows.append(
            {
                "fact_requirement_id": fact.get("fact_requirement_id"),
                "label_zh": fact.get("label_zh") or fact.get("fact_requirement_id"),
                "fact_type_zh": fact.get("fact_type_zh") or fact.get("fact_type"),
                "priority_zh": fact.get("priority_zh") or priority_label_zh(fact.get("priority")),
                "covering_skill_count": len(skills),
                "covering_skill_names_zh": [
                    skill.get("skill_name_zh") or skill.get("skill_id")
                    for skill in skills[:4]
                ],
                "execution_status": fact.get("execution_status"),
                "execution_status_zh": fact.get("execution_status_zh"),
                "suggested_action_zh": fact.get("suggested_action_zh"),
            }
        )
    return rows


def priority_label_zh(priority: Any) -> str:
    return "必须查询" if str(priority or "required") == "required" else "辅助参考"


def build_scenario_question_zh(intent_label: str, task_type: str, target_object_types: list[Any]) -> str:
    if task_type == "compare":
        return f"{intent_label}：比较000001和000002近一年表现"
    if task_type == "recommend":
        return f"{intent_label}：推荐近一年收益高、回撤低的基金"
    if task_type == "screen":
        return f"{intent_label}：筛选近一年最大回撤低于10%的基金"
    if task_type == "rank":
        return f"{intent_label}：查询近一年收益排名前十的基金"
    if "FundSet" in {str(item) for item in target_object_types}:
        return f"{intent_label}：分析基金池近一年表现"
    return f"{intent_label}：分析000001近一年表现"


def build_scenario_semantic_frame(
    *,
    intent_name: str,
    task_type: str,
    target_object_types: list[Any],
    sample_question: str,
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    target_type_set = {str(item) for item in target_object_types}
    is_collection = task_type in {"rank", "screen", "recommend"} or "FundSet" in target_type_set
    if task_type == "compare":
        targets = [
            {"object_type": "Fund", "instance_ref": {"fund_code": "000001"}, "role": "comparison_subject"},
            {"object_type": "Fund", "instance_ref": {"fund_code": "000002"}, "role": "comparison_subject"},
        ]
    elif is_collection:
        targets = [{"object_type": "FundSet", "instance_ref": {"fund_universe": "all_funds"}, "role": "candidate_set"}]
    else:
        targets = [{"object_type": "Fund", "instance_ref": {"fund_code": "000001"}, "role": "analysis_subject"}]

    attributes = [str(item.get("attribute_name")) for item in facts if item.get("attribute_name")]
    frame: dict[str, Any] = {
        "raw_question": sample_question,
        "domain": "finance_market",
        "task_type": task_type,
        "intent": intent_name,
        "target_objects": targets,
        "constraints": {"period": "1y"},
        "mentioned_attributes": list(dict.fromkeys(attributes))[:6],
        "debug": True,
    }
    relation_queries = [
        {
            "relation_type": item.get("relation_type"),
            "target_object_type": item.get("relation_target_object_type") or "RelatedObject",
        }
        for item in facts
        if item.get("relation_type")
    ]
    if relation_queries:
        frame["relation_queries"] = relation_queries[:4]
    if task_type == "compare":
        frame["comparison"] = {
            "mode": "side_by_side",
            "attributes": frame["mentioned_attributes"] or ["return_rate"],
            "target_object_policy": "all_targets",
        }
    if task_type in {"rank", "recommend"}:
        frame["ranking"] = [{"attribute": frame["mentioned_attributes"][0] if frame["mentioned_attributes"] else "return_rate", "direction": "desc"}]
        frame["limit"] = 10
    if task_type in {"screen", "recommend"}:
        frame["filters"] = [{"attribute": "max_drawdown", "operator": "<=", "value": 0.1}]
    if "holding" in intent_name or "allocation" in intent_name:
        frame["constraints"] = {"report_date": "latest"}
    return frame


def infer_task_type_from_intent(intent_name: str) -> str:
    if "recommend" in intent_name:
        return "recommend"
    if "screen" in intent_name:
        return "screen"
    if "ranking" in intent_name or "rank" in intent_name:
        return "rank"
    if "comparison" in intent_name or "compare" in intent_name:
        return "compare"
    if any(token in intent_name for token in ("profile", "fee", "dividend", "holding", "allocation")):
        return "query"
    return "analyze"


def build_relation_strategy_summary(edges: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode = Counter(str(edge.get("auto_expand_mode") or "未配置") for edge in edges)
    by_role = Counter(str(edge.get("planning_role") or edge.get("expansion_role") or "未配置") for edge in edges)
    missing_policy = [
        edge
        for edge in edges
        if not edge.get("planning_role")
        or not edge.get("auto_expand_mode")
        or not edge.get("reason_zh")
        or (not edge.get("applicable_tasks") and not edge.get("applicable_intents"))
    ]
    over_expanded = [
        edge
        for edge in edges
        if edge.get("auto_expand_mode") == "always"
        and str(edge.get("group")) == "object_relation"
    ]
    return {
        "summary": {
            "edge_count": len(edges),
            "attribute_expansion_count": len([edge for edge in edges if edge.get("group") == "attribute_expansion"]),
            "object_relation_count": len([edge for edge in edges if edge.get("group") == "object_relation"]),
            "missing_policy_count": len(missing_policy),
            "over_expanded_count": len(over_expanded),
        },
        "auto_expand_modes": [{"mode": key, "count": value} for key, value in by_mode.most_common()],
        "planning_roles": [{"role": key, "count": value} for key, value in by_role.most_common()],
        "policy_gaps": [
            {
                "edge_id": edge.get("edge_id"),
                "display_name_zh": edge.get("display_name_zh"),
                "source": edge.get("source"),
                "target": edge.get("target"),
                "message_zh": relation_policy_gap_message(edge),
                "suggested_action_zh": "补齐 planning_role、auto_expand_mode、适用范围和中文原因，避免关系过度扩展。",
            }
            for edge in missing_policy[:12]
        ],
        "over_expanded_edges": over_expanded[:12],
    }


def relation_policy_gap_message(edge: dict[str, Any]) -> str:
    missing = []
    if not edge.get("planning_role"):
        missing.append("规划角色")
    if not edge.get("auto_expand_mode"):
        missing.append("自动扩展模式")
    if not edge.get("reason_zh"):
        missing.append("中文原因")
    if not edge.get("applicable_tasks") and not edge.get("applicable_intents"):
        missing.append("适用范围")
    return f"{edge.get('edge_id') or '关系边'} 缺少{'、'.join(missing)}。"


def build_modeling_guide(
    sections: dict[str, Any],
    scenarios: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    relation_strategy: dict[str, Any],
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    required_gaps = [row for row in coverage_rows if row.get("execution_status") == "blocked_required"]
    return [
        guide_step("domain", "定义领域", len(list_rows(sections.get("object_types"))) > 0, "确认对象类型和领域边界。"),
        guide_step("attributes", "导入对象与属性", len(list_rows(sections.get("attributes"))) > 0, "补充对象属性和表字段映射。"),
        guide_step("facts", "设计事实类型", len(list_rows(sections.get("fact_types"))) > 0, "定义事实类型和典型属性。"),
        guide_step("skills", "注册 Skill 能力", len(list_rows(sections.get("skills"))) > 0, "声明 Skill 输入、权限和事实覆盖。"),
        guide_step("scenarios", "选择或生成场景矩阵", bool(scenarios), "用典型问题沉淀意图事实模板。"),
        guide_step("coverage", "形成事实需求与 Skill 覆盖矩阵", not required_gaps and bool(coverage_rows), "修复必须事实无 Skill 覆盖。"),
        guide_step("relations", "配置关系扩展策略", relation_strategy["summary"]["missing_policy_count"] == 0, "补齐关系策略字段，控制扩展范围。"),
        guide_step("debug", "运行规划调试台", bool(scenarios), "用样例问题验证 agent_plan 和 editor_plan。"),
        guide_step("diagnostics", "诊断治理", (diagnostics.get("summary") or {}).get("error_count", 0) == 0, "处理中文诊断和建议动作。"),
        guide_step("publish", "测试发布", not required_gaps and relation_strategy["summary"]["missing_policy_count"] == 0, "导出 YAML 或交给后续智能体消费。"),
    ]


def guide_step(step_id: str, title_zh: str, done: bool, action_zh: str) -> dict[str, Any]:
    return {
        "id": step_id,
        "title_zh": title_zh,
        "status": "done" if done else "needs_work",
        "status_zh": "已具备" if done else "待补齐",
        "action_zh": action_zh,
    }


def build_top_diagnostic_actions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(str(item.get("action_kind") or "inspect"), []).append(item)

    actions = []
    for kind, rows in sorted(grouped.items(), key=lambda pair: len(pair[1]), reverse=True)[:6]:
        target = diagnostic_repair_target(kind)
        diagnostic_types = [name for name, _ in Counter(str(row.get("diagnostic_type") or row.get("type")) for row in rows).most_common(4)]
        target_ids = []
        for row in rows:
            target_id = row.get("target_id") or row.get("node_id") or row.get("edge_id")
            if target_id and target_id not in target_ids:
                target_ids.append(str(target_id))
        actions.append(
            {
                "action_kind": kind,
                "label_zh": target["label_zh"],
                "count": len(rows),
                "suggested_task_id": target["task_id"],
                "suggested_task_title_zh": target["task_title_zh"],
                "suggested_action_zh": target["suggested_action_zh"],
                "diagnostic_types": diagnostic_types,
                "target_ids": target_ids[:5],
            }
        )
    return actions


def diagnostic_repair_target(action_kind: str) -> dict[str, str]:
    targets = {
        "edit_intent_template": {
            "label_zh": "补齐意图事实模板",
            "task_id": "intent_templates",
            "task_title_zh": "意图事实模板",
            "suggested_action_zh": "进入意图模板工作台，补齐 fact_requirements_template、事实类型、优先级和中文原因。",
        },
        "edit_skill_coverage": {
            "label_zh": "维护 Skill 覆盖",
            "task_id": "skill_coverage",
            "task_title_zh": "Skill 覆盖矩阵",
            "suggested_action_zh": "进入 Skill 覆盖矩阵，补齐支持事实、属性、主体对象、权限范围和必填输入参数。",
        },
        "edit_relation": {
            "label_zh": "治理关系扩展策略",
            "task_id": "semantic_relations",
            "task_title_zh": "关系策略工作台",
            "suggested_action_zh": "进入关系策略工作台，补齐 planning_role、auto_expand_mode、适用范围和中文原因。",
        },
        "edit_domain_model": {
            "label_zh": "补齐领域对象属性",
            "task_id": "core_graph",
            "task_title_zh": "领域对象与属性",
            "suggested_action_zh": "进入领域对象与属性视图，补齐对象、属性和表字段映射等基础模型配置。",
        },
        "inspect": {
            "label_zh": "检查配置对象",
            "task_id": "diagnostic",
            "task_title_zh": "诊断中心",
            "suggested_action_zh": "进入诊断中心，按类型定位具体对象后再编辑。",
        },
    }
    return targets.get(action_kind, targets["inspect"])


def build_sample_scenarios(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in scenarios[:12]:
        rows.append(
            {
                "intent_name": item.get("intent_name"),
                "intent_name_zh": item.get("intent_name_zh"),
                "question_zh": item.get("sample_question_zh"),
                "task_type": item.get("task_type"),
                "semantic_frame": item.get("semantic_frame"),
                "can_run": item.get("execution_status") == "ready",
                "can_run_zh": "可运行" if item.get("execution_status") == "ready" else "需先补齐配置",
            }
        )
    return rows


def build_release_readiness(
    diagnostics: dict[str, Any],
    coverage_rows: list[dict[str, Any]],
    relation_strategy: dict[str, Any],
) -> dict[str, Any]:
    summary = diagnostics.get("summary") or {}
    blockers: list[dict[str, Any]] = []
    required_gaps = [row for row in coverage_rows if row.get("execution_status") == "blocked_required"]
    if summary.get("error_count", 0):
        blockers.append({"type": "diagnostic_error", "message_zh": f"仍有 {summary.get('error_count')} 个错误诊断。"})
    if required_gaps:
        blockers.append({"type": "required_fact_gap", "message_zh": f"仍有 {len(required_gaps)} 个必须事实缺少 Skill 覆盖。"})
    missing_policy = relation_strategy.get("summary", {}).get("missing_policy_count", 0)
    if missing_policy:
        blockers.append({"type": "relation_policy_gap", "message_zh": f"仍有 {missing_policy} 条关系缺少治理策略字段。"})
    status = "ready" if not blockers else "needs_work"
    return {
        "status": status,
        "status_zh": "可以进入测试发布" if status == "ready" else "暂不建议发布",
        "blockers": blockers,
        "message_zh": "关键事实、Skill 覆盖和关系策略已具备。" if status == "ready" else "先修复阻塞项，再发布给智能体消费。",
    }


def build_publish_manifest(workbench: dict[str, Any], sample_validation: dict[str, Any]) -> dict[str, Any]:
    summary = workbench.get("summary") or {}
    readiness = (workbench.get("test_publish") or {}).get("release_readiness") or {}
    validation_summary = sample_validation.get("summary") or {}
    return {
        "package_type": "oag_model_publish_package",
        "package_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": summary.get("domain") or "finance_market",
        "domain_zh": summary.get("domain_zh") or "基金投研",
        "publish_status": readiness.get("status") or "needs_work",
        "publish_status_zh": readiness.get("status_zh") or "暂不建议发布",
        "publish_message_zh": readiness.get("message_zh") or "",
        "agent_plan_validation": {
            "sample_count": validation_summary.get("sample_count", 0),
            "ready_count": validation_summary.get("ready_count", 0),
            "needs_fix_count": validation_summary.get("needs_fix_count", 0),
            "missing_param_count": validation_summary.get("missing_param_count", 0),
            "uncovered_fact_count": validation_summary.get("uncovered_fact_count", 0),
            "status_zh": validation_summary.get("status_zh") or "",
        },
        "contents": [
            "manifest.json",
            "workbench_summary.json",
            "sample_agent_plan_validation.json",
            "ontology/*.yaml",
        ],
        "consumer_hint_zh": "后续智能体可读取 ontology/*.yaml 作为 OAG 模型配置，并使用 sample_agent_plan_validation.json 查看样例 agent_plan 覆盖与缺口。",
    }


def build_publish_package_zip(
    sections: dict[str, Any],
    workbench: dict[str, Any],
    sample_validation: dict[str, Any],
    manifest: dict[str, Any],
) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json_dumps_pretty(manifest))
        archive.writestr("workbench_summary.json", json_dumps_pretty(workbench))
        archive.writestr("sample_agent_plan_validation.json", json_dumps_pretty(sample_validation))
        section_by_file = {
            "attributes.yaml": "attributes",
            "data_sources.yaml": "data_sources",
            "fact_types.yaml": "fact_types",
            "instance_rules.yaml": "instance_rules",
            "intent_profiles.yaml": "intent_profiles",
            "object_types.yaml": "object_types",
            "period_variants.yaml": "period_variants",
            "queries.yaml": "queries",
            "relation_types.yaml": "relation_types",
            "schema_graph_edges.yaml": "schema_graph_edges",
            "skills.yaml": "skills",
            "table_schemas.yaml": "table_schemas",
        }
        for file_name in SUPPORTED_FILES:
            section = section_by_file[file_name]
            archive.writestr(f"ontology/{file_name}", dump_yaml(sections.get(section)))
    buffer.seek(0)
    return buffer


def json_dumps_pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_sample_plan_validation(workbench: dict[str, Any]) -> dict[str, Any]:
    planner = OAGV2Planner(
        ontology_repository=EditorCatalogRepository(),
        graph_repository=EditorSchemaGraphRepository(),
    )
    rows = []
    for sample in (workbench.get("test_publish") or {}).get("sample_scenarios") or []:
        frame = sample.get("semantic_frame") or {}
        try:
            full_plan = planner.plan(
                semantic_frame=frame,
                selector_mode="rule",
                user_context={"permission_scopes": ["fund_public_data:read"], "debug": True},
            )
            agent_plan = project_plan(full_plan, "agent")
            execution = agent_plan.get("execution") or {}
            coverage = agent_plan.get("coverage") or {}
            blocking_issues = execution.get("blocking_issues") or []
            uncovered_facts = agent_plan.get("uncovered_facts") or coverage.get("uncovered_required_facts") or []
            row_status = sample_plan_status(execution, coverage, uncovered_facts)
            rows.append(
                {
                    "intent_name": sample.get("intent_name"),
                    "intent_name_zh": sample.get("intent_name_zh"),
                    "question_zh": sample.get("question_zh"),
                    "status": row_status,
                    "status_zh": sample_plan_status_zh(row_status),
                    "execution_status": execution.get("execution_status"),
                    "execution_status_zh": execution_status_zh(execution.get("execution_status")),
                    "coverage_status": coverage.get("coverage_status"),
                    "coverage_status_zh": coverage_status_zh(coverage.get("coverage_status")),
                    "ready_skill_count": execution.get("ready_skill_count", 0),
                    "blocked_skill_count": execution.get("blocked_skill_count", 0),
                    "required_fact_count": coverage.get("required_fact_count", 0),
                    "covered_required_fact_count": coverage.get("covered_required_fact_count", 0),
                    "missing_params": [
                        {
                            "skill_id": item.get("skill_id"),
                            "skill_name_zh": item.get("skill_name_zh"),
                            "missing_params": item.get("missing_params") or [],
                            "message_zh": item.get("message_zh") or "",
                        }
                        for item in blocking_issues
                        if item.get("code") == "SKILL_PARAMS_MISSING"
                    ],
                    "uncovered_facts": uncovered_facts,
                    "message_zh": execution.get("message_zh") or coverage.get("message_zh") or "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "intent_name": sample.get("intent_name"),
                    "intent_name_zh": sample.get("intent_name_zh"),
                    "question_zh": sample.get("question_zh"),
                    "status": "error",
                    "status_zh": "规划失败",
                    "message_zh": f"样例规划失败：{exc}",
                    "missing_params": [],
                    "uncovered_facts": [],
                }
            )
    summary = {
        "sample_count": len(rows),
        "ready_count": len([item for item in rows if item.get("status") == "ready"]),
        "needs_fix_count": len([item for item in rows if item.get("status") != "ready"]),
        "missing_param_count": sum(len(item.get("missing_params") or []) for item in rows),
        "uncovered_fact_count": sum(len(item.get("uncovered_facts") or []) for item in rows),
    }
    return {
        "summary": {
            **summary,
            "status_zh": "样例验证通过" if summary["needs_fix_count"] == 0 else "样例验证发现缺口",
        },
        "items": rows,
    }


def run_golden_questions() -> dict[str, Any]:
    path = PROJECT_ROOT / "ontology" / "golden_questions.yaml"
    rows = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else []
    planner = OAGV2Planner(
        ontology_repository=EditorCatalogRepository(),
        graph_repository=EditorSchemaGraphRepository(),
    )
    items = []
    for item in rows or []:
        plan = planner.plan(
            semantic_frame=item.get("semantic_frame") or {},
            raw_question=item.get("question_zh"),
            recognized_intents=item.get("recognized_intents") or [],
            selector_mode=item.get("selector_mode") or "rule",
            planning_options=item.get("planning_options") or {},
            user_context={"permission_scopes": ["fund_public_data:read"], "debug": True},
        )
        validation = plan.get("validation_result") or {}
        coverage = plan.get("coverage_summary") or {}
        items.append(
            {
                "id": item.get("id"),
                "question_zh": item.get("question_zh"),
                "status": plan.get("status"),
                "status_zh": golden_status_zh(plan),
                "selector_mode": item.get("selector_mode") or "rule",
                "candidate_fact_count": len(plan.get("candidate_fact_pool") or []),
                "selected_fact_count": len(plan.get("selected_facts") or []),
                "dependency_count": len((plan.get("dependency_completion") or {}).get("completed_facts") or []),
                "skill_binding_count": len(plan.get("skill_bindings") or []),
                "validation_ok": validation.get("ok"),
                "coverage_status": coverage.get("coverage_status"),
                "missing_params": plan.get("missing_params") or [],
                "diagnostics": plan.get("diagnostics") or [],
            }
        )
    failed = [
        item
        for item in items
        if item["status"] not in {"success", "need_clarification"}
        or item["candidate_fact_count"] <= 0
        or not item["validation_ok"]
    ]
    return {
        "summary": {
            "sample_count": len(items),
            "passed_count": len(items) - len(failed),
            "failed_count": len(failed),
            "status": "passed" if not failed else "failed",
            "status_zh": "全部 golden questions 通过" if not failed else "存在 golden questions 未通过",
        },
        "items": items,
    }


def golden_status_zh(plan: dict[str, Any]) -> str:
    if plan.get("status") == "success":
        return "通过"
    if plan.get("status") == "need_clarification":
        return "需补参数"
    return "失败"


def build_scenario_draft(payload: ScenarioDraftPayload, plan: dict[str, Any]) -> dict[str, Any]:
    frame = plan.get("normalized_semantic_frame") or payload.semantic_frame
    intent_name = payload.intent_name or frame.get("intent") or slugify_identifier(frame.get("raw_question") or "new_oag_scenario")
    intent_name_zh = payload.intent_name_zh or infer_intent_label_zh(intent_name, frame)
    trigger_aliases = payload.trigger_aliases or [frame.get("raw_question") or intent_name_zh]
    fact_template = build_fact_template_from_plan(plan)
    relation_drafts = build_relation_strategy_drafts_from_plan(plan, frame)
    skill_gaps = build_scenario_skill_gaps(plan)
    intent_draft = {
        "intent_name": intent_name,
        "intent_name_zh": intent_name_zh,
        "enabled": True,
        "trigger_aliases": trigger_aliases,
        "target_object_types": list(dict.fromkeys(target.get("object_type") for target in frame.get("target_objects") or [] if target.get("object_type"))) or ["Fund"],
        "fact_requirements_template": fact_template,
        "default_attributes": list(dict.fromkeys(item.get("attribute_name") for item in fact_template if item.get("attribute_name"))),
        "description": f"由典型问题自动生成：{frame.get('raw_question') or intent_name_zh}",
    }
    return {
        "ok": plan.get("status") in {"success", "need_clarification"},
        "status": plan.get("status"),
        "message_zh": scenario_draft_message(plan, fact_template, relation_drafts, skill_gaps),
        "semantic_frame": frame,
        "intent_profile_draft": intent_draft,
        "fact_requirements_template": fact_template,
        "relation_strategy_drafts": relation_drafts,
        "skill_coverage_gaps": skill_gaps,
        "agent_plan": project_plan(plan, "agent"),
        "editor_plan": project_plan(plan, "editor"),
    }


def build_fact_template_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    seen: set[tuple[str, str, str]] = set()
    for fact in plan.get("fact_requirements") or []:
        attribute = fact.get("attribute") if isinstance(fact.get("attribute"), dict) else {}
        fact_type = str(fact.get("fact_type") or "")
        attribute_name = str(fact.get("attribute_name") or attribute.get("attribute_name") or "")
        relation_type = str(fact.get("predicate") or fact.get("relation_type") or "")
        if not fact_type:
            continue
        key = (fact_type, attribute_name, relation_type)
        if key in seen:
            continue
        seen.add(key)
        row = {
            "fact_type": fact_type,
            "priority": fact.get("priority") or "required",
            "reason_zh": fact.get("reason_zh") or fact.get("source_zh") or "该事实由典型问题自动生成，用于支撑场景回答。",
        }
        if attribute_name:
            row["attribute_name"] = attribute_name
        if relation_type and not attribute_name:
            row["relation_type"] = relation_type
        rows.append(row)
    return rows


def build_relation_strategy_drafts_from_plan(plan: dict[str, Any], frame: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    seen: set[str] = set()
    for item in (plan.get("debug_evidence") or {}).get("relation_expansion_edges") or []:
        source = item.get("from") or item.get("source") or item.get("source_attribute") or item.get("from_object_type")
        target = (
            item.get("to")
            or item.get("target")
            or item.get("target_attribute")
            or item.get("to_object_type")
            or item.get("target_object_type")
        )
        relation_type = item.get("relation_type")
        if not relation_type:
            continue
        source_id = normalize_relation_endpoint(source, relation_endpoint_default_type(item, "source"))
        target_id = normalize_relation_endpoint(target, relation_endpoint_default_type(item, "target"))
        edge_id = item.get("edge_id") or f"{source_id}__{relation_type}__{target_id}"
        if edge_id in seen:
            continue
        seen.add(edge_id)
        rows.append(
            {
                "edge_id": edge_id,
                "from": source_id,
                "to": target_id,
                "relation_type": relation_type,
                "applicable_tasks": [frame.get("task_type")] if frame.get("task_type") else [],
                "applicable_intents": [frame.get("intent")] if frame.get("intent") else [],
                "default_priority": item.get("default_priority") or "optional",
                "planning_role": item.get("planning_role") or item.get("expansion_role") or "scenario_context",
                "auto_expand_mode": item.get("auto_expand_mode") or "contextual",
                "answer_visibility": item.get("answer_visibility") or "supporting_context",
                "expansion_priority": item.get("expansion_priority") or item.get("default_priority") or "optional",
                "trigger_policy": item.get("trigger_policy") or {"match_intents": [frame.get("intent")] if frame.get("intent") else []},
                "expansion_limits": item.get("expansion_limits") or {"max_edges_per_seed": 3},
                "reason_zh": item.get("reason_zh") or "由典型问题规划过程自动建议，用于补齐关系扩展策略。",
                "weight": item.get("weight") or item.get("score") or 0.6,
            }
        )
    return rows


def build_scenario_skill_gaps(plan: dict[str, Any]) -> list[dict[str, Any]]:
    coverage = plan.get("coverage_summary") or {}
    rows = []
    for fact in coverage.get("uncovered_required_facts") or plan.get("uncovered_facts") or []:
        rows.append(
            {
                "fact_requirement_id": fact.get("fact_requirement_id") or fact.get("fact_id"),
                "label_zh": fact.get("label_zh") or fact.get("fact_requirement_id") or "未覆盖事实",
                "message_zh": "该必需事实当前没有 Skill 覆盖。",
                "suggested_action_zh": "注册或编辑 Skill 能力，并勾选该事实需求。",
            }
        )
    for item in plan.get("missing_params") or []:
        rows.append(
            {
                "skill_id": item.get("skill_id"),
                "skill_name_zh": item.get("skill_name_zh") or item.get("skill_id"),
                "missing_params": item.get("missing_params") or [],
                "message_zh": item.get("message_zh") or "Skill 调用缺失参数。",
                "suggested_action_zh": "在 semantic_frame 的目标对象、约束或选项中补齐参数，或调整 Skill 输入参数声明。",
            }
        )
    return rows


def scenario_draft_message(
    plan: dict[str, Any],
    facts: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> str:
    if plan.get("status") == "error":
        return plan.get("message_zh") or "场景草稿生成失败。"
    return f"已生成 {len(facts)} 条事实需求模板、{len(relations)} 条关系策略建议、{len(gaps)} 个覆盖缺口。"


def normalize_relation_endpoint(value: Any, default_type: str) -> str:
    text = str(value or "").strip()
    if not text:
        return f"{default_type}:unknown"
    if ":" in text:
        return text
    return f"{default_type}:{text}"


def relation_endpoint_default_type(item: dict[str, Any], side: str) -> str:
    if side == "source" and item.get("from_object_type"):
        return "ObjectType"
    if side == "target" and (item.get("to_object_type") or item.get("target_object_type")):
        return "ObjectType"
    return "Attribute"


def infer_intent_label_zh(intent_name: str, frame: dict[str, Any]) -> str:
    raw_question = str(frame.get("raw_question") or "").strip()
    if raw_question:
        return raw_question[:24]
    labels = {
        "performance_overview": "基金综合表现分析",
        "benchmark_comparison": "基金相对基准表现",
        "peer_comparison": "基金同类比较",
        "fund_comparison": "基金对比分析",
        "fund_ranking": "基金排序",
        "fund_screening": "基金筛选",
        "fund_recommendation": "基金推荐",
    }
    return labels.get(intent_name, intent_name)


def slugify_identifier(value: Any) -> str:
    text = str(value or "new_oag_scenario").strip().lower()
    chars = []
    for char in text:
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "_":
            chars.append("_")
    slug = "".join(chars).strip("_")
    return slug[:48] or "new_oag_scenario"


def sample_plan_status(execution: dict[str, Any], coverage: dict[str, Any], uncovered_facts: list[Any]) -> str:
    if uncovered_facts or coverage.get("coverage_status") in {"no_coverage", "partial_coverage"}:
        return "uncovered_facts"
    if execution.get("execution_status") == "blocked_missing_params":
        return "missing_params"
    if execution.get("execution_status") == "blocked_permission":
        return "permission_blocked"
    if execution.get("execution_status") == "ready":
        return "ready"
    return "needs_review"


def sample_plan_status_zh(status: str) -> str:
    return {
        "ready": "agent_plan 可执行",
        "missing_params": "缺失参数",
        "permission_blocked": "权限不足",
        "uncovered_facts": "存在未覆盖事实",
        "needs_review": "需要人工确认",
        "error": "规划失败",
    }.get(status, "需要人工确认")


def execution_status_zh(status: Any) -> str:
    return {
        "ready": "可执行",
        "blocked_missing_params": "缺失参数",
        "blocked_permission": "权限不足",
        "partial": "部分可执行",
        "no_skill_calls": "无 Skill 调用",
        "disabled": "Skill 不可用",
    }.get(str(status or ""), str(status or "未知"))


def coverage_status_zh(status: Any) -> str:
    return {
        "full_coverage": "完全覆盖",
        "partial_coverage": "部分覆盖",
        "no_coverage": "没有覆盖",
        "need_clarification": "需要补充信息",
        "permission_blocked": "权限受阻",
    }.get(str(status or ""), str(status or "未知"))


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
    action_kind = diagnostic_action_kind(item_type)
    repair_target = diagnostic_repair_target(action_kind)
    return {
        **item,
        "diagnostic_type": item_type,
        "type": item_type,
        "severity": item.get("severity") or "warning",
        "node_id": node_id,
        "edge_id": edge_id,
        "target_id": target_id,
        "node_type": item.get("node_type") or (node_id.split(":", 1)[0] if ":" in node_id else ""),
        "raw_action_kind": item.get("action_kind") or "",
        "action_kind": action_kind,
        "suggested_task_id": repair_target["task_id"],
        "suggested_task_title_zh": repair_target["task_title_zh"],
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
        "intents_without_skill": "edit_intent_template",
        "skill_missing_provides_fact_types": "edit_skill_coverage",
        "skill_missing_supported_attributes": "edit_skill_coverage",
        "skill_missing_supported_subject_types": "edit_skill_coverage",
        "attribute_without_skill_coverage": "edit_skill_coverage",
        "attributes_without_skill": "edit_skill_coverage",
        "skills_without_attributes": "edit_skill_coverage",
        "disabled_skills_referenced": "edit_skill_coverage",
        "semantic_edge_missing_reason_zh": "edit_relation",
        "semantic_edge_missing_applicability": "edit_relation",
        "planning_edge_missing_planning_role": "edit_relation",
        "planning_edge_missing_auto_expand_mode": "edit_relation",
        "object_profile_relation_auto_expands_always": "edit_relation",
        "relation_edge_unknown_node": "edit_relation",
        "relation_types_unused": "edit_relation",
        "required_fact_without_skill_coverage": "edit_skill_coverage",
        "attributes_without_table_mapping": "edit_domain_model",
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


def relation_strategy_draft_to_edge(draft: dict[str, Any]) -> dict[str, Any]:
    source = draft.get("source") or draft.get("from")
    target = draft.get("target") or draft.get("to")
    relation_type = draft.get("relation_type")
    if not source or not target or not relation_type:
        raise StoreError("关系策略建议缺少起点、终点或关系类型。")
    edge_id = draft.get("edge_id") or f"{source}__{relation_type}__{target}"
    props = dict(draft)
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


def upsert_schema_edges(edges: list[dict[str, Any]]) -> dict[str, Any]:
    for edge in edges:
        validate_schema_edge_endpoints(edge)
    rows = read_yaml_file("schema_graph_edges.yaml")
    if not isinstance(rows, list):
        raise StoreError("schema_graph_edges.yaml must contain a list")
    applied = []
    for edge in edges:
        existing = next((item for item in rows if isinstance(item, dict) and item.get("edge_id") == edge["edge_id"]), None)
        action = "updated"
        if existing:
            existing.clear()
            existing.update(edge)
        else:
            rows.append(edge)
            action = "created"
        applied.append({"action": action, "edge": edge})
    result = write_yaml_file("schema_graph_edges.yaml", rows)
    return {"applied_count": len(applied), "items": applied, "write": result}


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
