from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = PROJECT_ROOT / "ontology"
BACKUP_DIR = ONTOLOGY_DIR / ".backups"

SUPPORTED_FILES: tuple[str, ...] = (
    "attributes.yaml",
    "data_sources.yaml",
    "instance_rules.yaml",
    "intent_profiles.yaml",
    "object_types.yaml",
    "period_variants.yaml",
    "queries.yaml",
    "relation_types.yaml",
    "schema_graph_edges.yaml",
    "skills.yaml",
    "table_schemas.yaml",
)

SECTION_BY_FILE = {
    "attributes.yaml": "attributes",
    "data_sources.yaml": "data_sources",
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


class StoreError(ValueError):
    pass


def allowed_path(file_name: str) -> Path:
    if file_name == "table_shcemas.yaml":
        raise StoreError("table_shcemas.yaml is a typo. Use table_schemas.yaml.")
    if file_name not in SUPPORTED_FILES:
        raise StoreError(f"Unsupported ontology file: {file_name}")
    path = (ONTOLOGY_DIR / file_name).resolve()
    root = ONTOLOGY_DIR.resolve()
    if root not in path.parents:
        raise StoreError("Path traversal is not allowed")
    return path


def file_infos() -> list[dict[str, Any]]:
    infos: list[dict[str, Any]] = []
    for file_name in SUPPORTED_FILES:
        path = allowed_path(file_name)
        stat = path.stat() if path.exists() else None
        infos.append(
            {
                "name": file_name,
                "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "exists": path.exists(),
                "modified_at": (
                    datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                    if stat
                    else None
                ),
            }
        )
    typo_path = ONTOLOGY_DIR / "table_shcemas.yaml"
    if typo_path.exists():
        infos.append(
            {
                "name": "table_shcemas.yaml",
                "path": "ontology/table_shcemas.yaml",
                "exists": True,
                "modified_at": datetime.fromtimestamp(typo_path.stat().st_mtime).isoformat(
                    timespec="seconds"
                ),
                "error": "Typo file detected. Use ontology/table_schemas.yaml instead.",
            }
        )
    return infos


def read_yaml_file(file_name: str) -> Any:
    path = allowed_path(file_name)
    if not path.exists():
        raise StoreError(f"Ontology file does not exist: {file_name}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise StoreError(f"YAML parse failed in {file_name}: {exc}") from exc


def read_all() -> dict[str, Any]:
    return {SECTION_BY_FILE[name]: read_yaml_file(name) for name in SUPPORTED_FILES}


def backup_file(file_name: str) -> Path | None:
    path = allowed_path(file_name)
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = BACKUP_DIR / f"{path.stem}.{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def write_yaml_file(file_name: str, data: Any) -> dict[str, Any]:
    path = allowed_path(file_name)
    serialized = dump_yaml(data)
    try:
        yaml.safe_load(serialized)
    except yaml.YAMLError as exc:
        raise StoreError(f"Generated YAML is invalid for {file_name}: {exc}") from exc

    backup_path = backup_file(file_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.stem}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
        os.replace(temp_path, path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return {
        "file": file_name,
        "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "backup_path": (
            str(backup_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if backup_path
            else None
        ),
    }


def primary_key_for_node_type(node_type: str) -> tuple[str, str, str | None]:
    mapping: dict[str, tuple[str, str, str | None]] = {
        "ObjectType": ("object_types.yaml", "object_type", None),
        "Attribute": ("attributes.yaml", "attribute_name", None),
        "RelationType": ("relation_types.yaml", "relation_type", None),
        "QueryCapability": ("queries.yaml", "query_id", None),
        "SkillCapability": ("skills.yaml", "skill_id", None),
        "IntentProfile": ("intent_profiles.yaml", "intent_name", None),
        "DataSource": ("data_sources.yaml", "source_id", None),
        "DataTable": ("table_schemas.yaml", "table_name", None),
        "DataField": ("table_schemas.yaml", "field_name", "fields"),
        "PeriodVariant": ("period_variants.yaml", "code", "periods"),
        "InstanceRule": ("instance_rules.yaml", "rule_id", None),
    }
    if node_type not in mapping:
        raise StoreError(f"Unsupported node_type: {node_type}")
    return mapping[node_type]


def upsert_node_payload(node_type: str, node_id: str, data: dict[str, Any]) -> dict[str, Any]:
    file_name, key, nested_key = primary_key_for_node_type(node_type)
    payload = normalize_node_payload(node_type, node_id, data)
    content = read_yaml_file(file_name)
    changed = "updated"

    if node_type == "DataField":
        table_name = payload.pop("table_name", None) or parse_data_field_id(node_id)[0]
        field_name = payload.get("field_name") or parse_data_field_id(node_id)[1]
        payload["field_name"] = field_name
        table = find_item(content, "table_name", table_name)
        if table is None:
            raise StoreError(f"DataTable not found for DataField: {table_name}")
        fields = table.setdefault("fields", [])
        if not isinstance(fields, list):
            raise StoreError(f"DataTable {table_name} fields must be a list")
        existing = find_item(fields, key, field_name)
        if existing is None:
            fields.append(payload)
            changed = "created"
        else:
            existing.clear()
            existing.update(payload)
        result = write_yaml_file(file_name, content)
        result.update({"action": changed, "node_type": node_type, "node_id": f"{table_name}.{field_name}"})
        return result

    if nested_key:
        rows = content.setdefault(nested_key, []) if isinstance(content, dict) else None
        if not isinstance(rows, list):
            raise StoreError(f"{file_name} must contain list field {nested_key}")
    else:
        rows = content
        if not isinstance(rows, list):
            raise StoreError(f"{file_name} must contain a list")

    identity = payload.get(key) or strip_node_prefix(node_id)
    payload[key] = identity
    existing = find_item(rows, key, identity)
    if existing is None:
        rows.append(payload)
        changed = "created"
    else:
        existing.clear()
        existing.update(payload)
    result = write_yaml_file(file_name, content)
    result.update({"action": changed, "node_type": node_type, "node_id": identity})
    return result


def delete_node_payload(node_type: str, node_id: str) -> dict[str, Any]:
    file_name, key, nested_key = primary_key_for_node_type(node_type)
    identity = strip_node_prefix(node_id)
    content = read_yaml_file(file_name)

    if node_type == "DataField":
        table_name, field_name = parse_data_field_id(identity)
        table = find_item(content, "table_name", table_name)
        if table is None:
            raise StoreError(f"DataTable not found: {table_name}")
        fields = table.get("fields")
        if not isinstance(fields, list):
            raise StoreError(f"DataTable {table_name} fields must be a list")
        removed = remove_item(fields, "field_name", field_name)
    else:
        if nested_key:
            rows = content.get(nested_key) if isinstance(content, dict) else None
        else:
            rows = content
        if not isinstance(rows, list):
            raise StoreError(f"{file_name} target section must be a list")
        removed = remove_item(rows, key, identity)

    if removed is None:
        raise StoreError(f"Node not found: {node_id}")
    result = write_yaml_file(file_name, content)
    result.update({"deleted": removed, "node_type": node_type, "node_id": node_id})
    return result


def find_item(rows: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any] | None:
    for item in rows:
        if isinstance(item, dict) and str(item.get(key)) == str(value):
            return item
    return None


def remove_item(rows: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any] | None:
    for index, item in enumerate(rows):
        if isinstance(item, dict) and str(item.get(key)) == str(value):
            return rows.pop(index)
    return None


def strip_node_prefix(node_id: str) -> str:
    return node_id.split(":", 1)[1] if ":" in node_id else node_id


def parse_data_field_id(node_id: str) -> tuple[str, str]:
    identity = strip_node_prefix(node_id)
    if "." not in identity:
        raise StoreError("DataField id must use table_name.field_name")
    return identity.split(".", 1)


def normalize_node_payload(node_type: str, node_id: str, data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    payload.pop("raw", None)
    payload.pop("type", None)
    payload.pop("id", None)
    if node_type == "ObjectType":
        if "object_name_zh" in payload and "object_type_zh" not in payload:
            payload["object_type_zh"] = payload.pop("object_name_zh")
        payload.pop("object_name", None)
    if node_type == "Attribute":
        if "data_type" in payload and "value_type" not in payload:
            payload["value_type"] = payload.pop("data_type")
        if "object_type" in payload and "object_types" not in payload:
            value = payload.pop("object_type")
            payload["object_types"] = value if isinstance(value, list) else [value]
    if node_type == "DataField" and "data_type" in payload and "semantic_type" not in payload:
        payload["semantic_type"] = payload.pop("data_type")
    if node_type == "QueryCapability" and "description" not in payload:
        payload["description"] = payload.get("query_name", "")
    if node_type == "SkillCapability":
        if not payload.get("permission_scope"):
            payload["permission_scope"] = "fund_public_data:read"
        payload.setdefault("related_queries", [])
    if node_type == "PeriodVariant":
        payload.setdefault("code", strip_node_prefix(node_id))
    return payload
