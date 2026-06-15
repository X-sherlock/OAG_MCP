from __future__ import annotations

from pathlib import Path
from typing import Any

from oag_ontology_loader.loader import load_ontology
from oag_mcp.service import OAGContextService


DOMAIN = "finance_market"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CatalogRepository:
    def __init__(self) -> None:
        self.catalog = load_ontology(PROJECT_ROOT / "ontology")
        self.objects = {item["object_type"]: item for item in self.catalog.object_types}
        self.attributes = {item["attribute_name"]: item for item in self.catalog.attributes}

    def ping(self) -> None:
        return None

    def domain_enabled(self, domain: str) -> bool:
        return domain == DOMAIN

    def get_objects_by_ids(self, domain: str, object_ids: list[str]) -> list[dict[str, Any]]:
        rows = []
        for object_id in object_ids:
            item = self.objects.get(object_id)
            if not item:
                continue
            rows.append(
                {
                    "object_type": "ObjectType",
                    "object_id": object_id,
                    "object_name": item["object_type_zh"],
                    "aliases": [object_id, item["object_type_zh"]],
                    "params": {
                        "description": item["description"],
                        "source_tables": item.get("source_tables", []),
                    },
                }
            )
        return rows

    def get_attributes_by_names(self, domain: str, names: list[str]) -> list[dict[str, Any]]:
        rows = []
        for name in names:
            item = self.attributes.get(name)
            if not item:
                continue
            rows.append(
                {
                    "object_type": (item.get("object_types") or [""])[0],
                    "attribute_name": item["attribute_name"],
                    "attribute_name_zh": item["attribute_name_zh"],
                    "description": item["description"],
                    "aliases": item.get("aliases", []),
                }
            )
        return rows

    def get_query_capabilities(self, domain: str) -> list[dict[str, Any]]:
        return [item for item in self.catalog.queries if item.get("enabled", True)]

    def get_skill_capabilities(self, domain: str) -> list[dict[str, Any]]:
        return [item for item in self.catalog.skills if item.get("enabled", True)]

    def get_intent_profiles(self, domain: str) -> list[dict[str, Any]]:
        return [item for item in self.catalog.intent_profiles if item.get("enabled", True)]


class EmptyTextRepository:
    def ping(self) -> None:
        return None

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return []

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        return []


class SchemaGraphRepository:
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


def service() -> OAGContextService:
    return OAGContextService(
        ontology_repository=CatalogRepository(),
        text_repository=EmptyTextRepository(),
        graph_repository=SchemaGraphRepository(),
    )


def frame(
    *,
    raw_question: str = "分析000001近一年的表现",
    task_type: str = "analyze",
    intent: str | None = "performance_overview",
    object_type: str = "Fund",
    instance_ref: dict[str, Any] | None = None,
    role: str = "analysis_subject",
    constraints: dict[str, Any] | None = None,
    mentioned_attributes: list[str] | None = None,
    ranking: list[dict[str, Any]] | None = None,
    filters: list[dict[str, Any]] | None = None,
    relation_queries: list[dict[str, Any]] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    item = {
        "raw_question": raw_question,
        "domain": DOMAIN,
        "task_type": task_type,
        "target_objects": [
            {
                "object_type": object_type,
                "instance_ref": instance_ref if instance_ref is not None else {"fund_code": "000001"},
                "role": role,
            }
        ],
        "constraints": constraints if constraints is not None else {"period": "1y"},
        "mentioned_attributes": mentioned_attributes if mentioned_attributes is not None else [],
    }
    if intent is not None:
        item["intent"] = intent
    if ranking is not None:
        item["ranking"] = ranking
    if filters is not None:
        item["filters"] = filters
    if relation_queries is not None:
        item["relation_queries"] = relation_queries
    if limit is not None:
        item["limit"] = limit
    return item


def retrieve(semantic_frame: dict[str, Any] | None, debug: bool = False, output_view: str = "editor") -> dict[str, Any]:
    return service().retrieve_context(
        semantic_frame=semantic_frame,
        user_context={"permission_scopes": ["fund_public_data:read"], "debug": debug},
        output_view=output_view,
    )
