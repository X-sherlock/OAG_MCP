from __future__ import annotations

import json
import re
import unicodedata
from collections import deque
from typing import Any, Protocol

try:  # pragma: no cover
    from mysql import connector
    from mysql.connector import Error as MySQLError
except ImportError:  # pragma: no cover
    connector = None  # type: ignore[assignment]
    MySQLError = Exception  # type: ignore[assignment]

from oag_mcp.config import TDSQLConfig
from oag_mcp.errors import OAGRepositoryError


# 基金代码在当前领域中使用 6 位数字；负向环视避免从更长数字串中误截取。
FUND_CODE_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


class OntologyRepository(Protocol):
    """本体元数据仓储协议。

    服务层只依赖该协议读取对象、属性、查询能力和技能能力，因此测试可以用
    FakeRepository 替代真实 MySQL，实现更快的单元测试。
    """

    def ping(self) -> None: ...

    def domain_enabled(self, domain: str) -> bool: ...

    def get_objects_by_ids(self, domain: str, object_ids: list[str]) -> list[dict[str, Any]]: ...

    def get_attributes_by_names(self, domain: str, names: list[str]) -> list[dict[str, Any]]: ...

    def get_query_capabilities(self, domain: str) -> list[dict[str, Any]]: ...

    def get_skill_capabilities(self, domain: str) -> list[dict[str, Any]]: ...

    def get_intent_profiles(self, domain: str) -> list[dict[str, Any]]: ...


class TextSearchRepository(Protocol):
    """文本/别名召回仓储协议。

    当前实现使用 MySQL 别名表进行轻量匹配，但协议名称保留 text search 语义，
    方便未来替换为 Elasticsearch、向量检索或混合召回。
    """

    def ping(self) -> None: ...

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]: ...

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]: ...


class GraphRepository(Protocol):
    """关系图召回仓储协议。

    上层服务把实体列表交给该协议后，期望得到直接关系和多跳路径，具体图存储
    可以是 MySQL 表、图数据库或内存索引。
    """

    def ping(self) -> None: ...

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]: ...

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]: ...


class MySQLMetadataRepository:
    """通过 MySQL 协议访问 OAG 本体元数据。"""

    def __init__(self, config: TDSQLConfig) -> None:
        self._config = config

    def ping(self) -> None:
        """执行轻量 SELECT 1，用于服务启动或请求前健康检查。"""

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except MySQLError as exc:
            raise OAGRepositoryError(f"MySQL metadata repository unavailable: {exc}") from exc

    def domain_enabled(self, domain: str) -> bool:
        """检查指定领域是否在元数据表中启用。"""

        rows = self._fetch_all(
            "SELECT domain FROM oag_domains WHERE domain = %s AND enabled = 1",
            (domain,),
        )
        return bool(rows)

    def get_objects_by_ids(self, domain: str, object_ids: list[str]) -> list[dict[str, Any]]:
        """按对象 ID 批量读取对象元数据。

        这里只按 object_id 过滤，是因为当前 fund_code 等业务 ID 在领域内已能稳定
        定位对象；返回结构与文本召回结果保持兼容，方便服务层合并。
        """

        if not object_ids:
            return []
        placeholders = ",".join(["%s"] * len(object_ids))
        rows = self._fetch_all(
            f"""
            SELECT object_type, object_id, object_name, aliases_json, params_json
            FROM oag_objects
            WHERE domain = %s AND object_id IN ({placeholders})
            """,
            (domain, *object_ids),
        )
        results = [
            {
                "object_type": row["object_type"],
                "object_id": row["object_id"],
                "object_name": row["object_name"] or "",
                "aliases": _json_list(row["aliases_json"]),
                "params": _json_object(row["params_json"]),
            }
            for row in rows
        ]
        return results

    def get_attributes_by_names(self, domain: str, names: list[str]) -> list[dict[str, Any]]:
        """按属性英文名批量补齐属性中文名、对象类型和别名。"""

        if not names:
            return []
        placeholders = ",".join(["%s"] * len(names))
        rows = self._fetch_all(
            f"""
            SELECT object_type, attribute_name, attribute_name_zh, aliases_json
            FROM oag_attributes
            WHERE domain = %s AND attribute_name IN ({placeholders})
            """,
            (domain, *names),
        )
        return [
            {
                "object_type": row["object_type"],
                "attribute_name": row["attribute_name"],
                "attribute_name_zh": row["attribute_name_zh"] or "",
                "aliases": _json_list(row["aliases_json"]),
            }
            for row in rows
        ]

    def get_query_capabilities(self, domain: str) -> list[dict[str, Any]]:
        """读取当前领域已启用的结构化查询能力。"""

        rows = self._fetch_all(
            """
            SELECT query_id, description, target_object_type, required_params_json,
                   optional_params_json, output_attributes_json, tool_type, tool_name,
                   permission_scope, gn.properties_json AS graph_properties_json
            FROM oag_query_capabilities qc
            LEFT JOIN oag_graph_nodes gn
              ON gn.domain = qc.domain
             AND gn.node_id = CONCAT('QueryCapability:', qc.query_id)
             AND gn.enabled = 1
            WHERE qc.domain = %s AND qc.enabled = 1
            """,
            (domain,),
        )
        return [
            {
                "query_id": row["query_id"],
                "description": row["description"] or "",
                "target_object_type": row["target_object_type"],
                "required_params": _json_list(row["required_params_json"]),
                "optional_params": _json_list(row["optional_params_json"]),
                "output_attributes": _json_list(row["output_attributes_json"]),
                "tool_type": row["tool_type"],
                "tool_name": row["tool_name"],
                "permission_scope": row["permission_scope"] or "",
                "source_tables": _query_source_tables(row.get("graph_properties_json")),
            }
            for row in rows
        ]

    def get_skill_capabilities(self, domain: str) -> list[dict[str, Any]]:
        """读取当前领域已启用的技能能力。"""

        rows = self._fetch_all(
            """
            SELECT skill_id, skill_name, description, target_object_type,
                   input_params_json, output_attributes_json, related_queries_json,
                   permission_scope,
                   provides_fact_types_json, supported_subject_types_json,
                   supported_attributes_json, output_fact_schema_json,
                   supported_constraints_json
            FROM oag_skill_capabilities
            WHERE domain = %s AND enabled = 1
            """,
            (domain,),
            fallback_sql="""
            SELECT skill_id, skill_name, description, target_object_type,
                   input_params_json, output_attributes_json, related_queries_json,
                   permission_scope
            FROM oag_skill_capabilities
            WHERE domain = %s AND enabled = 1
            """,
        )
        return [
            {
                "skill_id": row["skill_id"],
                "skill_name": row["skill_name"],
                "description": row["description"] or "",
                "target_object_type": row["target_object_type"],
                "input_params": _json_list(row["input_params_json"]),
                "output_attributes": _json_list(row["output_attributes_json"]),
                "related_queries": _json_list(row.get("related_queries_json")),
                "permission_scope": row["permission_scope"] or "",
                "provides_fact_types": _json_list(row.get("provides_fact_types_json")),
                "supported_subject_types": _json_list(row.get("supported_subject_types_json")),
                "supported_attributes": _json_list(row.get("supported_attributes_json")),
                "output_fact_schema": _json_list(row.get("output_fact_schema_json")),
                "supported_constraints": _json_list(row.get("supported_constraints_json")),
            }
            for row in rows
        ]

    def get_intent_profiles(self, domain: str) -> list[dict[str, Any]]:
        """Read broad intent matching profiles from MySQL metadata."""

        rows = self._fetch_all(
            """
            SELECT intent_name, intent_name_zh, trigger_aliases_json,
                   default_attributes_json, primary_skills_json,
                   secondary_skills_json, optional_skills_json,
                   required_params_json, fact_requirements_template_json
            FROM oag_intent_profiles
            WHERE domain = %s AND enabled = 1
            """,
            (domain,),
            fallback_sql="""
            SELECT intent_name, intent_name_zh, trigger_aliases_json,
                   default_attributes_json, primary_skills_json,
                   secondary_skills_json, optional_skills_json,
                   required_params_json
            FROM oag_intent_profiles
            WHERE domain = %s AND enabled = 1
            """,
        )
        return [
            {
                "intent_name": row["intent_name"],
                "intent_name_zh": row.get("intent_name_zh") or "",
                "trigger_aliases": _json_list(row.get("trigger_aliases_json")),
                "default_attributes": _json_list(row.get("default_attributes_json")),
                "primary_skills": _json_list(row.get("primary_skills_json")),
                "secondary_skills": _json_list(row.get("secondary_skills_json")),
                "optional_skills": _json_list(row.get("optional_skills_json")),
                "required_params": _json_list(row.get("required_params_json")),
                "fact_requirements_template": _json_list(
                    row.get("fact_requirements_template_json")
                ),
            }
            for row in rows
        ]

    def _connect(self):
        """创建 MySQL 连接；驱动缺失时统一包装为仓储错误。"""

        if connector is None:
            raise OAGRepositoryError(
                "mysql-connector-python is not installed; install project dependencies"
            )
        return connector.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )

    def _fetch_all(
        self,
        sql: str,
        params: tuple[Any, ...],
        fallback_sql: str | None = None,
    ) -> list[dict[str, Any]]:
        """执行参数化查询并返回字典行，避免调用方依赖游标细节。"""

        try:
            with self._connect() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except MySQLError as exc:
            if fallback_sql and _looks_like_unknown_column(exc):
                try:
                    with self._connect() as conn:
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute(fallback_sql, params)
                        return list(cursor.fetchall())
                except MySQLError as fallback_exc:
                    raise OAGRepositoryError(
                        f"MySQL metadata query failed: {fallback_exc}"
                    ) from fallback_exc
            raise OAGRepositoryError(f"MySQL metadata query failed: {exc}") from exc


class MySQLTextRepository:
    """MySQL-only 模式下的对象和属性别名召回实现。"""

    def __init__(self, config: TDSQLConfig) -> None:
        self._config = config

    def ping(self) -> None:
        """检查别名召回所依赖的 MySQL 连接是否可用。"""

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except MySQLError as exc:
            raise OAGRepositoryError(f"MySQL text repository unavailable: {exc}") from exc

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        """用归一化别名表召回候选业务对象。

        SQL 中的分值是启发式：完全匹配最高、问句包含别名次之、别名包含问句再次。
        这能覆盖基金代码、基金名称和别名短语等常见输入。
        """

        normalized = normalize_alias(question)
        if not normalized:
            return []
        rows = self._fetch_all(
            """
            SELECT a.domain, a.object_type, a.object_id, o.object_name,
                   o.aliases_json, o.params_json,
                   MAX(
                       CASE
                           WHEN a.normalized_alias = %s THEN 10
                           WHEN %s LIKE CONCAT('%%', a.normalized_alias, '%%') THEN 7
                           WHEN a.normalized_alias LIKE %s THEN 4
                           ELSE 1
                       END
                   ) AS score
            FROM oag_object_aliases a
            LEFT JOIN oag_objects o
              ON o.domain = a.domain
             AND o.object_type = a.object_type
             AND o.object_id = a.object_id
            WHERE a.domain = %s
              AND (
                  a.normalized_alias = %s
                  OR %s LIKE CONCAT('%%', a.normalized_alias, '%%')
                  OR a.normalized_alias LIKE %s
              )
            GROUP BY a.domain, a.object_type, a.object_id, o.object_name,
                     o.aliases_json, o.params_json
            ORDER BY score DESC, CHAR_LENGTH(a.object_id) DESC
            LIMIT %s
            """,
            (
                normalized,
                normalized,
                f"%{normalized}%",
                domain,
                normalized,
                normalized,
                f"%{normalized}%",
                top_k,
            ),
        )
        return [
            {
                "domain": row["domain"],
                "object_type": row["object_type"],
                "object_id": row["object_id"],
                "object_name": row.get("object_name") or "",
                "aliases": _json_list(row.get("aliases_json")),
                "params": _json_object(row.get("params_json")),
                "_score": float(row.get("score") or 0),
            }
            for row in rows
        ]

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        """用归一化别名表召回候选属性。

        属性召回结果后续会再用元数据表补全，确保 response 中的 object_type 和
        attribute_name_zh 来自权威本体配置。
        """

        normalized = normalize_alias(question)
        if not normalized:
            return []
        rows = self._fetch_all(
            """
            SELECT aa.domain, attr.object_type, aa.attribute_name,
                   attr.attribute_name_zh, attr.aliases_json,
                   MAX(
                       CASE
                           WHEN aa.normalized_alias = %s THEN 10
                           WHEN %s LIKE CONCAT('%%', aa.normalized_alias, '%%') THEN 7
                           WHEN aa.normalized_alias LIKE %s THEN 4
                           ELSE 1
                       END
                   ) AS score
            FROM oag_attribute_aliases aa
            JOIN oag_attributes attr
              ON attr.domain = aa.domain
             AND attr.attribute_name = aa.attribute_name
            WHERE aa.domain = %s
              AND (
                  aa.normalized_alias = %s
                  OR %s LIKE CONCAT('%%', aa.normalized_alias, '%%')
                  OR aa.normalized_alias LIKE %s
              )
            GROUP BY aa.domain, attr.object_type, aa.attribute_name,
                     attr.attribute_name_zh, attr.aliases_json
            ORDER BY score DESC, CHAR_LENGTH(aa.attribute_name) DESC
            LIMIT %s
            """,
            (
                normalized,
                normalized,
                f"%{normalized}%",
                domain,
                normalized,
                normalized,
                f"%{normalized}%",
                top_k,
            ),
        )
        return [
            {
                "domain": row["domain"],
                "object_type": row["object_type"],
                "attribute_name": row["attribute_name"],
                "attribute_name_zh": row.get("attribute_name_zh") or "",
                "aliases": _json_list(row.get("aliases_json")),
                "_score": float(row.get("score") or 0),
            }
            for row in rows
        ]

    def _connect(self):
        """创建文本召回仓储所需的 MySQL 连接。"""

        if connector is None:
            raise OAGRepositoryError(
                "mysql-connector-python is not installed; install project dependencies"
            )
        return connector.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        """执行别名检索 SQL 并把驱动异常转换为 OAGRepositoryError。"""

        try:
            with self._connect() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except MySQLError as exc:
            raise OAGRepositoryError(f"MySQL text query failed: {exc}") from exc


class MySQLGraphRepository:
    """基于 MySQL 图节点/边表的关系和路径召回实现。"""

    def __init__(self, config: TDSQLConfig) -> None:
        self._config = config

    def ping(self) -> None:
        """检查关系图仓储所依赖的 MySQL 连接是否可用。"""

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except MySQLError as exc:
            raise OAGRepositoryError(f"MySQL graph repository unavailable: {exc}") from exc

    def health(self) -> None:
        """兼容脚本或测试使用的健康检查别名。"""

        self.ping()

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        """召回与命中实体直接相连的关系边。

        当前实现只返回一跳边，所以 max_hops 参数暂时丢弃；保留该参数是为了满足
        GraphRepository 协议，并给未来多跳关系召回留接口空间。
        """

        del max_hops
        start_nodes = _entity_node_ids(entities)
        if not start_nodes:
            return []
        placeholders = ",".join(["%s"] * len(start_nodes))
        rows = self._fetch_all(
            f"""
            SELECT e.edge_id, e.from_node_id, e.to_node_id, e.relation_type,
                   e.score, e.properties_json
            FROM oag_graph_edges e
            JOIN oag_graph_nodes fn
              ON fn.domain = e.domain
             AND fn.node_id = e.from_node_id
             AND fn.enabled = 1
            JOIN oag_graph_nodes tn
              ON tn.domain = e.domain
             AND tn.node_id = e.to_node_id
             AND tn.enabled = 1
            WHERE e.domain = %s
              AND e.enabled = 1
              AND (e.from_node_id IN ({placeholders}) OR e.to_node_id IN ({placeholders}))
            ORDER BY e.score DESC, e.edge_id ASC
            LIMIT %s
            """,
            (domain, *start_nodes, *start_nodes, top_k),
        )
        return [_edge_result(row) for row in rows]

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        """从命中实体出发做有限广度优先搜索，召回最多 max_hops 跳路径。

        MySQL 负责筛出启用边和启用节点，Python 侧构建无向邻接表并避免路径内
        重复节点，从而减少环路导致的无效路径。
        """

        start_nodes = _entity_node_ids(entities)
        if not start_nodes or max_hops < 1:
            return []
        rows = self._fetch_all(
            """
            SELECT e.edge_id, e.from_node_id, e.to_node_id, e.relation_type,
                   e.score, e.properties_json
            FROM oag_graph_edges e
            JOIN oag_graph_nodes fn
              ON fn.domain = e.domain
             AND fn.node_id = e.from_node_id
             AND fn.enabled = 1
            JOIN oag_graph_nodes tn
              ON tn.domain = e.domain
             AND tn.node_id = e.to_node_id
             AND tn.enabled = 1
            WHERE e.domain = %s AND e.enabled = 1
            ORDER BY e.score DESC, e.edge_id ASC
            """,
            (domain,),
        )
        adjacency: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            edge = _edge_result(row)
            # 关系图查询对调用方表现为可双向探索，因此同一条边挂到 from/to 两侧。
            adjacency.setdefault(edge["from"], []).append(edge)
            adjacency.setdefault(edge["to"], []).append(edge)

        paths: list[dict[str, Any]] = []
        for start in start_nodes:
            queue: deque[tuple[str, list[str], list[dict[str, Any]]]] = deque(
                [(start, [start], [])]
            )
            while queue and len(paths) < top_k:
                current, path_nodes, path_edges = queue.popleft()
                if len(path_edges) >= max_hops:
                    continue
                for edge in adjacency.get(current, []):
                    next_node = edge["to"] if edge["from"] == current else edge["from"]
                    if next_node in path_nodes:
                        # 路径内不重复节点，避免 A-B-A 这类环路污染候选路径。
                        continue
                    new_nodes = [*path_nodes, next_node]
                    new_edges = [*path_edges, edge]
                    paths.append(
                        {
                            "path": new_nodes,
                            "edges": new_edges,
                            "score": _path_score(new_edges),
                        }
                    )
                    if len(paths) >= top_k:
                        break
                    queue.append((next_node, new_nodes, new_edges))

        paths.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return paths[:top_k]

    def _connect(self):
        """创建关系图仓储所需的 MySQL 连接。"""

        if connector is None:
            raise OAGRepositoryError(
                "mysql-connector-python is not installed; install project dependencies"
            )
        return connector.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        """执行图查询 SQL 并统一包装 MySQL 异常。"""

        try:
            with self._connect() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except MySQLError as exc:
            raise OAGRepositoryError(f"MySQL graph query failed: {exc}") from exc

def extract_fund_codes(question: str) -> list[str]:
    """从问题中提取去重后的 6 位基金代码，保持首次出现顺序。"""

    return list(dict.fromkeys(FUND_CODE_PATTERN.findall(question)))


def normalize_alias(value: Any) -> str:
    """统一别名匹配口径：全半角归一化、去空白、小写化。"""

    text = unicodedata.normalize("NFKC", str(value or ""))
    return "".join(text.split()).lower()


def _entity_node_ids(entities: list[dict[str, Any]]) -> list[str]:
    """把服务层对象结构转换为图表使用的 node_id。"""

    return [
        f"{item.get('object_type')}:{item.get('object_id')}"
        for item in entities
        if item.get("object_type") and item.get("object_id")
    ]


def _edge_result(row: dict[str, Any]) -> dict[str, Any]:
    """把数据库边记录转换为 MCP 响应使用的边结构。"""

    edge = {
        "edge_id": row["edge_id"],
        "from": row["from_node_id"],
        "to": row["to_node_id"],
        "relation_type": row["relation_type"],
        "score": float(row.get("score") or 0),
        "properties": _json_object(row.get("properties_json")),
    }
    relation_name = edge["properties"].get("relation_name_zh")
    if relation_name:
        edge["relation_name_zh"] = relation_name
    return edge


def _path_score(edges: list[dict[str, Any]]) -> float:
    """路径分数取边分数均值，避免长路径天然获得更高总分。"""

    if not edges:
        return 0.0
    return round(sum(float(edge.get("score") or 0) for edge in edges) / len(edges), 3)


def _json_list(value: Any) -> list[Any]:
    """宽容解析 JSON 列表字段，空值或非列表结果都返回空列表。"""

    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    parsed = json.loads(value)
    return parsed if isinstance(parsed, list) else []


def _json_object(value: Any) -> dict[str, Any]:
    """宽容解析 JSON 对象字段，空值或非对象结果都返回空字典。"""

    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}


def _looks_like_unknown_column(exc: Exception) -> bool:
    text = str(exc).lower()
    return "unknown column" in text or "1054" in text


def _query_source_tables(graph_properties_json: Any) -> list[Any]:
    properties = _json_object(graph_properties_json)
    params = properties.get("params")
    if not isinstance(params, dict):
        return []
    source_tables = params.get("source_tables")
    return source_tables if isinstance(source_tables, list) else []
