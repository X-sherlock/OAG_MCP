from __future__ import annotations

from typing import Any

from oag_mcp.errors import OAGRepositoryError
from oag_mcp.service import OAGContextService, error_response


class FakeOntologyRepository:
    """服务层单元测试用的本体仓储替身。

    它只返回一个基金对象、一组属性、一个查询能力和一个技能能力，足以验证
    OAGContextService 的编排逻辑，同时避免连接真实数据库。
    """

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def ping(self) -> None:
        # fail=True 用于模拟 TDSQL 不可用，验证结构化错误响应。
        if self.fail:
            raise OAGRepositoryError("TDSQL unavailable")

    def domain_enabled(self, domain: str) -> bool:
        return domain == "finance_market"

    def get_objects_by_ids(self, domain: str, object_ids: list[str]) -> list[dict[str, Any]]:
        if "003095" not in object_ids:
            return []
        return [
            {
                "object_type": "Fund",
                "object_id": "003095",
                "object_name": "",
                "aliases": ["003095", "基金003095"],
                "params": {"fund_code": "003095"},
            }
        ]

    def get_attributes_by_names(self, domain: str, names: list[str]) -> list[dict[str, Any]]:
        mapping = {
            "return_rate": {
                "object_type": "PerformanceMetric",
                "attribute_name": "return_rate",
                "attribute_name_zh": "区间收益率",
                "aliases": ["收益率", "收益"],
            },
            "max_drawdown": {
                "object_type": "PerformanceMetric",
                "attribute_name": "max_drawdown",
                "attribute_name_zh": "最大回撤",
                "aliases": ["最大回撤", "回撤"],
            },
        }
        return [mapping[name] for name in names if name in mapping]

    def get_query_capabilities(self, domain: str) -> list[dict[str, Any]]:
        return [
            {
                "query_id": "fund_perf_interval_query",
                "description": "查询基金指定区间表现指标",
                "target_object_type": "Fund",
                "required_params": ["fund_code", "period"],
                "optional_params": ["benchmark_code"],
                "output_attributes": ["return_rate", "max_drawdown", "volatility"],
                "tool_type": "MCP",
                "tool_name": "structured_query_execute",
                "permission_scope": "fund_public_data:read",
            },
            {
                "query_id": "fund_risk_interval_query",
                "description": "查询基金指定区间风险指标",
                "target_object_type": "Fund",
                "required_params": ["fund_code", "period"],
                "optional_params": [],
                "output_attributes": ["max_drawdown", "volatility"],
                "tool_type": "MCP",
                "tool_name": "structured_query_execute",
                "permission_scope": "fund_public_data:read",
            },
        ]

    def get_skill_capabilities(self, domain: str) -> list[dict[str, Any]]:
        return [
            {
                "skill_id": "fund_performance_analysis",
                "skill_name": "基金业绩指标分析",
                "description": "分析基金区间收益、回撤和波动",
                "target_object_type": "Fund",
                "input_params": ["fund_code", "period"],
                "output_attributes": ["return_rate", "max_drawdown", "volatility"],
                "related_queries": ["fund_perf_interval_query"],
                "permission_scope": "fund_public_data:read",
            },
            {
                "skill_id": "fund_risk_analysis",
                "skill_name": "基金风险指标分析",
                "description": "分析基金区间最大回撤和波动",
                "target_object_type": "Fund",
                "input_params": ["fund_code", "period"],
                "output_attributes": ["max_drawdown", "volatility"],
                "related_queries": ["fund_risk_interval_query"],
                "permission_scope": "fund_public_data:read",
            },
        ]

    def get_intent_profiles(self, domain: str) -> list[dict[str, Any]]:
        return []


class FakeTextRepository:
    """文本召回替身：根据问题中是否包含关键词返回固定对象和属性。"""

    def ping(self) -> None:
        return None

    def search_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        # 只有问题中出现 003095 时才返回基金对象，模拟别名召回命中。
        if "003095" not in question:
            return []
        return [
            {
                "domain": domain,
                "object_type": "Fund",
                "object_id": "003095",
                "object_name": "",
                "aliases": ["003095"],
                "_score": 8.0,
                "params": {"fund_code": "003095"},
            }
        ]

    def search_attributes(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        # 按中文关键词返回属性，覆盖单属性和多属性同时命中的场景。
        rows = []
        if "收益" in question or "收益率" in question:
            rows.append(
                {
                    "object_type": "PerformanceMetric",
                    "attribute_name": "return_rate",
                    "attribute_name_zh": "区间收益率",
                    "aliases": ["收益率", "收益"],
                    "_score": 4.0,
                }
            )
        if "回撤" in question:
            rows.append(
                {
                    "object_type": "PerformanceMetric",
                    "attribute_name": "max_drawdown",
                    "attribute_name_zh": "最大回撤",
                    "aliases": ["最大回撤", "回撤"],
                    "_score": 4.0,
                }
            )
        return rows


class StaticGraphRepository:
    """关系图召回替身：对任意命中实体返回稳定的一跳关系和路径。"""

    def ping(self) -> None:
        return None

    def recall_relations(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        return [
            {
                "from": "QueryCapability:fund_perf_interval_query",
                "relation_type": "targets_object_type",
                "to": "ObjectType:Fund",
                "score": 0.95,
            },
            {
                "from": "QueryCapability:fund_perf_interval_query",
                "relation_type": "returns_attribute",
                "to": "Attribute:return_rate",
                "score": 0.95,
            },
            {
                "from": "QueryCapability:fund_perf_interval_query",
                "relation_type": "returns_attribute",
                "to": "Attribute:max_drawdown",
                "score": 0.95,
            },
            {
                "from": "QueryCapability:fund_perf_interval_query",
                "relation_type": "reads_from",
                "to": "DataTable:dws_fund_perf_1y",
                "score": 0.95,
            },
            {
                "from": "DataTable:dws_fund_perf_1y",
                "relation_type": "has_field",
                "to": "DataField:dws_fund_perf_1y.区间回报（近一年)",
                "score": 0.9,
            },
            {
                "from": "SkillCapability:fund_performance_analysis",
                "relation_type": "uses_query",
                "to": "QueryCapability:fund_perf_interval_query",
                "score": 0.95,
            },
        ]

    def recall_paths(
        self, domain: str, entities: list[dict[str, Any]], max_hops: int, top_k: int
    ) -> list[dict[str, Any]]:
        if not entities:
            return []
        return [
            {
                "path": [
                    "ObjectType:Fund",
                    "QueryCapability:fund_perf_interval_query",
                    "DataTable:dws_fund_perf_1y",
                    "DataField:dws_fund_perf_1y.区间回报（近一年)",
                ],
                "edges": [
                    {
                        "from": "QueryCapability:fund_perf_interval_query",
                        "relation_type": "targets_object_type",
                        "to": "ObjectType:Fund",
                        "score": 0.95,
                    },
                    {
                        "from": "QueryCapability:fund_perf_interval_query",
                        "relation_type": "reads_from",
                        "to": "DataTable:dws_fund_perf_1y",
                        "score": 0.95,
                    },
                    {
                        "from": "DataTable:dws_fund_perf_1y",
                        "relation_type": "has_field",
                        "to": "DataField:dws_fund_perf_1y.区间回报（近一年)",
                        "score": 0.9,
                    },
                ],
                "description": "schema-level fund performance context",
                "score": 0.95,
            }
        ]


def service(fail: bool = False) -> OAGContextService:
    """构造注入测试替身的上下文服务。"""

    return OAGContextService(
        ontology_repository=FakeOntologyRepository(fail=fail),
        text_repository=FakeTextRepository(),
        graph_repository=StaticGraphRepository(),
    )


def test_retrieve_context_matches_fund_code_and_params():
    # 基金代码显式出现时，服务应匹配对象并把 fund_code 与 period 一并解析出来。
    result = service().retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert {
        "matched_objects",
        "matched_attributes",
        "resolved_params",
        "target_instances",
        "fact_requirements",
        "fact_groups",
        "candidate_invocations",
        "missing_params",
        "confidence",
        "warnings",
    }.issubset(result)
    assert result["status"] == "success"
    assert result["matched_objects"][0]["object_type"] == "Fund"
    assert result["matched_objects"][0]["node_id"] == "ObjectType:Fund"
    assert result["matched_objects"][0]["object_id"] == "Fund"
    assert result["matched_objects"][0]["params"] == {}
    assert result["resolved_params"] == {"fund_code": "003095", "period": "1y"}


def test_retrieve_context_accepts_user_context_as_second_positional_argument():
    # 兼容旧调用方式：第二个位置参数传 dict 时应被解释为 user_context。
    result = service().retrieve_context(
        "分析003095近一年收益率和最大回撤表现",
        {"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["status"] == "success"
    assert result["fact_requirements"]
    assert result["candidate_invocations"]
    assert result["resolved_params"] == {"fund_code": "003095", "period": "1y"}


def test_retrieve_context_returns_standard_relation_subgraph():
    # relation_subgraph 需要把对象、边和路径规整为去重后的标准结构。
    result = service().retrieve_context(
        question="Analyze fund 003095 last year return.",
        user_context={"permission_scopes": ["fund_public_data:read"], "detail_level": "full", "debug": True},
    )

    subgraph = result["relation_subgraph"]
    assert set(subgraph) == {"nodes", "edges", "paths"}
    assert subgraph["nodes"]
    assert subgraph["edges"]
    assert subgraph["paths"] == [
        {
            "path": [
                "ObjectType:Fund",
                "QueryCapability:fund_perf_interval_query",
                "DataTable:dws_fund_perf_1y",
                "DataField:dws_fund_perf_1y.区间回报（近一年)",
            ],
            "edges": [
                "QueryCapability:fund_perf_interval_query__targets_object_type__ObjectType:Fund",
                "QueryCapability:fund_perf_interval_query__reads_from__DataTable:dws_fund_perf_1y",
                "DataTable:dws_fund_perf_1y__has_field__DataField:dws_fund_perf_1y.区间回报（近一年)",
            ],
            "score": 0.95,
        }
    ]

    node_ids = [node["node_id"] for node in subgraph["nodes"]]
    edge_ids = [edge["edge_id"] for edge in subgraph["edges"]]
    assert "Fund:003095" not in node_ids
    assert node_ids.count("ObjectType:Fund") == 1
    assert node_ids.count("Attribute:return_rate") == 1
    assert node_ids.count("Attribute:max_drawdown") == 1
    assert node_ids.count("QueryCapability:fund_perf_interval_query") == 1
    assert node_ids.count("SkillCapability:fund_performance_analysis") == 1
    assert any(node_id.startswith("DataTable:") for node_id in node_ids)
    assert any(node_id.startswith("DataField:") for node_id in node_ids)
    assert edge_ids.count(
        "QueryCapability:fund_perf_interval_query__targets_object_type__ObjectType:Fund"
    ) == 1

    fund_node = next(node for node in subgraph["nodes"] if node["node_id"] == "ObjectType:Fund")
    assert fund_node["object_type"] == "ObjectType"
    assert fund_node["object_id"] == "Fund"

    edge = next(edge for edge in subgraph["edges"] if edge["relation_type"] == "targets_object_type")
    assert edge["edge_id"] == (
        "QueryCapability:fund_perf_interval_query__targets_object_type__ObjectType:Fund"
    )
    assert edge["from"] == "QueryCapability:fund_perf_interval_query"
    assert edge["to"] == "ObjectType:Fund"
    assert edge["relation_type"] == "targets_object_type"
    assert edge["score"] == 0.95


def test_retrieve_context_matches_attributes_and_period():
    # 属性命中后，候选查询和候选调用应包含对应 tool 与已解析参数。
    result = service().retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    attribute_names = {item["attribute_name"] for item in result["matched_attributes"]}
    assert {"return_rate", "max_drawdown"}.issubset(attribute_names)
    assert result["candidate_invocations"][0]["skill_id"] == "fund_performance_analysis"
    assert result["candidate_invocations"][0]["tool_type"] == "SkillCapability"
    assert result["candidate_invocations"][0]["tool_name"] == "fund_performance_analysis"
    assert result["candidate_invocations"][0]["params"] == {
        "fund_code": "003095",
        "period": "1y",
    }
    assert result["candidate_invocations"][0]["missing_params"] == []
    assert result["candidate_invocations"][0]["covers_fact_requirements"]
    invocation_skill_ids = {item.get("skill_id") for item in result["candidate_invocations"]}
    assert {"fund_performance_analysis", "fund_risk_analysis"}.issubset(invocation_skill_ids)
    assert result["missing_params"] == []


def test_missing_period_is_reported():
    # 缺少 period 时不应阻止候选查询返回，但要在 missing_params 中明确指出。
    result = service().retrieve_context(
        question="分析003095收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert any(item["missing_params"] == ["period"] for item in result["missing_params"])
    assert result["resolved_params"] == {"fund_code": "003095"}
    assert result["candidate_invocations"][0]["params"] == {"fund_code": "003095"}
    assert result["candidate_invocations"][0]["missing_params"] == ["period"]
    assert any("period" in warning for warning in result["warnings"])


def test_trading_days_are_resolved_without_satisfying_period():
    # trading_days 不能错误地满足 period 必填项，二者业务口径不同。
    result = service().retrieve_context(
        question="分析003095近30个交易日收益率",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["resolved_params"] == {"fund_code": "003095", "trading_days": 30}
    assert result["candidate_invocations"][0]["params"] == {"fund_code": "003095"}
    assert result["candidate_invocations"][0]["missing_params"] == ["period"]


def test_permission_filters_candidate_query():
    # 用户权限不包含查询所需 scope 时，候选查询应被过滤并产生 warning。
    result = service().retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": []},
    )

    assert result["candidate_invocations"] == []
    assert result["confidence"]["query_match"] == 0.0
    assert any("fund_public_data:read" in warning for warning in result["warnings"])


def test_candidate_skills_are_core_output_but_can_be_suppressed():
    # 技能候选是默认核心输出；兼容调用方仍可显式关闭。
    base = service().retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"], "detail_level": "standard"},
    )
    without_skills = service().retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"], "detail_level": "standard"},
        options={"include_candidate_skills": False},
    )

    assert base["candidate_skills"][0]["skill_id"] == "fund_performance_analysis"
    assert without_skills["candidate_skills"] == []


def test_database_unavailable_returns_structured_error_without_fallback():
    # 仓储健康检查失败时，服务应返回同形状错误响应，而不是降级到假数据。
    result = service(fail=True).retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["status"] == "error"
    assert result["matched_objects"] == []
    assert result["candidate_queries"] == []
    assert result["resolved_params"] == {}
    assert result["candidate_invocations"] == []
    assert result["relation_subgraph"] == {"nodes": [], "edges": [], "paths": []}
    assert "TDSQL unavailable" in result["warnings"][0]


def test_error_response_includes_empty_relation_subgraph():
    # 错误响应也必须包含空 relation_subgraph，减少客户端字段分支判断。
    result = error_response(
        domain="finance_market",
        question="",
        intent="structured_query",
        message="question must not be empty",
    )

    assert result["relation_subgraph"] == {"nodes": [], "edges": [], "paths": []}
