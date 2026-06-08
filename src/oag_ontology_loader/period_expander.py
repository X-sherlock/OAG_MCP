from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PeriodVariant:
    code: str
    name_zh: str
    aliases: tuple[str, ...]
    table_suffix: str
    field_replacement: str


@dataclass(frozen=True)
class PeriodExpansionResult:
    sections: dict[str, list[dict[str, Any]]]
    table_node_map: dict[str, list[str]]
    field_node_map: dict[str, list[str]]


PERIOD_VARIANTS_FILE = "period_variants.yaml"
FIELD_PLACEHOLDER_PATTERN = re.compile(r"近\s*\d*\s*xx|近\s*x", re.IGNORECASE)


def load_period_variants(ontology_dir: str | Path) -> list[PeriodVariant]:
    path = Path(ontology_dir) / PERIOD_VARIANTS_FILE
    if not path.exists():
        return []
    import yaml  # type: ignore[import-not-found]

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    periods = payload.get("periods") or []
    variants: list[PeriodVariant] = []
    for item in periods:
        variants.append(
            PeriodVariant(
                code=str(item["code"]),
                name_zh=str(item["name_zh"]),
                aliases=tuple(str(alias) for alias in item.get("aliases", [])),
                table_suffix=str(item.get("table_suffix") or item["code"]),
                field_replacement=str(item.get("field_replacement") or item["name_zh"]),
            )
        )
    return variants


def expand_period_templates(
    sections: dict[str, list[dict[str, Any]]],
    periods: list[PeriodVariant],
) -> PeriodExpansionResult:
    if not periods:
        return PeriodExpansionResult(
            sections={name: [copy.deepcopy(item) for item in rows] for name, rows in sections.items()},
            table_node_map={},
            field_node_map={},
        )

    table_node_map: dict[str, list[str]] = {}
    field_node_map: dict[str, list[str]] = {}
    expanded_table_schemas = _expand_table_schemas(
        sections.get("table_schemas", []),
        periods,
        table_node_map,
        field_node_map,
    )
    expanded_sections = {
        name: [copy.deepcopy(item) for item in rows]
        for name, rows in sections.items()
    }
    expanded_sections["table_schemas"] = expanded_table_schemas
    expanded_sections["schema_graph_edges"] = _expand_schema_graph_edges(
        sections.get("schema_graph_edges", []),
        periods,
        table_node_map,
        field_node_map,
    )
    for section_name in ("queries", "object_types", "data_sources", "instance_rules"):
        if section_name in expanded_sections:
            expanded_sections[section_name] = [
                _expand_source_table_lists(item, periods) for item in expanded_sections[section_name]
            ]
    for section_name in ("attributes", "skills"):
        if section_name in expanded_sections:
            expanded_sections[section_name] = [
                _expand_source_table_lists(item, periods) for item in expanded_sections[section_name]
            ]
    return PeriodExpansionResult(expanded_sections, table_node_map, field_node_map)


def is_period_template_table(table_name: str) -> bool:
    return "xx" in str(table_name or "").lower()


def is_period_template_field(field_name: str) -> bool:
    return bool(FIELD_PLACEHOLDER_PATTERN.search(str(field_name or "")))


def expand_table_name(table_name: str, period: PeriodVariant) -> str:
    name = str(table_name).strip().replace(" ", "_")
    name = re.sub(r"(?i)retxx", f"ret_{period.table_suffix}", name)
    name = re.sub(r"(?i)xx", period.table_suffix, name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def expand_field_name(field_name: str, period: PeriodVariant) -> str:
    return FIELD_PLACEHOLDER_PATTERN.sub(period.field_replacement, str(field_name))


def expand_table_names(table_names: list[Any], periods: list[PeriodVariant]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for raw_name in table_names:
        table_name = str(raw_name)
        names = (
            [expand_table_name(table_name, period) for period in periods]
            if is_period_template_table(table_name)
            else [table_name]
        )
        for name in names:
            if name and name not in seen:
                seen.add(name)
                expanded.append(name)
    return expanded


def _expand_table_schemas(
    table_schemas: list[dict[str, Any]],
    periods: list[PeriodVariant],
    table_node_map: dict[str, list[str]],
    field_node_map: dict[str, list[str]],
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for table in table_schemas:
        table_name = str(table["table_name"])
        if not is_period_template_table(table_name):
            expanded.append(copy.deepcopy(table))
            continue
        table_node_map[f"DataTable:{table_name}"] = []
        supported_periods = table.get("supported_periods") or [period.code for period in periods]
        table_periods = [period for period in periods if period.code in supported_periods]
        for period in table_periods:
            expanded_table = copy.deepcopy(table)
            expanded_table_name = expand_table_name(table_name, period)
            expanded_table["table_name"] = expanded_table_name
            expanded_table["table_name_zh"] = expand_field_name(
                str(table.get("table_name_zh") or table_name), period
            )
            expanded_table["description"] = expand_field_name(
                str(table.get("description") or ""), period
            )
            expanded_table["period_expansion"] = _table_period_metadata(table_name, expanded_table_name, period)
            expanded_table["fields"] = [
                _expand_field_schema(field, table_name, expanded_table_name, period)
                for field in table.get("fields", [])
            ]
            expanded.append(expanded_table)
            table_node_map[f"DataTable:{table_name}"].append(f"DataTable:{expanded_table_name}")
            for field in table.get("fields", []):
                source_field_name = str(field["field_name"])
                source_field_node = f"DataField:{table_name}.{source_field_name}"
                expanded_field_name = expand_field_name(source_field_name, period)
                field_node_map.setdefault(source_field_node, []).append(
                    f"DataField:{expanded_table_name}.{expanded_field_name}"
                )
    return expanded


def _expand_field_schema(
    field: dict[str, Any],
    template_table: str,
    expanded_table: str,
    period: PeriodVariant,
) -> dict[str, Any]:
    expanded = copy.deepcopy(field)
    source_field_name = str(field["field_name"])
    expanded_field_name = expand_field_name(source_field_name, period)
    expanded["field_name"] = expanded_field_name
    expanded["field_name_zh"] = expand_field_name(str(field.get("field_name_zh") or source_field_name), period)
    expanded["aliases"] = [
        expand_field_name(str(alias), period)
        for alias in field.get("aliases", [])
    ]
    expanded["period_expansion"] = _field_period_metadata(
        template_table=template_table,
        template_field=source_field_name,
        logical_field_name=expanded_field_name,
        period=period,
    )
    expanded["period_expansion"]["logical_table_name"] = expanded_table
    return expanded


def _expand_schema_graph_edges(
    edges: list[dict[str, Any]],
    periods: list[PeriodVariant],
    table_node_map: dict[str, list[str]],
    field_node_map: dict[str, list[str]],
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    known_expanded_nodes = set()
    for nodes in table_node_map.values():
        known_expanded_nodes.update(nodes)
    for nodes in field_node_map.values():
        known_expanded_nodes.update(nodes)

    for edge in edges:
        from_nodes_by_period = _expand_node_ref(str(edge["from"]), periods, table_node_map, field_node_map)
        to_nodes_by_period = _expand_node_ref(str(edge["to"]), periods, table_node_map, field_node_map)
        if not from_nodes_by_period and not to_nodes_by_period:
            expanded.append(copy.deepcopy(edge))
            continue
        for period in periods:
            from_node = (from_nodes_by_period or {}).get(period.code) or edge["from"]
            to_node = (to_nodes_by_period or {}).get(period.code) or edge["to"]
            if _is_template_node(str(from_node)) or _is_template_node(str(to_node)):
                continue
            if (from_node in known_expanded_nodes or to_node in known_expanded_nodes) and (
                _expanded_endpoint_missing(str(from_node), known_expanded_nodes, table_node_map, field_node_map)
                or _expanded_endpoint_missing(str(to_node), known_expanded_nodes, table_node_map, field_node_map)
            ):
                continue
            item = copy.deepcopy(edge)
            item["from"] = from_node
            item["to"] = to_node
            item["edge_id"] = f"{from_node}__{item['relation_type']}__{to_node}"
            item.update(
                {
                    "is_expanded_from_period_template": True,
                    "template_source_edge": edge.get("edge_id") or (
                        f"{edge.get('from')}__{edge.get('relation_type')}__{edge.get('to')}"
                    ),
                    "period_code": period.code,
                    "period_name_zh": period.name_zh,
                }
            )
            expanded.append(item)
    return expanded


def _expand_node_ref(
    node_id: str,
    periods: list[PeriodVariant],
    table_node_map: dict[str, list[str]],
    field_node_map: dict[str, list[str]],
) -> dict[str, str]:
    if node_id in table_node_map:
        return {
            period.code: table_node_map[node_id][index]
            for index, period in enumerate(periods)
            if index < len(table_node_map[node_id])
        }
    if node_id in field_node_map:
        return {
            period.code: field_node_map[node_id][index]
            for index, period in enumerate(periods)
            if index < len(field_node_map[node_id])
        }
    object_type, object_id = _split_node_id(node_id)
    if object_type == "DataTable" and is_period_template_table(object_id):
        return {period.code: f"DataTable:{expand_table_name(object_id, period)}" for period in periods}
    if object_type == "DataField" and _field_ref_has_template(object_id):
        return {
            period.code: f"DataField:{_expand_field_ref_object_id(object_id, period)}"
            for period in periods
        }
    return {}


def _expand_field_ref_object_id(object_id: str, period: PeriodVariant) -> str:
    if "." not in object_id:
        return expand_field_name(expand_table_name(object_id, period), period)
    table_name, field_name = object_id.split(".", 1)
    return f"{expand_table_name(table_name, period)}.{expand_field_name(field_name, period)}"


def _field_ref_has_template(object_id: str) -> bool:
    if "." not in object_id:
        return is_period_template_table(object_id) or is_period_template_field(object_id)
    table_name, field_name = object_id.split(".", 1)
    return is_period_template_table(table_name) or is_period_template_field(field_name)


def _expand_source_table_lists(item: dict[str, Any], periods: list[PeriodVariant]) -> dict[str, Any]:
    expanded = copy.deepcopy(item)
    for key in ("source_tables", "tables"):
        if isinstance(expanded.get(key), list):
            expanded[key] = expand_table_names(expanded[key], periods)
    return expanded


def _table_period_metadata(template_table: str, logical_table_name: str, period: PeriodVariant) -> dict[str, Any]:
    return {
        "is_expanded_from_period_template": True,
        "template_source_table": template_table,
        "period_code": period.code,
        "period_name_zh": period.name_zh,
        "period_placeholder": "xx",
        "logical_table_name": logical_table_name,
        "physical_table_name": None,
        "physical_resolution_required": True,
    }


def _field_period_metadata(
    template_table: str,
    template_field: str,
    logical_field_name: str,
    period: PeriodVariant,
) -> dict[str, Any]:
    return {
        "is_expanded_from_period_template": True,
        "template_source_table": template_table,
        "template_source_field": template_field,
        "period_code": period.code,
        "period_name_zh": period.name_zh,
        "period_placeholder": "xx",
        "logical_field_name": logical_field_name,
        "physical_field_name": None,
        "physical_resolution_required": True,
    }


def _is_template_node(node_id: str) -> bool:
    object_type, object_id = _split_node_id(node_id)
    if object_type not in {"DataTable", "DataField"}:
        return False
    return "xx" in object_id.lower() or bool(FIELD_PLACEHOLDER_PATTERN.search(object_id))


def _expanded_endpoint_missing(
    node_id: str,
    known_expanded_nodes: set[str],
    table_node_map: dict[str, list[str]],
    field_node_map: dict[str, list[str]],
) -> bool:
    object_type, _ = _split_node_id(node_id)
    if object_type not in {"DataTable", "DataField"}:
        return False
    if node_id in known_expanded_nodes:
        return False
    if node_id in table_node_map or node_id in field_node_map:
        return True
    return False


def _split_node_id(node_id: str) -> tuple[str, str]:
    if ":" not in node_id:
        return "", node_id
    return node_id.split(":", 1)
