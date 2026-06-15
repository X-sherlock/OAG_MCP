from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oag_mcp.repositories import GraphRepository, OntologyRepository


SUPPORTED_TASK_TYPES = {"query", "analyze", "compare", "rank", "screen", "recommend", "profile", "explain", "summarize"}
SEMANTIC_EXPANSION_TYPES = {
    "compared_with",
    "derives",
    "ranked_by_peer",
    "risk_companion",
    "return_companion",
    "benchmark_metric_of",
    "peer_metric_of",
}
OBJECT_RELATION_TYPES = {
    "managed_by",
    "issued_by",
    "managed_by_company",
    "has_benchmark",
    "tracks_index",
    "belongs_to_category",
    "has_dividend",
    "has_fee",
    "has_asset_allocation",
    "has_position",
    "holds_asset",
}
TASK_GRAPH_RELATION_TYPES = SEMANTIC_EXPANSION_TYPES | OBJECT_RELATION_TYPES
MAX_OPTIONAL_EXPANSIONS_PER_REQUIRED_FACT = 3
MAX_RELATION_EXPANSION_FACTS = 8
ATTRIBUTE_FACT_TYPES = {
    "benchmark_return": "benchmark_metric_value",
    "excess_return": "excess_metric_value",
    "rank": "peer_rank",
    "percentile": "peer_rank",
    "peer_return_rank": "peer_rank",
    "peer_risk_rank": "peer_rank",
    "peer_sharpe_rank": "peer_rank",
    "peer_drawdown_rank": "peer_rank",
    "peer_average": "peer_average",
    "fund_name": "object_profile",
    "fund_type": "object_profile",
    "company_name": "object_profile",
    "manager_name": "object_profile",
    "benchmark_name": "object_profile",
    "fee_type": "fee_fact",
    "fee_value": "fee_fact",
    "fee_effective_date": "fee_fact",
    "dividend_per_share": "dividend_fact",
    "dividend_date": "dividend_fact",
    "stable_monthly_dividend": "dividend_fact",
    "stable_quarterly_dividend": "dividend_fact",
    "stable_yearly_dividend": "dividend_fact",
    "stock_name": "holding_fact",
    "stock_nav_ratio": "holding_fact",
    "bond_name": "holding_fact",
    "bond_nav_ratio": "holding_fact",
    "holding_industry": "holding_fact",
    "asset_total_value": "allocation_fact",
    "asset_net_value": "allocation_fact",
    "stock_asset_ratio": "allocation_fact",
    "bond_asset_ratio": "allocation_fact",
    "cash_asset_ratio": "allocation_fact",
    "fund_asset_ratio": "allocation_fact",
    "other_asset_ratio": "allocation_fact",
}
RELATION_ATTRIBUTE_MAP = {
    "managed_by": "manager_name",
    "issued_by": "company_name",
    "managed_by_company": "company_name",
    "has_benchmark": "benchmark_name",
    "tracks_index": "tracking_index_name",
    "belongs_to_category": "fund_type",
    "has_dividend": "dividend_date",
    "has_fee": "fee_type",
    "has_asset_allocation": "asset_total_value",
    "has_position": "stock_name",
    "holds_asset": "stock_name",
}
RELATION_QUERY_ALIASES = {
    "fund_manager": {"relation_type": "managed_by", "target_object_type": "FundManager", "attribute_name": "manager_name"},
    "manager_name": {"relation_type": "managed_by", "target_object_type": "FundManager", "attribute_name": "manager_name"},
    "fund_company": {"relation_type": "issued_by", "target_object_type": "FundCompany", "attribute_name": "company_name"},
    "company_name": {"relation_type": "issued_by", "target_object_type": "FundCompany", "attribute_name": "company_name"},
    "benchmark": {"relation_type": "has_benchmark", "target_object_type": "Benchmark", "attribute_name": "benchmark_name"},
    "benchmark_name": {"relation_type": "has_benchmark", "target_object_type": "Benchmark", "attribute_name": "benchmark_name"},
    "fund_category": {"relation_type": "belongs_to_category", "target_object_type": "FundCategory", "attribute_name": "fund_type"},
    "fund_type": {"relation_type": "belongs_to_category", "target_object_type": "FundCategory", "attribute_name": "fund_type"},
    "fee": {"relation_type": "has_fee", "target_object_type": "FundFee", "attribute_name": "fee_value"},
    "fee_value": {"relation_type": "has_fee", "target_object_type": "FundFee", "attribute_name": "fee_value"},
    "dividend": {"relation_type": "has_dividend", "target_object_type": "Dividend", "attribute_name": "dividend_per_share"},
    "dividend_date": {"relation_type": "has_dividend", "target_object_type": "Dividend", "attribute_name": "dividend_date"},
    "holding": {"relation_type": "has_position", "target_object_type": "FundPosition", "attribute_name": "stock_name"},
    "asset_allocation": {"relation_type": "has_asset_allocation", "target_object_type": "AssetAllocation", "attribute_name": "stock_asset_ratio"},
}

INTENT_SCENARIOS = {
    "fund_profile": "profile",
    "profile_query": "profile",
    "fee_analysis": "fee",
    "dividend_analysis": "dividend",
    "holding_analysis": "holding",
    "asset_allocation_analysis": "allocation",
    "fund_comparison": "comparison",
    "fund_ranking": "ranking",
    "fund_screening": "screening",
    "fund_recommendation": "recommendation",
}

SCENARIO_ATTRIBUTES = {
    "profile": ["fund_name", "fund_type", "manager_name", "company_name", "benchmark_name"],
    "fee": ["fee_type", "fee_value", "fee_effective_date"],
    "dividend": ["dividend_per_share", "dividend_date"],
    "holding": ["stock_name", "stock_nav_ratio", "bond_name", "bond_nav_ratio"],
    "allocation": ["asset_total_value", "asset_net_value", "stock_asset_ratio", "bond_asset_ratio", "cash_asset_ratio"],
}


@dataclass
class FactPlanner:
    ontology_repository: OntologyRepository
    graph_repository: GraphRepository
    domain: str = "finance_market"
    intent_profiles: list[dict[str, Any]] | None = None
    skills: list[dict[str, Any]] | None = None

    def plan(
        self,
        semantic_frame: dict[str, Any] | None,
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        user_context = user_context or {}
        if not semantic_frame:
            return semantic_frame_required_response(self.domain)
        if not isinstance(semantic_frame, dict):
            return _error_response(
                domain=self.domain,
                raw_question="",
                error_code="SEMANTIC_FRAME_INVALID",
                message_zh="semantic_frame 必须是对象结构，不能使用自然语言问题字符串替代。",
            )

        semantic_frame = _normalize_semantic_frame(semantic_frame)
        domain = str(semantic_frame.get("domain") or self.domain)
        debug = bool(user_context.get("debug") or semantic_frame.get("debug"))
        self._ensure_ready(domain)

        profiles = self.intent_profiles or self.ontology_repository.get_intent_profiles(domain)
        skills = self.skills or self.ontology_repository.get_skill_capabilities(domain)
        catalog = _Catalog(
            object_types={
                item["object_id"]: item
                for item in self.ontology_repository.get_objects_by_ids(
                    domain, _semantic_object_types(semantic_frame)
                )
                if item.get("object_id")
            },
            attributes={
                item["attribute_name"]: item
                for item in self.ontology_repository.get_attributes_by_names(
                    domain, _semantic_attribute_names(semantic_frame, profiles)
                )
                if item.get("attribute_name")
            },
            intent_profiles={
                item["intent_name"]: item
                for item in profiles
                if item.get("intent_name")
            },
            skills=[
                item
                for item in skills
                if item.get("enabled", True)
            ],
        )

        validation = _validate_semantic_frame(semantic_frame, catalog)
        if validation["errors"]:
            return _error_response(
                domain=domain,
                raw_question=semantic_frame.get("raw_question"),
                error_code="SEMANTIC_FRAME_INVALID",
                message_zh="semantic_frame 中存在本体无法识别的对象或属性，OAG 无法继续规划事实需求。",
                warnings=validation["warnings"],
                details=validation["errors"],
            )

        initial = _initial_fact_requirements(semantic_frame, catalog, validation["warnings"])
        if not initial.requirements:
            return _need_clarification_response(domain, semantic_frame, initial.warnings)

        relation_edges = self.graph_repository.recall_relations(
            domain=domain,
            entities=_relation_seed_entities(semantic_frame, initial.requirements),
            max_hops=1,
            top_k=1000,
        )
        fact_requirements, expansion_evidence = _expand_by_relations(
            semantic_frame=semantic_frame,
            requirements=initial.requirements,
            relation_edges=relation_edges,
            catalog=catalog,
        )
        invocations, coverage_warnings = _candidate_invocations(
            semantic_frame=semantic_frame,
            fact_requirements=fact_requirements,
            skills=catalog.skills,
            user_context=user_context,
        )
        coverage_summary = _coverage_summary(fact_requirements, invocations, coverage_warnings)
        missing_params = _missing_params(invocations)
        warnings = [*validation["warnings"], *initial.warnings, *coverage_warnings]
        if coverage_summary["uncovered_required_facts"]:
            warnings.append(
                {
                    "warning_code": "REQUIRED_FACT_UNCOVERED",
                    "message_zh": "存在必需事实当前没有可用 Skill 覆盖，需要补充能力或调整语义框架。",
                }
            )

        response = {
            "status": "success",
            "domain": domain,
            "raw_question": semantic_frame.get("raw_question") or "",
            "semantic_frame_summary": _semantic_frame_summary(semantic_frame),
            "normalized_semantic_frame": semantic_frame,
            "target_instances": _target_instances(semantic_frame, catalog),
            "fact_requirements": fact_requirements,
            "candidate_invocations": invocations,
            "task_graph": _task_graph(semantic_frame, catalog, fact_requirements, invocations),
            "coverage_summary": coverage_summary,
            "missing_params": missing_params,
            "uncovered_facts": coverage_summary.get("uncovered_required_facts", []),
            "diagnostics": _planning_diagnostics(semantic_frame, catalog, fact_requirements, invocations, coverage_summary, warnings),
            "warnings": warnings,
        }
        if debug:
            response["debug_evidence"] = {
                "message_zh": "调试证据仅用于排查事实规划过程，正常大模型消费可忽略。",
                "relation_expansion_edges": expansion_evidence,
                "skill_count": len(catalog.skills),
                "relation_edge_count": len(relation_edges),
            }
        return response

    def _ensure_ready(self, domain: str) -> None:
        if domain != self.domain:
            raise ValueError(f"Unsupported domain: {domain}")
        self.ontology_repository.ping()
        self.graph_repository.ping()
        if not self.ontology_repository.domain_enabled(domain):
            raise ValueError(f"Domain is not enabled: {domain}")


@dataclass
class _Catalog:
    object_types: dict[str, dict[str, Any]]
    attributes: dict[str, dict[str, Any]]
    intent_profiles: dict[str, dict[str, Any]]
    skills: list[dict[str, Any]]


@dataclass
class _InitialRequirements:
    requirements: list[dict[str, Any]]
    warnings: list[dict[str, Any]]


def semantic_frame_required_response(domain: str = "finance_market") -> dict[str, Any]:
    return _error_response(
        domain=domain,
        raw_question="",
        error_code="SEMANTIC_FRAME_REQUIRED",
        message_zh="缺少前置意图识别节点输出的结构化语义框架，OAG 无法进行事实规划。",
    )


def _error_response(
    domain: str,
    raw_question: Any,
    error_code: str,
    message_zh: str,
    warnings: list[dict[str, Any]] | None = None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": "error",
        "domain": domain,
        "raw_question": raw_question or "",
        "error_code": error_code,
        "message_zh": message_zh,
        "semantic_frame_summary": {},
        "target_instances": [],
        "fact_requirements": [],
        "candidate_invocations": [],
        "task_graph": {"nodes": [], "edges": []},
        "coverage_summary": {
            "required_fact_count": 0,
            "covered_required_fact_count": 0,
            "uncovered_required_facts": [],
            "optional_fact_count": 0,
            "covered_optional_fact_count": 0,
            "uncovered_optional_facts": [],
            "skill_count": 0,
            "has_permission_blocked_facts": False,
            "coverage_status": "need_clarification" if error_code == "FACT_REQUIREMENTS_INSUFFICIENT" else "no_coverage",
        },
        "missing_params": [],
        "warnings": warnings or [],
        **({"details": details} if details else {}),
    }


def _need_clarification_response(
    domain: str, semantic_frame: dict[str, Any], warnings: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        **_error_response(
            domain=domain,
            raw_question=semantic_frame.get("raw_question"),
            error_code="FACT_REQUIREMENTS_INSUFFICIENT",
            message_zh="当前语义信息不足，无法规划事实需求；请补充明确指标、筛选/排序条件，或使用已配置的宽泛意图。",
            warnings=warnings,
        ),
        "status": "need_clarification",
        "semantic_frame_summary": _semantic_frame_summary(semantic_frame),
    }


def _normalize_semantic_frame(frame: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(frame)
    normalized.setdefault("domain", "finance_market")
    normalized["task_type"] = str(normalized.get("task_type") or "query").strip() or "query"
    normalized["constraints"] = dict(normalized.get("constraints") or {})
    normalized["mentioned_attributes"] = list(dict.fromkeys(normalized.get("mentioned_attributes") or []))
    normalized["relation_queries"] = [item for item in normalized.get("relation_queries") or [] if isinstance(item, dict)]
    normalized["filters"] = [item for item in normalized.get("filters") or [] if isinstance(item, dict)]
    normalized["ranking"] = [item for item in normalized.get("ranking") or [] if isinstance(item, dict)]
    normalized["comparison"] = dict(normalized.get("comparison") or {})
    normalized["options"] = {
        "allow_relation_expansion": True,
        "allow_peer_expansion": True,
        "include_supporting_context": True,
        **dict(normalized.get("options") or {}),
    }
    targets = []
    for index, target in enumerate(normalized.get("target_objects") or [], start=1):
        if not isinstance(target, dict):
            continue
        item = dict(target)
        item["object_type"] = item.get("object_type") or "Fund"
        item["instance_ref"] = dict(item.get("instance_ref") or {})
        item["role"] = item.get("role") or ("candidate_set" if item["object_type"].endswith("Set") else "analysis_subject")
        item["target_index"] = index
        targets.append(item)
    normalized["target_objects"] = targets
    if normalized["task_type"] == "profile" and not normalized.get("intent"):
        normalized["intent"] = "fund_profile"
    if normalized.get("intent") in {"fund_recommendation"}:
        normalized["task_type"] = "recommend"
    return normalized


def _validate_semantic_frame(frame: dict[str, Any], catalog: _Catalog) -> dict[str, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not frame.get("domain"):
        errors.append({"error_code": "DOMAIN_REQUIRED", "message_zh": "semantic_frame 缺少 domain。"})
    targets = frame.get("target_objects")
    if not isinstance(targets, list) or not targets:
        errors.append({"error_code": "TARGET_OBJECTS_REQUIRED", "message_zh": "semantic_frame 缺少 target_objects。"})
    for target in targets or []:
        object_type = target.get("object_type")
        if object_type not in catalog.object_types:
            errors.append(
                {
                    "error_code": "UNKNOWN_OBJECT_TYPE",
                    "object_type": object_type,
                    "message_zh": f"本体中不存在对象类型：{object_type}。",
                }
            )
    for attr in _semantic_attribute_names(frame):
        if attr in RELATION_QUERY_ALIASES:
            continue
        if attr not in catalog.attributes:
            errors.append(
                {
                    "error_code": "UNKNOWN_ATTRIBUTE",
                    "attribute_name": attr,
                    "message_zh": f"本体中不存在属性：{attr}。",
                }
            )
    intent = frame.get("intent")
    if intent and intent not in catalog.intent_profiles:
        warnings.append(
            {
                "warning_code": "UNKNOWN_INTENT",
                "intent": intent,
                "message_zh": f"未找到意图画像 {intent}，将仅基于显式属性和操作规则规划事实需求。",
            }
        )
    task_type = frame.get("task_type")
    if task_type and task_type not in SUPPORTED_TASK_TYPES:
        warnings.append(
            {
                "warning_code": "UNKNOWN_TASK_TYPE",
                "task_type": task_type,
                "message_zh": f"未知任务类型 {task_type}，OAG 会尽量使用已有语义字段规划。",
            }
        )
    return {"errors": errors, "warnings": warnings}


def _initial_fact_requirements(
    frame: dict[str, Any], catalog: _Catalog, validation_warnings: list[dict[str, Any]]
) -> _InitialRequirements:
    del validation_warnings
    warnings: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    mentioned = list(dict.fromkeys(frame.get("mentioned_attributes") or []))
    targets = _planning_targets(frame)
    if mentioned:
        for name in mentioned:
            relation_hint = RELATION_QUERY_ALIASES.get(name)
            if relation_hint:
                for target in _targets_of_type(frame, "Fund") or targets:
                    requirements.append(
                        _relation_requirement(
                            frame=frame,
                            catalog=catalog,
                            relation_type=relation_hint["relation_type"],
                            target_object_type=relation_hint["target_object_type"],
                            priority="required",
                            source="explicit_relation",
                            reason_zh=_explicit_relation_reason(relation_hint["relation_type"], relation_hint["target_object_type"]),
                            attribute_name=relation_hint.get("attribute_name"),
                            target=target,
                            answer_visibility="answer_fact",
                            planning_role="explicit_relation",
                        )
                    )
                continue
            for target in _fact_targets_for_attribute(frame, name):
                requirements.append(
                    _attribute_requirement(
                        frame,
                        catalog,
                        name,
                        "required",
                        "explicit_attribute",
                        "用户显式提到该指标，优先作为必需事实。",
                        target=target,
                    )
                )
    else:
        intent = frame.get("intent")
        profile = catalog.intent_profiles.get(intent) if intent else None
        if profile:
            template = profile.get("fact_requirements_template") or []
            for item in template:
                name = item.get("attribute_name")
                if not name:
                    continue
                for target in _fact_targets_for_attribute(frame, name):
                    requirements.append(
                        _attribute_requirement(
                            frame,
                            catalog,
                            name,
                            item.get("priority") or "required",
                            "intent_template",
                            item.get("reason_zh") or "由命中的宽泛意图模板补全该事实需求。",
                            fact_type=item.get("fact_type"),
                            target=target,
                        )
                    )

    for item in _operation_requirements(frame, catalog):
        if not _has_requirement(
            requirements,
            item["fact_type"],
            item.get("attribute_name"),
            item["subject"]["object_type"],
            item["subject"].get("subject_id"),
            item.get("predicate"),
            item.get("target_object_type"),
        ):
            requirements.append(item)
    for item in _scenario_requirements(frame, catalog):
        if not _has_requirement(
            requirements,
            item["fact_type"],
            item.get("attribute_name"),
            item["subject"]["object_type"],
            item["subject"].get("subject_id"),
            item.get("predicate"),
            item.get("target_object_type"),
        ):
            requirements.append(item)
    for item in _explicit_relation_query_requirements(frame, catalog):
        key = (
            item.get("fact_type"),
            item.get("predicate"),
            item.get("target_object_type"),
            item["subject"].get("subject_id"),
        )
        if not any(
            (
                row.get("fact_type"),
                row.get("predicate"),
                row.get("target_object_type"),
                row["subject"].get("subject_id"),
            )
            == key
            for row in requirements
        ):
            requirements.append(item)

    return _InitialRequirements(requirements=_dedupe_requirements(requirements), warnings=warnings)


def _operation_requirements(frame: dict[str, Any], catalog: _Catalog) -> list[dict[str, Any]]:
    task_type = frame.get("task_type")
    if task_type not in {"rank", "screen", "recommend", "compare"}:
        return []
    rows: list[dict[str, Any]] = []
    target = _fund_set_target(frame) or (_synthetic_fund_set_target() if task_type in {"rank", "screen", "recommend"} else _primary_target(frame))
    target_type = target.get("object_type") or ("FundSet" if task_type in {"rank", "screen", "recommend"} else "Fund")
    if target_type.endswith("Set") or task_type in {"rank", "screen", "recommend"}:
        rows.append(
            _base_requirement(
                frame=frame,
                catalog=catalog,
                fact_type="entity_set",
                attribute_name=None,
                subject_type=target_type,
                priority="required",
                source="operation_rule",
                reason_zh="该操作型任务需要先确定候选对象集合。",
                target=target,
                planning_role="candidate_set",
            )
        )
    for ranking in frame.get("ranking") or []:
        name = ranking.get("attribute")
        if name:
            rows.append(
                _attribute_requirement(
                    frame,
                    catalog,
                    name,
                    "required",
                    "operation_rule",
                    "排序或推荐任务需要该指标作为排序依据。",
                    fact_type="metric_ranking",
                    subject_type=target_type,
                    target=target,
                    extra={"ranking": dict(ranking), "planning_role": "ranking_condition"},
                )
            )
    for item in frame.get("filters") or []:
        name = item.get("attribute")
        if name:
            rows.append(
                _attribute_requirement(
                    frame,
                    catalog,
                    name,
                    "required",
                    "operation_rule",
                    "筛选任务需要该指标作为过滤条件。",
                    fact_type="filter_condition",
                    subject_type=target_type,
                    target=target,
                    extra={"filter": dict(item), "planning_role": "filter_condition"},
                )
            )
    if task_type == "compare" and len(_targets_of_type(frame, "Fund")) >= 2:
        attrs = _comparison_attributes(frame)
        for name in attrs:
            rows.append(
                _base_requirement(
                    frame=frame,
                    catalog=catalog,
                    fact_type="comparison_result",
                    attribute_name=name,
                    subject_type="Fund",
                    priority="derived",
                    source="operation_rule",
                    reason_zh="多基金比较需要基于各主体指标事实形成比较结果。",
                    target=_targets_of_type(frame, "Fund")[0],
                    planning_role="derived_comparison",
                    answer_visibility="answer_fact",
                    extra={
                        "comparison": dict(frame.get("comparison") or {}),
                        "derived_from_subjects": [
                            _target_subject_id(target)
                            for target in _targets_of_type(frame, "Fund")
                        ],
                    },
                )
            )
    return rows


def _scenario_requirements(frame: dict[str, Any], catalog: _Catalog) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    task_type = frame.get("task_type")
    intent = frame.get("intent") or ""
    scenario = INTENT_SCENARIOS.get(intent)
    if task_type == "profile":
        scenario = "profile"
    if not scenario:
        return rows

    if scenario in {"profile", "fee", "dividend", "holding", "allocation"}:
        targets = _targets_of_type(frame, "Fund")
        attrs = SCENARIO_ATTRIBUTES[scenario]
        source = "scenario_rule"
        fact_type_override = {
            "profile": "object_profile",
            "fee": "fee_fact",
            "dividend": "dividend_fact",
            "holding": "holding_fact",
            "allocation": "allocation_fact",
        }[scenario]
        reason = {
            "profile": "画像类查询需要基金基础信息及核心对象关系。",
            "fee": "费率查询需要基金费率事实。",
            "dividend": "分红查询需要基金分红事实。",
            "holding": "持仓查询需要基金持仓事实。",
            "allocation": "配置查询需要基金资产配置事实。",
        }[scenario]
        for target in targets:
            for attr in attrs:
                rows.append(
                    _attribute_requirement(
                        frame,
                        catalog,
                        attr,
                        "required",
                        source,
                        reason,
                        fact_type=fact_type_override,
                        target=target,
                        planning_role=scenario,
                    )
                )
        if scenario == "profile":
            for relation_type, target_type in [
                ("managed_by", "FundManager"),
                ("issued_by", "FundCompany"),
                ("has_benchmark", "Benchmark"),
                ("belongs_to_category", "FundCategory"),
            ]:
                for target in targets:
                    rows.append(
                        _relation_requirement(
                            frame=frame,
                            catalog=catalog,
                            relation_type=relation_type,
                            target_object_type=target_type,
                            priority="required",
                            source=source,
                            reason_zh=_explicit_relation_reason(relation_type, target_type),
                            attribute_name=RELATION_ATTRIBUTE_MAP.get(relation_type),
                            target=target,
                            answer_visibility="answer_fact",
                            planning_role="profile_relation",
                        )
                    )
    if intent == "benchmark_comparison":
        for target in _targets_of_type(frame, "Fund"):
            rows.append(
                _relation_requirement(
                    frame=frame,
                    catalog=catalog,
                    relation_type="has_benchmark",
                    target_object_type="Benchmark",
                    priority="supporting",
                    source="scenario_rule",
                    reason_zh="基准比较需要确认基金对应的业绩比较基准作为支撑上下文。",
                    attribute_name="benchmark_name",
                    target=target,
                    answer_visibility="supporting_context",
                    planning_role="benchmark_context",
                )
            )
    if intent == "peer_comparison":
        for target in _targets_of_type(frame, "Fund"):
            rows.append(
                _relation_requirement(
                    frame=frame,
                    catalog=catalog,
                    relation_type="belongs_to_category",
                    target_object_type="FundCategory",
                    priority="supporting",
                    source="scenario_rule",
                    reason_zh="同类比较需要基金分类作为同类集合支撑上下文。",
                    attribute_name="fund_type",
                    target=target,
                    answer_visibility="supporting_context",
                    planning_role="peer_context",
                )
            )
    return rows


def _explicit_relation_query_requirements(frame: dict[str, Any], catalog: _Catalog) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for query in frame.get("relation_queries") or []:
        if not isinstance(query, dict):
            continue
        relation_type = query.get("relation_type")
        target_object_type = query.get("target_object_type")
        if not relation_type or not target_object_type:
            continue
        for target in _targets_of_type(frame, "Fund") or _planning_targets(frame):
            rows.append(
                _relation_requirement(
                    frame=frame,
                    catalog=catalog,
                    relation_type=relation_type,
                    target_object_type=target_object_type,
                    priority=query.get("priority") or "required",
                    source="explicit_relation",
                    reason_zh=query.get("reason_zh") or _explicit_relation_reason(relation_type, target_object_type),
                    attribute_name=query.get("attribute_name") or RELATION_ATTRIBUTE_MAP.get(relation_type),
                    target=target,
                    answer_visibility="answer_fact",
                    planning_role="explicit_relation",
                )
            )
    return rows


def _relation_requirement(
    frame: dict[str, Any],
    catalog: _Catalog,
    relation_type: str,
    target_object_type: str,
    priority: str,
    source: str,
    reason_zh: str,
    attribute_name: str | None = None,
    target: dict[str, Any] | None = None,
    answer_visibility: str | None = None,
    planning_role: str | None = None,
) -> dict[str, Any]:
    target = target or _primary_target(frame)
    subject_type = target.get("object_type") or _primary_target(frame).get("object_type") or "Fund"
    item = _base_requirement(
        frame=frame,
        catalog=catalog,
        fact_type="relation_instance",
        attribute_name=attribute_name,
        subject_type=subject_type,
        priority=priority,
        source=source,
        reason_zh=reason_zh,
        target=target,
        answer_visibility=answer_visibility,
        planning_role=planning_role,
    )
    suffix = item.get("constraints", {}).get("period") or frame.get("task_type") or "current"
    item["fact_requirement_id"] = f"FactRequirement:fr_{relation_type}_{target_object_type}_{suffix}".replace(" ", "_")
    item["predicate"] = relation_type
    item["predicate_zh"] = _relation_type_zh(relation_type)
    item["target_object_type"] = target_object_type
    item["target_object_type_zh"] = catalog.object_types.get(target_object_type, {}).get("object_name") or target_object_type
    item["object_relation"] = {
        "from_object_type": subject_type,
        "to_object_type": target_object_type,
        "relation_type": relation_type,
        "relation_type_zh": _relation_type_zh(relation_type),
    }
    item["label_zh"] = f"{item['subject']['label_zh']}与{item['target_object_type_zh']}关系事实"
    item["description_zh"] = reason_zh
    return item


def _expand_by_relations(
    semantic_frame: dict[str, Any],
    requirements: list[dict[str, Any]],
    relation_edges: list[dict[str, Any]],
    catalog: _Catalog,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = list(requirements)
    evidence: list[dict[str, Any]] = []
    existing = {
        (
            item.get("attribute_name"),
            item.get("fact_type"),
            item["subject"].get("subject_id"),
            item.get("predicate"),
            item.get("target_object_type"),
        )
        for item in rows
    }
    source_attributes = {
        item.get("attribute_name")
        for item in requirements
        if item.get("attribute_name") and item.get("priority") == "required"
    }
    target_object_types = {target.get("object_type") for target in semantic_frame.get("target_objects") or []}
    expansions_by_source: dict[str, int] = {}
    expansion_count = 0

    for edge in sorted(relation_edges, key=_relation_expansion_sort_key):
        if expansion_count >= MAX_RELATION_EXPANSION_FACTS:
            break
        relation_type = edge.get("relation_type")
        if relation_type not in TASK_GRAPH_RELATION_TYPES:
            continue
        if not _relation_usable_in_task_graph(relation_type):
            continue
        from_type, from_id = _split_node_id(edge.get("from"))
        to_type, to_id = _split_node_id(edge.get("to"))
        properties = _edge_properties(edge)
        auto_expand_mode = properties.get("auto_expand_mode") or "contextual"
        answer_visibility = properties.get("answer_visibility") or "answer_fact"
        if auto_expand_mode in {"disabled", "debug_only"} or answer_visibility == "debug_only":
            continue
        if not _edge_applicable(edge, semantic_frame, rows):
            continue
        if auto_expand_mode == "explicit_only" and not _explicit_relation_triggered(properties, semantic_frame, relation_type):
            continue
        if auto_expand_mode in {"contextual", "always"} and not _trigger_policy_matches(properties, semantic_frame, from_id, rows):
            continue
        if auto_expand_mode == "dependency_only" and answer_visibility not in {"supporting_context", "answer_fact"}:
            evidence.append(_edge_evidence(edge, properties))
            continue
        if from_type == "Attribute" and from_id in source_attributes and to_type == "Attribute" and relation_type in SEMANTIC_EXPANSION_TYPES:
            max_per_source = _max_per_source(properties)
            if expansions_by_source.get(from_id, 0) >= max_per_source:
                continue
            source_reqs = [item for item in requirements if item.get("attribute_name") == from_id and item.get("priority") == "required"]
            for source_req in source_reqs:
                if expansion_count >= MAX_RELATION_EXPANSION_FACTS:
                    break
                priority = properties.get("expansion_priority") or properties.get("default_priority") or "optional"
                target = _target_by_subject_id(semantic_frame, source_req["subject"].get("subject_id"))
                item = _attribute_requirement(
                    semantic_frame,
                    catalog,
                    to_id,
                    priority,
                    "relation_expansion",
                    properties.get("reason_zh") or _relation_reason(relation_type, from_id, to_id, catalog),
                    target=target,
                )
                if priority != "required":
                    item["priority"] = "optional"
                    item["priority_zh"] = "可选"
                item["planning_role"] = properties.get("planning_role")
                item["auto_expand_mode"] = auto_expand_mode
                item["answer_visibility"] = answer_visibility
                item["expansion_priority"] = priority
                item["expanded_from"] = {
                    "source_attribute": from_id,
                    "target_attribute": to_id,
                    "relation_type": relation_type,
                    "relation_type_zh": properties.get("relation_name_zh") or _relation_type_zh(relation_type),
                    "edge_id": edge.get("edge_id") or f"{edge.get('from')}__{relation_type}__{edge.get('to')}",
                    "weight": properties.get("weight") or edge.get("score"),
                    "planning_role": properties.get("planning_role"),
                    "answer_visibility": answer_visibility,
                }
                key = (item.get("attribute_name"), item.get("fact_type"), item["subject"].get("subject_id"), None, None)
                if key not in existing:
                    rows.append(item)
                    existing.add(key)
                    evidence.append(item["expanded_from"] | {"reason_zh": item["reason_zh"]})
                    expansions_by_source[from_id] = expansions_by_source.get(from_id, 0) + 1
                    expansion_count += 1
                else:
                    existing_item = _find_requirement(rows, item.get("fact_type"), item.get("attribute_name"), item["subject"].get("subject_id"))
                    if existing_item is not None:
                        existing_item.setdefault("relation_explanations", []).append(
                            item["expanded_from"] | {"reason_zh": item["reason_zh"]}
                        )
        elif from_type == "ObjectType" and from_id in target_object_types and to_type == "ObjectType" and relation_type in OBJECT_RELATION_TYPES:
            for target in _targets_of_type(semantic_frame, from_id):
                if expansion_count >= MAX_RELATION_EXPANSION_FACTS:
                    break
                attribute_name = RELATION_ATTRIBUTE_MAP.get(relation_type)
                item = _relation_requirement(
                    frame=semantic_frame,
                    catalog=catalog,
                    relation_type=relation_type,
                    target_object_type=to_id,
                    priority=properties.get("expansion_priority") or properties.get("default_priority") or "optional",
                    source="relation_expansion",
                    reason_zh=properties.get("reason_zh") or f"本体关系表明{from_id}需要关联{to_id}事实用于解释。",
                    attribute_name=attribute_name,
                    target=target,
                    answer_visibility=answer_visibility,
                    planning_role=properties.get("planning_role"),
                )
                item["planning_role"] = properties.get("planning_role")
                item["auto_expand_mode"] = auto_expand_mode
                item["answer_visibility"] = answer_visibility
                item["expansion_priority"] = item["priority"]
                item["object_relation"]["edge_id"] = edge.get("edge_id") or f"{edge.get('from')}__{relation_type}__{edge.get('to')}"
                item["object_relation"]["weight"] = properties.get("weight") or edge.get("score")
                item["object_relation"]["planning_role"] = properties.get("planning_role")
                item["object_relation"]["answer_visibility"] = answer_visibility
                key = (
                    item.get("attribute_name"),
                    item.get("fact_type"),
                    item["subject"].get("subject_id"),
                    item.get("predicate"),
                    item.get("target_object_type"),
                )
                if key not in existing:
                    rows.append(item)
                    existing.add(key)
                    evidence.append(item["object_relation"] | {"reason_zh": item["reason_zh"]})
                    expansion_count += 1
    return _dedupe_requirements(rows), evidence


def _candidate_invocations(
    semantic_frame: dict[str, Any],
    fact_requirements: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    user_context: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    invocations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    scopes = set(user_context.get("permission_scopes") or [])
    for skill in skills:
        permission_scope = skill.get("permission_scope") or ""
        if permission_scope and permission_scope not in scopes:
            blocked = [_fact for _fact in fact_requirements if _skill_covers(skill, _fact, ignore_permission=True)]
            if blocked:
                warnings.append(
                    {
                        "warning_code": "SKILL_PERMISSION_BLOCKED",
                        "skill_id": skill.get("skill_id"),
                        "skill_name_zh": skill.get("skill_name") or skill.get("skill_id"),
                        "permission_scope": permission_scope,
                        "blocked_fact_requirements": [item["fact_requirement_id"] for item in blocked],
                        "message_zh": f"Skill {skill.get('skill_name') or skill.get('skill_id')} 需要权限 {permission_scope}，当前上下文未授权。",
                    }
                )
            continue
        covered = [_fact for _fact in fact_requirements if _skill_covers(skill, _fact)]
        if not covered:
            continue
        for group_index, group in enumerate(_invocation_fact_groups(skill, covered), start=1):
            params, missing = _skill_params(skill, semantic_frame, group)
            if missing:
                warnings.append(
                    {
                        "warning_code": "SKILL_PARAMS_MISSING",
                        "skill_id": skill.get("skill_id"),
                        "skill_name_zh": skill.get("skill_name") or skill.get("skill_id"),
                        "missing_params": missing,
                        "message_zh": f"Skill {skill.get('skill_name') or skill.get('skill_id')} 缺少必要调用参数：{', '.join(missing)}。",
                    }
                )
            invocation_id = f"SkillInvocation:{skill['skill_id']}:{group_index}"
            invocations.append(
                {
                    "invocation_id": invocation_id,
                    "skill_id": skill["skill_id"],
                    "skill_name_zh": skill.get("skill_name") or skill["skill_id"],
                    "description_zh": skill.get("description") or "",
                    "covers_fact_requirements": [item["fact_requirement_id"] for item in group],
                    "covered_subjects": list(dict.fromkeys(item.get("subject", {}).get("subject_id") for item in group if item.get("subject"))),
                    "params": params,
                    "missing_params": missing,
                    "permission_scope": permission_scope,
                    "coverage_score": _coverage_score(group, fact_requirements),
                    "covers_required_count": len([item for item in group if item.get("priority") == "required"]),
                    "covers_optional_count": len([item for item in group if item.get("priority") not in {"required", "derived", "supporting"}]),
                    "covers_supporting_count": len([item for item in group if item.get("priority") == "supporting"]),
                    "covers_derived_count": len([item for item in group if item.get("priority") == "derived"]),
                    "coverage_reason_zh": _coverage_reason(skill, group),
                    "uncovered_reason_zh": "",
                }
            )
    return invocations, warnings


def _skill_covers(skill: dict[str, Any], requirement: dict[str, Any], ignore_permission: bool = False) -> bool:
    del ignore_permission
    fact_types = set(skill.get("provides_fact_types") or [])
    subject_types = set(skill.get("supported_subject_types") or [])
    attributes = set(skill.get("supported_attributes") or [])
    relations = set(skill.get("supported_relations") or [])
    required_fact_type = requirement.get("fact_type")
    if requirement.get("priority") == "derived" and not fact_types:
        return False
    if required_fact_type not in fact_types and not (
        required_fact_type == "relation_instance" and "object_profile" in fact_types
    ):
        return False
    subject_type = requirement.get("subject", {}).get("object_type")
    if subject_types and subject_type not in subject_types:
        return False
    attribute_name = requirement.get("attribute_name")
    if required_fact_type == "relation_instance":
        if relations and requirement.get("predicate") in relations:
            return True
        if attribute_name and attributes and attribute_name in attributes:
            return True
        if not relations and not attributes:
            return True
        return False
    if attribute_name and attributes and attribute_name not in attributes:
        return False
    return True


def _skill_params(
    skill: dict[str, Any], frame: dict[str, Any], covered: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    params: dict[str, Any] = {}
    constraints = frame.get("constraints") or {}
    instance_refs = [item.get("subject", {}).get("instance_ref") or {} for item in covered]
    instance_ref = next((item for item in instance_refs if item), {})
    for name in skill.get("input_params") or []:
        if name == "attributes":
            attrs = [item.get("attribute_name") for item in covered if item.get("attribute_name")]
            params["attributes"] = list(dict.fromkeys(attrs))
        elif name == "fund_codes":
            codes = [item.get("fund_code") for item in instance_refs if item.get("fund_code")]
            if codes:
                params["fund_codes"] = list(dict.fromkeys(codes))
        elif name in instance_ref:
            params[name] = instance_ref[name]
        elif name in constraints:
            params[name] = constraints[name]
        elif name in frame:
            params[name] = frame[name]
    missing = [
        name
        for name in skill.get("input_params") or []
        if name not in params and name != "attributes"
    ]
    return params, missing


def _invocation_fact_groups(skill: dict[str, Any], covered: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    subject_types = set(skill.get("supported_subject_types") or [])
    if "FundSet" in subject_types or "fund_codes" in set(skill.get("input_params") or []):
        return [covered]
    groups: dict[str, list[dict[str, Any]]] = {}
    for fact in covered:
        subject_id = fact.get("subject", {}).get("subject_id") or "global"
        groups.setdefault(subject_id, []).append(fact)
    return list(groups.values())


def _task_graph(
    frame: dict[str, Any],
    catalog: _Catalog,
    requirements: list[dict[str, Any]],
    invocations: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    def add_node(node: dict[str, Any]) -> None:
        node.setdefault("role", _node_role(node.get("node_type", "")))
        nodes.setdefault(node["node_id"], node)

    def add_edge(source: str, target: str, relation_type: str, label_zh: str, reason_zh: str, weight: Any = None) -> None:
        edge_id = f"{source}__{relation_type}__{target}"
        edges.setdefault(
            edge_id,
            {
                "edge_id": edge_id,
                "source": source,
                "target": target,
                "relation_type": relation_type,
                "label_zh": label_zh,
                "reason_zh": reason_zh,
                **({"weight": weight} if weight is not None else {}),
            },
        )

    sf_id = "SemanticFrame:current"
    add_node({"node_id": sf_id, "node_type": "SemanticFrame", "label_zh": "当前语义框架", "description_zh": "前置意图识别节点输出的结构化语义结果。"})
    if frame.get("task_type"):
        node_id = f"TaskType:{frame['task_type']}"
        add_node({"node_id": node_id, "node_type": "TaskType", "label_zh": _task_type_zh(frame["task_type"]), "description_zh": "本次问题的通用任务类型。"})
        add_edge(sf_id, node_id, "has_task_type", "具有任务类型", "semantic_frame 显式给出 task_type。")
    if frame.get("intent"):
        profile = catalog.intent_profiles.get(frame["intent"], {})
        node_id = f"IntentProfile:{frame['intent']}"
        add_node({"node_id": node_id, "node_type": "IntentProfile", "label_zh": profile.get("intent_name_zh") or f"意图：{frame['intent']}", "description_zh": profile.get("description") or "本次问题的宽泛业务意图。"})
        add_edge(sf_id, node_id, "has_intent", "具有意图", "semantic_frame 显式给出 intent。")
    for target in _target_instances(frame, catalog):
        object_node = f"ObjectType:{target['object_type']}"
        add_node({"node_id": object_node, "node_type": "ObjectType", "label_zh": target.get("object_type_zh") or target["object_type"], "description_zh": target.get("description_zh") or "本次问题涉及的业务对象类型。"})
        add_node({"node_id": target["target_instance_id"], "node_type": "TargetInstance", "label_zh": target["display_name_zh"], "description_zh": "本次问题中的目标对象实例或对象集合。", **target})
        add_edge(sf_id, target["target_instance_id"], "has_target", "包含目标对象", "semantic_frame 的 target_objects 指定该对象。")
        add_edge(target["target_instance_id"], object_node, "has_subject", "属于对象类型", "目标对象实例对应该本体对象类型。")
    for name, value in (frame.get("constraints") or {}).items():
        node_id = f"Constraint:{name}"
        add_node({"node_id": node_id, "node_type": "Constraint", "label_zh": _constraint_label_zh(name, value), "description_zh": f"{_constraint_name_zh(name)}为 {value}。", "constraint_name": name, "constraint_value": value})
        add_edge(sf_id, node_id, "has_constraint", "包含约束", "semantic_frame 给出该约束参数。")
    for req in requirements:
        if req.get("answer_visibility") in {"hidden_dependency", "debug_only"}:
            continue
        add_node({"node_id": req["fact_requirement_id"], "node_type": "FactRequirement", "label_zh": req["label_zh"], "description_zh": req["description_zh"], **req})
        add_edge(sf_id, req["fact_requirement_id"], "requires_fact", "需要事实", req["reason_zh"])
        target_instance_id = req.get("subject", {}).get("target_instance_id")
        if target_instance_id:
            add_edge(target_instance_id, req["fact_requirement_id"], "requires_subject_fact", "主体需要事实", "该事实需求归属于这个目标对象。")
        if req.get("attribute_name"):
            attr = catalog.attributes.get(req["attribute_name"], {})
            attr_node = f"Attribute:{req['attribute_name']}"
            add_node({"node_id": attr_node, "node_type": "Attribute", "label_zh": attr.get("attribute_name_zh") or req["attribute_name"], "description_zh": attr.get("description") or "本次事实需求涉及的指标或属性。", "attribute_name": req["attribute_name"]})
            add_edge(req["fact_requirement_id"], attr_node, "has_attribute", "对应属性", "该事实需求需要查询这个属性。")
        if req.get("ranking"):
            rank_node = f"Ranking:{req['fact_requirement_id']}"
            ranking = req["ranking"]
            add_node({"node_id": rank_node, "node_type": "Ranking", "label_zh": f"排序：{ranking.get('direction', '')}", "description_zh": "集合任务中的指标排序条件。", "ranking": ranking})
            add_edge(req["fact_requirement_id"], rank_node, "uses_ranking", "使用排序条件", "该事实需求来自 ranking 规划条件。")
        if req.get("filter"):
            filter_node = f"Filter:{req['fact_requirement_id']}"
            item = req["filter"]
            add_node({"node_id": filter_node, "node_type": "Filter", "label_zh": f"筛选：{item.get('operator', '')} {item.get('value', '')}", "description_zh": "集合任务中的指标筛选条件。", "filter": item})
            add_edge(req["fact_requirement_id"], filter_node, "uses_filter", "使用筛选条件", "该事实需求来自 filters 规划条件。")
        relation_explanations = []
        if req.get("expanded_from"):
            relation_explanations.append(req["expanded_from"] | {"reason_zh": req.get("reason_zh")})
        relation_explanations.extend(req.get("relation_explanations") or [])
        for relation_explanation in relation_explanations:
            source_attr = relation_explanation.get("source_attribute")
            target_attr = relation_explanation.get("target_attribute") or req.get("attribute_name")
            if source_attr and target_attr:
                source_meta = catalog.attributes.get(source_attr, {})
                target_meta = catalog.attributes.get(target_attr, {})
                add_node({"node_id": f"Attribute:{source_attr}", "node_type": "Attribute", "label_zh": source_meta.get("attribute_name_zh") or source_attr, "description_zh": source_meta.get("description") or "关系扩展的来源属性。", "attribute_name": source_attr})
                add_node({"node_id": f"Attribute:{target_attr}", "node_type": "Attribute", "label_zh": target_meta.get("attribute_name_zh") or target_attr, "description_zh": target_meta.get("description") or "关系扩展的目标属性。", "attribute_name": target_attr})
                add_edge(
                    f"Attribute:{source_attr}",
                    f"Attribute:{target_attr}",
                    relation_explanation.get("relation_type") or "expanded_by_relation",
                    relation_explanation.get("relation_type_zh") or "本体关系扩展",
                    relation_explanation.get("reason_zh") or req["reason_zh"],
                    relation_explanation.get("weight"),
                )
                add_edge(f"Attribute:{target_attr}", req["fact_requirement_id"], "requires_expanded_fact", "形成补充事实", relation_explanation.get("reason_zh") or req["reason_zh"])
                add_edge(f"Attribute:{source_attr}", req["fact_requirement_id"], "expanded_by_relation", "由本体关系扩展", relation_explanation.get("reason_zh") or req["reason_zh"])
        if req.get("object_relation"):
            relation = req["object_relation"]
            source_node = f"ObjectType:{relation['from_object_type']}"
            target_node = f"ObjectType:{relation['to_object_type']}"
            source_meta = catalog.object_types.get(relation["from_object_type"], {})
            target_meta = catalog.object_types.get(relation["to_object_type"], {})
            add_node({"node_id": source_node, "node_type": "ObjectType", "label_zh": source_meta.get("object_name") or relation["from_object_type"], "description_zh": _object_description(source_meta)})
            add_node({"node_id": target_node, "node_type": "ObjectType", "label_zh": target_meta.get("object_name") or relation["to_object_type"], "description_zh": _object_description(target_meta)})
            add_edge(
                source_node,
                target_node,
                relation["relation_type"],
                relation.get("relation_type_zh") or _relation_type_zh(relation["relation_type"]),
                req["reason_zh"],
                relation.get("weight"),
            )
            add_edge(target_node, req["fact_requirement_id"], "provides_relation_target", "关系事实目标对象", req["reason_zh"])
    covered_by = {fr: inv for inv in invocations for fr in inv.get("covers_fact_requirements", [])}
    for invocation in invocations:
        skill_node = f"SkillCapability:{invocation['skill_id']}"
        add_node({"node_id": skill_node, "node_type": "SkillCapability", "label_zh": invocation["skill_name_zh"], "description_zh": invocation["description_zh"], "skill_id": invocation["skill_id"]})
        for fr_id in invocation.get("covers_fact_requirements") or []:
            add_edge(fr_id, skill_node, "covered_by_skill", "由该 Skill 获取", invocation["coverage_reason_zh"])
        for param in invocation.get("missing_params") or []:
            param_node = f"Parameter:{param}"
            add_node({"node_id": param_node, "node_type": "Parameter", "label_zh": f"缺失参数：{param}", "description_zh": "调用 Skill 前需要补充的结构化参数。", "param_name": param})
            add_edge(skill_node, param_node, "requires_param", "需要参数", f"调用该 Skill 还缺少参数 {param}。")
    del covered_by
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def _attribute_requirement(
    frame: dict[str, Any],
    catalog: _Catalog,
    attribute_name: str,
    priority: str,
    source: str,
    reason_zh: str,
    fact_type: str | None = None,
    subject_type: str | None = None,
    target: dict[str, Any] | None = None,
    answer_visibility: str | None = None,
    planning_role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = target or _primary_target(frame)
    return _base_requirement(
        frame=frame,
        catalog=catalog,
        fact_type=fact_type or ATTRIBUTE_FACT_TYPES.get(attribute_name, "metric_value"),
        attribute_name=attribute_name,
        subject_type=subject_type or target.get("object_type") or _primary_target(frame).get("object_type") or "Fund",
        priority=priority,
        source=source,
        reason_zh=reason_zh,
        target=target,
        answer_visibility=answer_visibility,
        planning_role=planning_role,
        extra=extra,
    )


def _base_requirement(
    frame: dict[str, Any],
    catalog: _Catalog,
    fact_type: str,
    attribute_name: str | None,
    subject_type: str,
    priority: str,
    source: str,
    reason_zh: str,
    target: dict[str, Any] | None = None,
    answer_visibility: str | None = None,
    planning_role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    constraints = dict(frame.get("constraints") or {})
    attr = catalog.attributes.get(attribute_name or "", {})
    target = target or _primary_target(frame)
    instance_ref = dict(target.get("instance_ref") or {}) if target.get("object_type") == subject_type else {}
    suffix = constraints.get("period") or frame.get("task_type") or "current"
    base = attribute_name or fact_type
    subject_key = _subject_key(subject_type, instance_ref, target.get("target_index"))
    requirement_id = f"FactRequirement:fr_{base}_{subject_key}_{suffix}".replace(" ", "_")
    label_attr = attr.get("attribute_name_zh") or attribute_name or _fact_type_zh(fact_type)
    row = {
        "fact_requirement_id": requirement_id,
        "fact_type": fact_type,
        "fact_type_zh": _fact_type_zh(fact_type),
        "subject": {
            "object_type": subject_type,
            "subject_id": _subject_id(subject_type, instance_ref, target.get("target_index")),
            "instance_ref": instance_ref,
            "label_zh": catalog.object_types.get(subject_type, {}).get("object_name") or subject_type,
            "target_index": target.get("target_index"),
            "target_role": target.get("role") or "",
            "target_instance_id": _target_instance_id(target),
        },
        "attribute_name": attribute_name,
        "attribute": (
            {
                "attribute_name": attribute_name,
                "attribute_name_zh": attr.get("attribute_name_zh") or attribute_name,
                "label_zh": attr.get("attribute_name_zh") or attribute_name,
                "description_zh": attr.get("description") or "",
            }
            if attribute_name
            else None
        ),
        "constraints": constraints,
        "priority": priority,
        "priority_zh": {"required": "必需", "supporting": "支撑上下文", "derived": "派生事实", "debug": "调试证据"}.get(priority, "可选"),
        "source": source,
        "source_zh": _source_zh(source),
        "reason_zh": reason_zh,
        "answer_visibility": answer_visibility or ("supporting_context" if priority == "supporting" else "answer_fact"),
        "planning_role": planning_role or priority,
        "label_zh": f"{label_attr}事实需求",
        "description_zh": reason_zh,
    }
    if extra:
        row.update(extra)
    return row


def _semantic_object_types(frame: dict[str, Any]) -> list[str]:
    names = [target.get("object_type") for target in frame.get("target_objects") or []]
    names.extend(query.get("target_object_type") for query in frame.get("relation_queries") or [] if isinstance(query, dict))
    for name in frame.get("mentioned_attributes") or []:
        relation_hint = RELATION_QUERY_ALIASES.get(name)
        if relation_hint:
            names.append(relation_hint["target_object_type"])
    intent = frame.get("intent")
    if intent in {"fund_profile", "profile_query"} or frame.get("task_type") == "profile":
        names.extend(["FundManager", "FundCompany", "Benchmark", "FundCategory"])
    if intent == "benchmark_comparison":
        names.append("Benchmark")
    if intent == "peer_comparison":
        names.append("FundCategory")
    if intent == "fee_analysis":
        names.append("FundFee")
    if intent == "dividend_analysis":
        names.append("Dividend")
    if intent == "holding_analysis":
        names.append("FundPosition")
    if intent == "asset_allocation_analysis":
        names.append("AssetAllocation")
    return list(dict.fromkeys([name for name in names if name]))


def _semantic_attribute_names(frame: dict[str, Any], profiles: list[dict[str, Any]] | None = None) -> list[str]:
    names: list[str] = []
    for name in frame.get("mentioned_attributes") or []:
        if name in RELATION_QUERY_ALIASES:
            mapped = RELATION_QUERY_ALIASES[name].get("attribute_name")
            if mapped and mapped in frame.get("mentioned_attributes", []):
                names.append(mapped)
            continue
        names.append(name)
    for query in frame.get("relation_queries") or []:
        if isinstance(query, dict) and query.get("attribute_name"):
            names.append(query["attribute_name"])
    names.extend(item.get("attribute") for item in frame.get("ranking") or [] if item.get("attribute"))
    names.extend(item.get("attribute") for item in frame.get("filters") or [] if item.get("attribute"))
    comparison = frame.get("comparison") if isinstance(frame.get("comparison"), dict) else {}
    names.extend(comparison.get("attributes") or [])
    scenario = INTENT_SCENARIOS.get(frame.get("intent") or "")
    if frame.get("task_type") == "profile":
        scenario = "profile"
    if scenario in SCENARIO_ATTRIBUTES:
        names.extend(SCENARIO_ATTRIBUTES[scenario])
    intent = frame.get("intent")
    if intent and profiles:
        profile = next((item for item in profiles if item.get("intent_name") == intent), None)
        if profile:
            names.extend(item.get("attribute_name") for item in profile.get("fact_requirements_template") or [] if item.get("attribute_name"))
            names.extend(profile.get("default_attributes") or [])
    return list(dict.fromkeys([name for name in names if name]))


def _semantic_frame_summary(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_type": frame.get("task_type"),
        "intent": frame.get("intent"),
        "target_objects": frame.get("target_objects") or [],
        "constraints": frame.get("constraints") or {},
        "mentioned_attributes": frame.get("mentioned_attributes") or [],
        "relation_queries": frame.get("relation_queries") or [],
        "filters": frame.get("filters") or [],
        "ranking": frame.get("ranking") or [],
        "comparison": frame.get("comparison") or {},
        "limit": frame.get("limit"),
    }


def _target_instances(frame: dict[str, Any], catalog: _Catalog) -> list[dict[str, Any]]:
    rows = []
    for index, target in enumerate(frame.get("target_objects") or [], start=1):
        object_type = target.get("object_type")
        meta = catalog.object_types.get(object_type, {})
        instance_ref = dict(target.get("instance_ref") or {})
        display = _display_target(object_type, instance_ref, target.get("role"))
        rows.append(
            {
                "target_instance_id": f"TargetInstance:{object_type}:{index}",
                "object_type": object_type,
                "object_type_zh": meta.get("object_name") or object_type,
                "instance_ref": instance_ref,
                "role": target.get("role") or "",
                "display_name_zh": display,
                "description_zh": meta.get("params", {}).get("description") if isinstance(meta.get("params"), dict) else "",
            }
        )
    return rows


def _coverage_summary(
    facts: list[dict[str, Any]],
    invocations: list[dict[str, Any]],
    warnings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    covered = {fr_id for invocation in invocations for fr_id in invocation.get("covers_fact_requirements", [])}
    required = [item for item in facts if item.get("priority") == "required"]
    optional = [item for item in facts if item.get("priority") not in {"required", "supporting", "derived"}]
    supporting = [item for item in facts if item.get("priority") == "supporting"]
    derived = [item for item in facts if item.get("priority") == "derived"]
    derived_covered_ids = _covered_derived_fact_ids(derived, facts, covered)
    covered_required = [item for item in required if item["fact_requirement_id"] in covered]
    covered_optional = [item for item in optional if item["fact_requirement_id"] in covered]
    covered_supporting = [item for item in supporting if item["fact_requirement_id"] in covered]
    covered_derived = [item for item in derived if item["fact_requirement_id"] in covered or item["fact_requirement_id"] in derived_covered_ids]
    uncovered_required = [item for item in required if item["fact_requirement_id"] not in covered]
    uncovered_optional = [item for item in optional if item["fact_requirement_id"] not in covered]
    uncovered_supporting = [item for item in supporting if item["fact_requirement_id"] not in covered]
    permission_blocked = any(item.get("warning_code") == "SKILL_PERMISSION_BLOCKED" for item in warnings or [])
    if required and len(covered_required) == len(required):
        status = "full_coverage"
    elif covered_required:
        status = "partial_coverage"
    elif permission_blocked and required:
        status = "permission_blocked"
    else:
        status = "no_coverage"
    message = {
        "full_coverage": "必需事实均有 Skill 覆盖，规划可以继续执行。",
        "partial_coverage": "部分必需事实已有 Skill 覆盖，但仍存在能力缺口。",
        "permission_blocked": "存在 Skill 权限未授权，导致事实无法覆盖。",
        "no_coverage": "当前事实需求没有可用 Skill 覆盖，需要补充 Skill 能力声明。",
    }[status]
    return {
        "required_fact_count": len(required),
        "covered_required_fact_count": len(covered_required),
        "uncovered_required_facts": [
            {"fact_requirement_id": item["fact_requirement_id"], "label_zh": item["label_zh"], "reason_zh": "当前没有可用 Skill 覆盖该必需事实。"}
            for item in uncovered_required
        ],
        "optional_fact_count": len(optional),
        "covered_optional_fact_count": len(covered_optional),
        "uncovered_optional_facts": [
            {"fact_requirement_id": item["fact_requirement_id"], "label_zh": item["label_zh"], "reason_zh": "当前没有可用 Skill 覆盖该可选补充事实。"}
            for item in uncovered_optional
        ],
        "supporting_context_count": len(supporting),
        "covered_supporting_context_count": len(covered_supporting),
        "uncovered_supporting_context": [
            {"fact_requirement_id": item["fact_requirement_id"], "label_zh": item["label_zh"], "reason_zh": "支撑上下文当前没有 Skill 覆盖。"}
            for item in uncovered_supporting
        ],
        "derived_fact_count": len(derived),
        "covered_derived_fact_count": len(covered_derived),
        "uncovered_derived_facts": [
            {"fact_requirement_id": item["fact_requirement_id"], "label_zh": item["label_zh"], "reason_zh": "派生事实缺少直接 Skill 或可支撑的基础事实。"}
            for item in derived
            if item not in covered_derived
        ],
        "skill_count": len(invocations),
        "has_permission_blocked_facts": permission_blocked,
        "coverage_status": status,
        "coverage_message_zh": message,
    }


def _missing_params(invocations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for invocation in invocations:
        if invocation.get("missing_params"):
            rows.append(
                {
                    "skill_id": invocation["skill_id"],
                    "skill_name_zh": invocation["skill_name_zh"],
                    "missing_params": invocation["missing_params"],
                    "message_zh": "调用该 Skill 前需要补充参数：" + "、".join(invocation["missing_params"]),
                }
            )
    return rows


def _covered_derived_fact_ids(derived: list[dict[str, Any]], facts: list[dict[str, Any]], covered_ids: set[str]) -> set[str]:
    result: set[str] = set()
    covered_by_subject_attr = {
        (item.get("subject", {}).get("subject_id"), item.get("attribute_name"))
        for item in facts
        if item.get("fact_requirement_id") in covered_ids and item.get("attribute_name")
    }
    for item in derived:
        attr = item.get("attribute_name")
        subjects = item.get("derived_from_subjects") or []
        if attr and subjects and all((subject_id, attr) in covered_by_subject_attr for subject_id in subjects):
            result.add(item["fact_requirement_id"])
    return result


def _planning_diagnostics(
    frame: dict[str, Any],
    catalog: _Catalog,
    facts: list[dict[str, Any]],
    invocations: list[dict[str, Any]],
    coverage: dict[str, Any],
    warnings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []

    def add(code: str, message: str, suggestion: str, severity: str = "warning") -> None:
        diagnostics.append(
            {
                "diagnostic_code": code,
                "severity": severity,
                "message_zh": message,
                "suggestion_zh": suggestion,
            }
        )

    targets = _planning_targets(frame)
    fund_targets = _targets_of_type(frame, "Fund")
    if not targets:
        add("SEMANTIC_FRAME_TARGET_MISSING", "semantic_frame 缺少目标对象。", "请在 target_objects 中补充 Fund、FundSet、FundManager 等目标对象。", "error")
    if frame.get("task_type") == "compare" and len(fund_targets) < 2 and not _fund_set_target(frame):
        add("COMPARE_TARGET_TOO_FEW", "比较任务的基金目标对象少于 2 个。", "请在 target_objects 中提供至少两只 Fund，或改用 FundSet 排序/筛选任务。", "error")
    if frame.get("task_type") in {"rank", "screen", "recommend"} and not _fund_set_target(frame):
        add("FUNDSET_TARGET_MISSING", "集合排序、筛选或推荐任务缺少 FundSet 目标对象。", "请添加 object_type=FundSet 且 role=candidate_set 的目标对象。", "error")
    for item in [*(frame.get("ranking") or []), *(frame.get("filters") or [])]:
        attr = item.get("attribute")
        if attr and attr not in catalog.attributes:
            add("UNKNOWN_CONDITION_ATTRIBUTE", f"条件中使用了本体不存在的属性：{attr}。", "请改用 attributes.yaml 中的标准属性名，或先补充属性定义。", "error")
    for query in frame.get("relation_queries") or []:
        relation_type = query.get("relation_type")
        if relation_type and relation_type not in OBJECT_RELATION_TYPES:
            add("UNKNOWN_RELATION_QUERY", f"relation_queries 中的关系不存在或暂不支持：{relation_type}。", "请改用 managed_by、issued_by、has_benchmark、belongs_to_category 等标准关系。", "error")
    if not facts:
        add("FACT_REQUIREMENTS_EMPTY", "当前语义框架没有生成任何事实需求。", "请补充明确属性、关系查询、排序/筛选条件，或配置对应 intent 模板。", "error")
    if facts and not invocations:
        add("CANDIDATE_INVOCATIONS_EMPTY", "事实需求已生成，但没有任何 Skill 能覆盖。", "请在 skills.yaml 中为相关 fact_type、subject_type 和 attribute 声明 Skill 能力。", "error")
    for item in coverage.get("uncovered_required_facts") or []:
        add("REQUIRED_FACT_UNCOVERED", f"必需事实未覆盖：{item.get('label_zh')}。", item.get("reason_zh") or "请补充对应 Skill。")
    for fact in facts:
        if fact.get("fact_type") == "relation_instance":
            covered = any(fact["fact_requirement_id"] in invocation.get("covers_fact_requirements", []) for invocation in invocations)
            if not covered and fact.get("priority") == "required":
                add("RELATION_INSTANCE_UNCOVERED", f"关系事实未覆盖：{fact.get('predicate_zh') or fact.get('predicate')}。", "请确认 get_fund_profile_facts 的 supported_relations 覆盖该关系。")
        if fact.get("subject", {}).get("object_type") == "FundSet" and fact.get("fact_type") == "metric_ranking":
            covered = any(fact["fact_requirement_id"] in invocation.get("covers_fact_requirements", []) for invocation in invocations)
            if not covered:
                add("FUNDSET_RANKING_SKILL_MISSING", "FundSet 指标排序事实没有 Skill 覆盖。", "请补充 rank_funds_by_metric 或 recommend_funds_by_risk_return 能力声明。")
        if fact.get("subject", {}).get("object_type") == "FundSet" and fact.get("fact_type") == "filter_condition":
            covered = any(fact["fact_requirement_id"] in invocation.get("covers_fact_requirements", []) for invocation in invocations)
            if not covered:
                add("FUNDSET_SCREENING_SKILL_MISSING", "FundSet 筛选条件事实没有 Skill 覆盖。", "请补充 screen_funds_by_metric_condition 或 recommend_funds_by_risk_return 能力声明。")
    if len(fund_targets) >= 2:
        fact_subjects = {fact.get("subject", {}).get("subject_id") for fact in facts}
        missing = [_target_subject_id(target) for target in fund_targets if _target_subject_id(target) not in fact_subjects]
        if missing:
            add("MULTI_TARGET_FACT_MISSING", "多主体任务中存在目标对象没有生成事实需求。", "请检查比较属性和 target_objects 是否被完整传入。", "error")
    if frame.get("intent") and frame.get("intent") not in catalog.intent_profiles and not frame.get("mentioned_attributes"):
        add("INTENT_TEMPLATE_MISSING", f"意图 {frame.get('intent')} 未配置模板且没有显式属性。", "请配置 intent_profiles.yaml 的 fact_requirements_template，或在 semantic_frame 中补充 mentioned_attributes。")
    for warning in warnings or []:
        if warning.get("warning_code") == "SKILL_PARAMS_MISSING":
            add("SKILL_PARAMS_MISSING", warning.get("message_zh") or "Skill 缺少调用参数。", "请在 semantic_frame 的 target_objects、constraints 或 options 中补充参数。")
    return diagnostics


def _relation_seed_entities(frame: dict[str, Any], requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for target in frame.get("target_objects") or []:
        if target.get("object_type"):
            rows.append({"object_type": "ObjectType", "object_id": target["object_type"]})
    for item in requirements:
        if item.get("attribute_name"):
            rows.append({"object_type": "Attribute", "object_id": item["attribute_name"]})
    return rows


def _primary_target(frame: dict[str, Any]) -> dict[str, Any]:
    targets = frame.get("target_objects") or []
    return targets[0] if targets else {}


def _planning_targets(frame: dict[str, Any]) -> list[dict[str, Any]]:
    return list(frame.get("target_objects") or [])


def _targets_of_type(frame: dict[str, Any], object_type: str) -> list[dict[str, Any]]:
    return [target for target in _planning_targets(frame) if target.get("object_type") == object_type]


def _fund_set_target(frame: dict[str, Any]) -> dict[str, Any] | None:
    return next((target for target in _planning_targets(frame) if str(target.get("object_type") or "").endswith("Set")), None)


def _synthetic_fund_set_target() -> dict[str, Any]:
    return {"object_type": "FundSet", "instance_ref": {}, "role": "candidate_set", "target_index": 0}


def _fact_targets_for_attribute(frame: dict[str, Any], attribute_name: str) -> list[dict[str, Any]]:
    del attribute_name
    if frame.get("task_type") in {"rank", "screen", "recommend"}:
        target = _fund_set_target(frame) or _synthetic_fund_set_target()
        return [target] if target else []
    funds = _targets_of_type(frame, "Fund")
    return funds or _planning_targets(frame) or [{}]


def _comparison_attributes(frame: dict[str, Any]) -> list[str]:
    comparison = frame.get("comparison") or {}
    attrs = list(comparison.get("attributes") or [])
    attrs.extend(frame.get("mentioned_attributes") or [])
    attrs.extend(item.get("attribute") for item in frame.get("ranking") or [] if item.get("attribute"))
    return list(dict.fromkeys([item for item in attrs if item and item not in RELATION_QUERY_ALIASES])) or ["return_rate"]


def _target_instance_id(target: dict[str, Any] | None) -> str:
    if not target:
        return ""
    index = target.get("target_index") or 1
    if index == 0:
        return ""
    return f"TargetInstance:{target.get('object_type')}:{index}"


def _target_subject_id(target: dict[str, Any]) -> str:
    return _subject_id(target.get("object_type") or "Fund", dict(target.get("instance_ref") or {}), target.get("target_index"))


def _target_by_subject_id(frame: dict[str, Any], subject_id: str | None) -> dict[str, Any]:
    return next((target for target in _planning_targets(frame) if _target_subject_id(target) == subject_id), _primary_target(frame))


def _subject_key(subject_type: str, instance_ref: dict[str, Any], target_index: Any = None) -> str:
    if instance_ref.get("fund_code"):
        return str(instance_ref["fund_code"])
    if instance_ref.get("fund_universe"):
        return str(instance_ref["fund_universe"])
    if target_index:
        return f"{subject_type}_{target_index}"
    return subject_type


def _has_requirement(
    rows: list[dict[str, Any]],
    fact_type: str,
    attribute_name: str | None,
    subject_type: str,
    subject_id: str | None = None,
    predicate: str | None = None,
    target_object_type: str | None = None,
) -> bool:
    return any(
        item.get("fact_type") == fact_type
        and item.get("attribute_name") == attribute_name
        and item.get("subject", {}).get("object_type") == subject_type
        and (subject_id is None or item.get("subject", {}).get("subject_id") == subject_id)
        and (predicate is None or item.get("predicate") == predicate)
        and (target_object_type is None or item.get("target_object_type") == target_object_type)
        for item in rows
    )


def _find_requirement(
    rows: list[dict[str, Any]], fact_type: str | None, attribute_name: str | None, subject_id: str
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in rows
            if item.get("fact_type") == fact_type
            and item.get("attribute_name") == attribute_name
            and item.get("subject", {}).get("subject_id") == subject_id
        ),
        None,
    )


def _dedupe_requirements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, Any, Any, Any, Any], dict[str, Any]] = {}
    for item in rows:
        key = (
            item.get("fact_type"),
            item.get("attribute_name"),
            item.get("subject", {}).get("subject_id"),
            item.get("predicate"),
            item.get("target_object_type"),
        )
        existing = deduped.get(key)
        if existing and existing.get("priority") == "required":
            continue
        deduped[key] = item
    return list(deduped.values())


def _split_node_id(value: Any) -> tuple[str, str]:
    text = str(value or "")
    if ":" not in text:
        return "", text
    return tuple(text.split(":", 1))  # type: ignore[return-value]


def _edge_properties(edge: dict[str, Any]) -> dict[str, Any]:
    properties = dict(edge)
    nested = edge.get("properties")
    if isinstance(nested, dict):
        properties.update(nested)
    return properties


def _relation_expansion_sort_key(edge: dict[str, Any]) -> tuple[int, float, str]:
    from_type, _ = _split_node_id(edge.get("from"))
    relation_type = str(edge.get("relation_type") or "")
    phase = 0 if from_type == "Attribute" and relation_type in SEMANTIC_EXPANSION_TYPES else 1
    return (phase, -float(edge.get("score") or 0), str(edge.get("edge_id") or ""))


def _edge_applicable(edge: dict[str, Any], frame: dict[str, Any], requirements: list[dict[str, Any]]) -> bool:
    properties = _edge_properties(edge)
    tasks = properties.get("applicable_tasks") or []
    intents = properties.get("applicable_intents") or []
    trigger_policy = properties.get("trigger_policy") if isinstance(properties.get("trigger_policy"), dict) else {}
    if trigger_policy:
        tasks = trigger_policy.get("tasks") or tasks
        intents = trigger_policy.get("intents") or intents
    if tasks and frame.get("task_type") not in tasks:
        return False
    if intents and frame.get("intent") and frame.get("intent") not in intents:
        return False
    if trigger_policy and not _trigger_policy_matches(properties, frame, _split_node_id(edge.get("from"))[1], requirements):
        return False
    return True


def _relation_usable_in_task_graph(relation_type: str) -> bool:
    return relation_type in TASK_GRAPH_RELATION_TYPES


def _trigger_policy_matches(
    properties: dict[str, Any],
    frame: dict[str, Any],
    source_id: str,
    requirements: list[dict[str, Any]],
) -> bool:
    policy = properties.get("trigger_policy") if isinstance(properties.get("trigger_policy"), dict) else {}
    if not policy:
        return True
    mentioned = set(frame.get("mentioned_attributes") or [])
    requirement_attrs = {item.get("attribute_name") for item in requirements if item.get("attribute_name")}
    requirement_fact_types = {item.get("fact_type") for item in requirements if item.get("fact_type")}
    source_attributes = set(policy.get("source_attributes") or [])
    if source_attributes and source_id not in source_attributes and not (source_attributes & mentioned) and not (source_attributes & requirement_attrs):
        return False
    source_fact_types = set(policy.get("source_fact_types") or [])
    if source_fact_types and source_id in source_attributes:
        source_req = next((item for item in requirements if item.get("attribute_name") == source_id), None)
        if source_req and source_req.get("fact_type") not in source_fact_types:
            return False
    required_fact_types = set(policy.get("requires_existing_fact_types") or [])
    if required_fact_types and not (required_fact_types & requirement_fact_types):
        return False
    if policy.get("requires_explicit_attribute"):
        explicit_attrs = set(policy.get("explicit_attributes") or source_attributes)
        if not (explicit_attrs & mentioned):
            return False
    if policy.get("requires_relation_query"):
        relations = {
            item.get("relation_type")
            for item in frame.get("relation_queries") or []
            if isinstance(item, dict)
        }
        explicit_attrs = set(policy.get("explicit_attributes") or source_attributes)
        if properties.get("relation_type") not in relations and not (explicit_attrs & mentioned):
            return False
    return True


def _explicit_relation_triggered(properties: dict[str, Any], frame: dict[str, Any], relation_type: str) -> bool:
    policy = properties.get("trigger_policy") if isinstance(properties.get("trigger_policy"), dict) else {}
    mentioned = set(frame.get("mentioned_attributes") or [])
    explicit_attrs = set(policy.get("explicit_attributes") or policy.get("source_attributes") or [])
    relation_queries = {
        item.get("relation_type")
        for item in frame.get("relation_queries") or []
        if isinstance(item, dict)
    }
    if relation_type in relation_queries:
        return True
    if explicit_attrs and explicit_attrs & mentioned:
        return True
    alias = next((item for item in RELATION_QUERY_ALIASES.values() if item["relation_type"] == relation_type), None)
    if alias and alias.get("attribute_name") in mentioned:
        return True
    intents = set(policy.get("intents") or [])
    return bool(frame.get("intent") and frame.get("intent") in intents and frame.get("task_type") in {"query", "explain"})


def _max_per_source(properties: dict[str, Any]) -> int:
    limits = properties.get("expansion_limits") if isinstance(properties.get("expansion_limits"), dict) else {}
    raw = limits.get("max_per_source_attribute", MAX_OPTIONAL_EXPANSIONS_PER_REQUIRED_FACT)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return MAX_OPTIONAL_EXPANSIONS_PER_REQUIRED_FACT


def _edge_evidence(edge: dict[str, Any], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge_id": edge.get("edge_id") or f"{edge.get('from')}__{edge.get('relation_type')}__{edge.get('to')}",
        "from": edge.get("from"),
        "to": edge.get("to"),
        "relation_type": edge.get("relation_type"),
        "planning_role": properties.get("planning_role"),
        "auto_expand_mode": properties.get("auto_expand_mode"),
        "answer_visibility": properties.get("answer_visibility"),
        "reason_zh": properties.get("reason_zh") or "",
    }


def _relation_reason(relation_type: str, source_attr: str, target_attr: str, catalog: _Catalog) -> str:
    source = catalog.attributes.get(source_attr, {}).get("attribute_name_zh") or source_attr
    target = catalog.attributes.get(target_attr, {}).get("attribute_name_zh") or target_attr
    return f"本体关系 {_relation_type_zh(relation_type)} 表明分析{source}时通常需要补充{target}。"


def _relation_type_zh(relation_type: str) -> str:
    mapping = {
        "compared_with": "对比指标",
        "derives": "派生解释",
        "ranked_by_peer": "扩展为同类排名",
        "risk_companion": "风险伴随指标",
        "return_companion": "收益伴随指标",
        "benchmark_metric_of": "基准相关指标",
        "peer_metric_of": "同类比较相关指标",
        "managed_by": "管理关系",
        "issued_by": "基金公司发行或管理",
        "managed_by_company": "基金公司管理",
        "has_benchmark": "基准关系",
        "tracks_index": "跟踪指数",
        "belongs_to_category": "分类关系",
        "has_dividend": "分红关系",
        "has_fee": "费率关系",
        "has_asset_allocation": "资产配置关系",
        "has_position": "持仓关系",
        "holds_asset": "持有资产关系",
    }
    return mapping.get(relation_type, relation_type)


def _explicit_relation_reason(relation_type: str, target_object_type: str) -> str:
    target_zh = {
        "FundManager": "基金经理",
        "FundCompany": "基金公司",
        "Benchmark": "业绩比较基准",
        "FundCategory": "基金分类",
        "Index": "指数",
    }.get(target_object_type, target_object_type)
    return f"用户需要查询基金与{target_zh}之间的{_relation_type_zh(relation_type)}。"


def _coverage_reason(skill: dict[str, Any], covered: list[dict[str, Any]]) -> str:
    attrs = [item.get("attribute", {}).get("attribute_name_zh") or item.get("attribute_name") for item in covered if item.get("attribute_name")]
    relations = [item.get("predicate_zh") for item in covered if item.get("fact_type") == "relation_instance"]
    subject_types = sorted({item.get("subject", {}).get("object_type") for item in covered if item.get("subject")})
    attr_text = "、".join([item for item in [*attrs, *relations] if item]) or "相关事实"
    return f"该 Skill 声明支持 {', '.join(subject_types)} 的 {attr_text} 查询，并且 fact_type 与事实需求匹配。"


def _coverage_score(covered: list[dict[str, Any]], facts: list[dict[str, Any]]) -> float:
    if not facts:
        return 0.0
    score = 0.0
    total = 0.0
    covered_ids = {item["fact_requirement_id"] for item in covered}
    for fact in facts:
        weight = 2.0 if fact.get("priority") == "required" else 1.0
        total += weight
        if fact["fact_requirement_id"] in covered_ids:
            score += weight
    return round(score / total, 3) if total else 0.0


def _display_target(object_type: str, instance_ref: dict[str, Any], role: Any) -> str:
    if instance_ref.get("fund_code"):
        return f"基金 {instance_ref['fund_code']}"
    if instance_ref.get("fund_universe"):
        return f"基金集合 {instance_ref['fund_universe']}"
    return f"{object_type} 目标对象" + (f"（{role}）" if role else "")


def _fact_type_zh(fact_type: str) -> str:
    mapping = {
        "metric_value": "指标值",
        "benchmark_metric_value": "基准指标值",
        "excess_metric_value": "超额指标值",
        "peer_rank": "同类排名",
        "peer_average": "同类平均",
        "entity_set": "候选对象集合",
        "metric_ranking": "指标排序",
        "filter_condition": "筛选条件",
        "relation_instance": "关系事实",
        "object_profile": "对象基础事实",
        "comparison_result": "比较结果",
        "holding_fact": "持仓事实",
        "allocation_fact": "配置事实",
        "fee_fact": "费率事实",
        "dividend_fact": "分红事实",
        "document_fact": "文档事实",
    }
    return mapping.get(fact_type, fact_type)


def _source_zh(source: str) -> str:
    mapping = {
        "explicit_attribute": "显式属性",
        "intent_template": "意图模板",
        "operation_rule": "操作规则",
        "relation_expansion": "本体关系扩展",
        "explicit_relation": "显式关系查询",
        "scenario_rule": "场景规划规则",
    }
    return mapping.get(source, source)


def _subject_id(subject_type: str, instance_ref: dict[str, Any], target_index: Any = None) -> str:
    if instance_ref.get("fund_code"):
        return f"{subject_type}:{instance_ref['fund_code']}"
    if instance_ref.get("fund_universe"):
        return f"{subject_type}:{instance_ref['fund_universe']}"
    if target_index:
        return f"{subject_type}:{target_index}"
    return subject_type


def _task_type_zh(task_type: str) -> str:
    mapping = {
        "query": "查询任务",
        "analyze": "分析任务",
        "compare": "比较任务",
        "rank": "排序任务",
        "screen": "筛选任务",
        "recommend": "推荐任务",
        "explain": "解释任务",
        "profile": "画像任务",
        "summarize": "总结任务",
    }
    return mapping.get(task_type, "业务任务")


def _constraint_name_zh(name: str) -> str:
    mapping = {
        "period": "时间周期",
        "report_date": "报告日期",
        "as_of_date": "数据日期",
    }
    return mapping.get(name, "约束条件")


def _constraint_label_zh(name: str, value: Any) -> str:
    return f"{_constraint_name_zh(name)}：{value}"


def _node_role(node_type: str) -> str:
    mapping = {
        "SemanticFrame": "input_context",
        "TaskType": "task_control",
        "IntentProfile": "intent_context",
        "TargetInstance": "subject",
        "ObjectType": "ontology_object",
        "Constraint": "constraint",
        "FactRequirement": "fact_requirement",
        "Attribute": "fact_attribute",
        "Ranking": "ranking_condition",
        "Filter": "filter_condition",
        "SkillCapability": "skill_candidate",
        "Parameter": "missing_param",
    }
    return mapping.get(node_type, "task_context")


def _object_description(meta: dict[str, Any]) -> str:
    params = meta.get("params")
    if isinstance(params, dict) and params.get("description"):
        return str(params["description"])
    return "本次任务涉及的业务对象类型。"
