from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from oag_mcp.config import TDSQLConfig, load_config
from oag_ontology_loader.loader import DEFAULT_ONTOLOGY_DIR, load_ontology
from oag_ontology_loader.mysql_writer import MySQLOntologyWriter


DOMAIN = "finance_market"


def main(argv: list[str] | None = None) -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--include-sample",
        action="store_true",
        help="also seed optional sample instance nodes/edges for smoke tests",
    )
    args = parser.parse_args(argv or [])
    config = load_config()
    payloads = load_seed_payloads(include_sample=args.include_sample)
    summary = seed_mysql(payloads, config.tdsql) or _payload_summary(payloads)
    print(
        "Seeded OAG schema-level ontology data from ontology/*.yaml into MySQL metadata, "
        "aliases, and graph tables."
    )
    print(
        "Summary: "
        f"objects={summary['objects']}, "
        f"attributes={summary['attributes']}, "
        f"queries={summary['queries']}, "
        f"skills={summary['skills']}, "
        f"intent_profiles={summary['intent_profiles']}, "
        f"graph_nodes={summary['graph_nodes']}, "
        f"graph_edges={summary['graph_edges']}"
    )


def load_seed_payloads(
    ontology_dir: str | Path | None = None,
    domain: str = DOMAIN,
    include_sample: bool = False,
) -> dict[str, Any]:
    catalog = load_ontology(ontology_dir or DEFAULT_ONTOLOGY_DIR)
    objects = [_seed_schema_object_type(item, domain) for item in catalog.object_types]
    attributes = [
        _seed_attribute(item, object_type, domain)
        for item in catalog.attributes
        for object_type in item["object_types"]
    ]
    queries = [_seed_query(item, domain) for item in catalog.queries]
    skills = [_seed_skill(item, domain) for item in catalog.skills]
    intent_profiles = [_seed_intent_profile(item, domain) for item in catalog.intent_profiles]
    nodes = _schema_graph_nodes(catalog, domain)
    edges = [_seed_graph_edge(item) for item in catalog.schema_graph_edges]
    if include_sample:
        nodes.extend(_seed_graph_node(item, domain) for item in catalog.sample_instances)
        edges.extend(_seed_graph_edge(item) for item in catalog.sample_graph_edges)
    return {
        "domain": domain,
        "include_sample": include_sample,
        "objects": objects,
        "attributes": attributes,
        "queries": queries,
        "skills": skills,
        "intent_profiles": intent_profiles,
        "graph": {
            "nodes": _dedupe_by_id(nodes, "id"),
            "edges": _dedupe_by_id(edges, "edge_id"),
        },
    }


def seed_mysql(payloads: dict[str, Any], config: TDSQLConfig) -> dict[str, int]:
    return MySQLOntologyWriter(config).write_payloads(payloads)


def _seed_object(item: dict[str, Any], domain: str) -> dict[str, Any]:
    return {
        "domain": item.get("domain") or domain,
        "object_type": item["object_type"],
        "object_id": item["object_id"],
        "object_name": item.get("object_name", ""),
        "aliases": item.get("aliases", []),
        "params": item.get("params", {}),
    }


def _seed_schema_object_type(item: dict[str, Any], domain: str) -> dict[str, Any]:
    object_type = item["object_type"]
    object_name = item.get("object_type_zh") or object_type
    return {
        "domain": domain,
        "object_type": "ObjectType",
        "object_id": object_type,
        "object_name": object_name,
        "aliases": [object_type, object_name],
        "params": {
            "schema_level": True,
            "target_object_type": object_type,
            "object_name_zh": object_name,
            "description": item.get("description", ""),
            "source_tables": item.get("source_tables", []),
            "enabled": item.get("enabled", True),
        },
    }


def _seed_attribute(item: dict[str, Any], object_type: str, domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "object_type": object_type,
        "attribute_name": item["attribute_name"],
        "attribute_name_zh": item["attribute_name_zh"],
        "aliases": item.get("aliases", []),
    }


def _seed_query(item: dict[str, Any], domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "query_id": item["query_id"],
        "description": item.get("description") or item["query_name"],
        "target_object_type": item["target_object_type"],
        "required_params": item["required_params"],
        "optional_params": item.get("optional_params", []),
        "output_attributes": item["output_attributes"],
        "tool_type": item.get("tool_type", "MCP"),
        "tool_name": item["tool_name"],
        "permission_scope": item["permission_scope"],
        "enabled": item.get("enabled", True),
    }


def _seed_skill(item: dict[str, Any], domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "skill_id": item["skill_id"],
        "skill_name": item["skill_name"],
        "description": item["description"],
        "target_object_type": item["target_object_type"],
        "input_params": item["input_params"],
        "output_attributes": item["output_attributes"],
        "provides_fact_types": item.get("provides_fact_types", []),
        "supported_subject_types": item.get("supported_subject_types", []),
        "supported_attributes": item.get("supported_attributes", []),
        "supported_relations": item.get("supported_relations", []),
        "output_fact_schema": item.get("output_fact_schema", []),
        "supported_constraints": item.get("supported_constraints", []),
        "related_queries": item.get("related_queries", []),
        "permission_scope": item["permission_scope"],
        "enabled": item.get("enabled", True),
    }


def _seed_intent_profile(item: dict[str, Any], domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "intent_name": item["intent_name"],
        "intent_name_zh": item.get("intent_name_zh", ""),
        "trigger_aliases": item.get("trigger_aliases", []),
        "default_attributes": item.get("default_attributes", []),
        "primary_skills": item.get("primary_skills", []),
        "secondary_skills": item.get("secondary_skills", []),
        "optional_skills": item.get("optional_skills", []),
        "required_params": item.get("required_params", []),
        "fact_requirements_template": item.get("fact_requirements_template", []),
        "enabled": item.get("enabled", True),
    }


def _seed_graph_node(item: dict[str, Any], domain: str) -> dict[str, Any]:
    return {"id": item["id"], **_seed_object(item, domain)}


def _seed_graph_edge(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge_id": item["edge_id"],
        "from": item["from"],
        "to": item["to"],
        "relation_type": item["relation_type"],
        "relation_name_zh": item.get("relation_name_zh", ""),
        "score": item.get("score", 0.9),
        **{
            key: value
            for key, value in item.items()
            if key not in {"edge_id", "from", "to", "relation_type", "relation_name_zh", "score"}
        },
    }


def _schema_graph_nodes(catalog: Any, domain: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for item in catalog.object_types:
        object_type = item["object_type"]
        nodes.append(
            _node_payload(
                domain,
                f"ObjectType:{object_type}",
                "ObjectType",
                object_type,
                item.get("object_type_zh", object_type),
                [object_type, item.get("object_type_zh", "")],
                {"source_tables": item.get("source_tables", [])},
            )
        )
    for item in catalog.attributes:
        attribute_name = item["attribute_name"]
        nodes.append(
            _node_payload(
                domain,
                f"Attribute:{attribute_name}",
                "Attribute",
                attribute_name,
                item.get("attribute_name_zh", attribute_name),
                [attribute_name, item.get("attribute_name_zh", ""), *item.get("aliases", [])],
                {
                    "value_type": item.get("value_type"),
                    "source_tables": item.get("source_tables", []),
                    "source_fields": item.get("source_fields", []),
                    "object_types": item.get("object_types", []),
                },
            )
        )
    for item in catalog.fact_types:
        fact_type = item["fact_type"]
        nodes.append(
            _node_payload(
                domain,
                f"FactType:{fact_type}",
                "FactType",
                fact_type,
                item.get("fact_type_name_zh", fact_type),
                [fact_type, item.get("fact_type_name_zh", "")],
                {
                    "description_zh": item.get("description_zh", ""),
                    "applicable_subject_types": item.get("applicable_subject_types", []),
                    "default_priority": item.get("default_priority"),
                    "typical_attributes": item.get("typical_attributes", []),
                },
            )
        )
    for table in catalog.table_schemas:
        table_name = table["table_name"]
        nodes.append(
            _node_payload(
                domain,
                f"DataTable:{table_name}",
                "DataTable",
                table_name,
                table.get("table_name_zh", table_name),
                [table_name, table.get("table_name_zh", "")],
                {
                    "layer": table.get("layer"),
                    "entity_types": table.get("entity_types", []),
                    "description": table.get("description", ""),
                    **table.get("period_expansion", {}),
                },
            )
        )
        for field in table.get("fields", []):
            field_id = f"{table_name}.{field['field_name']}"
            nodes.append(
                _node_payload(
                    domain,
                    f"DataField:{field_id}",
                    "DataField",
                    field_id,
                    field.get("field_name_zh", field["field_name"]),
                    [
                        field_id,
                        field["field_name"],
                        field.get("field_name_zh", ""),
                        *field.get("aliases", []),
                    ],
                    {
                        "table_name": table_name,
                        "field_name": field["field_name"],
                        "field_name_zh": field.get("field_name_zh", ""),
                        "semantic_type": field.get("semantic_type", "unknown"),
                        "maps_to_attribute": field.get("maps_to_attribute"),
                        "is_key": bool(field.get("is_key", False)),
                        "is_time_field": bool(field.get("is_time_field", False)),
                        **field.get("period_expansion", {}),
                    },
                )
            )
    parameter_names: set[str] = set()
    for query in catalog.queries:
        query_id = query["query_id"]
        nodes.append(
            _node_payload(
                domain,
                f"QueryCapability:{query_id}",
                "QueryCapability",
                query_id,
                query.get("query_name", query_id),
                [query_id, query.get("query_name", "")],
                {
                    "target_object_type": query.get("target_object_type"),
                    "required_params": query.get("required_params", []),
                    "optional_params": query.get("optional_params", []),
                    "output_attributes": query.get("output_attributes", []),
                    "source_tables": query.get("source_tables", []),
                    "enabled": query.get("enabled", True),
                },
            )
        )
        parameter_names.update(query.get("required_params", []))
        parameter_names.update(query.get("optional_params", []))
    for parameter in sorted(parameter_names):
        nodes.append(_node_payload(domain, f"Parameter:{parameter}", "Parameter", parameter, parameter, [parameter], {}))
    for source in catalog.data_sources:
        source_id = source["source_id"]
        nodes.append(
            _node_payload(
                domain,
                f"DataSource:{source_id}",
                "DataSource",
                source_id,
                source_id,
                [source_id],
                {"source_type": source.get("source_type"), "tables": source.get("tables", [])},
            )
        )
    for skill in catalog.skills:
        skill_id = skill["skill_id"]
        nodes.append(
            _node_payload(
                domain,
                f"SkillCapability:{skill_id}",
                "SkillCapability",
                skill_id,
                skill.get("skill_name", skill_id),
                [skill_id, skill.get("skill_name", "")],
                {
                    "target_object_type": skill.get("target_object_type"),
                    "input_params": skill.get("input_params", []),
                    "output_attributes": skill.get("output_attributes", []),
                    "provides_fact_types": skill.get("provides_fact_types", []),
                    "supported_subject_types": skill.get("supported_subject_types", []),
                    "supported_attributes": skill.get("supported_attributes", []),
                    "supported_relations": skill.get("supported_relations", []),
                    "output_fact_schema": skill.get("output_fact_schema", []),
                    "supported_constraints": skill.get("supported_constraints", []),
                    "related_queries": skill.get("related_queries", []),
                    "enabled": skill.get("enabled", True),
                },
            )
        )
    return nodes


def _node_payload(
    domain: str,
    node_id: str,
    object_type: str,
    object_id: str,
    object_name: str,
    aliases: list[str],
    params: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": node_id,
        "domain": domain,
        "object_type": object_type,
        "object_id": object_id,
        "object_name": object_name,
        "aliases": aliases,
        "params": params,
    }


def _dedupe_by_id(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        deduped.setdefault(str(item[key]), item)
    return list(deduped.values())


def _payload_summary(payloads: dict[str, Any]) -> dict[str, int]:
    graph = payloads.get("graph", {})
    return {
        "objects": len(payloads.get("objects", [])),
        "attributes": len(payloads.get("attributes", [])),
        "queries": len(payloads.get("queries", [])),
        "skills": len(payloads.get("skills", [])),
        "intent_profiles": len(payloads.get("intent_profiles", [])),
        "graph_nodes": len(graph.get("nodes", [])),
        "graph_edges": len(graph.get("edges", [])),
    }


if __name__ == "__main__":
    main(sys.argv[1:])
