from __future__ import annotations

import json
from typing import Any

try:  # pragma: no cover
    from mysql import connector
    from mysql.connector import Error as MySQLError
except ImportError:  # pragma: no cover
    connector = None  # type: ignore[assignment]
    MySQLError = Exception  # type: ignore[assignment]

from oag_mcp.config import TDSQLConfig
from oag_mcp.errors import OAGRepositoryError
from oag_mcp.repositories import normalize_alias


class MySQLOntologyWriter:
    """Write ontology metadata into MySQL before the MCP server is started."""

    def __init__(self, config: TDSQLConfig) -> None:
        self._config = config

    def write_payloads(self, payloads: dict[str, Any]) -> dict[str, int]:
        with self._connect() as conn:
            cursor = conn.cursor()
            self.ensure_optional_columns(cursor)
            self.upsert_domain(cursor, payloads["domain"])
            self.clear_seed_owned_rows(cursor, payloads["domain"])
            self.upsert_objects(cursor, payloads.get("objects", []))
            self.upsert_attributes(cursor, payloads.get("attributes", []))
            self.upsert_query_capabilities(cursor, payloads.get("queries", []))
            self.upsert_skill_capabilities(cursor, payloads.get("skills", []))
            self.upsert_intent_profiles(cursor, payloads.get("intent_profiles", []))
            self.upsert_object_aliases(cursor, payloads)
            self.upsert_attribute_aliases(cursor, payloads.get("attributes", []))
            self.upsert_graph_nodes(cursor, payloads.get("graph", {}).get("nodes", []), payloads["domain"])
            self.upsert_graph_edges(cursor, payloads.get("graph", {}).get("edges", []), payloads["domain"])
            conn.commit()
        return _payload_summary(payloads)

    def ensure_optional_columns(self, cursor: Any) -> None:
        """Add fact-oriented metadata columns when seeding an older metadata schema."""

        for table, columns in {
            "oag_skill_capabilities": {
                "provides_fact_types_json": "JSON NULL",
                "supported_subject_types_json": "JSON NULL",
                "supported_attributes_json": "JSON NULL",
                "output_fact_schema_json": "JSON NULL",
                "supported_constraints_json": "JSON NULL",
            },
            "oag_intent_profiles": {
                "fact_requirements_template_json": "JSON NULL",
            },
        }.items():
            for column, definition in columns.items():
                cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", (column,))
                if cursor.fetchone():
                    continue
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def clear_seed_owned_rows(self, cursor: Any, domain: str) -> None:
        """Remove stale ontology graph rows and aliases before writing the current seed payload."""

        cursor.execute("DELETE FROM oag_graph_edges WHERE domain = %s", (domain,))
        cursor.execute("DELETE FROM oag_graph_nodes WHERE domain = %s", (domain,))
        cursor.execute("DELETE FROM oag_attribute_aliases WHERE domain = %s", (domain,))
        cursor.execute(
            """
            DELETE FROM oag_object_aliases
            WHERE domain = %s
              AND object_type IN (
                  'ObjectType', 'Attribute', 'DataTable', 'DataField',
                  'QueryCapability', 'SkillCapability', 'Parameter', 'DataSource'
              )
            """,
            (domain,),
        )

    def upsert_domain(self, cursor: Any, domain: str) -> None:
        cursor.execute(
            "INSERT INTO oag_domains(domain, enabled) VALUES(%s, 1) "
            "ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)",
            (domain,),
        )

    def upsert_objects(self, cursor: Any, objects: list[dict[str, Any]]) -> None:
        for item in objects:
            aliases = item.get("aliases", [])
            params = item.get("params", {})
            cursor.execute(
                """
                INSERT INTO oag_objects(domain, object_type, object_id, object_name, aliases_json, params_json)
                VALUES(%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE object_name = VALUES(object_name),
                    aliases_json = VALUES(aliases_json), params_json = VALUES(params_json)
                """,
                (
                    item["domain"],
                    item["object_type"],
                    item["object_id"],
                    item.get("object_name", ""),
                    json.dumps(aliases if isinstance(aliases, list) else [], ensure_ascii=False),
                    json.dumps(params if isinstance(params, dict) else {}, ensure_ascii=False),
                ),
            )

    def upsert_attributes(self, cursor: Any, attributes: list[dict[str, Any]]) -> None:
        for item in attributes:
            cursor.execute(
                """
                INSERT INTO oag_attributes(domain, object_type, attribute_name, attribute_name_zh, aliases_json)
                VALUES(%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE attribute_name_zh = VALUES(attribute_name_zh),
                    aliases_json = VALUES(aliases_json)
                """,
                (
                    item["domain"],
                    item["object_type"],
                    item["attribute_name"],
                    item["attribute_name_zh"],
                    json.dumps(item["aliases"], ensure_ascii=False),
                ),
            )

    def upsert_query_capabilities(self, cursor: Any, queries: list[dict[str, Any]]) -> None:
        for item in queries:
            cursor.execute(
                """
                INSERT INTO oag_query_capabilities(
                    domain, query_id, description, target_object_type, required_params_json,
                    optional_params_json, output_attributes_json, tool_type, tool_name,
                    permission_scope, enabled
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE description = VALUES(description),
                    target_object_type = VALUES(target_object_type),
                    required_params_json = VALUES(required_params_json),
                    optional_params_json = VALUES(optional_params_json),
                    output_attributes_json = VALUES(output_attributes_json),
                    tool_type = VALUES(tool_type), tool_name = VALUES(tool_name),
                    permission_scope = VALUES(permission_scope), enabled = VALUES(enabled)
                """,
                (
                    item["domain"],
                    item["query_id"],
                    item["description"],
                    item["target_object_type"],
                    json.dumps(item["required_params"], ensure_ascii=False),
                    json.dumps(item["optional_params"], ensure_ascii=False),
                    json.dumps(item["output_attributes"], ensure_ascii=False),
                    item["tool_type"],
                    item["tool_name"],
                    item["permission_scope"],
                    int(bool(item["enabled"])),
                ),
            )

    def upsert_skill_capabilities(self, cursor: Any, skills: list[dict[str, Any]]) -> None:
        for item in skills:
            cursor.execute(
                """
                INSERT INTO oag_skill_capabilities(
                    domain, skill_id, skill_name, description, target_object_type,
                    input_params_json, output_attributes_json, related_queries_json,
                    permission_scope, provides_fact_types_json,
                    supported_subject_types_json, supported_attributes_json,
                    output_fact_schema_json, supported_constraints_json, enabled
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE skill_name = VALUES(skill_name),
                    description = VALUES(description),
                    target_object_type = VALUES(target_object_type),
                    input_params_json = VALUES(input_params_json),
                    output_attributes_json = VALUES(output_attributes_json),
                    related_queries_json = VALUES(related_queries_json),
                    permission_scope = VALUES(permission_scope),
                    provides_fact_types_json = VALUES(provides_fact_types_json),
                    supported_subject_types_json = VALUES(supported_subject_types_json),
                    supported_attributes_json = VALUES(supported_attributes_json),
                    output_fact_schema_json = VALUES(output_fact_schema_json),
                    supported_constraints_json = VALUES(supported_constraints_json),
                    enabled = VALUES(enabled)
                """,
                (
                    item["domain"],
                    item["skill_id"],
                    item["skill_name"],
                    item["description"],
                    item["target_object_type"],
                    json.dumps(item["input_params"], ensure_ascii=False),
                    json.dumps(item["output_attributes"], ensure_ascii=False),
                    json.dumps(item.get("related_queries", []), ensure_ascii=False),
                    item["permission_scope"],
                    json.dumps(item.get("provides_fact_types", []), ensure_ascii=False),
                    json.dumps(item.get("supported_subject_types", []), ensure_ascii=False),
                    json.dumps(item.get("supported_attributes", []), ensure_ascii=False),
                    json.dumps(item.get("output_fact_schema", []), ensure_ascii=False),
                    json.dumps(item.get("supported_constraints", []), ensure_ascii=False),
                    int(bool(item["enabled"])),
                ),
            )

    def upsert_intent_profiles(self, cursor: Any, profiles: list[dict[str, Any]]) -> None:
        for item in profiles:
            cursor.execute(
                """
                INSERT INTO oag_intent_profiles(
                    domain, intent_name, intent_name_zh, trigger_aliases_json,
                    default_attributes_json, primary_skills_json,
                    secondary_skills_json, optional_skills_json,
                    required_params_json, fact_requirements_template_json, enabled
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE intent_name_zh = VALUES(intent_name_zh),
                    trigger_aliases_json = VALUES(trigger_aliases_json),
                    default_attributes_json = VALUES(default_attributes_json),
                    primary_skills_json = VALUES(primary_skills_json),
                    secondary_skills_json = VALUES(secondary_skills_json),
                    optional_skills_json = VALUES(optional_skills_json),
                    required_params_json = VALUES(required_params_json),
                    fact_requirements_template_json = VALUES(fact_requirements_template_json),
                    enabled = VALUES(enabled)
                """,
                (
                    item["domain"],
                    item["intent_name"],
                    item.get("intent_name_zh", ""),
                    json.dumps(item.get("trigger_aliases", []), ensure_ascii=False),
                    json.dumps(item.get("default_attributes", []), ensure_ascii=False),
                    json.dumps(item.get("primary_skills", []), ensure_ascii=False),
                    json.dumps(item.get("secondary_skills", []), ensure_ascii=False),
                    json.dumps(item.get("optional_skills", []), ensure_ascii=False),
                    json.dumps(item.get("required_params", []), ensure_ascii=False),
                    json.dumps(item.get("fact_requirements_template", []), ensure_ascii=False),
                    int(bool(item.get("enabled", True))),
                ),
            )

    def upsert_object_aliases(self, cursor: Any, payloads: dict[str, Any]) -> None:
        seen: set[tuple[str, str, str, str]] = set()
        for item in [*payloads.get("objects", []), *payloads.get("graph", {}).get("nodes", [])]:
            domain = item.get("domain") or payloads["domain"]
            object_type = item["object_type"]
            object_id = item["object_id"]
            for alias in _alias_values(item.get("object_id"), item.get("object_name"), item.get("aliases", [])):
                normalized = normalize_alias(alias)
                key = (domain, object_type, object_id, normalized)
                if not normalized or key in seen:
                    continue
                seen.add(key)
                cursor.execute(
                    """
                    INSERT INTO oag_object_aliases(
                        domain, object_id, object_type, alias, normalized_alias
                    )
                    VALUES(%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE alias = VALUES(alias)
                    """,
                    (domain, object_id, object_type, alias, normalized),
                )

    def upsert_attribute_aliases(self, cursor: Any, attributes: list[dict[str, Any]]) -> None:
        seen: set[tuple[str, str, str]] = set()
        for item in attributes:
            for alias in _alias_values(item["attribute_name"], item["attribute_name_zh"], item["aliases"]):
                key = (item["domain"], item["attribute_name"], normalize_alias(alias))
                if not key[2] or key in seen:
                    continue
                seen.add(key)
                cursor.execute(
                    """
                    INSERT INTO oag_attribute_aliases(
                        domain, attribute_name, alias, normalized_alias
                    )
                    VALUES(%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE alias = VALUES(alias)
                    """,
                    (item["domain"], item["attribute_name"], alias, key[2]),
                )

    def upsert_graph_nodes(self, cursor: Any, nodes: list[dict[str, Any]], domain: str) -> None:
        for node in nodes:
            cursor.execute(
                """
                INSERT INTO oag_graph_nodes(
                    domain, node_id, object_type, object_id, name,
                    properties_json, enabled
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE object_type = VALUES(object_type),
                    object_id = VALUES(object_id), name = VALUES(name),
                    properties_json = VALUES(properties_json),
                    enabled = VALUES(enabled), updated_at = CURRENT_TIMESTAMP
                """,
                (
                    node.get("domain") or domain,
                    node["id"],
                    node["object_type"],
                    node["object_id"],
                    node.get("object_name", ""),
                    json.dumps(
                        {
                            "aliases": node.get("aliases", []),
                            "params": node.get("params", {}),
                        },
                        ensure_ascii=False,
                    ),
                    1,
                ),
            )

    def upsert_graph_edges(self, cursor: Any, edges: list[dict[str, Any]], domain: str) -> None:
        for edge in edges:
            cursor.execute(
                """
                INSERT INTO oag_graph_edges(
                    domain, edge_id, from_node_id, to_node_id, relation_type,
                    score, properties_json, enabled
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE from_node_id = VALUES(from_node_id),
                    to_node_id = VALUES(to_node_id),
                    relation_type = VALUES(relation_type), score = VALUES(score),
                    properties_json = VALUES(properties_json),
                    enabled = VALUES(enabled), updated_at = CURRENT_TIMESTAMP
                """,
                (
                    domain,
                    edge["edge_id"],
                    edge["from"],
                    edge["to"],
                    edge["relation_type"],
                    float(edge.get("score") or 0),
                    json.dumps(
                        {
                            key: value
                            for key, value in edge.items()
                            if key not in {"edge_id", "from", "to", "relation_type", "score"}
                        },
                        ensure_ascii=False,
                    ),
                    1,
                ),
            )

    def _connect(self):
        if connector is None:
            raise OAGRepositoryError(
                "mysql-connector-python is not installed; install project dependencies"
            )
        try:
            return connector.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                database=self._config.database,
            )
        except MySQLError as exc:
            raise OAGRepositoryError(f"MySQL ontology writer unavailable: {exc}") from exc


def _alias_values(*values: Any) -> list[str]:
    aliases: list[str] = []
    for value in values:
        if isinstance(value, list):
            aliases.extend(str(item) for item in value if item not in (None, ""))
        elif value not in (None, ""):
            aliases.append(str(value))
    deduped: dict[str, str] = {}
    for alias in aliases:
        normalized = normalize_alias(alias)
        if normalized:
            deduped.setdefault(normalized, alias)
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
