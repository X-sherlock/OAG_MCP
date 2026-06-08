from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any

from .graph_builder import build_graph
from .yaml_store import ONTOLOGY_DIR, PROJECT_ROOT, read_all

SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def validate_ontology() -> dict[str, list[str]]:
    errors: list[str] = []
    warning_messages: list[str] = []

    try:
        from oag_ontology_loader.loader import load_ontology

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            load_ontology(ONTOLOGY_DIR)
        warning_messages.extend(str(item.message) for item in caught)
    except Exception as exc:  # Keep API structured for YAML and model errors.
        errors.append(str(exc))

    try:
        sections = read_all()
        extra_errors, extra_warnings = validate_references(sections)
        errors.extend(extra_errors)
        warning_messages.extend(extra_warnings)
    except Exception as exc:
        errors.append(f"Reference validation failed: {exc}")

    return {"errors": dedupe(errors), "warnings": dedupe(warning_messages)}


def validate_references(sections: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings_out: list[str] = []

    object_types = values(sections, "object_types", "object_type")
    attributes = values(sections, "attributes", "attribute_name")
    skills = values(sections, "skills", "skill_id")
    queries = values(sections, "queries", "query_id")
    tables = values(sections, "table_schemas", "table_name")
    node_ids = graph_node_ids()

    for edge in rows(sections, "schema_graph_edges"):
        edge_id = edge.get("edge_id", "<unknown>")
        source = edge.get("from") or edge.get("source")
        target = edge.get("to") or edge.get("target")
        if source not in node_ids:
            errors.append(f"schema_graph_edges.yaml edge {edge_id} references unknown source: {source}")
        if target not in node_ids:
            errors.append(f"schema_graph_edges.yaml edge {edge_id} references unknown target: {target}")
    for attr in rows(sections, "attributes"):
        name = attr.get("attribute_name")
        for object_type in list_field(attr, "object_types"):
            if object_type not in object_types:
                errors.append(f"attributes.yaml item {name} references unknown object_type: {object_type}")
        for table_name in list_field(attr, "source_tables"):
            if table_name not in tables:
                warnings_out.append(f"attributes.yaml item {name} references source table not listed in table_schemas.yaml: {table_name}")

    for query in rows(sections, "queries"):
        query_id = query.get("query_id")
        if query.get("target_object_type") not in object_types:
            errors.append(
                f"queries.yaml item {query_id} references unknown target_object_type: {query.get('target_object_type')}"
            )
        for attr in list_field(query, "output_attributes"):
            if attr not in attributes:
                errors.append(f"queries.yaml item {query_id} references unknown output_attribute: {attr}")
        for table_name in list_field(query, "source_tables"):
            if table_name not in tables:
                warnings_out.append(f"queries.yaml item {query_id} references source table not listed in table_schemas.yaml: {table_name}")

    for skill in rows(sections, "skills"):
        skill_id = skill.get("skill_id")
        if skill.get("target_object_type") not in object_types:
            errors.append(
                f"skills.yaml item {skill_id} references unknown target_object_type: {skill.get('target_object_type')}"
            )
        for attr in list_field(skill, "supported_attributes"):
            if attr not in attributes:
                errors.append(f"skills.yaml item {skill_id} references unknown supported_attributes: {attr}")
        for attr in list_field(skill, "output_attributes"):
            if attr not in attributes:
                warnings_out.append(f"skills.yaml item {skill_id} references output_attribute not listed in attributes.yaml: {attr}")
        for query_id in list_field(skill, "related_queries"):
            if query_id not in queries:
                errors.append(f"skills.yaml item {skill_id} references unknown related_query: {query_id}")

    for profile in rows(sections, "intent_profiles"):
        intent = profile.get("intent_name")
        for attr in list_field(profile, "default_attributes"):
            if attr not in attributes:
                errors.append(f"intent_profiles.yaml item {intent} references unknown default_attribute: {attr}")
        for field in ("primary_skills", "secondary_skills", "optional_skills"):
            for skill_id in list_field(profile, field):
                if skill_id not in skills:
                    errors.append(f"intent_profiles.yaml item {intent} references unknown {field}: {skill_id}")
        priorities = profile.get("skill_priorities")
        if isinstance(priorities, dict):
            for skill_id in priorities:
                if skill_id not in skills:
                    errors.append(f"intent_profiles.yaml item {intent} references unknown skill_priorities key: {skill_id}")

    periods = (sections.get("period_variants") or {}).get("periods")
    if not isinstance(periods, list) or not periods:
        errors.append("period_variants.yaml must contain a non-empty periods list for xx template expansion")
    else:
        for period in periods:
            if not all(period.get(key) for key in ("code", "table_suffix", "field_replacement")):
                errors.append("period_variants.yaml periods items require code, table_suffix, and field_replacement")

    for table in rows(sections, "table_schemas"):
        table_name = table.get("table_name")
        fields = table.get("fields")
        if not isinstance(fields, list) or not fields:
            errors.append(f"table_schemas.yaml item {table_name} must define non-empty fields")
            continue
        seen_fields: set[str] = set()
        for field in fields:
            field_name = field.get("field_name")
            if not field_name:
                errors.append(f"table_schemas.yaml item {table_name} has a field without field_name")
            if field_name in seen_fields:
                errors.append(f"table_schemas.yaml item {table_name} has duplicate field_name: {field_name}")
            seen_fields.add(field_name)

    return errors, warnings_out


def graph_node_ids() -> set[str]:
    return {node["data"]["id"] for node in build_graph()["nodes"]}


def values(sections: dict[str, Any], section: str, key: str) -> set[str]:
    return {str(item.get(key)) for item in rows(sections, section) if item.get(key)}


def rows(sections: dict[str, Any], section: str) -> list[dict[str, Any]]:
    value = sections.get(section)
    return value if isinstance(value, list) else []


def list_field(item: dict[str, Any], field: str) -> list[Any]:
    value = item.get(field)
    return value if isinstance(value, list) else []


def dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
