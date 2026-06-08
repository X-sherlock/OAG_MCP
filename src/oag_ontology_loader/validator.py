from __future__ import annotations

import warnings
from typing import Any


class OntologyValidationError(ValueError):
    """本体元数据结构不符合约定时抛出。

    继承 ValueError 是为了表达“输入文件内容非法”，同时保留专用类型方便测试
    和脚本精确捕获校验失败。
    """


# 每个本体分区的最小必填字段集合；只校验服务运行必需的结构，不约束业务枚举值。
REQUIRED_FIELDS: dict[str, set[str]] = {
    "object_types": {"object_type", "object_type_zh", "description", "source_tables", "enabled"},
    "attributes": {
        "attribute_name",
        "attribute_name_zh",
        "aliases",
        "value_type",
        "description",
        "source_tables",
        "source_fields",
        "object_types",
    },
    "relation_types": {
        "relation_type",
        "from_object_type",
        "to_object_type",
        "description",
        "direction",
        "default_score",
        "source_tables",
        "enabled",
    },
    "queries": {
        "query_id",
        "query_name",
        "target_object_type",
        "required_params",
        "output_attributes",
        "tool_name",
        "permission_scope",
        "source_tables",
        "enabled",
    },
    "skills": {
        "skill_id",
        "skill_name",
        "description",
        "target_object_type",
        "input_params",
        "output_attributes",
        "related_queries",
        "permission_scope",
        "enabled",
    },
    "data_sources": {"source_id", "source_type", "enabled", "description", "tables"},
    "instance_rules": {
        "rule_id",
        "enabled",
        "source_tables",
        "source_type",
        "object_type",
        "relation_type",
        "from_object_type",
        "to_object_type",
        "key_fields",
        "alias_fields",
        "description",
    },
    "table_schemas": {
        "table_name",
        "table_name_zh",
        "layer",
        "domain",
        "entity_types",
        "description",
        "fields",
    },
    "schema_graph_edges": {
        "edge_id",
        "from",
        "to",
        "relation_type",
        "score",
    },
    "intent_profiles": {
        "intent_name",
        "trigger_aliases",
        "default_attributes",
        "primary_skills",
        "secondary_skills",
        "optional_skills",
        "required_params",
    },
    "sample_instances": {
        "id",
        "domain",
        "object_type",
        "object_id",
        "object_name",
        "aliases",
        "params",
    },
    "sample_graph_edges": {
        "edge_id",
        "from",
        "to",
        "relation_type",
        "relation_name_zh",
        "score",
    },
}


# 这些字段在本体文件中必须是 list，避免后续遍历时把字符串误拆成字符。
LIST_FIELDS = {
    "source_tables",
    "aliases",
    "source_fields",
    "object_types",
    "required_params",
    "optional_params",
    "output_attributes",
    "input_params",
    "related_queries",
    "provides_fact_types",
    "supported_subject_types",
    "supported_attributes",
    "output_fact_schema",
    "supported_constraints",
    "tables",
    "key_fields",
    "alias_fields",
    "entity_types",
    "fields",
    "trigger_aliases",
    "default_attributes",
    "primary_skills",
    "secondary_skills",
    "optional_skills",
    "fact_requirements_template",
}


def validate_section(section_name: str, rows: Any) -> list[dict[str, Any]]:
    """校验单个本体分区并返回原始条目列表。

    函数重点检查三类问题：未知分区、分区不是对象列表、条目缺少必填字段或
    列表字段类型错误。校验通过后不做深拷贝，保持加载器低成本。
    """

    if section_name not in REQUIRED_FIELDS:
        raise OntologyValidationError(f"Unknown ontology section: {section_name}")
    if not isinstance(rows, list):
        raise OntologyValidationError(f"{section_name}.yaml must contain a list of objects")
    if not rows:
        raise OntologyValidationError(f"{section_name}.yaml must not be empty")

    required = REQUIRED_FIELDS[section_name]
    validated = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            raise OntologyValidationError(
                f"{section_name}.yaml item #{index + 1} must be an object"
            )
        missing = sorted(field for field in required if field not in item)
        if missing:
            identity = _identity(section_name, item, index)
            raise OntologyValidationError(
                f"{section_name}.yaml item {identity} missing required fields: "
                + ", ".join(missing)
            )
        for field in LIST_FIELDS.intersection(item):
            if not isinstance(item[field], list):
                identity = _identity(section_name, item, index)
                raise OntologyValidationError(
                    f"{section_name}.yaml item {identity} field {field} must be a list"
                )
        if section_name == "table_schemas":
            _validate_table_schema(item, index)
        validated.append(item)
    return validated


def validate_catalog_sections(sections: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """批量校验完整本体目录的所有分区。"""

    validated = {name: validate_section(name, rows) for name, rows in sections.items()}
    _warn_unknown_intent_references(validated)
    return validated


def _identity(section_name: str, item: dict[str, Any], index: int) -> str:
    """为错误信息挑选最有辨识度的条目标识。

    不同分区的主键字段不同，因此按常见主键顺序尝试；如果条目连主键也缺失，
    就退回到 1-based 序号，便于用户定位文件里的具体项。
    """

    for key in (
        "object_type",
        "attribute_name",
        "relation_type",
        "query_id",
        "skill_id",
        "source_id",
        "rule_id",
        "table_name",
        "id",
        "edge_id",
        "intent_name",
    ):
        if item.get(key):
            return str(item[key])
    return f"#{index + 1}"


def _warn_unknown_intent_references(sections: dict[str, list[dict[str, Any]]]) -> None:
    """Warn when intent profiles reference attributes or skills outside the catalog."""

    profiles = sections.get("intent_profiles") or []
    if not profiles:
        return
    attribute_names = {
        item.get("attribute_name")
        for item in sections.get("attributes", [])
        if item.get("attribute_name")
    }
    skill_ids = {
        item.get("skill_id")
        for item in sections.get("skills", [])
        if item.get("skill_id")
    }
    for profile in profiles:
        intent_name = profile.get("intent_name", "<unknown>")
        for attribute_name in profile.get("default_attributes") or []:
            if attribute_name not in attribute_names:
                warnings.warn(
                    f"intent_profiles.yaml item {intent_name} references unknown attribute: {attribute_name}",
                    stacklevel=2,
                )
        for field in ("primary_skills", "secondary_skills", "optional_skills"):
            for skill_id in profile.get(field) or []:
                if skill_id not in skill_ids:
                    warnings.warn(
                        f"intent_profiles.yaml item {intent_name} references unknown skill: {skill_id}",
                        stacklevel=2,
                    )


def _validate_table_schema(item: dict[str, Any], index: int) -> None:
    """Validate the nested field list for a table schema entry."""

    identity = _identity("table_schemas", item, index)
    fields = item.get("fields")
    if not isinstance(fields, list) or not fields:
        raise OntologyValidationError(
            f"table_schemas.yaml item {identity} field fields must be a non-empty list"
        )
    required = {"field_name", "field_name_zh", "semantic_type", "aliases"}
    for field_index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise OntologyValidationError(
                f"table_schemas.yaml item {identity} field #{field_index + 1} must be an object"
            )
        missing = sorted(name for name in required if name not in field)
        if missing:
            raise OntologyValidationError(
                f"table_schemas.yaml item {identity} field #{field_index + 1} "
                "missing required fields: " + ", ".join(missing)
            )
        if not isinstance(field["aliases"], list):
            raise OntologyValidationError(
                f"table_schemas.yaml item {identity} field #{field_index + 1} aliases must be a list"
            )
