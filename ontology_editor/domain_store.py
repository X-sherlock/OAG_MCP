from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .yaml_store import ONTOLOGY_DIR, PROJECT_ROOT, StoreError


DOMAINS_DIR = (ONTOLOGY_DIR / "domains").resolve()
VERSION_FILES = (
    "domain.yaml",
    "plan.yaml",
    "object_types.yaml",
    "attributes.yaml",
    "relation_types.yaml",
    "schema_graph_edges.yaml",
)

DOMAIN_META_FILE = "domain.yaml"
DOMAIN_FILES = (*VERSION_FILES, DOMAIN_META_FILE)


def slugify_domain_id(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    if normalized:
        return normalized[:60]
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"domain_{digest}"


def unique_domain_id(name: str) -> str:
    base = slugify_domain_id(name)
    candidate = base
    if not domain_dir(candidate).exists():
        return candidate
    digest = hashlib.sha1(f"{name}:{datetime.now().isoformat()}".encode("utf-8")).hexdigest()[:6]
    return f"{base}_{digest}"


def new_version_id() -> str:
    return f"v{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def domain_dir(domain_id: str) -> Path:
    clean = slugify_domain_id(domain_id)
    path = (DOMAINS_DIR / clean).resolve()
    if DOMAINS_DIR not in path.parents and path != DOMAINS_DIR:
        raise StoreError("Domain path traversal is not allowed")
    return path


def domain_meta_path(domain_id: str) -> Path:
    root = domain_dir(domain_id)
    path = (root / DOMAIN_META_FILE).resolve()
    if root not in path.parents:
        raise StoreError("Domain metadata path traversal is not allowed")
    return path


def versions_dir(domain_id: str) -> Path:
    root = domain_dir(domain_id)
    path = (root / "versions").resolve()
    if root not in path.parents:
        raise StoreError("Domain versions path traversal is not allowed")
    return path


def version_dir(domain_id: str, version_id: str) -> Path:
    clean = slugify_domain_id(version_id)
    path = (versions_dir(domain_id) / clean).resolve()
    if versions_dir(domain_id) not in path.parents:
        raise StoreError("Domain version path traversal is not allowed")
    return path


def domain_file_path(domain_id: str, file_name: str, version_id: str | None = None) -> Path:
    if file_name not in VERSION_FILES:
        raise StoreError(f"Unsupported domain ontology file: {file_name}")
    root = version_dir(domain_id, version_id or current_version_id(domain_id))
    path = (root / file_name).resolve()
    if root not in path.parents:
        raise StoreError("Domain file path traversal is not allowed")
    return path


def list_domains() -> list[dict[str, Any]]:
    if not DOMAINS_DIR.exists():
        return []
    rows = []
    for path in sorted(item for item in DOMAINS_DIR.iterdir() if item.is_dir()):
        try:
            meta = read_domain_meta(path.name)
        except StoreError:
            continue
        if not meta.get("current_version_id"):
            continue
        rows.append(
            {
                "domain_id": path.name,
                "domain_name": meta.get("domain_name") or path.name,
                "description": meta.get("description") or "",
                "path": display_path(path),
                "current_version_id": meta.get("current_version_id") or "",
                "modified_at": meta.get("updated_at") or datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "versions": list_domain_versions(path.name),
            }
        )
    return sorted(rows, key=lambda item: item.get("modified_at") or "", reverse=True)


def read_domain_meta(domain_id: str) -> dict[str, Any]:
    path = domain_meta_path(domain_id)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_domain_meta(domain_id: str, data: dict[str, Any]) -> dict[str, Any]:
    path = domain_meta_path(domain_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(serialized, encoding="utf-8", newline="\n")
    return {"file": DOMAIN_META_FILE, "path": display_path(path), "backup_path": "", "size": path.stat().st_size}


def current_version_id(domain_id: str) -> str:
    meta = read_domain_meta(domain_id)
    version_id = str(meta.get("current_version_id") or "").strip()
    if not version_id:
        raise StoreError(f"Domain has no current version: {domain_id}")
    return version_id


def list_domain_versions(domain_id: str) -> list[dict[str, Any]]:
    root = versions_dir(domain_id)
    if not root.exists():
        return []
    versions = []
    current = ""
    try:
        current = current_version_id(domain_id)
    except StoreError:
        current = ""
    for path in sorted(item for item in root.iterdir() if item.is_dir()):
        meta = read_version_meta(domain_id, path.name)
        if not meta:
            continue
        meta["is_current"] = meta.get("version_id") == current
        versions.append(meta)
    return sorted(versions, key=lambda item: item.get("created_at") or "")


def read_version_meta(domain_id: str, version_id: str) -> dict[str, Any]:
    data = read_domain_file(domain_id, "plan.yaml", version_id)
    version = data.get("version") if isinstance(data, dict) and isinstance(data.get("version"), dict) else {}
    version = dict(version)
    version["feedback"] = str(data.get("feedback") or "") if isinstance(data, dict) else ""
    version["change_type"] = str(version.get("change_type") or ("manual" if version.get("manual_change") else "plan"))
    version["manual_change"] = version.get("manual_change") if isinstance(version.get("manual_change"), dict) else {}
    version["deleted"] = bool(version.get("deleted"))
    version["deleted_at"] = str(version.get("deleted_at") or "")
    version["delete_mode"] = str(version.get("delete_mode") or "")
    plan = data.get("plan") if isinstance(data, dict) and isinstance(data.get("plan"), dict) else {}
    version["plan_summary"] = str(plan.get("summary_zh") or "") if isinstance(plan, dict) else ""
    version["operation_summary"] = describe_version_operation(version)
    return version


def update_domain_version_note(domain_id: str, version_id: str, note: str) -> dict[str, Any]:
    data = read_domain_file(domain_id, "plan.yaml", version_id)
    if not isinstance(data, dict):
        raise StoreError(f"Invalid version metadata: {version_id}")
    version = data.get("version") if isinstance(data.get("version"), dict) else {}
    version["note"] = str(note or "").strip()
    data["version"] = version
    write = write_domain_file(domain_id, "plan.yaml", data, version_id)
    return {"domain_id": domain_id, "version_id": version_id, "note": version["note"], "write": write}


def delete_domain_version(domain_id: str, version_id: str, mode: str) -> dict[str, Any]:
    clean_version_id = slugify_domain_id(version_id)
    if not version_dir(domain_id, clean_version_id).exists():
        raise StoreError(f"Domain version does not exist: {version_id}")
    if mode not in {"reparent", "cascade"}:
        raise StoreError("Version delete mode must be reparent or cascade")

    versions = list_domain_versions(domain_id)
    version_by_id = {item["version_id"]: item for item in versions}
    target = version_by_id.get(clean_version_id)
    if not target:
        raise StoreError(f"Domain version does not exist: {version_id}")
    now = datetime.now().isoformat(timespec="seconds")
    deleted_ids = {clean_version_id}
    writes = []

    if mode == "cascade":
        deleted_ids.update(descendant_version_ids(versions, clean_version_id))
    else:
        target_parent = str(target.get("parent_version_id") or "")
        for child in versions:
            if child.get("parent_version_id") != clean_version_id:
                continue
            child_data = read_domain_file(domain_id, "plan.yaml", child["version_id"])
            if not isinstance(child_data, dict):
                continue
            child_version = child_data.get("version") if isinstance(child_data.get("version"), dict) else {}
            child_version["parent_version_id"] = target_parent
            child_version["reparented_from"] = clean_version_id
            child_data["version"] = child_version
            writes.append(write_domain_file(domain_id, "plan.yaml", child_data, child["version_id"]))

    for delete_id in sorted(deleted_ids):
        data = read_domain_file(domain_id, "plan.yaml", delete_id)
        if not isinstance(data, dict):
            data = {}
        version = data.get("version") if isinstance(data.get("version"), dict) else {}
        version["deleted"] = True
        version["deleted_at"] = now
        version["delete_mode"] = mode
        data["version"] = version
        writes.append(write_domain_file(domain_id, "plan.yaml", data, delete_id))

    meta = read_domain_meta(domain_id)
    current = str(meta.get("current_version_id") or "")
    if current in deleted_ids:
        replacement = choose_replacement_version(list_domain_versions(domain_id), deleted_ids, target.get("parent_version_id") or "")
        if replacement:
            meta["current_version_id"] = replacement
            meta["updated_at"] = now
            writes.append(write_domain_meta(domain_id, meta))

    return {
        "domain_id": domain_id,
        "version_id": clean_version_id,
        "mode": mode,
        "deleted_version_ids": sorted(deleted_ids),
        "current_version_id": meta.get("current_version_id") or "",
        "writes": writes,
    }


def descendant_version_ids(versions: list[dict[str, Any]], version_id: str) -> set[str]:
    children: dict[str, list[str]] = {}
    for version in versions:
        children.setdefault(str(version.get("parent_version_id") or ""), []).append(version["version_id"])
    descendants: set[str] = set()
    stack = list(children.get(version_id, []))
    while stack:
        child_id = stack.pop()
        if child_id in descendants:
            continue
        descendants.add(child_id)
        stack.extend(children.get(child_id, []))
    return descendants


def choose_replacement_version(versions: list[dict[str, Any]], deleted_ids: set[str], preferred_parent: str) -> str:
    if preferred_parent and preferred_parent not in deleted_ids:
        parent = next((item for item in versions if item["version_id"] == preferred_parent and not item.get("deleted")), None)
        if parent:
            return preferred_parent
    for version in reversed(versions):
        if version["version_id"] not in deleted_ids and not version.get("deleted"):
            return version["version_id"]
    return ""


def read_domain_file(domain_id: str, file_name: str, version_id: str | None = None) -> Any:
    path = domain_file_path(domain_id, file_name, version_id)
    if not path.exists():
        return {} if file_name in {"domain.yaml", "plan.yaml"} else []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise StoreError(f"Invalid YAML in {display_path(path)}: {exc}") from exc
    return data if data is not None else ({} if file_name in {"domain.yaml", "plan.yaml"} else [])


def read_domain(domain_id: str, version_id: str | None = None) -> dict[str, Any]:
    resolved_version_id = version_id or current_version_id(domain_id)
    return {
        "domain": read_domain_file(domain_id, "domain.yaml", resolved_version_id),
        "domain_meta": read_domain_meta(domain_id),
        "version_id": resolved_version_id,
        "versions": list_domain_versions(domain_id),
        "plan_metadata": read_domain_file(domain_id, "plan.yaml", resolved_version_id),
        "object_types": as_list(read_domain_file(domain_id, "object_types.yaml", resolved_version_id), "object_types.yaml"),
        "attributes": as_list(read_domain_file(domain_id, "attributes.yaml", resolved_version_id), "attributes.yaml"),
        "relation_types": as_list(read_domain_file(domain_id, "relation_types.yaml", resolved_version_id), "relation_types.yaml"),
        "schema_graph_edges": as_list(read_domain_file(domain_id, "schema_graph_edges.yaml", resolved_version_id), "schema_graph_edges.yaml"),
    }


def create_domain_from_sections(
    domain_input: dict[str, Any],
    sections: dict[str, Any],
    plan: dict[str, Any] | None = None,
    feedback: str = "",
    domain_id: str | None = None,
    parent_version_id: str | None = None,
) -> dict[str, Any]:
    domain_info = normalize_domain_info(domain_input, sections.get("domain") or {})
    domain_id = slugify_domain_id(domain_id or "") if domain_id else unique_domain_id(domain_info["domain_name"])
    if parent_version_id is None and domain_dir(domain_id).exists():
        try:
            parent_version_id = current_version_id(domain_id)
        except StoreError:
            parent_version_id = ""
    version_id = new_version_id()
    normalized = normalize_sections(domain_info, sections)
    root = domain_dir(domain_id)
    root.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    plan_summary = ""
    if isinstance(plan, dict):
        plan_summary = str(plan.get("summary_zh") or "").strip()
    version_summary = summarize_version_change(feedback, parent_version_id, plan_summary)
    plan_metadata = {
        "domain_input": domain_input,
        "plan": plan or {},
        "feedback": feedback or "",
        "created_at": now,
        "version": {
            "version_id": version_id,
            "parent_version_id": parent_version_id or "",
            "summary": version_summary,
            "operation_summary": feedback or plan_summary or version_summary,
            "created_at": now,
        },
    }
    writes = []
    for file_name, content in {
        "domain.yaml": normalized["domain"],
        "plan.yaml": plan_metadata,
        "object_types.yaml": normalized["object_types"],
        "attributes.yaml": normalized["attributes"],
        "relation_types.yaml": normalized["relation_types"],
        "schema_graph_edges.yaml": normalized["schema_graph_edges"],
    }.items():
        writes.append(write_domain_file(domain_id, file_name, content, version_id))
    existing_meta = read_domain_meta(domain_id)
    meta = {
        "domain_id": domain_id,
        "domain_name": normalized["domain"].get("domain_name") or domain_info["domain_name"],
        "description": normalized["domain"].get("description") or domain_info.get("description") or "",
        "current_version_id": version_id,
        "created_at": existing_meta.get("created_at") or now,
        "updated_at": now,
    }
    writes.append(write_domain_meta(domain_id, meta))
    return {
        "domain_id": domain_id,
        "version_id": version_id,
        "parent_version_id": parent_version_id or "",
        "domain": normalized["domain"],
        "writes": writes,
        "path": display_path(root),
    }


def summarize_version_change(feedback: str, parent_version_id: str | None, plan_summary: str = "") -> str:
    text = " ".join(str(feedback or "").split())
    if text:
        return text[:80]
    summary = " ".join(str(plan_summary or "").split())
    if summary:
        return summary[:80]
    return "更新规划方案" if parent_version_id else "初始版本"


def write_domain_file(domain_id: str, file_name: str, data: Any, version_id: str | None = None) -> dict[str, Any]:
    path = domain_file_path(domain_id, file_name, version_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup_domain_file(domain_id, file_name, version_id)
    serialized = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(serialized, encoding="utf-8", newline="\n")
    return {
        "file": file_name,
        "path": display_path(path),
        "backup_path": display_path(backup_path) if backup_path else "",
        "size": path.stat().st_size,
    }


def backup_domain_file(domain_id: str, file_name: str, version_id: str | None = None) -> Path | None:
    path = domain_file_path(domain_id, file_name, version_id)
    if not path.exists():
        return None
    backup_dir = path.parent / ".backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{path.stem}.{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def checkout_domain_version(domain_id: str, version_id: str) -> dict[str, Any]:
    if not version_dir(domain_id, version_id).exists():
        raise StoreError(f"Domain version does not exist: {version_id}")
    meta = read_domain_meta(domain_id)
    if not meta:
        raise StoreError(f"Domain does not exist: {domain_id}")
    meta["current_version_id"] = slugify_domain_id(version_id)
    meta["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write = write_domain_meta(domain_id, meta)
    return {"domain_id": domain_id, "version_id": meta["current_version_id"], "write": write}


def create_manual_edit_version(domain_id: str, base_version_id: str | None, summary: str, change: dict[str, Any]) -> str:
    base_version_id = base_version_id or current_version_id(domain_id)
    base = version_dir(domain_id, base_version_id)
    if not base.exists():
        raise StoreError(f"Domain version does not exist: {base_version_id}")
    version_id = new_version_id()
    target = version_dir(domain_id, version_id)
    target.mkdir(parents=True, exist_ok=True)
    for file_name in VERSION_FILES:
        source_file = base / file_name
        if source_file.exists():
            shutil.copy2(source_file, target / file_name)
    data = read_domain_file(domain_id, "plan.yaml", version_id)
    if not isinstance(data, dict):
        data = {}
    now = datetime.now().isoformat(timespec="seconds")
    data["feedback"] = ""
    data["version"] = {
        "version_id": version_id,
        "parent_version_id": base_version_id,
        "summary": summary,
        "operation_summary": describe_manual_change(change) or summary,
        "created_at": now,
        "change_type": "manual",
        "manual_change": change,
    }
    write_domain_file(domain_id, "plan.yaml", data, version_id)
    meta = read_domain_meta(domain_id)
    if not meta:
        raise StoreError(f"Domain does not exist: {domain_id}")
    meta["current_version_id"] = version_id
    meta["updated_at"] = now
    write_domain_meta(domain_id, meta)
    return version_id


def describe_version_operation(version: dict[str, Any]) -> str:
    feedback = str(version.get("feedback") or "").strip()
    if feedback:
        return feedback
    manual_summary = describe_manual_change(version.get("manual_change") if isinstance(version.get("manual_change"), dict) else {})
    if manual_summary:
        return manual_summary
    return str(version.get("operation_summary") or version.get("summary") or version.get("plan_summary") or "").strip()


def describe_manual_change(change: dict[str, Any]) -> str:
    if not isinstance(change, dict) or not change:
        return ""
    action = str(change.get("action") or "")
    if action == "upsert_node":
        return f"新增/修改节点：{change.get('node_type') or ''}:{change.get('node_id') or ''}".strip()
    if action == "delete_node":
        return f"删除节点：{change.get('node_id') or ''}".strip()
    if action == "upsert_edge":
        source = change.get("source") or ""
        target = change.get("target") or ""
        relation_type = change.get("relation_type") or ""
        return f"新增/修改关系：{source} -[{relation_type}]-> {target}".strip()
    if action == "delete_edge":
        return f"删除关系：{change.get('edge_id') or ''}".strip()
    return str(change.get("summary") or action or "").strip()


def normalize_domain_info(domain_input: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    domain_name = (
        generated.get("domain_name")
        or generated.get("name")
        or domain_input.get("domain_name")
        or domain_input.get("name")
        or "new_domain"
    )
    return {
        "domain_name": str(domain_name).strip(),
        "description": str(generated.get("description") or domain_input.get("description") or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def normalize_sections(domain_info: dict[str, Any], sections: dict[str, Any]) -> dict[str, Any]:
    object_types = as_list(sections.get("object_types"), "object_types")
    attributes = as_list(sections.get("attributes"), "attributes")
    relation_types = as_list(sections.get("relation_types"), "relation_types")
    schema_graph_edges = as_list(sections.get("schema_graph_edges"), "schema_graph_edges")
    for item in object_types:
        require_key(item, "object_type", "object_types")
        item.setdefault("enabled", True)
    object_ids = {str(item["object_type"]) for item in object_types}
    for item in attributes:
        require_key(item, "attribute_name", "attributes")
        if isinstance(item.get("object_types"), str):
            item["object_types"] = [item["object_types"]]
        item.setdefault("object_types", [])
        missing = [obj for obj in item["object_types"] if obj not in object_ids]
        if missing:
            raise StoreError(f"attributes.{item['attribute_name']} references unknown object_types: {', '.join(missing)}")
    for item in relation_types:
        require_key(item, "relation_type", "relation_types")
        item.setdefault("enabled", True)
    relation_ids = {str(item["relation_type"]) for item in relation_types}
    relation_ids.add("has_attribute")
    node_ids = {f"ObjectType:{item['object_type']}" for item in object_types}
    node_ids.update(f"Attribute:{item['attribute_name']}" for item in attributes)
    for item in schema_graph_edges:
        item["from"] = item.get("from") or item.get("source")
        item["to"] = item.get("to") or item.get("target")
        require_key(item, "from", "schema_graph_edges")
        require_key(item, "to", "schema_graph_edges")
        require_key(item, "relation_type", "schema_graph_edges")
        if item["from"] not in node_ids:
            raise StoreError(f"schema_graph_edges references unknown from node: {item['from']}")
        if item["to"] not in node_ids:
            raise StoreError(f"schema_graph_edges references unknown to node: {item['to']}")
        if item["relation_type"] not in relation_ids:
            raise StoreError(f"schema_graph_edges references unknown relation_type: {item['relation_type']}")
        item["edge_id"] = item.get("edge_id") or f"{item['from']}__{item['relation_type']}__{item['to']}"
    return {
        "domain": domain_info,
        "object_types": object_types,
        "attributes": attributes,
        "relation_types": relation_types,
        "schema_graph_edges": schema_graph_edges,
    }


def upsert_domain_node(domain_id: str, node_type: str, node_id: str, data: dict[str, Any], version_id: str | None = None) -> dict[str, Any]:
    version_id = version_id or current_version_id(domain_id)
    file_name, key = domain_node_target(node_type)
    rows = as_list(read_domain_file(domain_id, file_name, version_id), file_name)
    identity = strip_node_prefix(node_id)
    payload = dict(data)
    payload[key] = payload.get(key) or identity
    if node_type == "Attribute" and isinstance(payload.get("object_types"), str):
        payload["object_types"] = [payload["object_types"]]
    existing = next((item for item in rows if str(item.get(key)) == str(payload[key])), None)
    action = "updated"
    if existing:
        existing.clear()
        existing.update(payload)
    else:
        rows.append(payload)
        action = "created"
    write = write_domain_file(domain_id, file_name, rows, version_id)
    return {"action": action, "node_type": node_type, "node_id": payload[key], "write": write}


def delete_domain_node(domain_id: str, node_id: str, *, force: bool = False, version_id: str | None = None) -> dict[str, Any]:
    version_id = version_id or current_version_id(domain_id)
    graph = read_domain(domain_id, version_id)
    node_type = node_id.split(":", 1)[0]
    file_name, key = domain_node_target(node_type)
    incident = [
        edge
        for edge in graph["schema_graph_edges"]
        if edge.get("from") == node_id or edge.get("source") == node_id or edge.get("to") == node_id or edge.get("target") == node_id
    ]
    if incident and not force:
        raise StoreError(f"Node has {len(incident)} associated explicit edges")
    removed_edges = []
    if force and incident:
        kept = []
        for edge in graph["schema_graph_edges"]:
            if edge in incident:
                removed_edges.append(edge)
            else:
                kept.append(edge)
        write_domain_file(domain_id, "schema_graph_edges.yaml", kept, version_id)

    rows = as_list(read_domain_file(domain_id, file_name, version_id), file_name)
    identity = strip_node_prefix(node_id)
    for index, item in enumerate(rows):
        if str(item.get(key)) == identity:
            deleted = rows.pop(index)
            write = write_domain_file(domain_id, file_name, rows, version_id)
            return {"deleted": deleted, "deleted_schema_edges": removed_edges, "write": write}
    raise StoreError(f"Domain node not found: {node_id}")


def upsert_domain_edge(domain_id: str, edge_id: str | None, source: str, target: str, relation_type: str, properties: dict[str, Any], version_id: str | None = None) -> dict[str, Any]:
    version_id = version_id or current_version_id(domain_id)
    domain = read_domain(domain_id, version_id)
    node_ids = {f"ObjectType:{item['object_type']}" for item in domain["object_types"]}
    node_ids.update(f"Attribute:{item['attribute_name']}" for item in domain["attributes"])
    relation_ids = {item.get("relation_type") for item in domain["relation_types"]}
    relation_ids.add("has_attribute")
    if source not in node_ids:
        raise StoreError(f"source does not exist: {source}")
    if target not in node_ids:
        raise StoreError(f"target does not exist: {target}")
    if relation_type not in relation_ids:
        raise StoreError(f"relation_type does not exist in domain relation_types.yaml: {relation_type}")
    rows = domain["schema_graph_edges"]
    next_edge_id = edge_id or f"{source}__{relation_type}__{target}"
    edge = {"edge_id": next_edge_id, "from": source, "to": target, "relation_type": relation_type, **properties}
    existing = next((item for item in rows if item.get("edge_id") == next_edge_id), None)
    action = "updated"
    if existing:
        existing.clear()
        existing.update(edge)
    else:
        rows.append(edge)
        action = "created"
    write = write_domain_file(domain_id, "schema_graph_edges.yaml", rows, version_id)
    return {"action": action, "edge": edge, "write": write}


def delete_domain_edge(domain_id: str, edge_id: str, version_id: str | None = None) -> dict[str, Any]:
    version_id = version_id or current_version_id(domain_id)
    rows = as_list(read_domain_file(domain_id, "schema_graph_edges.yaml", version_id), "schema_graph_edges.yaml")
    for index, item in enumerate(rows):
        if item.get("edge_id") == edge_id:
            deleted = rows.pop(index)
            write = write_domain_file(domain_id, "schema_graph_edges.yaml", rows, version_id)
            return {"deleted": deleted, "write": write}
    raise StoreError(f"Domain edge not found: {edge_id}")


def domain_node_target(node_type: str) -> tuple[str, str]:
    mapping = {
        "ObjectType": ("object_types.yaml", "object_type"),
        "Attribute": ("attributes.yaml", "attribute_name"),
        "RelationType": ("relation_types.yaml", "relation_type"),
    }
    if node_type not in mapping:
        raise StoreError(f"Unsupported domain node_type: {node_type}")
    return mapping[node_type]


def as_list(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise StoreError(f"{label} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise StoreError(f"{label} must contain objects")
    return value


def require_key(item: dict[str, Any], key: str, label: str) -> None:
    if not str(item.get(key) or "").strip():
        raise StoreError(f"{label} item missing {key}")


def strip_node_prefix(node_id: str) -> str:
    return node_id.split(":", 1)[1] if ":" in node_id else node_id


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())
