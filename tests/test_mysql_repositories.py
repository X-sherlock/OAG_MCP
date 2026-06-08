from __future__ import annotations

import json
from typing import Any

from oag_mcp.config import TDSQLConfig
from oag_mcp.repositories import MySQLGraphRepository, MySQLTextRepository, normalize_alias
from oag_ontology_loader.mysql_writer import MySQLOntologyWriter


CONFIG = TDSQLConfig(
    host="127.0.0.1",
    port=3306,
    user="oag",
    password="oag_password",
    database="oag_meta",
)


class StubTextRepository(MySQLTextRepository):
    def __init__(self) -> None:
        super().__init__(CONFIG)
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        self.calls.append((sql, params))
        if "oag_object_aliases" in sql:
            return [
                {
                    "domain": "finance_market",
                    "object_type": "Fund",
                    "object_id": "003095",
                    "object_name": "Fund 003095",
                    "aliases_json": json.dumps(["003095", "Fund 003095"]),
                    "params_json": json.dumps({"fund_code": "003095"}),
                    "score": 10,
                }
            ]
        return [
            {
                "domain": "finance_market",
                "object_type": "RiskMetric",
                "attribute_name": "max_drawdown",
                "attribute_name_zh": "\u6700\u5927\u56de\u64a4",
                "aliases_json": json.dumps(["\u6700\u5927\u56de\u64a4", "drawdown"]),
                "score": 10,
            }
        ]


def test_mysql_text_repository_returns_es_compatible_object_shape():
    repo = StubTextRepository()

    rows = repo.search_objects("finance_market", "\uff10\uff10\uff13\uff10\uff19\uff15", 5)

    assert repo.calls[0][1][0] == "003095"
    assert rows == [
        {
            "domain": "finance_market",
            "object_type": "Fund",
            "object_id": "003095",
            "object_name": "Fund 003095",
            "aliases": ["003095", "Fund 003095"],
            "params": {"fund_code": "003095"},
            "_score": 10.0,
        }
    ]


def test_mysql_text_repository_returns_chinese_attribute_alias_match():
    repo = StubTextRepository()

    rows = repo.search_attributes("finance_market", "\u6700\u5927\u56de\u64a4", 5)

    assert repo.calls[0][1][0] == normalize_alias("\u6700\u5927\u56de\u64a4")
    assert rows[0]["attribute_name"] == "max_drawdown"
    assert rows[0]["attribute_name_zh"] == "\u6700\u5927\u56de\u64a4"
    assert rows[0]["aliases"] == ["\u6700\u5927\u56de\u64a4", "drawdown"]
    assert rows[0]["_score"] == 10.0


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, sql: str) -> None:
        self.executed.append(sql)

    def fetchone(self) -> tuple[int]:
        return (1,)


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_obj = cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.cursor_obj


class StubGraphRepository(MySQLGraphRepository):
    def __init__(self) -> None:
        super().__init__(CONFIG)
        self.cursor_obj = FakeCursor()
        self.fetch_calls: list[tuple[str, tuple[Any, ...]]] = []

    def _connect(self) -> FakeConnection:
        return FakeConnection(self.cursor_obj)

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        self.fetch_calls.append((sql, params))
        rows = [
            {
                "edge_id": "Fund:003095__has_performance_metric__PerformanceMetric:fund_performance_metric",
                "from_node_id": "Fund:003095",
                "to_node_id": "PerformanceMetric:fund_performance_metric",
                "relation_type": "has_performance_metric",
                "score": 0.95,
                "properties_json": json.dumps({"relation_name_zh": "has metric"}),
            },
            {
                "edge_id": "PerformanceMetric:fund_performance_metric__related_to__RiskMetric:fund_risk_metric",
                "from_node_id": "PerformanceMetric:fund_performance_metric",
                "to_node_id": "RiskMetric:fund_risk_metric",
                "relation_type": "related_to",
                "score": 0.8,
                "properties_json": "{}",
            },
        ]
        if "OR e.to_node_id IN" in sql:
            return rows[:1]
        return rows


def test_mysql_graph_health_executes_select_one():
    repo = StubGraphRepository()

    repo.health()

    assert repo.cursor_obj.executed == ["SELECT 1"]


class WriterCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        self.executed.append((sql, params))


def test_ontology_writer_upserts_schema_level_objects():
    writer = MySQLOntologyWriter(CONFIG)
    cursor = WriterCursor()
    objects = [
        {
            "domain": "finance_market",
            "object_type": "ObjectType",
            "object_id": "Fund",
            "object_name": "基金产品",
            "aliases": ["Fund", "基金产品"],
            "params": {
                "schema_level": True,
                "description": "schema object metadata",
                "source_tables": ["dim_fund_info"],
            },
        }
    ]

    writer.upsert_objects(cursor, objects)

    sql, params = cursor.executed[0]
    assert "INSERT INTO oag_objects" in sql
    assert params[:4] == ("finance_market", "ObjectType", "Fund", "基金产品")
    assert json.loads(params[4]) == ["Fund", "基金产品"]
    assert json.loads(params[5])["schema_level"] is True


def test_ontology_writer_upserts_graph_nodes_and_edges():
    writer = MySQLOntologyWriter(CONFIG)
    cursor = WriterCursor()
    nodes = [
        {
            "id": "Fund:003095",
            "domain": "finance_market",
            "object_type": "Fund",
            "object_id": "003095",
            "object_name": "Fund 003095",
            "aliases": ["003095"],
            "params": {"fund_code": "003095"},
        }
    ]
    edges = [
        {
            "edge_id": "Fund:003095__has_performance_metric__PerformanceMetric:fund_performance_metric",
            "from": "Fund:003095",
            "to": "PerformanceMetric:fund_performance_metric",
            "relation_type": "has_performance_metric",
            "relation_name_zh": "has metric",
            "score": 0.95,
        }
    ]

    writer.upsert_graph_nodes(cursor, nodes, "finance_market")
    writer.upsert_graph_edges(cursor, edges, "finance_market")

    assert any("INSERT INTO oag_graph_nodes" in sql for sql, _ in cursor.executed)
    assert any("INSERT INTO oag_graph_edges" in sql for sql, _ in cursor.executed)
    assert cursor.executed[0][1][1] == "Fund:003095"
    assert cursor.executed[1][1][1].startswith("Fund:003095")


def test_mysql_graph_relations_and_paths_use_enabled_table_queries():
    repo = StubGraphRepository()
    entities = [{"object_type": "Fund", "object_id": "003095"}]

    relations = repo.recall_relations("finance_market", entities, max_hops=2, top_k=10)
    paths = repo.recall_paths("finance_market", entities, max_hops=2, top_k=10)

    assert "e.enabled = 1" in repo.fetch_calls[0][0]
    assert "fn.enabled = 1" in repo.fetch_calls[0][0]
    assert relations[0]["edge_id"].startswith("Fund:003095")
    assert relations[0]["from"] == "Fund:003095"
    assert relations[0]["to"] == "PerformanceMetric:fund_performance_metric"
    assert relations[0]["relation_type"] == "has_performance_metric"
    assert paths[0]["path"] == ["Fund:003095", "PerformanceMetric:fund_performance_metric"]
    assert any(len(path["edges"]) == 2 for path in paths)
