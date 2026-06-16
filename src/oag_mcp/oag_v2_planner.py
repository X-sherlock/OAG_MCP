from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from oag_mcp.llm_config import LLMConfig, load_llm_config
from oag_mcp.repositories import GraphRepository, OntologyRepository


DOMAIN = "finance_market"
METRIC_PERIOD_FACT_TYPES = {
    "metric_value",
    "benchmark_metric_value",
    "excess_metric_value",
    "peer_rank",
    "peer_average",
    "metric_ranking",
    "filter_condition",
    "comparison_result",
}
BENCHMARK_DEPENDENCY_ATTRIBUTES = {
    "benchmark_return",
    "excess_return",
    "tracking_error",
    "information_ratio",
}
PEER_DEPENDENCY_FACT_TYPES = {"peer_rank", "peer_average"}
PROFILE_ATTRIBUTE_RELATIONS = {
    "fund_manager": ("managed_by", "FundManager"),
    "manager_name": ("managed_by", "FundManager"),
    "manager_id": ("managed_by", "FundManager"),
    "fund_company": ("issued_by", "FundCompany"),
    "company_name": ("issued_by", "FundCompany"),
    "company_code": ("issued_by", "FundCompany"),
    "benchmark_name": ("has_benchmark", "Benchmark"),
    "fund_type": ("belongs_to_category", "FundCategory"),
    "tracking_index_name": ("tracks_index", "Index"),
    "tracking_index_code": ("tracks_index", "Index"),
}
FACT_TYPE_BY_ATTRIBUTE = {
    "benchmark_return": "benchmark_metric_value",
    "tracking_error": "benchmark_metric_value",
    "information_ratio": "benchmark_metric_value",
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
    "company_code": "object_profile",
    "manager_name": "object_profile",
    "manager_id": "object_profile",
    "benchmark_name": "object_profile",
    "tracking_index_name": "object_profile",
    "tracking_index_code": "object_profile",
    "fee_type": "fee_fact",
    "fee_value": "fee_fact",
    "fee_effective_date": "fee_fact",
    "dividend_per_share": "dividend_fact",
    "dividend_date": "dividend_fact",
    "stock_name": "holding_fact",
    "stock_nav_ratio": "holding_fact",
    "bond_name": "holding_fact",
    "bond_nav_ratio": "holding_fact",
    "asset_total_value": "allocation_fact",
    "asset_net_value": "allocation_fact",
    "stock_asset_ratio": "allocation_fact",
    "bond_asset_ratio": "allocation_fact",
    "cash_asset_ratio": "allocation_fact",
}
TASK_TYPE_LABELS = {
    "query": "查询",
    "analyze": "分析",
    "compare": "比较",
    "rank": "排序",
    "screen": "筛选",
    "recommend": "推荐",
    "profile": "画像",
}


@dataclass
class OAGV2Planner:
    ontology_repository: OntologyRepository
    graph_repository: GraphRepository
    domain: str = DOMAIN
    intent_profiles: list[dict[str, Any]] | None = None
    skills: list[dict[str, Any]] | None = None
    llm_config: LLMConfig | None = None

    def plan(
        self,
        semantic_frame: dict[str, Any] | None,
        recognized_intents: list[dict[str, Any]] | None = None,
        raw_question: str | None = None,
        selector_mode: str = "rule",
        planning_options: dict[str, Any] | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        planning_options = planning_options or {}
        user_context = user_context or {}
        if not semantic_frame:
            return _semantic_frame_required_response(self.domain)
        if not isinstance(semantic_frame, dict):
            return _error_response(
                domain=self.domain,
                raw_question=raw_question or "",
                error_code="SEMANTIC_FRAME_INVALID",
                message_zh="semantic_frame 必须是对象结构。",
            )

        frame = _normalize_frame(semantic_frame, raw_question, recognized_intents)
        domain = frame.get("domain") or self.domain
        self._ensure_ready(domain)
        profiles = self.intent_profiles or self.ontology_repository.get_intent_profiles(domain)
        skills = self.skills or self.ontology_repository.get_skill_capabilities(domain)
        llm_config = self.llm_config or load_llm_config()
        catalog = _Catalog.from_repositories(self.ontology_repository, domain, frame, profiles, skills)
        ontology_subgraph = self._build_ontology_subgraph(domain, frame, catalog)
        candidate_fact_pool = _build_candidate_fact_pool(frame, catalog, ontology_subgraph)
        if not candidate_fact_pool:
            return _need_clarification_response(domain, frame, llm_config)

        selector = _FactSelector(llm_config=llm_config)
        selection = selector.select(
            mode=selector_mode,
            frame=frame,
            candidate_fact_pool=candidate_fact_pool,
            planning_options=planning_options,
        )
        if selection.get("status") == "error":
            return _selector_error_response(domain, frame, llm_config, ontology_subgraph, candidate_fact_pool, selection)

        validation = _validate_selection(selection["selected_facts"], candidate_fact_pool, planning_options)
        selected_facts = validation["selected_facts"]
        dependency_completion = _complete_dependencies(selected_facts, candidate_fact_pool)
        executable_facts = _dedupe_facts([*selected_facts, *dependency_completion["completed_facts"]])
        _decorate_facts(executable_facts, frame)
        skill_bindings = _bind_skills(executable_facts, catalog.skills, frame, user_context)
        validation = _validate_bindings(validation, executable_facts, skill_bindings)
        coverage_summary = _coverage_summary(executable_facts, skill_bindings, validation)
        diagnostics = _diagnostics(validation, coverage_summary, selection, dependency_completion, frame)
        missing_params = _missing_params(skill_bindings)
        status = "success"
        if validation["illegal_fact_ids"]:
            status = "error"
        elif missing_params and not skill_bindings:
            status = "need_clarification"

        plan = {
            "status": status,
            "oag_version": "v2",
            "domain": domain,
            "raw_question": frame.get("raw_question") or "",
            "selector_mode": selector_mode,
            "recognized_intents": frame.get("recognized_intents") or [],
            "semantic_frame_summary": _semantic_frame_summary(frame),
            "normalized_semantic_frame": frame,
            "llm_config_status": llm_config.status(),
            "ontology_subgraph": ontology_subgraph,
            "candidate_fact_pool": candidate_fact_pool,
            "selected_facts": selected_facts,
            "selection_trace": selection,
            "validation_result": validation,
            "dependency_completion": dependency_completion,
            "skill_bindings": skill_bindings,
            "agent_plan": _agent_plan(frame, executable_facts, skill_bindings, validation, coverage_summary),
            "editor_plan": _editor_plan(frame, ontology_subgraph, candidate_fact_pool, selected_facts, validation, dependency_completion, skill_bindings),
            "target_instances": _target_instances(frame),
            "fact_requirements": executable_facts,
            "candidate_invocations": skill_bindings,
            "task_graph": _task_graph(frame, ontology_subgraph, executable_facts, skill_bindings),
            "coverage_summary": coverage_summary,
            "missing_params": missing_params,
            "uncovered_facts": coverage_summary["uncovered_required_facts"],
            "diagnostics": diagnostics,
            "warnings": [*validation["warnings"], *_semantic_warnings(frame, catalog)],
        }
        if user_context.get("debug") or frame.get("debug"):
            plan["debug_evidence"] = {
                "message_zh": "OAG V2 调试证据用于追踪候选池、选择、依赖补全和 Skill 绑定。",
                "candidate_fact_count": len(candidate_fact_pool),
                "selected_fact_count": len(selected_facts),
                "dependency_fact_count": len(dependency_completion.get("completed_facts") or []),
                "skill_binding_count": len(skill_bindings),
            }
        return plan

    def _ensure_ready(self, domain: str) -> None:
        if domain != self.domain:
            raise ValueError(f"Unsupported domain: {domain}")
        self.ontology_repository.ping()
        self.graph_repository.ping()
        if not self.ontology_repository.domain_enabled(domain):
            raise ValueError(f"Domain is not enabled: {domain}")

    def _build_ontology_subgraph(self, domain: str, frame: dict[str, Any], catalog: "_Catalog") -> dict[str, Any]:
        entities = [{"object_type": "ObjectType", "object_id": item.get("object_type")} for item in frame.get("target_objects") or []]
        entities.extend({"object_type": "Attribute", "object_id": name} for name in catalog.attributes)
        try:
            raw_edges = self.graph_repository.recall_relations(domain, entities, max_hops=1, top_k=1000)
        except Exception:
            raw_edges = []
        nodes: dict[str, dict[str, Any]] = {}
        for target in frame.get("target_objects") or []:
            node_id = f"ObjectType:{target.get('object_type')}"
            nodes[node_id] = {"node_id": node_id, "node_type": "ObjectType", "label_zh": target.get("object_type"), "source": "semantic_frame"}
        for name, attr in catalog.attributes.items():
            node_id = f"Attribute:{name}"
            nodes[node_id] = {
                "node_id": node_id,
                "node_type": "Attribute",
                "label_zh": attr.get("attribute_name_zh") or name,
                "attribute_name": name,
                "source": "attribute_catalog",
            }
        for skill in catalog.skills:
            node_id = f"SkillCapability:{skill.get('skill_id')}"
            nodes[node_id] = {
                "node_id": node_id,
                "node_type": "SkillCapability",
                "label_zh": skill.get("skill_name") or skill.get("skill_id"),
                "source": "skill_catalog",
            }
        edges = [
            edge
            for edge in (_normalize_edge(edge) for edge in raw_edges)
            if edge
            and "DataTable:" not in json.dumps(edge, ensure_ascii=False)
            and "DataField:" not in json.dumps(edge, ensure_ascii=False)
            and "QueryCapability:" not in json.dumps(edge, ensure_ascii=False)
        ]
        return {
            "nodes": list(nodes.values()),
            "edges": [edge for edge in edges if edge],
            "summary": {
                "node_count": len(nodes),
                "edge_count": len([edge for edge in edges if edge]),
                "message_zh": "本体子图用于解释候选事实来源，不再直接决定最终事实选择。",
            },
        }


@dataclass
class _Catalog:
    object_types: dict[str, dict[str, Any]]
    attributes: dict[str, dict[str, Any]]
    intent_profiles: dict[str, dict[str, Any]]
    skills: list[dict[str, Any]]

    @classmethod
    def from_repositories(
        cls,
        repository: OntologyRepository,
        domain: str,
        frame: dict[str, Any],
        profiles: list[dict[str, Any]],
        skills: list[dict[str, Any]],
    ) -> "_Catalog":
        object_ids = _unique(target.get("object_type") for target in frame.get("target_objects") or [])
        attr_names = _semantic_attribute_names(frame, profiles)
        return cls(
            object_types={item["object_id"]: item for item in repository.get_objects_by_ids(domain, object_ids) if item.get("object_id")},
            attributes={item["attribute_name"]: item for item in repository.get_attributes_by_names(domain, attr_names) if item.get("attribute_name")},
            intent_profiles={item["intent_name"]: item for item in profiles if item.get("intent_name")},
            skills=[item for item in skills if item.get("enabled", True)],
        )


class _FactSelector:
    def __init__(self, llm_config: LLMConfig) -> None:
        self.llm_config = llm_config

    def select(
        self,
        mode: str,
        frame: dict[str, Any],
        candidate_fact_pool: list[dict[str, Any]],
        planning_options: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = str(mode or "rule").lower()
        if normalized == "rule":
            return _rule_select(candidate_fact_pool, planning_options)
        if normalized == "mock":
            ids = planning_options.get("selected_fact_ids") or []
            return _selection_from_ids(ids, candidate_fact_pool, "mock_selector")
        if normalized == "llm":
            if not self.llm_config.enabled:
                return _selector_error("LLM_DISABLED", "LLM selector 已禁用，请使用 rule selector 或启用 OAG_LLM_ENABLED。")
            if not self.llm_config.api_key:
                return _selector_error("LLM_API_KEY_MISSING", "缺少 OAG_LLM_API_KEY，无法调用通义百炼 LLM selector。")
            return self._llm_select(frame, candidate_fact_pool, planning_options)
        return _selector_error("SELECTOR_MODE_UNSUPPORTED", f"不支持的 selector_mode：{mode}")

    def _llm_select(self, frame: dict[str, Any], candidate_fact_pool: list[dict[str, Any]], planning_options: dict[str, Any]) -> dict[str, Any]:
        allowed = [
            {
                "fact_id": item["fact_id"],
                "fact_type": item["fact_type"],
                "attribute_name": item.get("attribute_name"),
                "priority": item.get("priority"),
                "reason_zh": item.get("reason_zh"),
            }
            for item in candidate_fact_pool
        ]
        prompt = {
            "instruction": "你只能从 candidate_fact_pool 中选择已有 fact_id 并排序，不能创造属性、关系、fact_id 或 Skill。",
            "raw_question": frame.get("raw_question"),
            "semantic_frame": frame,
            "candidate_fact_pool": allowed,
            "output_schema": {"selected_fact_ids": ["fact_id"], "reasons": [{"fact_id": "fact_id", "reason_zh": "选择理由"}]},
        }
        payload = {
            "model": self.llm_config.model,
            "temperature": self.llm_config.temperature,
            "messages": [
                {"role": "system", "content": "你是 OAG V2 的候选事实选择器，只能返回 JSON。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            request = urllib.request.Request(
                self.llm_config.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.llm_config.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.llm_config.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            return _selector_error("LLM_SELECTOR_CALL_FAILED", f"LLM selector 调用失败：{exc}")
        content = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "{}")
        try:
            parsed = json.loads(content)
        except ValueError:
            return _selector_error("LLM_SELECTOR_INVALID_JSON", "LLM selector 未返回合法 JSON。")
        return _selection_from_ids(parsed.get("selected_fact_ids") or [], candidate_fact_pool, "llm_selector", parsed.get("reasons") or [])


def _normalize_frame(
    frame: dict[str, Any],
    raw_question: str | None,
    recognized_intents: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized = dict(frame)
    normalized["domain"] = str(normalized.get("domain") or DOMAIN)
    normalized["raw_question"] = raw_question or normalized.get("raw_question") or normalized.get("question") or ""
    if not normalized.get("target_objects"):
        fund_codes = re.findall(r"(?<!\d)(\d{6})(?!\d)", normalized["raw_question"])
        normalized["target_objects"] = [
            {"object_type": "Fund", "instance_ref": {"fund_code": code}, "role": "analysis_subject"}
            for code in fund_codes[:2]
        ]
    normalized["target_objects"] = [dict(item, target_index=index) for index, item in enumerate(normalized.get("target_objects") or [])]
    normalized["constraints"] = dict(normalized.get("constraints") or {})
    normalized["mentioned_attributes"] = _unique(normalized.get("mentioned_attributes") or [])
    intents = list(recognized_intents or normalized.get("recognized_intents") or [])
    if normalized.get("intent") and not intents:
        intents = [{"intent_name": normalized.get("intent"), "confidence": 1.0, "source": "semantic_frame.intent"}]
    normalized["recognized_intents"] = [_normalize_intent(item) for item in intents]
    return normalized


def _normalize_intent(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"intent_name": item, "confidence": 1.0}
    if isinstance(item, dict):
        name = item.get("intent_name") or item.get("intent") or item.get("name")
        return {**item, "intent_name": name}
    return {"intent_name": str(item), "confidence": 0.0}


def _semantic_attribute_names(frame: dict[str, Any], profiles: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    names.extend(frame.get("mentioned_attributes") or [])
    names.extend(item.get("attribute") for item in frame.get("ranking") or [])
    names.extend(item.get("attribute") for item in frame.get("filters") or [])
    comparison = frame.get("comparison") or {}
    names.extend(comparison.get("attributes") or [])
    profile_by_name = {item.get("intent_name"): item for item in profiles}
    for intent in frame.get("recognized_intents") or []:
        profile = profile_by_name.get(intent.get("intent_name")) or {}
        for template in profile.get("fact_requirements_template") or []:
            names.append(template.get("attribute_name"))
        names.extend(profile.get("default_attributes") or [])
    if not names and frame.get("intent"):
        profile = profile_by_name.get(frame.get("intent")) or {}
        names.extend(profile.get("default_attributes") or [])
    return _unique(name for name in names if name)


def _build_candidate_fact_pool(frame: dict[str, Any], catalog: _Catalog, ontology_subgraph: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mentioned = set(frame.get("mentioned_attributes") or [])
    profile_by_name = catalog.intent_profiles
    targets = frame.get("target_objects") or []
    if not targets:
        targets = [{"object_type": "Fund", "instance_ref": {}, "role": "analysis_subject", "target_index": 0}]
    intents = frame.get("recognized_intents") or []
    templates: list[dict[str, Any]] = []
    if not frame.get("mentioned_attributes"):
        for intent in intents:
            profile = profile_by_name.get(intent.get("intent_name")) or {}
            for template in profile.get("fact_requirements_template") or []:
                templates.append({**template, "source_intent": intent.get("intent_name")})
            existing_attrs = {item.get("attribute_name") for item in templates}
            for attr in profile.get("default_attributes") or []:
                if attr not in existing_attrs:
                    templates.append(
                        {
                            "attribute_name": attr,
                            "fact_type": _fact_type_for_attribute(attr),
                            "priority": "required",
                            "reason_zh": "意图默认属性生成候选事实。",
                            "source_intent": intent.get("intent_name"),
                        }
                    )
    if not templates:
        templates = [
            {"attribute_name": name, "fact_type": _fact_type_for_attribute(name), "priority": "required", "source_intent": "mentioned_attributes"}
            for name in frame.get("mentioned_attributes") or []
        ]
    for attr in _unique(frame.get("mentioned_attributes") or []):
        if not any(item.get("attribute_name") == attr for item in templates):
            templates.insert(0, {"attribute_name": attr, "fact_type": _fact_type_for_attribute(attr), "priority": "required", "source_intent": "mentioned_attributes"})
    if frame.get("mentioned_attributes"):
        for intent in intents:
            profile = profile_by_name.get(intent.get("intent_name")) or {}
            existing_attrs = {item.get("attribute_name") for item in templates}
            for attr in profile.get("default_attributes") or []:
                if attr in {"benchmark_return", "excess_return"} and "return_rate" in set(frame.get("mentioned_attributes") or []) and frame.get("task_type") != "screen":
                    continue
                if intent.get("intent_name") == "risk_overview" and attr not in {"volatility", "calmar_ratio", "peer_drawdown_rank", "peer_sharpe_rank"}:
                    continue
                if attr not in existing_attrs:
                    templates.append(
                        {
                            "attribute_name": attr,
                            "fact_type": _fact_type_for_attribute(attr),
                            "priority": "optional",
                            "reason_zh": "意图默认属性作为可选候选事实。",
                            "source_intent": intent.get("intent_name"),
                        }
                    )
    if "return_rate" in set(frame.get("mentioned_attributes") or []) and frame.get("task_type") != "screen":
        for attr, fact_type in (("benchmark_return", "benchmark_metric_value"), ("excess_return", "excess_metric_value")):
            if not any(item.get("attribute_name") == attr for item in templates):
                templates.append(
                    {
                        "attribute_name": attr,
                        "fact_type": fact_type,
                        "priority": "optional",
                        "source_intent": "relation_expansion",
                        "source_override": "relation_expansion",
                        "expanded_from": {"source_attribute": "return_rate", "relation_type": "compared_with"},
                        "reason_zh": "收益率分析可通过受控关系扩展补充基准和超额收益。",
                    }
                )
    for target in _targets_for_templates(frame, targets):
        for template in templates:
            attr = template.get("attribute_name")
            fact_type = template.get("fact_type") or _fact_type_for_attribute(attr)
            if not attr and fact_type not in {"entity_set"}:
                continue
            rows.append(_candidate_fact(frame, target, template, catalog, attr, fact_type, mentioned, ontology_subgraph))
    rows.extend(_operation_candidates(frame, catalog, mentioned))
    rows.extend(_explicit_relation_candidates(frame, targets, catalog))
    return _dedupe_facts(rows)


def _candidate_fact(
    frame: dict[str, Any],
    target: dict[str, Any],
    template: dict[str, Any],
    catalog: _Catalog,
    attr: str,
    fact_type: str,
    mentioned: set[str],
    ontology_subgraph: dict[str, Any],
) -> dict[str, Any]:
    attr_meta = catalog.attributes.get(attr, {})
    priority = "required" if attr in mentioned else template.get("priority") or "optional"
    source = template.get("source_override") or ("explicit_attribute" if attr in mentioned else f"recognized_intent:{template.get('source_intent') or frame.get('intent') or ''}")
    fact_id = _fact_id(target, fact_type, attr or template.get("predicate") or "fact")
    return {
        "fact_id": fact_id,
        "fact_requirement_id": fact_id,
        "fact_type": fact_type,
        "fact_type_zh": _fact_type_zh(fact_type),
        "subject": _subject(target),
        "predicate": template.get("predicate") or _predicate_for_fact_type(fact_type),
        "attribute_name": attr,
        "attribute": {
            "attribute_name": attr,
            "attribute_name_zh": attr_meta.get("attribute_name_zh") or attr,
            "object_type": attr_meta.get("object_type") or (attr_meta.get("object_types") or [""])[0],
        },
        "target_object_type": template.get("target_object_type"),
        "constraints": _fact_constraints(frame, fact_type),
        "priority": priority,
        "selection_priority": 100 if attr in mentioned else (80 if priority == "required" else 40),
        "source": source,
        **({"expanded_from": template.get("expanded_from")} if template.get("expanded_from") else {}),
        "reason_zh": template.get("reason_zh") or ("用户显式提到该属性。" if attr in mentioned else "前置意图识别命中该候选事实。"),
        "trace": {"ontology_subgraph_node_count": len(ontology_subgraph.get("nodes") or [])},
        "label_zh": _fact_label_zh(fact_type, attr_meta.get("attribute_name_zh") or attr, target),
    }


def _operation_candidates(frame: dict[str, Any], catalog: _Catalog, mentioned: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    task_type = frame.get("task_type")
    fundset = _fundset_target(frame)
    if task_type in {"recommend"}:
        rows.append(
            {
                "fact_id": _fact_id(fundset, "entity_set", "candidate_funds"),
                "fact_requirement_id": _fact_id(fundset, "entity_set", "candidate_funds"),
                "fact_type": "entity_set",
                "fact_type_zh": "候选集合",
                "subject": _subject(fundset),
                "predicate": "has_entity_set",
                "attribute_name": "candidate_funds",
                "attribute": {"attribute_name": "candidate_funds", "attribute_name_zh": "候选基金集合", "object_type": "FundSet"},
                "constraints": dict(frame.get("constraints") or {}),
                "priority": "required",
                "selection_priority": 90,
                "source": "operation_requirement",
                "reason_zh": "推荐任务需要先形成候选基金集合事实。",
                "label_zh": "候选基金集合",
            }
        )
    for item in frame.get("ranking") or []:
        attr = item.get("attribute")
        if not attr:
            continue
        rows.append(_candidate_fact(frame, fundset, {"attribute_name": attr, "fact_type": "metric_ranking", "priority": "required", "reason_zh": "排序任务需要该指标的排序事实。"}, catalog, attr, "metric_ranking", mentioned, {}))
    for item in frame.get("filters") or []:
        attr = item.get("attribute")
        if not attr:
            continue
        rows.append(_candidate_fact(frame, fundset, {"attribute_name": attr, "fact_type": "filter_condition", "priority": "required", "reason_zh": "筛选任务需要该指标的过滤条件事实。"}, catalog, attr, "filter_condition", mentioned, {}))
    if task_type == "compare" and len(_targets_of_type(frame, "Fund")) > 1:
        attrs = (frame.get("comparison") or {}).get("attributes") or frame.get("mentioned_attributes") or ["return_rate"]
        for attr in attrs:
            rows.append(_candidate_fact(frame, _targets_of_type(frame, "Fund")[0], {"attribute_name": attr, "fact_type": "comparison_result", "priority": "required", "reason_zh": "多目标比较需要结构化比较结果事实。"}, catalog, attr, "comparison_result", mentioned, {}))
    return rows


def _explicit_relation_candidates(frame: dict[str, Any], targets: list[dict[str, Any]], catalog: _Catalog) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    relation_queries = list(frame.get("relation_queries") or [])
    for attr in frame.get("mentioned_attributes") or []:
        if attr in PROFILE_ATTRIBUTE_RELATIONS:
            relation_type, target_object_type = PROFILE_ATTRIBUTE_RELATIONS[attr]
            relation_queries.append({"relation_type": relation_type, "target_object_type": target_object_type, "attribute_name": attr})
    for query in relation_queries:
        relation_type = query.get("relation_type")
        attr = query.get("attribute_name") or _relation_attribute(relation_type)
        for target in targets:
            fact_type = "relation_instance"
            fact_id = _fact_id(target, fact_type, relation_type or attr)
            attr_meta = catalog.attributes.get(attr, {})
            rows.append(
                {
                    "fact_id": fact_id,
                    "fact_requirement_id": fact_id,
                    "fact_type": fact_type,
                    "fact_type_zh": "关系实例",
                    "subject": _subject(target),
                    "predicate": relation_type,
                    "attribute_name": attr,
                    "attribute": {
                        "attribute_name": attr,
                        "attribute_name_zh": attr_meta.get("attribute_name_zh") or attr,
                        "object_type": attr_meta.get("object_type") or "",
                    },
                    "target_object_type": query.get("target_object_type"),
                    "constraints": {},
                    "priority": "required",
                    "selection_priority": 95,
                    "source": "explicit_relation_query",
                    "answer_visibility": "answer_fact",
                    "reason_zh": f"用户显式查询{_attribute_zh(attr)}，候选池生成关系实例事实。",
                    "label_zh": f"{target.get('object_type')} 的{attr_meta.get('attribute_name_zh') or attr}",
                }
            )
    return rows


def _rule_select(candidate_fact_pool: list[dict[str, Any]], planning_options: dict[str, Any]) -> dict[str, Any]:
    budget = int(planning_options.get("fact_budget") or 20)
    ranked = sorted(candidate_fact_pool, key=lambda item: (-int(item.get("selection_priority") or 0), item.get("fact_id") or ""))
    selected = ranked[:budget]
    return {
        "status": "success",
        "selector": "rule_selector",
        "selected_fact_ids": [item["fact_id"] for item in selected],
        "selected_facts": selected,
        "message_zh": "rule selector 只在候选事实池内按显式属性、必需事实和本体优先级排序选择。",
    }


def _selection_from_ids(ids: list[Any], candidate_fact_pool: list[dict[str, Any]], selector: str, reasons: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    by_id = {item["fact_id"]: item for item in candidate_fact_pool}
    selected = [by_id[str(fact_id)] for fact_id in ids if str(fact_id) in by_id]
    return {
        "status": "success",
        "selector": selector,
        "selected_fact_ids": [str(item) for item in ids],
        "selected_facts": selected,
        "reasons": reasons or [],
        "message_zh": "selector 返回的 fact_id 将由 deterministic validation 复核。",
    }


def _selector_error(code: str, message_zh: str) -> dict[str, Any]:
    return {"status": "error", "error_code": code, "message_zh": message_zh, "selected_facts": [], "selected_fact_ids": []}


def _validate_selection(selected_facts: list[dict[str, Any]], candidate_fact_pool: list[dict[str, Any]], planning_options: dict[str, Any]) -> dict[str, Any]:
    candidate_ids = {item["fact_id"] for item in candidate_fact_pool}
    selected_ids = [item.get("fact_id") for item in selected_facts]
    requested_ids = [str(item) for item in planning_options.get("selected_fact_ids") or selected_ids]
    illegal = [fact_id for fact_id in requested_ids if fact_id not in candidate_ids]
    budget = int(planning_options.get("fact_budget") or 20)
    budgeted = selected_facts[:budget]
    warnings = []
    if illegal:
        warnings.append({"warning_code": "ILLEGAL_FACT_ID_REJECTED", "message_zh": "selector 返回了候选池外 fact_id，已被拒绝。", "illegal_fact_ids": illegal})
    if len(selected_facts) > budget:
        warnings.append({"warning_code": "FACT_BUDGET_TRUNCATED", "message_zh": f"事实选择超过预算 {budget}，已截断。"})
    return {
        "ok": not illegal,
        "candidate_fact_count": len(candidate_fact_pool),
        "selected_fact_count": len(budgeted),
        "illegal_fact_ids": illegal,
        "selected_facts": budgeted,
        "warnings": warnings,
        "message_zh": "事实选择合法。" if not illegal else "存在非法 fact_id，不能进入最终执行计划。",
    }


def _complete_dependencies(selected_facts: list[dict[str, Any]], candidate_fact_pool: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rules = []
    by_key = {
        ((item.get("subject") or {}).get("subject_id"), item.get("predicate"), item.get("attribute_name")): item
        for item in candidate_fact_pool
    }
    for fact in selected_facts:
        subject = fact.get("subject") or {}
        attr = fact.get("attribute_name")
        if attr in BENCHMARK_DEPENDENCY_ATTRIBUTES:
            dep = _dependency_fact(fact, "has_benchmark", "benchmark_name", "Benchmark", "benchmark_context", "benchmark_return / excess_return 需要业绩比较基准上下文。")
            rows.append(dep)
            rules.append({"rule_id": "benchmark_metric_requires_has_benchmark", "source_fact_id": fact["fact_id"], "completed_fact_id": dep["fact_id"], "message_zh": dep["reason_zh"]})
        if fact.get("fact_type") in PEER_DEPENDENCY_FACT_TYPES:
            dep = _dependency_fact(fact, "belongs_to_category", "fund_type", "FundCategory", "peer_context", "同类排名需要基金所属分类上下文。")
            rows.append(dep)
            rules.append({"rule_id": "peer_rank_requires_belongs_to_category", "source_fact_id": fact["fact_id"], "completed_fact_id": dep["fact_id"], "message_zh": dep["reason_zh"]})
        existing = by_key.get((subject.get("subject_id"), fact.get("predicate"), attr))
        if existing and existing.get("fact_id") not in {item["fact_id"] for item in rows}:
            continue
    return {"completed_facts": _dedupe_facts(rows), "rules": rules, "message_zh": f"确定性依赖补全新增 {len(_dedupe_facts(rows))} 条上下文事实。"}


def _dependency_fact(source: dict[str, Any], predicate: str, attr: str, target_object_type: str, dependency_type: str, reason: str) -> dict[str, Any]:
    subject = dict(source.get("subject") or {})
    fact_id = f"dep_{subject.get('subject_id', 'subject').replace(':', '_')}_{predicate}"
    return {
        "fact_id": fact_id,
        "fact_requirement_id": fact_id,
        "fact_type": "relation_instance",
        "fact_type_zh": "关系实例",
        "subject": subject,
        "predicate": predicate,
        "attribute_name": attr,
        "attribute": {"attribute_name": attr, "attribute_name_zh": _attribute_zh(attr), "object_type": target_object_type},
        "target_object_type": target_object_type,
        "constraints": dict(source.get("constraints") or {}),
        "priority": "supporting",
        "source": "deterministic_dependency_completion",
        "dependency_type": dependency_type,
        "answer_visibility": "supporting_context",
        "reason_zh": reason,
        "label_zh": f"{subject.get('object_type', '对象')} 的{_attribute_zh(attr)}上下文",
    }


def _bind_skills(facts: list[dict[str, Any]], skills: list[dict[str, Any]], frame: dict[str, Any], user_context: dict[str, Any]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for skill in skills:
        covered = [fact for fact in facts if _skill_covers(skill, fact)]
        if not covered:
            continue
        params, missing = _binding_params(skill, covered, frame)
        permission_scope = skill.get("permission_scope") or ""
        permission_blocked = bool(permission_scope and permission_scope not in set(user_context.get("permission_scopes") or [permission_scope]))
        bindings.append(
            {
                "binding_id": f"binding_{skill.get('skill_id')}",
                "capability_type": "skill",
                "skill_id": skill.get("skill_id"),
                "skill_name_zh": skill.get("skill_name") or skill.get("skill_id"),
                "description_zh": skill.get("description") or "",
                "tool_type": "SkillCapability",
                "tool_name": skill.get("skill_id"),
                "priority": "primary" if any(item.get("priority") == "required" for item in covered) else "optional",
                "covers_fact_ids": [item["fact_id"] for item in covered],
                "covers_fact_requirements": [item["fact_id"] for item in covered],
                "covers_required_count": len([item for item in covered if item.get("priority") == "required"]),
                "covers_optional_count": len([item for item in covered if item.get("priority") != "required"]),
                "params": params,
                "missing_params": missing,
                "permission_scope": permission_scope,
                "permission_blocked": permission_blocked,
                "expected_facts": [{"fact_id": item["fact_id"], "fact_type": item.get("fact_type"), "attribute_name": item.get("attribute_name")} for item in covered],
                "coverage_score": round(len(covered) / max(1, len(facts)), 3),
                "coverage_reason_zh": "Skill 能力声明确定性覆盖这些候选事实。",
                "call_status": "blocked_permission"
                if permission_blocked
                else ("blocked_missing_params" if missing else "ready"),
            }
        )
    return sorted(bindings, key=lambda item: (-item["covers_required_count"], _skill_sort_rank(item.get("skill_id") or ""), item.get("skill_id") or ""))


def _skill_covers(skill: dict[str, Any], fact: dict[str, Any]) -> bool:
    provides = set(skill.get("provides_fact_types") or [])
    attrs = set(skill.get("supported_attributes") or skill.get("output_attributes") or [])
    subjects = set(skill.get("supported_subject_types") or [skill.get("target_object_type")])
    relations = set(skill.get("supported_relations") or [])
    subject = fact.get("subject") or {}
    if provides and fact.get("fact_type") not in provides:
        return False
    if subjects and subject.get("object_type") not in subjects:
        return False
    if fact.get("fact_type") == "relation_instance" and relations:
        return fact.get("predicate") in relations
    if fact.get("fact_type") != "entity_set" and attrs and fact.get("attribute_name") not in attrs:
        return False
    return True


def _binding_params(skill: dict[str, Any], covered: list[dict[str, Any]], frame: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    params: dict[str, Any] = {}
    constraints = dict(frame.get("constraints") or {})
    first_subject = (covered[0].get("subject") or {}) if covered else {}
    instance_ref = dict(first_subject.get("instance_ref") or {})
    available = {**constraints, **instance_ref}
    attrs = _unique(item.get("attribute_name") for item in covered if item.get("attribute_name"))
    missing: list[str] = []
    for input_param in skill.get("input_params") or []:
        if input_param == "attributes":
            params["attributes"] = attrs
        elif input_param == "fund_codes":
            codes = _unique((fact.get("subject") or {}).get("instance_ref", {}).get("fund_code") for fact in covered)
            if codes:
                params["fund_codes"] = codes
        elif input_param == "fund_universe" and "fund_universe" not in params:
            params["fund_universe"] = instance_ref.get("fund_universe") or "all_funds"
        elif input_param == "filters" and frame.get("filters") is not None:
            params["filters"] = frame.get("filters")
        elif input_param == "ranking" and frame.get("ranking") is not None:
            params["ranking"] = frame.get("ranking")
        elif input_param == "limit" and frame.get("limit") is not None:
            params["limit"] = frame.get("limit")
        elif input_param in available and available[input_param] not in (None, ""):
            params[input_param] = available[input_param]
        elif input_param not in params:
            missing.append(input_param)
    return params, _unique(missing)


def _validate_bindings(validation: dict[str, Any], facts: list[dict[str, Any]], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    covered_ids = {fact_id for binding in bindings for fact_id in binding.get("covers_fact_ids") or []}
    uncovered = [fact for fact in facts if fact.get("priority") == "required" and fact.get("fact_id") not in covered_ids]
    missing_params = _missing_params(bindings)
    return {
        **validation,
        "skill_binding_ok": not uncovered,
        "uncovered_required_facts": uncovered,
        "missing_params": missing_params,
        "message_zh": validation["message_zh"] if validation["illegal_fact_ids"] else ("事实、依赖和 Skill 绑定校验完成。"),
    }


def _coverage_summary(facts: list[dict[str, Any]], bindings: list[dict[str, Any]], validation: dict[str, Any]) -> dict[str, Any]:
    covered_ids = {fact_id for binding in bindings for fact_id in binding.get("covers_fact_ids") or []}
    required = [fact for fact in facts if fact.get("priority") == "required"]
    optional = [fact for fact in facts if fact.get("priority") != "required"]
    uncovered = [fact for fact in required if fact.get("fact_id") not in covered_ids]
    status = "full_coverage"
    if validation.get("illegal_fact_ids"):
        status = "invalid_selection"
    elif uncovered and covered_ids:
        status = "partial_coverage"
    elif uncovered:
        status = "no_coverage"
    return {
        "coverage_status": status,
        "required_fact_count": len(required),
        "covered_required_fact_count": len([fact for fact in required if fact.get("fact_id") in covered_ids]),
        "uncovered_required_facts": uncovered,
        "optional_fact_count": len(optional),
        "covered_optional_fact_count": len([fact for fact in optional if fact.get("fact_id") in covered_ids]),
        "skill_count": len(bindings),
        "coverage_message_zh": _coverage_message(status),
    }


def _task_graph(frame: dict[str, Any], ontology_subgraph: dict[str, Any], facts: list[dict[str, Any]], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [
        {"node_id": "SemanticFrame:current", "node_type": "SemanticFrame", "label_zh": "语义输入", "role": "input", "raw_question": frame.get("raw_question")},
        {"node_id": f"TaskType:{frame.get('task_type') or 'unknown'}", "node_type": "TaskType", "label_zh": TASK_TYPE_LABELS.get(frame.get("task_type"), frame.get("task_type") or "任务"), "role": "task"},
    ]
    if frame.get("intent"):
        nodes.append({"node_id": f"IntentProfile:{frame.get('intent')}", "node_type": "IntentProfile", "label_zh": frame.get("intent"), "role": "intent"})
    edges = []
    for node in ontology_subgraph.get("nodes") or []:
        if node.get("node_type") in {"ObjectType", "Attribute", "SkillCapability"}:
            nodes.append({**node, "role": node.get("role") or "ontology_context"})
    for target in frame.get("target_objects") or []:
        node_id = f"TargetInstance:{_target_instance_id(target)}"
        nodes.append({"node_id": node_id, "node_type": "TargetInstance", "label_zh": _target_label(target), "role": target.get("role"), "instance_ref": target.get("instance_ref") or {}})
        edges.append({"edge_id": f"SemanticFrame:current__has_target__{node_id}", "from": "SemanticFrame:current", "to": node_id, "relation_type": "has_target", "label_zh": "目标对象", "reason_zh": "semantic_frame 指定本次规划目标。"})
    for fact in facts:
        node_id = f"Fact:{fact['fact_id']}"
        nodes.append({"node_id": node_id, "node_type": "FactRequirement", "label_zh": fact.get("label_zh") or fact["fact_id"], "role": "candidate_or_dependency", "fact_id": fact["fact_id"]})
        if fact.get("target_object_type"):
            nodes.append(
                {
                    "node_id": f"ObjectType:{fact['target_object_type']}",
                    "node_type": "ObjectType",
                    "label_zh": fact.get("target_object_type"),
                    "role": "dependency_target",
                }
            )
            if fact.get("predicate"):
                edges.append(
                    {
                        "edge_id": f"ObjectType:{(fact.get('subject') or {}).get('object_type')}__{fact.get('predicate')}__ObjectType:{fact['target_object_type']}",
                        "from": f"ObjectType:{(fact.get('subject') or {}).get('object_type')}",
                        "to": f"ObjectType:{fact['target_object_type']}",
                        "source": f"ObjectType:{(fact.get('subject') or {}).get('object_type')}",
                        "target": f"ObjectType:{fact['target_object_type']}",
                        "relation_type": fact.get("predicate"),
                        "label_zh": "对象关系",
                        "reason_zh": fact.get("reason_zh") or "关系实例事实对应的本体对象关系。",
                    }
                )
        edges.append({"edge_id": f"SemanticFrame:current__selects_fact__{node_id}", "from": "SemanticFrame:current", "to": node_id, "relation_type": "selects_fact", "label_zh": "选择事实", "reason_zh": fact.get("reason_zh") or ""})
        edges.append({"edge_id": f"SemanticFrame:current__requires_fact__{node_id}", "from": "SemanticFrame:current", "to": node_id, "relation_type": "requires_fact", "label_zh": "需要事实", "reason_zh": fact.get("reason_zh") or ""})
        if fact.get("attribute_name"):
            attr_node = f"Attribute:{fact.get('attribute_name')}"
            edges.append({"edge_id": f"{node_id}__has_attribute__{attr_node}", "from": node_id, "to": attr_node, "relation_type": "has_attribute", "label_zh": "事实属性", "reason_zh": "该事实围绕此本体属性生成。"})
    for binding in bindings:
        node_id = f"SkillBinding:{binding['skill_id']}"
        nodes.append({"node_id": node_id, "node_type": "SkillBinding", "label_zh": binding.get("skill_name_zh") or binding["skill_id"], "role": "deterministic_skill_binding"})
        for fact_id in binding.get("covers_fact_ids") or []:
            edges.append({"edge_id": f"Fact:{fact_id}__bound_to__{node_id}", "from": f"Fact:{fact_id}", "to": node_id, "relation_type": "bound_to_skill", "label_zh": "绑定 Skill", "reason_zh": "系统根据 Skill 能力声明确定性绑定。"})
            edges.append({"edge_id": f"Fact:{fact_id}__covered_by_skill__{node_id}", "from": f"Fact:{fact_id}", "to": node_id, "relation_type": "covered_by_skill", "label_zh": "Skill 覆盖", "reason_zh": "兼容旧任务图关系名，实际绑定仍由系统确定性完成。"})
    fact_by_attr = {item.get("attribute_name"): item for item in facts}
    if "return_rate" in fact_by_attr and "benchmark_return" in fact_by_attr:
        edges.append(
            {
                "edge_id": f"Fact:{fact_by_attr['return_rate']['fact_id']}__compared_with__Fact:{fact_by_attr['benchmark_return']['fact_id']}",
                "from": f"Fact:{fact_by_attr['return_rate']['fact_id']}",
                "to": f"Fact:{fact_by_attr['benchmark_return']['fact_id']}",
                "relation_type": "compared_with",
                "label_zh": "对比基准",
                "reason_zh": "收益率分析可与基准收益进行比较。",
            }
        )
        edges.append(
            {
                "edge_id": f"Fact:{fact_by_attr['return_rate']['fact_id']}__expanded_by_relation__Fact:{fact_by_attr['benchmark_return']['fact_id']}",
                "from": f"Fact:{fact_by_attr['return_rate']['fact_id']}",
                "to": f"Fact:{fact_by_attr['benchmark_return']['fact_id']}",
                "relation_type": "expanded_by_relation",
                "label_zh": "关系扩展",
                "reason_zh": "兼容旧任务图关系名；V2 中该事实来自候选池前置生成。",
            }
        )
    for edge in edges:
        edge.setdefault("source", edge.get("from"))
        edge.setdefault("target", edge.get("to"))
        edge.setdefault("description_zh", edge.get("reason_zh") or edge.get("label_zh") or "")
    for node in nodes:
        node.setdefault("description_zh", node.get("label_zh") or node.get("node_id") or "")
    return {"kind": "task_graph", "nodes": nodes, "edges": edges, "ontology_subgraph_summary": ontology_subgraph.get("summary") or {}}


def _agent_plan(frame: dict[str, Any], facts: list[dict[str, Any]], bindings: list[dict[str, Any]], validation: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    execution = _execution(bindings)
    return {
        "oag_version": "v2",
        "task": _semantic_frame_summary(frame),
        "targets": _target_instances(frame),
        "facts": [
            {
                "fact_id": item["fact_id"],
                "fact_type": item["fact_type"],
                "attribute": item.get("attribute_name"),
                "attribute_name": item.get("attribute_name"),
                "reason_zh": item.get("reason_zh"),
            }
            for item in facts
        ],
        "skill_calls": bindings,
        "validation": validation,
        "coverage": coverage,
        "execution": execution,
        "uncovered_facts": coverage.get("uncovered_required_facts") or [],
        "issues": _agent_issues(validation, coverage, execution),
    }


def _execution(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    ready = [item for item in bindings if not item.get("missing_params") and not item.get("permission_blocked")]
    blocked_missing = [item for item in bindings if item.get("missing_params")]
    blocked_permission = [item for item in bindings if item.get("permission_blocked")]
    if blocked_missing:
        status = "blocked_missing_params"
    elif blocked_permission:
        status = "blocked_permission"
    elif ready:
        status = "ready"
    else:
        status = "no_skill_calls"
    issues = []
    seen_missing = set()
    for item in blocked_missing:
        key = tuple(item.get("missing_params") or [])
        if key in seen_missing:
            continue
        seen_missing.add(key)
        issues.append(
            {
                "code": "SKILL_PARAMS_MISSING",
                "skill_id": item.get("skill_id"),
                "skill_name_zh": item.get("skill_name_zh"),
                "missing_params": item.get("missing_params") or [],
                "message_zh": "调用该 Skill 前需要补充参数：" + "、".join(item.get("missing_params") or []),
            }
        )
    for item in blocked_permission:
        issues.append(
            {
                "code": "SKILL_PERMISSION_BLOCKED",
                "skill_id": item.get("skill_id"),
                "skill_name_zh": item.get("skill_name_zh"),
                "message_zh": "调用该 Skill 前需要补充权限。",
            }
        )
    return {
        "execution_status": status,
        "ready_skill_count": len(ready),
        "blocked_skill_count": len(blocked_missing) + len(blocked_permission),
        "message_zh": {
            "ready": "Skill 调用参数齐全，可以执行。",
            "blocked_missing_params": "存在 Skill 调用缺失参数，需要补充后再执行。",
            "blocked_permission": "存在 Skill 调用权限不足，需要授权后再执行。",
            "no_skill_calls": "当前没有可执行的 Skill 调用计划。",
        }.get(status, "执行状态需要人工确认。"),
        "blocking_issues": issues,
    }


def _agent_issues(validation: dict[str, Any], coverage: dict[str, Any], execution: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    if validation.get("illegal_fact_ids"):
        issues.append({"code": "ILLEGAL_FACT_ID_REJECTED", "severity": "error", "message_zh": validation.get("message_zh")})
    for item in coverage.get("uncovered_required_facts") or []:
        issues.append({"code": "REQUIRED_FACT_UNCOVERED", "severity": "warning", "fact_id": item.get("fact_id"), "message_zh": "必需事实未覆盖。"})
    return issues


def _skill_sort_rank(skill_id: str) -> int:
    if skill_id.startswith("get_"):
        return 0
    if skill_id.startswith("rank_") or skill_id.startswith("screen_") or skill_id.startswith("recommend_") or skill_id.startswith("compare_"):
        return 1
    return 2


def _editor_plan(frame: dict[str, Any], ontology_subgraph: dict[str, Any], pool: list[dict[str, Any]], selected: list[dict[str, Any]], validation: dict[str, Any], dependencies: dict[str, Any], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "input": {"raw_question": frame.get("raw_question"), "semantic_frame": frame, "recognized_intents": frame.get("recognized_intents"), "selector_mode": frame.get("selector_mode")},
        "planning_chain": [
            {"step": "ontology_subgraph", "count": (ontology_subgraph.get("summary") or {}).get("node_count", 0), "message_zh": "召回本体子图。"},
            {"step": "candidate_fact_pool", "count": len(pool), "message_zh": "基于本体和 Skill 声明生成候选事实池。"},
            {"step": "selected_facts", "count": len(selected), "message_zh": "selector 只选择候选池内 fact_id。"},
            {"step": "validation_result", "ok": validation.get("ok"), "message_zh": validation.get("message_zh")},
            {"step": "dependency_completion", "count": len(dependencies.get("completed_facts") or []), "message_zh": dependencies.get("message_zh")},
            {"step": "skill_bindings", "count": len(bindings), "message_zh": "系统确定性完成 Skill 绑定。"},
        ],
    }


def _selector_error_response(domain: str, frame: dict[str, Any], llm_config: LLMConfig, subgraph: dict[str, Any], pool: list[dict[str, Any]], selection: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "error",
        "oag_version": "v2",
        "domain": domain,
        "raw_question": frame.get("raw_question") or "",
        "error_code": selection.get("error_code"),
        "message_zh": selection.get("message_zh"),
        "normalized_semantic_frame": frame,
        "recognized_intents": frame.get("recognized_intents") or [],
        "llm_config_status": llm_config.status(),
        "ontology_subgraph": subgraph,
        "candidate_fact_pool": pool,
        "selected_facts": [],
        "selection_trace": selection,
        "validation_result": {"ok": False, "message_zh": selection.get("message_zh"), "illegal_fact_ids": []},
        "dependency_completion": {"completed_facts": [], "rules": []},
        "skill_bindings": [],
        "agent_plan": {},
        "editor_plan": {},
        "fact_requirements": [],
        "candidate_invocations": [],
        "task_graph": {"kind": "task_graph", "nodes": [], "edges": []},
        "coverage_summary": {"coverage_status": "no_coverage", "coverage_message_zh": selection.get("message_zh")},
        "missing_params": [],
        "diagnostics": [{"diagnostic_code": selection.get("error_code"), "severity": "error", "message_zh": selection.get("message_zh"), "suggestion_zh": "配置 API KEY 或切换 selector_mode=rule。"}],
        "warnings": [],
    }


def _semantic_frame_required_response(domain: str) -> dict[str, Any]:
    return _error_response(domain, "", "SEMANTIC_FRAME_REQUIRED", "OAG V2 需要前置意图识别节点提供 semantic_frame，不能直接使用空输入规划。")


def _need_clarification_response(domain: str, frame: dict[str, Any], llm_config: LLMConfig) -> dict[str, Any]:
    return {
        "status": "need_clarification",
        "oag_version": "v2",
        "domain": domain,
        "raw_question": frame.get("raw_question") or "",
        "error_code": "FACT_REQUIREMENTS_INSUFFICIENT",
        "normalized_semantic_frame": frame,
        "recognized_intents": frame.get("recognized_intents") or [],
        "llm_config_status": llm_config.status(),
        "message_zh": "语义信息不足，没有生成候选事实池，请补充 recognized_intents、mentioned_attributes 或目标对象。",
        "candidate_fact_pool": [],
        "selected_facts": [],
        "validation_result": {"ok": False, "message_zh": "candidate_fact_pool 为空。", "illegal_fact_ids": []},
        "dependency_completion": {"completed_facts": [], "rules": []},
        "skill_bindings": [],
        "fact_requirements": [],
        "candidate_invocations": [],
        "task_graph": {"kind": "task_graph", "nodes": [], "edges": []},
        "coverage_summary": {"coverage_status": "need_clarification", "coverage_message_zh": "需要补充语义输入后才能规划。"},
        "missing_params": [],
        "diagnostics": [{"diagnostic_code": "CANDIDATE_FACT_POOL_EMPTY", "severity": "warning", "message_zh": "候选事实池为空。", "suggestion_zh": "检查前置意图识别输出。"}],
        "warnings": [],
    }


def _error_response(domain: str, raw_question: str, error_code: str, message_zh: str) -> dict[str, Any]:
    return {
        "status": "error",
        "oag_version": "v2",
        "domain": domain,
        "raw_question": raw_question,
        "error_code": error_code,
        "message_zh": message_zh,
        "candidate_fact_pool": [],
        "selected_facts": [],
        "validation_result": {"ok": False, "message_zh": message_zh, "illegal_fact_ids": []},
        "dependency_completion": {"completed_facts": [], "rules": []},
        "skill_bindings": [],
        "fact_requirements": [],
        "candidate_invocations": [],
        "task_graph": {"kind": "task_graph", "nodes": [], "edges": []},
        "coverage_summary": {"coverage_status": "no_coverage", "coverage_message_zh": message_zh},
        "missing_params": [],
        "diagnostics": [{"diagnostic_code": error_code, "severity": "error", "message_zh": message_zh, "suggestion_zh": "请修正 OAG V2 输入。"}],
        "warnings": [],
    }


def _diagnostics(validation: dict[str, Any], coverage: dict[str, Any], selection: dict[str, Any], dependencies: dict[str, Any], frame: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    if frame.get("task_type") == "compare" and len(_targets_of_type(frame, "Fund")) < 2:
        rows.append({"diagnostic_code": "COMPARE_TARGET_TOO_FEW", "severity": "warning", "message_zh": "比较任务至少需要两个基金目标。", "suggestion_zh": "请在 semantic_frame.target_objects 中补充第二个 Fund。"})
    if frame.get("task_type") in {"rank", "screen", "recommend"} and not any(item.get("object_type") == "FundSet" for item in frame.get("target_objects") or []):
        rows.append({"diagnostic_code": "FUNDSET_TARGET_MISSING", "severity": "warning", "message_zh": "集合类任务缺少 FundSet 目标。", "suggestion_zh": "请将候选基金集合写入 target_objects。"})
    if validation.get("illegal_fact_ids"):
        rows.append({"diagnostic_code": "ILLEGAL_FACT_ID_REJECTED", "severity": "error", "message_zh": "selector 返回候选池外 fact_id，已拒绝。", "suggestion_zh": "修正 LLM 输出解析或候选池约束提示。"})
    if validation.get("missing_params"):
        rows.append({"diagnostic_code": "SKILL_PARAMS_MISSING", "severity": "warning", "message_zh": "存在 Skill 调用缺失参数。", "suggestion_zh": "补充 period、fund_code、report_date 等必要参数。"})
    if coverage.get("uncovered_required_facts"):
        rows.append({"diagnostic_code": "REQUIRED_FACT_UNCOVERED", "severity": "warning", "message_zh": "存在必需事实没有 Skill 覆盖。", "suggestion_zh": "补充 Skill 能力声明或调整事实类型。"})
    if dependencies.get("completed_facts"):
        rows.append({"diagnostic_code": "DEPENDENCY_COMPLETED", "severity": "info", "message_zh": dependencies.get("message_zh"), "suggestion_zh": "检查补全上下文是否符合业务预期。"})
    if not rows:
        rows.append({"diagnostic_code": "OAG_V2_PLAN_READY", "severity": "info", "message_zh": "OAG V2 规划链路完整。", "suggestion_zh": "可以交给后续 Agent 执行 Skill。"})
    return rows


def _semantic_warnings(frame: dict[str, Any], catalog: _Catalog) -> list[dict[str, Any]]:
    rows = []
    for intent in frame.get("recognized_intents") or []:
        name = intent.get("intent_name")
        if name and name not in catalog.intent_profiles:
            rows.append(
                {
                    "warning_code": "UNKNOWN_INTENT",
                    "message_zh": f"recognized_intents 中的 {name} 未在本体意图画像中配置，已仅基于显式属性规划。",
                }
            )
    return rows


def _missing_params(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "skill_id": item.get("skill_id"),
            "skill_name_zh": item.get("skill_name_zh"),
            "missing_params": item.get("missing_params") or [],
            "message_zh": "调用该 Skill 前需要补充参数：" + "、".join(item.get("missing_params") or []),
            "suggested_question": _suggested_question(item.get("missing_params") or []),
        }
        for item in bindings
        if item.get("missing_params")
    ]


def _suggested_question(missing: list[str]) -> str:
    if "period" in missing:
        return "请补充查询周期，例如近一年、近三个月或今年以来。"
    if "report_date" in missing:
        return "请补充报告期，例如最近一期。"
    return "请补充必要参数：" + "、".join(missing)


def _semantic_frame_summary(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_question": frame.get("raw_question") or "",
        "domain": frame.get("domain") or DOMAIN,
        "task_type": frame.get("task_type") or "",
        "task_type_zh": TASK_TYPE_LABELS.get(frame.get("task_type"), frame.get("task_type") or ""),
        "intent": frame.get("intent") or ((frame.get("recognized_intents") or [{}])[0].get("intent_name")),
        "recognized_intents": frame.get("recognized_intents") or [],
        "constraints": dict(frame.get("constraints") or {}),
        "mentioned_attributes": list(frame.get("mentioned_attributes") or []),
    }


def _target_instances(frame: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "target_instance_id": _target_instance_id(item),
            "object_type": item.get("object_type"),
            "instance_ref": dict(item.get("instance_ref") or {}),
            "role": item.get("role") or "",
            "display_name_zh": _target_label(item),
        }
        for item in frame.get("target_objects") or []
    ]


def _targets_for_templates(frame: dict[str, Any], targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if frame.get("task_type") in {"rank", "screen", "recommend"}:
        return [_fundset_target(frame)]
    return targets


def _fundset_target(frame: dict[str, Any]) -> dict[str, Any]:
    for target in frame.get("target_objects") or []:
        if target.get("object_type") == "FundSet":
            return target
    return {"object_type": "FundSet", "instance_ref": {"fund_universe": "all_funds"}, "role": "candidate_set", "target_index": 0}


def _targets_of_type(frame: dict[str, Any], object_type: str) -> list[dict[str, Any]]:
    return [item for item in frame.get("target_objects") or [] if item.get("object_type") == object_type]


def _subject(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_type": target.get("object_type") or "Fund",
        "instance_ref": dict(target.get("instance_ref") or {}),
        "role": target.get("role") or "",
        "target_instance_id": _target_instance_id(target),
        "subject_id": _target_instance_id(target),
    }


def _target_instance_id(target: dict[str, Any]) -> str:
    object_type = target.get("object_type") or "Fund"
    instance_ref = target.get("instance_ref") or {}
    if object_type == "Fund" and instance_ref.get("fund_code"):
        return f"Fund:{instance_ref['fund_code']}"
    if object_type == "FundSet":
        return f"FundSet:{instance_ref.get('fund_universe') or 'all_funds'}"
    if instance_ref:
        first_key = sorted(instance_ref)[0]
        return f"{object_type}:{instance_ref[first_key]}"
    return f"{object_type}:{target.get('target_index', 0)}"


def _fact_id(target: dict[str, Any], fact_type: str, attr: str) -> str:
    return "fact_" + re.sub(r"[^a-zA-Z0-9_]+", "_", f"{_target_instance_id(target)}_{fact_type}_{attr}").strip("_")


def _fact_constraints(frame: dict[str, Any], fact_type: str) -> dict[str, Any]:
    constraints = dict(frame.get("constraints") or {})
    if fact_type not in METRIC_PERIOD_FACT_TYPES:
        constraints.pop("period", None)
    return constraints


def _fact_type_for_attribute(attribute_name: str) -> str:
    return FACT_TYPE_BY_ATTRIBUTE.get(attribute_name, "metric_value")


def _predicate_for_fact_type(fact_type: str) -> str:
    return {
        "benchmark_metric_value": "has_benchmark_metric_value",
        "excess_metric_value": "has_excess_metric_value",
        "peer_rank": "has_peer_rank",
        "peer_average": "has_peer_average",
        "object_profile": "has_profile_fact",
        "metric_ranking": "has_metric_ranking",
        "filter_condition": "has_filter_condition",
        "comparison_result": "has_comparison_result",
    }.get(fact_type, "has_metric_value")


def _fact_type_zh(fact_type: str) -> str:
    return {
        "metric_value": "指标值",
        "benchmark_metric_value": "基准指标值",
        "excess_metric_value": "超额指标值",
        "peer_rank": "同类排名",
        "peer_average": "同类平均",
        "object_profile": "对象画像",
        "relation_instance": "关系实例",
        "metric_ranking": "指标排序",
        "filter_condition": "筛选条件",
        "comparison_result": "比较结果",
        "fee_fact": "费率事实",
        "dividend_fact": "分红事实",
        "holding_fact": "持仓事实",
        "allocation_fact": "配置事实",
    }.get(fact_type, fact_type)


def _fact_label_zh(fact_type: str, attribute_zh: str, target: dict[str, Any]) -> str:
    return f"{_target_label(target)} {_fact_type_zh(fact_type)}：{attribute_zh}"


def _target_label(target: dict[str, Any]) -> str:
    instance_ref = target.get("instance_ref") or {}
    if target.get("object_type") == "Fund" and instance_ref.get("fund_code"):
        return f"基金 {instance_ref['fund_code']}"
    if target.get("object_type") == "FundSet":
        return "基金集合"
    return str(target.get("object_type") or "目标对象")


def _relation_attribute(relation_type: str) -> str:
    return {
        "managed_by": "manager_name",
        "issued_by": "company_name",
        "has_benchmark": "benchmark_name",
        "belongs_to_category": "fund_type",
        "tracks_index": "tracking_index_name",
    }.get(relation_type or "", relation_type or "")


def _attribute_zh(attribute_name: str) -> str:
    return {
        "benchmark_name": "业绩比较基准",
        "fund_manager": "基金经理",
        "fund_company": "基金公司",
        "fund_type": "基金类型",
        "manager_name": "基金经理",
        "company_name": "基金公司",
    }.get(attribute_name, attribute_name)


def _normalize_edge(edge: Any) -> dict[str, Any] | None:
    if not isinstance(edge, dict):
        return None
    source = edge.get("from") or edge.get("source")
    target = edge.get("to") or edge.get("target")
    relation_type = edge.get("relation_type")
    if not source or not target or not relation_type:
        return None
    return {
        "edge_id": edge.get("edge_id") or f"{source}__{relation_type}__{target}",
        "from": source,
        "to": target,
        "relation_type": relation_type,
        "label_zh": edge.get("label_zh") or edge.get("reason_zh") or relation_type,
        "properties": dict(edge.get("properties") or {}),
    }


def _dedupe_facts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for row in rows:
        fact_id = row.get("fact_id")
        if not fact_id or fact_id in seen:
            continue
        seen.add(fact_id)
        result.append(row)
    return result


def _unique(values: Any) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        if value in (None, "") or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _coverage_message(status: str) -> str:
    return {
        "full_coverage": "候选事实、依赖事实和 Skill 绑定已完整覆盖。",
        "partial_coverage": "部分必需事实尚未被 Skill 覆盖。",
        "no_coverage": "必需事实没有可用 Skill 覆盖。",
        "need_clarification": "Skill 调用缺少必要参数，需要补充后执行。",
        "invalid_selection": "selector 输出包含非法 fact_id，已拒绝执行。",
    }.get(status, "覆盖状态需要人工确认。")


def _decorate_facts(facts: list[dict[str, Any]], frame: dict[str, Any]) -> None:
    period = (frame.get("constraints") or {}).get("period")
    for fact in facts:
        constraints = dict(fact.get("constraints") or {})
        if period and "period" not in constraints:
            constraints["period"] = period
        fact["constraints"] = constraints
        fact.setdefault("description_zh", fact.get("reason_zh") or fact.get("label_zh") or fact.get("fact_id") or "")
        fact.setdefault("priority_zh", {"required": "必须", "optional": "可选", "supporting": "支撑上下文"}.get(fact.get("priority"), fact.get("priority") or ""))
        fact.setdefault(
            "source_zh",
            {
                "explicit_attribute": "显式属性",
                "relation_expansion": "关系扩展",
                "deterministic_dependency_completion": "确定性依赖补全",
                "operation_requirement": "任务操作需求",
                "explicit_relation_query": "显式关系查询",
            }.get(fact.get("source"), "候选事实池"),
        )
