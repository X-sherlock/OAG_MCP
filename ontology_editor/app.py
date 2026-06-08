from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
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

app = FastAPI(title="OAG Ontology Editor", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
    q: str | None = None,
) -> dict[str, Any]:
    try:
        return build_graph_view(
            view_mode=view_mode,
            focus_id=focus_id,
            depth=depth,
            include_fields=include_fields,
            include_inferred=include_inferred,
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
        )
    except StoreError as exc:
        raise http_error(400, str(exc)) from exc


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
