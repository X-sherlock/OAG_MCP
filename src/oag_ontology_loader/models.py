from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OntologyCatalog:
    """加载并校验后的本体目录快照。

    每个字段对应 ontology 目录下的一类 YAML/JSON 配置，服务层和种子数据脚本
    通过这个统一对象读取对象类型、属性、关系、查询能力、技能能力和演示实例。
    """

    ontology_dir: Path
    object_types: list[dict[str, Any]]
    attributes: list[dict[str, Any]]
    relation_types: list[dict[str, Any]]
    queries: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    data_sources: list[dict[str, Any]]
    instance_rules: list[dict[str, Any]]
    table_schemas: list[dict[str, Any]]
    schema_graph_edges: list[dict[str, Any]]
    intent_profiles: list[dict[str, Any]]
    sample_instances: list[dict[str, Any]]
    sample_graph_edges: list[dict[str, Any]]

    @property
    def demo_instances(self) -> list[dict[str, Any]]:
        """Backward-compatible alias for the smoke-test sample instance catalog."""

        return self.sample_instances

    @property
    def demo_graph_edges(self) -> list[dict[str, Any]]:
        """Backward-compatible alias for the smoke-test sample graph catalog."""

        return self.sample_graph_edges

    def enabled_queries(self) -> list[dict[str, Any]]:
        """返回启用状态的查询能力，保留默认 enabled 缺省为 True 的兼容行为。"""

        return [item for item in self.queries if item.get("enabled", True)]

    def enabled_skills(self) -> list[dict[str, Any]]:
        """返回启用状态的技能能力，供调用方过滤掉暂不开放的能力。"""

        return [item for item in self.skills if item.get("enabled", True)]


# 本体分区名到磁盘文件名的唯一映射；加载器和校验器都依赖这些稳定键名。
ONTOLOGY_FILE_NAMES = {
    "object_types": "object_types.yaml",
    "attributes": "attributes.yaml",
    "relation_types": "relation_types.yaml",
    "queries": "queries.yaml",
    "skills": "skills.yaml",
    "data_sources": "data_sources.yaml",
    "instance_rules": "instance_rules.yaml",
    "table_schemas": "table_schemas.yaml",
    "schema_graph_edges": "schema_graph_edges.yaml",
    "intent_profiles": "intent_profiles.yaml",
    "sample_instances": "sample_instances.yaml",
    "sample_graph_edges": "sample_graph_edges.yaml",
}
