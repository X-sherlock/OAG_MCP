from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from oag_mcp.config import load_config
from oag_mcp.errors import OAGRepositoryError
from oag_mcp.fact_planner import semantic_frame_required_response
from oag_mcp.oag_v2_planner import OAGV2Planner
from oag_mcp.intent_matcher import PRIORITY_RANK, IntentMatcher
from oag_mcp.param_extractor import extract_params
from oag_mcp.plan_projector import project_plan
from oag_mcp.repositories import (
    GraphRepository,
    MySQLGraphRepository,
    MySQLMetadataRepository,
    MySQLTextRepository,
    OntologyRepository,
    TextSearchRepository,
    extract_fund_codes,
)


SUPPORTED_DOMAIN = "finance_market"
# 默认召回选项控制响应体大小和候选能力开关；调用方可通过 options 覆盖。
DEFAULT_OPTIONS = {
    "max_hops": 2,
    "top_k_objects": 8,
    "top_k_paths": 300,
    "include_candidate_queries": True,
    "include_candidate_skills": True,
    "detail_level": "compact",
    "debug": False,
}

OUTPUT_BUDGETS: dict[str, dict[str, int]] = {
    "compact": {
        "max_matched_objects": 8,
        "max_matched_attributes": 10,
        "max_matched_relations": 30,
        "max_relation_paths": 8,
        "max_subgraph_nodes": 40,
        "max_subgraph_edges": 60,
        "max_fields_per_attribute": 3,
        "max_fields_per_table": 5,
        "max_tables_per_query": 3,
        "max_paths_per_start_node": 3,
        "max_candidate_queries": 6,
        "max_candidate_skills": 6,
        "max_candidate_invocations": 6,
    },
    "standard": {
        "max_matched_objects": 8,
        "max_matched_attributes": 12,
        "max_matched_relations": 80,
        "max_relation_paths": 20,
        "max_subgraph_nodes": 100,
        "max_subgraph_edges": 150,
        "max_fields_per_attribute": 6,
        "max_fields_per_table": 10,
        "max_tables_per_query": 5,
        "max_paths_per_start_node": 5,
        "max_candidate_queries": 10,
        "max_candidate_skills": 10,
        "max_candidate_invocations": 10,
    },
    "full": {
        "max_matched_objects": 20,
        "max_matched_attributes": 30,
        "max_matched_relations": 300,
        "max_relation_paths": 80,
        "max_subgraph_nodes": 300,
        "max_subgraph_edges": 500,
        "max_fields_per_attribute": 20,
        "max_fields_per_table": 50,
        "max_tables_per_query": 20,
        "max_paths_per_start_node": 20,
        "max_candidate_queries": 30,
        "max_candidate_skills": 30,
        "max_candidate_invocations": 30,
    },
}

ALLOWED_MATCHED_OBJECT_TYPES = {"ObjectType", "DataTable", "QueryCapability", "SkillCapability"}
SHORT_OBJECT_SEARCH_STOPWORDS = {"年", "月", "日", "周", "近", "高", "低", "好", "差", "是", "否", "1", "0"}
PERIOD_MISMATCH_TERMS = (
    "一周",
    "近1周",
    "最近一周",
    "一月",
    "一个月",
    "近1月",
    "三个月",
    "六个月",
    "两年",
    "三年",
    "五年",
    "成立以来",
    "今年以来",
    "当天",
    "本周以来",
    "本月以来",
    "本季以来",
    "本年以来",
)
PERIOD_1Y_TERMS = ("一年", "近一年", "最近一年", "1y", "近1年")
PERIOD_TEMPLATE_TERMS = ("近xx", "近 xx", "period", "interval", "区间")
PERIOD_CODES = ("20y", "10y", "ytd", "1w", "1m", "3m", "6m", "1y", "2y", "3y", "5y", "si")
ENUM_NOISE_TERMS = (
    "0-非ETF",
    "1-ETF",
    "0:否",
    "0：否",
    "1:是",
    "1：是",
    "1：不可售",
    "2：纸质合同",
    "3：无合同",
)
CORE_DIM_FUND_FIELDS = ("fund_code", "fund_name", "benchmark", "fund_category", "基金产品代码", "基金产品名称", "业绩比较基准", "基金类型")
CORE_TABLE_HINTS = (
    "dws_fund_perf_",
    "dws_fund_risk_ret_",
    "dwd_fund_bm_grth_rate",
    "dwd_fund_nav_grth",
    "dws_bm_perf_",
)


@dataclass
class OAGContextService:
    """OAG 上下文召回编排服务。

    服务层不直接关心底层存储实现，只依赖三个仓储协议：本体元数据、文本/别名
    召回和关系图召回。这样既便于测试替身注入，也便于未来替换检索后端。
    """

    ontology_repository: OntologyRepository
    text_repository: TextSearchRepository
    graph_repository: GraphRepository
    domain: str = SUPPORTED_DOMAIN
    intent_profiles: list[dict[str, Any]] | None = None
    skill_related_queries: dict[str, list[str]] | None = None

    def __post_init__(self) -> None:
        if self.intent_profiles is None:
            self.intent_profiles = self.ontology_repository.get_intent_profiles(self.domain)
        if self.skill_related_queries is None:
            self.skill_related_queries = {
                item["skill_id"]: list(item.get("related_queries") or [])
                for item in self.ontology_repository.get_skill_capabilities(self.domain)
            }

    def retrieve_context(
        self,
        semantic_frame: dict[str, Any] | None = None,
        raw_question: str | None = None,
        recognized_intents: list[dict[str, Any]] | None = None,
        selector_mode: str = "rule",
        planning_options: dict[str, Any] | None = None,
        domain: str | None = None,
        user_context: dict[str, Any] | None = None,
        output_view: str = "agent",
    ) -> dict[str, Any]:
        """Run the OAG V2 planning chain and project it for the caller."""

        domain = domain or self.domain
        if semantic_frame is None:
            return project_plan(semantic_frame_required_response(domain), output_view)
        try:
            full_plan = OAGV2Planner(
                ontology_repository=self.ontology_repository,
                graph_repository=self.graph_repository,
                domain=self.domain,
                intent_profiles=self.intent_profiles,
                skills=self.ontology_repository.get_skill_capabilities(domain),
            ).plan(
                semantic_frame=semantic_frame,
                raw_question=raw_question,
                recognized_intents=recognized_intents,
                selector_mode=selector_mode,
                planning_options=planning_options or {},
                user_context=user_context or {},
            )
            return project_plan(full_plan, output_view)
        except (OAGRepositoryError, ValueError) as exc:
            full_plan = _task_planning_error_response(domain=domain, semantic_frame=semantic_frame, message=str(exc))
            return project_plan(full_plan, output_view)

    def _retrieve_context_legacy(
        self,
        question: str,
        intent: str | dict[str, Any] = "structured_query",
        domain: str | None = None,
        user_context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """旧版自然语言大图召回链路，保留为内部参考，不作为正式入口调用。"""

        if isinstance(intent, dict) and user_context is None:
            user_context = intent
            intent = "structured_query"
        if not isinstance(intent, str):
            intent = "structured_query"
        domain = domain or self.domain
        try:
            if not question or not question.strip():
                raise ValueError("question must not be empty")
            opts = _merge_options(user_context, options)
            detail_level = str(opts["detail_level"])
            debug = bool(opts["debug"])
            budget = OUTPUT_BUDGETS[detail_level]
            self._ensure_ready(domain)

            # 对象召回先处理问句里显式出现的基金代码，再用别名检索补充候选实体。
            entities = self._match_objects(domain, question, int(opts["top_k_objects"]))
            attributes = self._match_attributes(domain, question)
            param_result = extract_params(question, matched_objects=entities)
            resolved_params = dict(param_result.params)
            params = resolved_params
            intent_result = IntentMatcher(self.intent_profiles or []).match(
                question=question,
                resolved_params=resolved_params,
                explicit_attributes=attributes,
            )
            inferred_attributes = self._inferred_attributes(
                domain=domain,
                inferred=intent_result.inferred_attributes,
            )
            attributes = _merge_attributes(attributes, inferred_attributes)
            attributes = attributes[: budget["max_matched_attributes"]]
            candidate_queries, query_warnings = self._candidate_queries(
                domain=domain,
                entities=entities,
                attributes=attributes,
                params=params,
                user_context=user_context or {},
                include=bool(opts["include_candidate_queries"]),
                skill_priority_hints=intent_result.skill_priority_hints,
            )
            candidate_queries = candidate_queries[: budget["max_candidate_queries"]]
            candidate_queries = _period_filter_candidate_query_tables(
                candidate_queries, resolved_params.get("period"), detail_level
            )
            candidate_skills = self._candidate_skills(
                domain=domain,
                entities=entities,
                attributes=attributes,
                params=resolved_params,
                user_context=user_context or {},
                include=bool(opts["include_candidate_skills"]),
                skill_priority_hints=intent_result.skill_priority_hints,
            )
            candidate_skills = candidate_skills[: budget["max_candidate_skills"]]
            graph_entities = _graph_seed_entities(
                entities, attributes, candidate_queries, candidate_skills
            )
            # 关系边和路径只提供上下文，不代表最终业务查询一定要沿这些路径执行。
            raw_relations = self.graph_repository.recall_relations(
                domain=domain,
                entities=graph_entities,
                max_hops=int(opts["max_hops"]),
                top_k=int(opts["top_k_paths"]),
            )
            raw_paths = self.graph_repository.recall_paths(
                domain=domain,
                entities=graph_entities,
                max_hops=int(opts["max_hops"]),
                top_k=int(opts["top_k_paths"]),
            )
            output_context = _output_context(
                detail_level=detail_level,
                debug=debug,
                budget=budget,
                resolved_params=resolved_params,
                matched_attributes=attributes,
                candidate_queries=candidate_queries,
                candidate_skills=candidate_skills,
                matched_intents=intent_result.matched_intents,
            )
            relations = _filter_and_limit_relations(raw_relations, output_context)
            paths = _filter_and_limit_paths(raw_paths, output_context)
            target_instances = _target_instances(entities, resolved_params)
            fact_requirements = _fact_requirements(
                matched_intents=intent_result.matched_intents,
                intent_profiles=self.intent_profiles or [],
                matched_attributes=attributes,
                resolved_params=resolved_params,
                target_instances=target_instances,
            )
            fact_groups = _fact_groups(fact_requirements)
            missing_params, missing_warnings = self._missing_params(candidate_queries, params)
            missing_params = _merge_missing_params(
                missing_params,
                _missing_fact_params(fact_requirements, resolved_params),
            )
            candidate_invocations = self._fact_candidate_invocations(
                domain=domain,
                fact_requirements=fact_requirements,
                candidate_skills=candidate_skills,
                params=resolved_params,
                user_context=user_context or {},
            )
            candidate_invocations = _dedupe_and_limit_invocations(
                candidate_invocations, output_context
            )
            confidence = self._confidence(entities, attributes, relations, candidate_queries)
            relation_subgraph = build_relation_subgraph(
                matched_objects=entities,
                matched_attributes=attributes,
                matched_relations=relations,
                relation_paths=paths,
                candidate_queries=candidate_queries,
                candidate_skills=candidate_skills,
                context=output_context,
            )
            retrieval_summary = _retrieval_summary(
                matched_objects=entities,
                matched_attributes=attributes,
                candidate_queries=candidate_queries,
                candidate_skills=candidate_skills,
                matched_relations=relations,
                relation_subgraph=relation_subgraph,
                resolved_params=resolved_params,
                fact_requirements=fact_requirements,
                candidate_invocations=candidate_invocations,
                matched_intents=intent_result.matched_intents,
            )
            truncation = _truncation_info(
                detail_level=detail_level,
                budget=budget,
                raw_relations=raw_relations,
                raw_paths=raw_paths,
                returned_relations=relations,
                returned_paths=paths,
                relation_subgraph=relation_subgraph,
                reasons=output_context["reasons"],
            )
            schema_evidence = _schema_evidence(
                matched_relations=relations,
                relation_paths=paths,
                relation_subgraph=relation_subgraph,
                candidate_queries=candidate_queries,
            )
            response = {
                "status": "success",
                "domain": domain,
                "question": question,
                "intent": intent,
                "matched_objects": entities,
                "matched_intents": intent_result.matched_intents,
                "matched_attributes": attributes,
                "resolved_params": resolved_params,
                "target_instances": target_instances,
                "fact_requirements": fact_requirements,
                "fact_groups": fact_groups,
                "candidate_invocations": candidate_invocations,
                "retrieval_summary": retrieval_summary,
                "truncation": truncation,
                "missing_params": missing_params,
                "confidence": confidence,
                "warnings": [
                    *param_result.warnings,
                    *_intent_warnings(intent_result.matched_intents, inferred_attributes),
                    *query_warnings,
                    *missing_warnings,
                    *_period_expansion_warnings(retrieval_summary),
                ],
                **({"debug_info": output_context["debug_info"]} if debug else {}),
            }
            return _shape_response_for_detail(
                response=response,
                detail_level=detail_level,
                debug=debug,
                candidate_skills=candidate_skills,
                candidate_queries=candidate_queries,
                schema_evidence=schema_evidence,
            )
        except (OAGRepositoryError, ValueError) as exc:
            return error_response(domain=domain, question=question, intent=intent, message=str(exc))

    def _ensure_ready(self, domain: str) -> None:
        """校验领域和三个仓储是否可用。

        这里在每次请求前做 ping，是为了让 MCP 响应能明确告诉调用方底层存储不可用，
        而不是在某个后续查询步骤里返回半成品上下文。
        """

        if domain != SUPPORTED_DOMAIN:
            raise ValueError(f"Unsupported domain: {domain}")
        self.ontology_repository.ping()
        self.text_repository.ping()
        self.graph_repository.ping()
        if not self.ontology_repository.domain_enabled(domain):
            raise ValueError(f"Domain is not enabled: {domain}")

    def _match_objects(self, domain: str, question: str, top_k: int) -> list[dict[str, Any]]:
        """召回并去重问句中的业务对象。

        显式基金代码只推断 Fund 对象类型，不制造 Fund:<code> 实例节点；
        具体代码由参数抽取层写入 resolved_params.fund_code。
        """

        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        explicit_codes = extract_fund_codes(question)
        if explicit_codes:
            seen.add(("ObjectType", "Fund"))
            rows.append(
                {
                    "mention": explicit_codes[0],
                    "node_id": "ObjectType:Fund",
                    "object_type": "Fund",
                    "object_id": "Fund",
                    "object_name": "Fund",
                    "confidence": 0.98,
                    "match_method": "fund_code_param_inference",
                    "params": {},
                    "resolved_params": {"fund_code": explicit_codes[0]},
                }
            )

        for hit in self.text_repository.search_objects(domain, question, top_k):
            object_type = hit.get("object_type")
            object_id = hit.get("object_id")
            if not object_type or not object_id:
                continue
            if object_type == "DataField":
                continue
            if object_type not in ALLOWED_MATCHED_OBJECT_TYPES and object_type != "Fund":
                continue
            mention = _best_mention(question, hit)
            if mention in SHORT_OBJECT_SEARCH_STOPWORDS:
                continue
            if object_type == "Fund" and str(object_id) in explicit_codes:
                continue
            key = (object_type, object_id)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "mention": mention,
                    "object_type": object_type,
                    "object_id": object_id,
                    "object_name": hit.get("object_name", ""),
                    "confidence": _score_to_confidence(hit.get("_score"), base=0.72),
                    "match_method": "text_search",
                    "params": _object_params(hit),
                }
            )
        return rows[:top_k]

    def _match_attributes(self, domain: str, question: str) -> list[dict[str, Any]]:
        """召回属性并用本体元数据补齐标准字段。

        文本仓储负责根据别名找到 attribute_name，本体仓储负责返回权威中文名和
        object_type；seen 用于过滤同一属性的多个别名命中。
        """

        hits = self.text_repository.search_attributes(domain, question, top_k=20)
        names = [hit["attribute_name"] for hit in hits if hit.get("attribute_name")]
        metadata = {
            item["attribute_name"]: item
            for item in self.ontology_repository.get_attributes_by_names(domain, names)
        }
        rows = []
        seen: set[str] = set()
        for hit in hits:
            name = hit.get("attribute_name")
            if not name or name in seen:
                continue
            seen.add(name)
            item = metadata.get(name, hit)
            rows.append(
                {
                    "object_type": item.get("object_type", hit.get("object_type", "")),
                    "attribute_name": name,
                    "attribute_name_zh": item.get("attribute_name_zh", hit.get("attribute_name_zh", "")),
                    "confidence": _score_to_confidence(hit.get("_score"), base=0.78),
                    "match_reason": "alias_matched",
                }
            )
        return rows

    def _inferred_attributes(
        self,
        domain: str,
        inferred: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Enrich intent-inferred attribute names with ontology metadata."""

        names = [item["attribute_name"] for item in inferred if item.get("attribute_name")]
        metadata = {
            item["attribute_name"]: item
            for item in self.ontology_repository.get_attributes_by_names(domain, names)
        }
        rows = []
        for item in inferred:
            name = item.get("attribute_name")
            if not name:
                continue
            meta = metadata.get(name, {})
            rows.append(
                {
                    "object_type": meta.get("object_type", _fallback_attribute_object_type(name)),
                    "attribute_name": name,
                    "attribute_name_zh": meta.get("attribute_name_zh", name),
                    "confidence": item.get("confidence", 0.7),
                    "match_reason": item.get("match_reason", "inferred_by_intent"),
                }
            )
        return rows

    def _candidate_queries(
        self,
        domain: str,
        entities: list[dict[str, Any]],
        attributes: list[dict[str, Any]],
        params: dict[str, Any],
        user_context: dict[str, Any],
        include: bool,
        skill_priority_hints: dict[str, str] | None = None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """根据对象类型、输出属性和权限范围筛选候选查询。

        查询能力需要同时满足：目标对象类型命中、输出属性与问题中识别的属性兼容、
        用户权限包含所需 scope。被权限过滤的查询会生成 warning，便于调用端解释
        为什么没有可执行候选。
        """

        if not include:
            return [], []

        object_types = _target_object_types(entities)
        attribute_names = {attr.get("attribute_name") for attr in attributes}
        permission_scopes = set(user_context.get("permission_scopes") or [])
        hinted_query_ids = self._related_query_ids_for_skills(
            domain=domain,
            skill_ids=set((skill_priority_hints or {}).keys()),
        )
        rows = []
        warnings = []

        for query in self.ontology_repository.get_query_capabilities(domain):
            if query.get("target_object_type") not in object_types:
                continue
            outputs = set(query.get("output_attributes") or [])
            if (
                attribute_names
                and not attribute_names.intersection(outputs)
                and query.get("query_id") not in hinted_query_ids
            ):
                continue
            scope = query.get("permission_scope")
            if scope and scope not in permission_scopes:
                warnings.append(f"当前用户权限范围不包含 {scope}，已过滤候选查询 {query.get('query_id')}")
                continue
            rows.append({**query, "confidence": self._query_confidence(query, params)})

        rows.sort(key=lambda item: item.get("confidence", 0.0), reverse=True)
        return rows, warnings

    def _related_query_ids_for_skills(self, domain: str, skill_ids: set[str]) -> set[str]:
        if not skill_ids:
            return set()
        query_ids: set[str] = set()
        for skill in self.ontology_repository.get_skill_capabilities(domain):
            if skill.get("skill_id") not in skill_ids:
                continue
            query_ids.update(
                skill.get("related_queries")
                or (self.skill_related_queries or {}).get(str(skill.get("skill_id")), [])
            )
        return query_ids

    def _candidate_skills(
        self,
        domain: str,
        entities: list[dict[str, Any]],
        attributes: list[dict[str, Any]],
        params: dict[str, Any],
        user_context: dict[str, Any],
        include: bool,
        skill_priority_hints: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """按与候选查询相同的匹配口径筛选候选技能。

        技能是默认核心输出；调用方仍可用 options.include_candidate_skills=false
        显式关闭。
        """

        if not include:
            return []

        object_types = _target_object_types(entities)
        attribute_names = {attr.get("attribute_name") for attr in attributes}
        permission_scopes = set(user_context.get("permission_scopes") or [])
        skill_priority_hints = skill_priority_hints or {}
        rows = []
        for skill in self.ontology_repository.get_skill_capabilities(domain):
            skill_id = skill.get("skill_id")
            if skill.get("target_object_type") not in object_types:
                continue
            outputs = set(skill.get("output_attributes") or [])
            if (
                attribute_names
                and not attribute_names.intersection(outputs)
                and skill_id not in skill_priority_hints
            ):
                continue
            scope = skill.get("permission_scope")
            if scope and scope not in permission_scopes:
                continue
            input_params = list(skill.get("input_params") or [])
            missing = [name for name in input_params if params.get(name) in (None, "")]
            rows.append(
                {
                    "skill_id": skill["skill_id"],
                    "skill_name": skill.get("skill_name", skill["skill_id"]),
                    "description": skill.get("description", ""),
                    "target_object_type": skill.get("target_object_type"),
                    "input_params": input_params,
                    "output_attributes": skill.get("output_attributes", []),
                    "provides_fact_types": skill.get("provides_fact_types", []),
                    "supported_subject_types": skill.get("supported_subject_types", []),
                    "supported_attributes": skill.get("supported_attributes", []),
                    "output_fact_schema": skill.get("output_fact_schema", []),
                    "supported_constraints": skill.get("supported_constraints", []),
                    "related_queries": skill.get("related_queries")
                    or (self.skill_related_queries or {}).get(str(skill_id), []),
                    "permission_scope": skill.get("permission_scope", ""),
                    "missing_params": missing,
                    "confidence": self._skill_confidence(skill, params),
                    "priority": skill_priority_hints.get(skill_id, "optional"),
                }
            )
        rows.sort(
            key=lambda item: (
                PRIORITY_RANK.get(item.get("priority", "optional"), 99),
                -item.get("confidence", 0.0),
            )
        )
        return rows

    def _missing_params(
        self, candidate_queries: list[dict[str, Any]], params: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """检查候选查询所需但尚未解析到的必填参数。"""

        rows = []
        warnings = []
        for query in candidate_queries:
            missing = [
                param
                for param in query.get("required_params", [])
                if params.get(param) in (None, "")
            ]
            if not missing:
                continue
            rows.append(
                {
                    "query_id": query["query_id"],
                    "missing_params": missing,
                    "suggested_question": _suggested_question(missing),
                }
            )
            warnings.append(f"候选查询缺少必要参数：{', '.join(missing)}")
        return rows, warnings

    def _fact_candidate_invocations(
        self,
        domain: str,
        fact_requirements: list[dict[str, Any]],
        candidate_skills: list[dict[str, Any]],
        params: dict[str, Any],
        user_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build SkillCapability calls that cover fact_requirements."""

        del domain
        permission_scopes = set(user_context.get("permission_scopes") or [])
        candidate_by_id = {item.get("skill_id"): item for item in candidate_skills}
        all_skills = list(candidate_skills)
        known_ids = {item.get("skill_id") for item in all_skills}
        for skill in self.ontology_repository.get_skill_capabilities(self.domain):
            skill_id = skill.get("skill_id")
            if skill_id in known_ids:
                continue
            scope = skill.get("permission_scope")
            if scope and scope not in permission_scopes:
                continue
            all_skills.append(skill)
            known_ids.add(skill_id)

        explicit_fact_skills = [skill for skill in all_skills if skill.get("provides_fact_types")]
        skills_to_consider = explicit_fact_skills or all_skills

        rows = []
        for skill in skills_to_consider:
            covered = _skill_covers_fact_requirements(skill, fact_requirements)
            if not covered:
                continue
            input_params = list(skill.get("input_params") or [])
            attribute_names = _unique(
                req.get("attribute", {}).get("attribute_name")
                for req in covered
                if req.get("attribute", {}).get("attribute_name")
            )
            invocation_params = {
                name: params[name]
                for name in input_params
                if name != "attributes" and params.get(name) not in (None, "")
            }
            if "attributes" in input_params:
                invocation_params["attributes"] = attribute_names
            missing = [
                name
                for name in input_params
                if name != "attributes" and params.get(name) in (None, "")
            ]
            if "attributes" in input_params and not attribute_names:
                missing.append("attributes")
            candidate = candidate_by_id.get(skill.get("skill_id"), {})
            priority = candidate.get("priority") or _fact_invocation_priority(covered)
            rows.append(
                {
                    "capability_type": "skill",
                    "skill_id": skill.get("skill_id"),
                    "tool_type": "SkillCapability",
                    "tool_name": skill.get("skill_id", ""),
                    "priority": priority,
                    "covers_fact_requirements": [
                        item["fact_requirement_id"] for item in covered
                    ],
                    "params": invocation_params,
                    "expected_facts": [
                        {
                            "fact_type": item.get("fact_type"),
                            "attribute_name": item.get("attribute", {}).get("attribute_name"),
                        }
                        for item in covered
                    ],
                    "missing_params": missing,
                    "confidence": _fact_skill_confidence(skill, covered, missing),
                    "match_reasons": _fact_invocation_reasons(skill, covered, invocation_params, missing),
                }
            )
        return rows

    def _candidate_invocations(
        self,
        candidate_queries: list[dict[str, Any]],
        candidate_skills: list[dict[str, Any]],
        params: dict[str, Any],
        attributes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """把候选查询转换为可执行调用建议。

        只把 required/optional 中已解析且非空的参数写入 params；缺失必填参数单独
        列出，调用端可以据此追问用户或暂缓执行。
        """

        attribute_names = {attr.get("attribute_name") for attr in attributes}
        rows = []
        for query in candidate_queries:
            required_params = list(query.get("required_params") or [])
            optional_params = list(query.get("optional_params") or [])
            accepted_params = [*required_params, *optional_params]
            invocation_params = {
                name: params[name]
                for name in accepted_params
                if params.get(name) not in (None, "")
            }
            missing = [
                name
                for name in required_params
                if params.get(name) in (None, "")
            ]
            confidence = query.get("confidence")
            if confidence is None:
                confidence = self._query_confidence(query, params)

            rows.append(
                {
                    "capability_type": "query",
                    "query_id": query.get("query_id"),
                    "tool_type": query.get("tool_type", ""),
                    "tool_name": query.get("tool_name", ""),
                    "priority": _query_invocation_priority(query, candidate_skills),
                    "params": invocation_params,
                    "missing_params": missing,
                    "confidence": confidence,
                    "match_reasons": _candidate_invocation_reasons(
                        query=query,
                        attribute_names=attribute_names,
                        resolved_param_names=set(invocation_params),
                        missing_params=missing,
                    ),
                }
            )
        for skill in candidate_skills:
            input_params = list(skill.get("input_params") or [])
            invocation_params = {
                name: params[name]
                for name in input_params
                if params.get(name) not in (None, "")
            }
            missing = [name for name in input_params if params.get(name) in (None, "")]
            rows.append(
                {
                    "capability_type": "skill",
                    "skill_id": skill.get("skill_id"),
                    "tool_type": "SkillCapability",
                    "tool_name": skill.get("skill_id", ""),
                    "priority": skill.get("priority", "optional"),
                    "related_queries": skill.get("related_queries", []),
                    "params": invocation_params,
                    "missing_params": missing,
                    "confidence": skill.get("confidence", self._skill_confidence(skill, params)),
                    "match_reasons": _candidate_invocation_reasons(
                        query={
                            "target_object_type": skill.get("target_object_type"),
                            "output_attributes": skill.get("output_attributes", []),
                            "required_params": input_params,
                            "permission_scope": skill.get("permission_scope", ""),
                        },
                        attribute_names=attribute_names,
                        resolved_param_names=set(invocation_params),
                        missing_params=missing,
                    ),
                }
            )
        return rows

    def _query_confidence(self, query: dict[str, Any], params: dict[str, Any]) -> float:
        """根据必填参数覆盖率给候选查询打分。"""

        required = query.get("required_params") or []
        if not required:
            return 0.9
        present = sum(1 for param in required if params.get(param) not in (None, ""))
        return round(0.75 + 0.2 * (present / len(required)), 3)

    def _skill_confidence(self, skill: dict[str, Any], params: dict[str, Any]) -> float:
        """Score a candidate skill by resolved input parameter coverage."""

        required = skill.get("input_params") or []
        if not required:
            return 0.9
        present = sum(1 for param in required if params.get(param) not in (None, ""))
        return round(0.75 + 0.2 * (present / len(required)), 3)

    def _confidence(
        self,
        entities: list[dict[str, Any]],
        attributes: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        candidate_queries: list[dict[str, Any]],
    ) -> dict[str, float]:
        """汇总对象、属性、关系和查询四类匹配置信度。"""

        entity_match = max([item.get("confidence", 0.0) for item in entities] or [0.0])
        attribute_match = max([item.get("confidence", 0.0) for item in attributes] or [0.0])
        relation_match = max([item.get("score", 0.0) for item in relations] or [0.0])
        query_match = max([item.get("confidence", 0.0) for item in candidate_queries] or [0.0])
        overall = round(
            entity_match * 0.35
            + attribute_match * 0.25
            + relation_match * 0.2
            + query_match * 0.2,
            3,
        )
        return {
            "overall": overall,
            "entity_match": round(entity_match, 3),
            "attribute_match": round(attribute_match, 3),
            "relation_match": round(relation_match, 3),
            "query_match": round(query_match, 3),
        }


def create_context_service() -> OAGContextService:
    """根据环境配置创建默认 OAGContextService。

    生产入口使用 MySQL/TDSQL 仓储；单元测试通常直接构造 OAGContextService 并注入
    Fake 仓储，避免依赖真实数据库。
    """

    config = load_config()
    return OAGContextService(
        ontology_repository=MySQLMetadataRepository(config.tdsql),
        text_repository=MySQLTextRepository(config.tdsql),
        graph_repository=MySQLGraphRepository(config.tdsql),
        domain=config.domain,
    )


def error_response(domain: str, question: str, intent: str, message: str) -> dict[str, Any]:
    """构造与成功响应同形状的错误响应。

    返回固定空列表/空图/零置信度，可以减少 MCP 客户端在错误分支上的字段判断。
    """

    return {
        "status": "error",
        "domain": domain,
        "question": question,
        "intent": intent,
        "matched_objects": [],
        "matched_intents": [],
        "matched_attributes": [],
        "matched_relations": [],
        "relation_paths": [],
        "relation_subgraph": {
            "nodes": [],
            "edges": [],
            "paths": [],
        },
        "candidate_queries": [],
        "resolved_params": {},
        "target_instances": [],
        "fact_requirements": [],
        "fact_groups": [],
        "candidate_invocations": [],
        "candidate_skills": [],
        "retrieval_summary": {},
        "truncation": {"truncated": False},
        "missing_params": [],
        "confidence": {
            "overall": 0.0,
            "entity_match": 0.0,
            "attribute_match": 0.0,
            "relation_match": 0.0,
            "query_match": 0.0,
        },
        "warnings": [message],
    }


def _task_planning_error_response(
    domain: str, semantic_frame: dict[str, Any], message: str
) -> dict[str, Any]:
    return {
        "status": "error",
        "domain": domain,
        "raw_question": semantic_frame.get("raw_question") or "",
        "error_code": "OAG_TASK_PLANNING_FAILED",
        "message_zh": f"OAG 事实规划失败：{message}",
        "semantic_frame_summary": {
            "task_type": semantic_frame.get("task_type"),
            "intent": semantic_frame.get("intent"),
            "target_objects": semantic_frame.get("target_objects") or [],
            "constraints": semantic_frame.get("constraints") or {},
        },
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
        },
        "missing_params": [],
        "warnings": [
            {
                "warning_code": "TASK_PLANNING_EXCEPTION",
                "message_zh": f"OAG 事实规划过程中发生异常：{message}",
            }
        ],
    }


def _merge_options(
    user_context: dict[str, Any] | None,
    options: dict[str, Any] | None,
) -> dict[str, Any]:
    """合并调用方 user_context/options 与默认召回选项。"""

    context_options = {
        key: value
        for key, value in (user_context or {}).items()
        if key in {"detail_level", "debug"}
    }
    merged = {**DEFAULT_OPTIONS, **context_options, **(options or {})}
    detail_level = str(merged.get("detail_level") or "compact").lower()
    if detail_level not in OUTPUT_BUDGETS:
        detail_level = "compact"
    merged["detail_level"] = detail_level
    merged["debug"] = bool(merged.get("debug"))
    return merged


def _graph_seed_entities(
    entities: list[dict[str, Any]],
    attributes: list[dict[str, Any]],
    candidate_queries: list[dict[str, Any]],
    candidate_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add schema-level start nodes for graph recall."""

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(object_type: str, object_id: str) -> None:
        if not object_type or not object_id:
            return
        key = (object_type, object_id)
        if key in seen:
            return
        seen.add(key)
        rows.append({"object_type": object_type, "object_id": object_id})

    for entity in entities:
        if entity.get("object_type") in ALLOWED_MATCHED_OBJECT_TYPES:
            add(str(entity.get("object_type") or ""), str(entity.get("object_id") or ""))
        else:
            add("ObjectType", _target_object_type(entity))
    for attribute in attributes:
        add("Attribute", str(attribute.get("attribute_name") or ""))
    for query in candidate_queries:
        add("QueryCapability", str(query.get("query_id") or ""))
    for skill in candidate_skills:
        add("SkillCapability", str(skill.get("skill_id") or ""))
    return rows


def _merge_attributes(
    explicit_attributes: list[dict[str, Any]],
    inferred_attributes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = list(explicit_attributes)
    seen = {item.get("attribute_name") for item in rows if item.get("attribute_name")}
    for item in inferred_attributes:
        name = item.get("attribute_name")
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append(item)
    return rows


FACT_REQUIREMENT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "performance_overview": [
        {
            "attribute_name": "return_rate",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "required",
            "reason": "用于判断基金近一年收益表现",
        },
        {
            "attribute_name": "benchmark_return",
            "fact_type": "benchmark_metric_value",
            "predicate": "has_benchmark_metric_value",
            "priority": "required",
            "reason": "用于判断基金相对业绩比较基准表现",
        },
        {
            "attribute_name": "excess_return",
            "fact_type": "excess_metric_value",
            "predicate": "has_excess_metric_value",
            "priority": "required",
            "reason": "用于判断基金是否跑赢基准",
        },
        {
            "attribute_name": "max_drawdown",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "required",
            "reason": "用于判断基金近一年回撤风险",
        },
        {
            "attribute_name": "volatility",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于辅助判断收益稳定性",
        },
        {
            "attribute_name": "sharpe_ratio",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于辅助判断风险调整后收益",
        },
        {
            "attribute_name": "rank",
            "fact_type": "peer_rank",
            "predicate": "has_peer_rank",
            "priority": "optional",
            "reason": "用于判断同类相对表现",
        },
    ],
    "risk_overview": [
        {
            "attribute_name": "max_drawdown",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "required",
            "reason": "用于判断基金回撤风险",
        },
        {
            "attribute_name": "volatility",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "required",
            "reason": "用于判断基金收益波动风险",
        },
        {
            "attribute_name": "sharpe_ratio",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "required",
            "reason": "用于判断风险调整后收益",
        },
        {
            "attribute_name": "sortino_ratio",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于补充判断下行风险调整后收益",
        },
        {
            "attribute_name": "calmar_ratio",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于补充判断回撤调整后收益",
        },
        {
            "attribute_name": "downside_risk",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于补充判断下行风险",
        },
        {
            "attribute_name": "var",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于补充判断尾部损失风险",
        },
        {
            "attribute_name": "cvar",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "optional",
            "reason": "用于补充判断条件尾部损失风险",
        },
    ],
    "benchmark_comparison": [
        {
            "attribute_name": "return_rate",
            "fact_type": "metric_value",
            "predicate": "has_metric_value",
            "priority": "required",
            "reason": "用于获取基金自身区间收益",
        },
        {
            "attribute_name": "benchmark_return",
            "fact_type": "benchmark_metric_value",
            "predicate": "has_benchmark_metric_value",
            "priority": "required",
            "reason": "用于获取同期业绩比较基准收益",
        },
        {
            "attribute_name": "excess_return",
            "fact_type": "excess_metric_value",
            "predicate": "has_excess_metric_value",
            "priority": "required",
            "reason": "用于判断基金是否跑赢基准",
        },
        {
            "attribute_name": "tracking_error",
            "fact_type": "benchmark_metric_value",
            "predicate": "has_benchmark_metric_value",
            "priority": "optional",
            "reason": "用于补充判断相对基准的偏离程度",
        },
        {
            "attribute_name": "information_ratio",
            "fact_type": "benchmark_metric_value",
            "predicate": "has_benchmark_metric_value",
            "priority": "optional",
            "reason": "用于补充判断主动收益效率",
        },
    ],
    "peer_comparison": [
        {
            "attribute_name": "rank",
            "fact_type": "peer_rank",
            "predicate": "has_peer_rank",
            "priority": "required",
            "reason": "用于判断基金在同类中的排名表现",
        },
        {
            "attribute_name": "peer_average",
            "fact_type": "peer_average",
            "predicate": "has_peer_average",
            "priority": "optional",
            "reason": "用于补充判断同类平均水平",
        },
    ],
}


def _target_instances(
    matched_objects: list[dict[str, Any]],
    resolved_params: dict[str, Any],
) -> list[dict[str, Any]]:
    fund_code = resolved_params.get("fund_code")
    if not fund_code:
        return []
    confidence = max(
        [
            float(item.get("confidence") or 0.0)
            for item in matched_objects
            if _target_object_type(item) == "Fund"
        ]
        or [0.98]
    )
    return [
        {
            "object_type": "Fund",
            "instance_ref": {"fund_code": fund_code},
            "role": "analysis_subject",
            "source": "fund_code_param_inference",
            "confidence": round(confidence, 3),
        }
    ]


def _fact_requirements(
    matched_intents: list[dict[str, Any]],
    intent_profiles: list[dict[str, Any]],
    matched_attributes: list[dict[str, Any]],
    resolved_params: dict[str, Any],
    target_instances: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    attribute_meta = {
        item.get("attribute_name"): item
        for item in matched_attributes
        if item.get("attribute_name")
    }
    profile_by_name = {
        item.get("intent_name"): item for item in intent_profiles if item.get("intent_name")
    }
    intent_names = [item.get("intent_name") for item in matched_intents if item.get("intent_name")]
    if not intent_names:
        intent_names = ["performance_overview"]

    subject_ref = target_instances[0]["instance_ref"] if target_instances else {}
    subject = {"object_type": "Fund", "instance_ref": dict(subject_ref)}
    period = resolved_params.get("period")
    rows = []
    seen_ids: set[str] = set()
    for intent_name in intent_names:
        templates = _intent_fact_templates(profile_by_name.get(intent_name), str(intent_name))
        for template in templates:
            attribute_name = str(template.get("attribute_name") or "")
            if not attribute_name:
                continue
            requirement_id = _fact_requirement_id(attribute_name, period)
            if requirement_id in seen_ids:
                continue
            seen_ids.add(requirement_id)
            meta = attribute_meta.get(attribute_name, {})
            constraints: dict[str, Any] = {}
            if period:
                constraints["period"] = period
            rows.append(
                {
                    "fact_requirement_id": requirement_id,
                    "fact_type": template.get("fact_type") or _fact_type_for_attribute(attribute_name),
                    "subject": dict(subject),
                    "predicate": template.get("predicate") or _predicate_for_fact_type(
                        str(template.get("fact_type") or "")
                    ),
                    "attribute": {
                        "attribute_name": attribute_name,
                        "attribute_name_zh": meta.get("attribute_name_zh", attribute_name),
                        "object_type": meta.get(
                            "object_type",
                            _fallback_attribute_object_type(attribute_name),
                        ),
                    },
                    "constraints": constraints,
                    "priority": template.get("priority", "optional"),
                    "reason": template.get("reason", "用于回答当前问题所需的本体事实"),
                    "source": f"inferred_by_intent:{intent_name}",
                    "confidence": _fact_requirement_confidence(template, meta),
                    "expected_output": {
                        "value_required": True,
                        "unit_required": True,
                        "as_of_date_required": False,
                    },
                }
            )
    return rows


def _intent_fact_templates(profile: dict[str, Any] | None, intent_name: str) -> list[dict[str, Any]]:
    if (
        profile
        and isinstance(profile.get("fact_requirements_template"), list)
        and profile.get("fact_requirements_template")
    ):
        return list(profile["fact_requirements_template"])
    return list(FACT_REQUIREMENT_TEMPLATES.get(intent_name) or [])


def _fact_requirement_id(attribute_name: str, period: Any) -> str:
    suffix = _normalize_period(period) or "unspecified_period"
    return f"fr_{attribute_name}_{suffix}"


def _fact_requirement_confidence(template: dict[str, Any], meta: dict[str, Any]) -> float:
    if meta.get("confidence") is not None:
        return round(min(0.95, float(meta.get("confidence") or 0.0)), 3)
    return 0.82 if template.get("priority") == "required" else 0.76


def _fact_type_for_attribute(attribute_name: str) -> str:
    if attribute_name in {"benchmark_return", "tracking_error", "information_ratio"}:
        return "benchmark_metric_value"
    if attribute_name == "excess_return":
        return "excess_metric_value"
    if attribute_name in {"rank", "peer_return_rank", "peer_risk_rank", "peer_sharpe_rank", "peer_drawdown_rank"}:
        return "peer_rank"
    if attribute_name == "peer_average":
        return "peer_average"
    if attribute_name in {"fund_name", "fund_category", "fund_company", "fund_manager", "benchmark"}:
        return "object_profile"
    return "metric_value"


def _predicate_for_fact_type(fact_type: str) -> str:
    predicates = {
        "benchmark_metric_value": "has_benchmark_metric_value",
        "excess_metric_value": "has_excess_metric_value",
        "peer_rank": "has_peer_rank",
        "peer_average": "has_peer_average",
        "object_profile": "has_profile_fact",
        "relation_instance": "has_relation_instance",
    }
    return predicates.get(fact_type, "has_metric_value")


def _fact_groups(fact_requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids_by_type: dict[str, list[str]] = {}
    for item in fact_requirements:
        ids_by_type.setdefault(str(item.get("fact_type") or ""), []).append(
            item["fact_requirement_id"]
        )
    groups = []
    return_ids = [
        item["fact_requirement_id"]
        for item in fact_requirements
        if item.get("attribute", {}).get("attribute_name")
        in {"return_rate", "benchmark_return", "excess_return"}
    ]
    risk_ids = [
        item["fact_requirement_id"]
        for item in fact_requirements
        if item.get("attribute", {}).get("attribute_name")
        in {"max_drawdown", "volatility", "sharpe_ratio", "sortino_ratio", "calmar_ratio", "downside_risk", "var", "cvar"}
    ]
    peer_ids = [*ids_by_type.get("peer_rank", []), *ids_by_type.get("peer_average", [])]
    if return_ids:
        groups.append(
            {
                "group_id": "fg_return_performance",
                "group_name": "收益表现事实",
                "purpose": "判断基金区间收益表现",
                "fact_requirement_ids": return_ids,
                "priority": "required",
            }
        )
    if risk_ids:
        groups.append(
            {
                "group_id": "fg_risk_performance",
                "group_name": "风险表现事实",
                "purpose": "判断基金区间风险水平",
                "fact_requirement_ids": risk_ids,
                "priority": "required",
            }
        )
    if peer_ids:
        groups.append(
            {
                "group_id": "fg_peer_comparison",
                "group_name": "同类比较事实",
                "purpose": "判断基金在同类中的相对表现",
                "fact_requirement_ids": peer_ids,
                "priority": "optional",
            }
        )
    return groups


def _missing_fact_params(
    fact_requirements: list[dict[str, Any]],
    resolved_params: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for param_name in ("fund_code", "period"):
        if resolved_params.get(param_name) not in (None, ""):
            continue
        requirement_ids = [
            item["fact_requirement_id"]
            for item in fact_requirements
            if _fact_requirement_needs_param(item, param_name)
        ]
        if not requirement_ids:
            continue
        rows.append(
            {
                "source": "fact_requirements",
                "param_name": param_name,
                "missing_params": [param_name],
                "fact_requirement_ids": requirement_ids,
                "suggested_question": _suggested_question([param_name]),
            }
        )
    return rows


def _fact_requirement_needs_param(item: dict[str, Any], param_name: str) -> bool:
    if param_name == "fund_code":
        return item.get("subject", {}).get("object_type") == "Fund"
    if param_name == "period":
        return item.get("fact_type") in {
            "metric_value",
            "benchmark_metric_value",
            "excess_metric_value",
            "peer_rank",
            "peer_average",
            "metric_ranking",
            "filter_condition",
        }
    return False


def _merge_missing_params(
    current: list[dict[str, Any]],
    additional: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = list(current)
    seen = {
        (item.get("source", "candidate_queries"), tuple(item.get("missing_params") or []))
        for item in rows
    }
    for item in additional:
        key = (item.get("source"), tuple(item.get("missing_params") or []))
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return rows


def _intent_warnings(
    matched_intents: list[dict[str, Any]],
    inferred_attributes: list[dict[str, Any]],
) -> list[str]:
    intent_names = {item.get("intent_name") for item in matched_intents}
    if "performance_overview" in intent_names and inferred_attributes:
        return [
            "问题未显式指定具体指标，已按基金综合表现分析默认补全收益、风险、基准和排名相关指标。"
        ]
    return []


def _fallback_attribute_object_type(attribute_name: str) -> str:
    if attribute_name in {"rank", "percentile"} or "rank" in attribute_name:
        return "PeerRanking"
    if attribute_name in {
        "max_drawdown",
        "volatility",
        "sharpe_ratio",
        "downside_deviation",
        "var",
        "calmar_ratio",
        "tracking_error",
        "information_ratio",
    }:
        return "RiskMetric"
    return "PerformanceMetric"


def _attribute_node(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("attribute_name") or "")
    return {
        "object_type": "Attribute",
        "object_id": name,
        "object_name": item.get("attribute_name_zh", name),
    }


def _query_invocation_priority(
    query: dict[str, Any],
    candidate_skills: list[dict[str, Any]],
) -> str:
    query_id = query.get("query_id")
    priority = "optional"
    for skill in candidate_skills:
        if query_id in (skill.get("related_queries") or []):
            skill_priority = skill.get("priority", "optional")
            if PRIORITY_RANK.get(skill_priority, 99) < PRIORITY_RANK.get(priority, 99):
                priority = skill_priority
    return priority


def _skill_covers_fact_requirements(
    skill: dict[str, Any],
    fact_requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    provides = set(skill.get("provides_fact_types") or [])
    supported_subjects = set(skill.get("supported_subject_types") or [])
    supported_attributes = set(skill.get("supported_attributes") or [])
    if not provides:
        provides = _infer_skill_fact_types(skill)
    if not supported_subjects and skill.get("target_object_type"):
        supported_subjects = {str(skill.get("target_object_type"))}
    if not supported_attributes:
        supported_attributes = set(skill.get("output_attributes") or [])

    rows = []
    for requirement in fact_requirements:
        fact_type = requirement.get("fact_type")
        subject_type = requirement.get("subject", {}).get("object_type")
        attribute_name = requirement.get("attribute", {}).get("attribute_name")
        if provides and fact_type not in provides:
            continue
        if supported_subjects and subject_type not in supported_subjects:
            continue
        if supported_attributes and attribute_name not in supported_attributes:
            continue
        rows.append(requirement)
    return rows


def _infer_skill_fact_types(skill: dict[str, Any]) -> set[str]:
    rows = set()
    for attribute_name in skill.get("output_attributes") or []:
        rows.add(_fact_type_for_attribute(str(attribute_name)))
    return rows


def _fact_invocation_priority(requirements: list[dict[str, Any]]) -> str:
    if any(item.get("priority") == "required" for item in requirements):
        return "primary"
    return "optional"


def _fact_skill_confidence(
    skill: dict[str, Any],
    covered: list[dict[str, Any]],
    missing: list[str],
) -> float:
    if missing:
        return 0.72
    provides = set(skill.get("provides_fact_types") or [])
    supported_attributes = set(skill.get("supported_attributes") or [])
    fact_types = {item.get("fact_type") for item in covered}
    attributes = {
        item.get("attribute", {}).get("attribute_name")
        for item in covered
        if item.get("attribute", {}).get("attribute_name")
    }
    metadata_bonus = 0.03 if provides.intersection(fact_types) else 0.0
    attribute_bonus = 0.02 if supported_attributes.intersection(attributes) else 0.0
    return round(min(0.97, 0.9 + metadata_bonus + attribute_bonus), 3)


def _fact_invocation_reasons(
    skill: dict[str, Any],
    covered: list[dict[str, Any]],
    params: dict[str, Any],
    missing: list[str],
) -> list[str]:
    fact_types = _unique(item.get("fact_type") for item in covered if item.get("fact_type"))
    attributes = _unique(
        item.get("attribute", {}).get("attribute_name")
        for item in covered
        if item.get("attribute", {}).get("attribute_name")
    )
    reasons = []
    if fact_types:
        reasons.append(f"provides_fact_types covered: {','.join(fact_types)}")
    if attributes:
        reasons.append(f"supported_attributes covered: {','.join(attributes)}")
    resolved = [name for name in (skill.get("input_params") or []) if name in params]
    if resolved:
        reasons.append(f"required_params resolved: {','.join(resolved)}")
    if missing:
        reasons.append(f"required_params missing: {','.join(missing)}")
    return reasons


def _target_object_types(entities: list[dict[str, Any]]) -> set[str]:
    """Return business object types implied by matched schema objects."""

    return {
        object_type
        for object_type in (_target_object_type(entity) for entity in entities)
        if object_type
    }


def _target_object_type(entity: dict[str, Any]) -> str:
    object_type = str(entity.get("object_type") or "")
    object_id = str(entity.get("object_id") or "")
    if object_type == "ObjectType":
        return object_id
    return object_type


def _output_context(
    detail_level: str,
    debug: bool,
    budget: dict[str, int],
    resolved_params: dict[str, Any],
    matched_attributes: list[dict[str, Any]],
    candidate_queries: list[dict[str, Any]],
    candidate_skills: list[dict[str, Any]],
    matched_intents: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_tables = {
        str(table)
        for query in candidate_queries
        for table in (query.get("source_tables") or [])
        if table
    }
    return {
        "detail_level": detail_level,
        "debug": debug,
        "budget": budget,
        "period": resolved_params.get("period"),
        "attribute_names": {
            item.get("attribute_name") for item in matched_attributes if item.get("attribute_name")
        },
        "query_ids": {item.get("query_id") for item in candidate_queries if item.get("query_id")},
        "skill_ids": {item.get("skill_id") for item in candidate_skills if item.get("skill_id")},
        "candidate_tables": candidate_tables,
        "intent_names": {
            item.get("intent_name") for item in matched_intents if item.get("intent_name")
        },
        "reasons": set(),
        "debug_info": {
            "detail_level": detail_level,
            "period": resolved_params.get("period"),
            "filters": [
                "matched_objects_exclude_datafield",
                "period_aware_datafield_filter",
                "max_fields_per_attribute",
                "max_fields_per_table",
                "relation_path_budget",
                "relation_subgraph_budget",
            ],
            "candidate_query_ids": [item.get("query_id") for item in candidate_queries],
            "candidate_skill_ids": [item.get("skill_id") for item in candidate_skills],
        },
    }


def _schema_evidence(
    matched_relations: list[dict[str, Any]],
    relation_paths: list[dict[str, Any]],
    relation_subgraph: dict[str, list[dict[str, Any]]],
    candidate_queries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "matched_relations": matched_relations,
        "relation_paths": relation_paths,
        "relation_subgraph": relation_subgraph,
        "candidate_queries": candidate_queries,
    }


def _schema_evidence_summary(schema_evidence: dict[str, Any]) -> dict[str, Any]:
    subgraph = schema_evidence.get("relation_subgraph") or {}
    return {
        "evidence_available": bool(
            schema_evidence.get("matched_relations")
            or schema_evidence.get("relation_paths")
            or subgraph.get("nodes")
        ),
        "matched_relation_count": len(schema_evidence.get("matched_relations") or []),
        "relation_path_count": len(schema_evidence.get("relation_paths") or []),
        "subgraph_node_count": len(subgraph.get("nodes") or []),
        "subgraph_edge_count": len(subgraph.get("edges") or []),
        "debug_required_for_details": True,
    }


def _candidate_queries_summary(candidate_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "query_id": item.get("query_id"),
            "target_object_type": item.get("target_object_type"),
            "output_attributes": item.get("output_attributes", []),
            "required_params": item.get("required_params", []),
            "permission_scope": item.get("permission_scope", ""),
        }
        for item in candidate_queries
    ]


def _shape_response_for_detail(
    response: dict[str, Any],
    detail_level: str,
    debug: bool,
    candidate_skills: list[dict[str, Any]],
    candidate_queries: list[dict[str, Any]],
    schema_evidence: dict[str, Any],
) -> dict[str, Any]:
    if detail_level == "compact" and not debug:
        return response
    shaped = dict(response)
    if detail_level == "standard" and not debug:
        shaped["candidate_skills"] = candidate_skills
        shaped["candidate_queries_summary"] = _candidate_queries_summary(candidate_queries)
        shaped["schema_evidence_summary"] = _schema_evidence_summary(schema_evidence)
        return shaped
    shaped["candidate_skills"] = candidate_skills
    shaped["candidate_queries"] = candidate_queries
    shaped["matched_relations"] = schema_evidence["matched_relations"]
    shaped["relation_paths"] = schema_evidence["relation_paths"]
    shaped["relation_subgraph"] = schema_evidence["relation_subgraph"]
    shaped["schema_evidence"] = schema_evidence
    return shaped


def _period_filter_candidate_query_tables(
    candidate_queries: list[dict[str, Any]],
    period: Any,
    detail_level: str,
) -> list[dict[str, Any]]:
    normalized = _normalize_period(period)
    if not normalized or detail_level == "full":
        return candidate_queries
    rows: list[dict[str, Any]] = []
    for query in candidate_queries:
        source_tables = query.get("source_tables")
        if not isinstance(source_tables, list):
            rows.append(query)
            continue
        filtered = []
        for table in source_tables:
            table_period = _period_code_from_text(str(table))
            if not table_period or table_period == normalized:
                filtered.append(table)
        rows.append({**query, "source_tables": filtered})
    return rows


def _filter_and_limit_relations(
    relations: list[dict[str, Any]], context: dict[str, Any]
) -> list[dict[str, Any]]:
    budget = context["budget"]
    detail_level = context["detail_level"]
    ranked: list[dict[str, Any]] = []
    for relation in relations:
        edge = _ensure_edge_id(dict(relation))
        if _drop_relation(edge, context):
            continue
        edge["_rank_score"] = _relation_rank_score(edge, context)
        ranked.append(edge)

    ranked.sort(key=lambda item: item.get("_rank_score", 0.0), reverse=True)
    selected: list[dict[str, Any]] = []
    fields_by_attribute: dict[str, int] = {}
    fields_by_table: dict[str, int] = {}
    for edge in ranked:
        relation_type = edge.get("relation_type")
        if relation_type == "mapped_to_field":
            attr = _edge_attribute_id(edge)
            if attr:
                count = fields_by_attribute.get(attr, 0)
                if count >= budget["max_fields_per_attribute"]:
                    context["reasons"].add("max_fields_per_attribute")
                    continue
                fields_by_attribute[attr] = count + 1
        if relation_type == "has_field":
            table = _edge_table_id(edge)
            if table:
                count = fields_by_table.get(table, 0)
                if count >= budget["max_fields_per_table"]:
                    context["reasons"].add("max_fields_per_table")
                    continue
                fields_by_table[table] = count + 1
        selected.append(_relation_for_output(edge, detail_level))
        if len(selected) >= budget["max_matched_relations"]:
            context["reasons"].add("output_budget")
            break
    return selected


def _filter_and_limit_paths(paths: list[dict[str, Any]], context: dict[str, Any]) -> list[dict[str, Any]]:
    budget = context["budget"]
    detail_level = context["detail_level"]
    ranked: list[dict[str, Any]] = []
    for path in paths:
        if _drop_path(path, context):
            continue
        item = dict(path)
        item["_rank_score"] = _path_rank_score(path, context)
        ranked.append(item)
    ranked.sort(key=lambda item: item.get("_rank_score", 0.0), reverse=True)

    selected: list[dict[str, Any]] = []
    per_start: dict[str, int] = {}
    for path in ranked:
        nodes = [str(node) for node in (path.get("path") or path.get("nodes") or [])]
        start = nodes[0] if nodes else ""
        if start:
            count = per_start.get(start, 0)
            if count >= budget["max_paths_per_start_node"]:
                context["reasons"].add("max_paths_per_start_node")
                continue
            per_start[start] = count + 1
        selected.append(_path_for_output(path, detail_level))
        if len(selected) >= budget["max_relation_paths"]:
            context["reasons"].add("output_budget")
            break
    return selected


def _drop_relation(edge: dict[str, Any], context: dict[str, Any]) -> bool:
    detail_level = context["detail_level"]
    relation_type = edge.get("relation_type")
    if detail_level == "compact" and relation_type == "joins_on":
        context["reasons"].add("path_pruning")
        return True
    if detail_level == "compact" and _has_period_template_token(edge):
        context["reasons"].add("period_template_filter")
        return True
    if detail_level == "compact" and _period_mismatch(edge, context.get("period")):
        context["reasons"].add("period_filter")
        return True
    if not _edge_has_datafield(edge):
        return False
    field_id = _edge_datafield_id(edge)
    if detail_level != "full" and _is_noise_field(field_id):
        context["reasons"].add("datafield_noise_filter")
        return True
    if detail_level == "compact" and relation_type == "has_field":
        table = _edge_table_id(edge)
        if _is_dim_fund_info_table(table) and not _is_core_dim_fund_field(field_id):
            context["reasons"].add("datafield_noise_filter")
            return True
    return False


def _drop_path(path: dict[str, Any], context: dict[str, Any]) -> bool:
    detail_level = context["detail_level"]
    nodes = [str(node) for node in (path.get("path") or path.get("nodes") or [])]
    edges = path.get("edges") or []
    if detail_level == "compact" and any(_path_has_generic_field_expansion(nodes, edges)):
        context["reasons"].add("path_pruning")
        return True
    if detail_level == "compact" and (
        any(_has_period_template_token(node) for node in nodes)
        or any(_has_period_template_token(edge) for edge in edges if isinstance(edge, dict))
    ):
        context["reasons"].add("period_template_filter")
        return True
    if detail_level == "compact" and (
        any(_period_mismatch(node, context.get("period")) for node in nodes)
        or any(_period_mismatch(edge, context.get("period")) for edge in edges if isinstance(edge, dict))
    ):
        context["reasons"].add("period_filter")
        return True
    if detail_level != "full" and any(_is_noise_field(node) for node in nodes):
        context["reasons"].add("datafield_noise_filter")
        return True
    return False


def _path_has_generic_field_expansion(nodes: list[str], edges: list[Any]) -> list[bool]:
    results = []
    lowered_nodes = [node.lower() for node in nodes]
    has_dim_table = any("datatable:dim_fund_info" == node for node in lowered_nodes)
    has_field = any(node.startswith("datafield:") for node in lowered_nodes)
    results.append(has_dim_table and has_field)
    for edge in edges:
        if isinstance(edge, dict) and edge.get("relation_type") == "has_field":
            table = _edge_table_id(edge)
            field = _edge_datafield_id(edge)
            results.append(_is_dim_fund_info_table(table) and not _is_core_dim_fund_field(field))
    return results


def _relation_rank_score(edge: dict[str, Any], context: dict[str, Any]) -> float:
    score = _numeric_score(edge.get("score"))
    relation_type = str(edge.get("relation_type") or "")
    score += max(0, 10 - _relation_type_priority(relation_type))
    text = f"{edge.get('from', '')} {edge.get('to', '')}".lower()
    if any(table in text for table in CORE_TABLE_HINTS):
        score += 3.0
    if any(f"attribute:{attr}" in text for attr in context["attribute_names"]):
        score += 2.0
    datafield = _edge_datafield_id(edge)
    edge_period = _period_code(edge)
    if edge_period and edge_period == _normalize_period(context.get("period")):
        score += 5.0
    elif edge_period and context.get("period"):
        score -= 6.0
    elif datafield:
        if _is_period_match_field(datafield, context.get("period")):
            score += 2.0
        elif _is_period_mismatch_field(datafield, context.get("period")):
            score -= 5.0
    if "peer" in text and "peer_comparison" not in context["intent_names"]:
        score -= 1.0
    if any(value in text for value in ("benchmark", "bm_", "index", "idx_")) and (
        "benchmark_comparison" not in context["intent_names"]
        and "performance_overview" not in context["intent_names"]
    ):
        score -= 1.0
    return score


def _path_rank_score(path: dict[str, Any], context: dict[str, Any]) -> float:
    score = _numeric_score(path.get("score"))
    for edge in path.get("edges") or []:
        if isinstance(edge, dict):
            score += _relation_rank_score(edge, context) / 10
    for node in path.get("path") or path.get("nodes") or []:
        node_text = str(node).lower()
        if any(table in node_text for table in CORE_TABLE_HINTS):
            score += 2.0
        if any(f"attribute:{attr}" in node_text for attr in context["attribute_names"]):
            score += 1.0
        node_period = _period_code(node)
        if node_period and node_period == _normalize_period(context.get("period")):
            score += 3.0
        elif node_period and context.get("period"):
            score -= 4.0
        elif _is_period_match_field(node_text, context.get("period")):
            score += 2.0
        elif _is_period_mismatch_field(node_text, context.get("period")):
            score -= 3.0
    return score


def _relation_for_output(edge: dict[str, Any], detail_level: str) -> dict[str, Any]:
    result = {
        "edge_id": edge["edge_id"],
        "from": edge.get("from", ""),
        "to": edge.get("to", ""),
        "relation_type": edge.get("relation_type", ""),
        "score": _numeric_score(edge.get("score")),
    }
    if detail_level in {"standard", "full"} and edge.get("relation_name_zh"):
        result["relation_name_zh"] = edge["relation_name_zh"]
    period_code = _period_code(edge)
    if period_code:
        result["period_code"] = period_code
    if detail_level == "full":
        if isinstance(edge.get("properties"), dict) and edge["properties"]:
            result["properties"] = dict(edge["properties"])
        datafield = _edge_datafield_id(edge)
        if datafield and _is_period_mismatch_field(datafield, None):
            result.setdefault("properties", {})["period_mismatch"] = True
    return result


def _path_for_output(path: dict[str, Any], detail_level: str) -> dict[str, Any]:
    edges = path.get("edges") or []
    if detail_level == "compact":
        output_edges: list[Any] = [
            _ensure_edge_id(dict(edge))["edge_id"] if isinstance(edge, dict) else str(edge)
            for edge in edges
        ]
    else:
        output_edges = [
            _relation_for_output(_ensure_edge_id(dict(edge)), detail_level)
            if isinstance(edge, dict)
            else str(edge)
            for edge in edges
        ]
    return {
        "path": list(path.get("path") or path.get("nodes") or []),
        "edges": output_edges,
        "score": _numeric_score(path.get("score")),
    }


def _dedupe_and_limit_invocations(
    invocations: list[dict[str, Any]], context: dict[str, Any]
) -> list[dict[str, Any]]:
    detail_level = context["detail_level"]
    budget = context["budget"]
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[tuple[str, Any], ...]]] = set()
    seen_skill: set[str] = set()
    for item in sorted(invocations, key=_invocation_sort_key):
        capability_type = str(item.get("capability_type") or "")
        capability_id = str(item.get("skill_id") or item.get("query_id") or item.get("tool_name") or "")
        params_key = tuple(
            sorted((key, _hashable_param_value(value)) for key, value in (item.get("params") or {}).items())
        )
        key = (capability_type, capability_id, params_key)
        if key in seen:
            context["reasons"].add("candidate_invocation_dedup")
            continue
        seen.add(key)
        if detail_level == "compact" and capability_type == "skill":
            if capability_id in seen_skill:
                context["reasons"].add("candidate_invocation_dedup")
                continue
            seen_skill.add(capability_id)
        deduped.append(item)

    if detail_level == "compact":
        queries = [item for item in deduped if item.get("capability_type") == "query"]
        skills = [item for item in deduped if item.get("capability_type") == "skill"]
        rows = []
        if queries:
            rows.append(queries[0])
        rows.extend(skills)
        rows.extend(queries[1:])
    else:
        rows = deduped
    if len(rows) > budget["max_candidate_invocations"]:
        context["reasons"].add("output_budget")
    return rows[: budget["max_candidate_invocations"]]


def _invocation_sort_key(item: dict[str, Any]) -> tuple[int, int, float]:
    priority = PRIORITY_RANK.get(item.get("priority", "optional"), 99)
    capability_rank = 0 if item.get("capability_type") == "query" else 1
    return (priority, capability_rank, -_numeric_score(item.get("confidence")))


def _hashable_param_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_hashable_param_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _hashable_param_value(item)) for key, item in value.items()))
    return value


def _limit_relation_subgraph(
    subgraph: dict[str, list[dict[str, Any]]], context: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    budget = context["budget"]
    nodes_by_id = {node["node_id"]: node for node in subgraph.get("nodes", [])}
    sorted_nodes = sorted(nodes_by_id.values(), key=_node_priority)
    selected_nodes: dict[str, dict[str, Any]] = {}
    for node in sorted_nodes:
        if len(selected_nodes) >= budget["max_subgraph_nodes"]:
            context["reasons"].add("output_budget")
            break
        selected_nodes[node["node_id"]] = node

    selected_edges: list[dict[str, Any]] = []
    for edge in sorted(subgraph.get("edges", []), key=_edge_priority):
        if len(selected_edges) >= budget["max_subgraph_edges"]:
            context["reasons"].add("output_budget")
            break
        endpoints = [edge.get("from"), edge.get("to")]
        missing = [node_id for node_id in endpoints if node_id not in selected_nodes]
        if missing:
            if len(selected_nodes) + len(missing) > budget["max_subgraph_nodes"]:
                context["reasons"].add("output_budget")
                continue
            for node_id in missing:
                selected_nodes[node_id] = nodes_by_id.get(
                    node_id, _normalize_node(node_id, "edge_endpoint") or {}
                )
        selected_edges.append(edge)

    selected_edge_ids = {edge["edge_id"] for edge in selected_edges}
    selected_node_ids = set(selected_nodes)
    selected_paths = []
    for path in subgraph.get("paths", [])[: budget["max_relation_paths"]]:
        if set(path.get("edges") or []).issubset(selected_edge_ids) and set(
            path.get("path") or []
        ).issubset(selected_node_ids):
            selected_paths.append(path)
    return {
        "nodes": list(selected_nodes.values())[: budget["max_subgraph_nodes"]],
        "edges": selected_edges[: budget["max_subgraph_edges"]],
        "paths": selected_paths,
    }


def _retrieval_summary(
    matched_objects: list[dict[str, Any]],
    matched_attributes: list[dict[str, Any]],
    candidate_queries: list[dict[str, Any]],
    candidate_skills: list[dict[str, Any]],
    matched_relations: list[dict[str, Any]],
    relation_subgraph: dict[str, list[dict[str, Any]]],
    resolved_params: dict[str, Any],
    fact_requirements: list[dict[str, Any]] | None = None,
    candidate_invocations: list[dict[str, Any]] | None = None,
    matched_intents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    period = _normalize_period(resolved_params.get("period"))
    tables = []
    expanded_from_templates: list[dict[str, str]] = []
    for query in candidate_queries:
        tables.extend(query.get("source_tables") or [])
    for edge in matched_relations:
        if edge.get("relation_type") == "reads_from":
            for node_id in (edge.get("from"), edge.get("to")):
                object_type, object_id = _split_node_id(str(node_id or ""))
                if object_type == "DataTable":
                    tables.append(object_id)
                    if _period_code_from_text(object_id):
                        expanded_from_templates.append({"expanded_table": object_id})
    for node in relation_subgraph.get("nodes", []):
        if node.get("object_type") == "DataTable":
            tables.append(node.get("object_id"))
    if period:
        period_tables = [table for table in tables if _period_code_from_text(str(table)) == period]
        plain_tables = [table for table in tables if not _period_code_from_text(str(table))]
        tables = [*period_tables, *plain_tables]
    main_tables = _unique(table for table in tables if table)[:8]
    summary: dict[str, Any] = {
        "main_object_types": _unique(
            _target_object_type(item) for item in matched_objects if _target_object_type(item)
        ),
        "main_intents": _unique(
            item.get("intent_name") for item in (matched_intents or []) if item.get("intent_name")
        ),
        "main_fact_types": _unique(
            item.get("fact_type") for item in (fact_requirements or []) if item.get("fact_type")
        ),
        "main_attributes": _unique(
            (
                item.get("attribute", {}).get("attribute_name")
                if item.get("attribute")
                else item.get("attribute_name")
            )
            for item in [*(fact_requirements or []), *matched_attributes]
            if (
                item.get("attribute", {}).get("attribute_name")
                if item.get("attribute")
                else item.get("attribute_name")
            )
        ),
        "main_skills": _unique(
            item.get("skill_id")
            for item in [*(candidate_invocations or []), *candidate_skills]
            if item.get("skill_id")
        ),
        "period": resolved_params.get("period"),
        "fund_code": resolved_params.get("fund_code"),
    }
    if period and expanded_from_templates:
        summary["period_expansion"] = {
            "period": period,
            "expanded_from_templates": _unique_expansion_rows(expanded_from_templates),
        }
        name_zh = _period_name_zh_from_code(period)
        if name_zh:
            summary["period_expansion"]["period_name_zh"] = name_zh
    return summary


def _truncation_info(
    detail_level: str,
    budget: dict[str, int],
    raw_relations: list[dict[str, Any]],
    raw_paths: list[dict[str, Any]],
    returned_relations: list[dict[str, Any]],
    returned_paths: list[dict[str, Any]],
    relation_subgraph: dict[str, list[dict[str, Any]]],
    reasons: set[str],
) -> dict[str, Any]:
    original_counts = _raw_graph_counts(raw_relations, raw_paths)
    returned_counts = {
        "matched_relations": len(returned_relations),
        "relation_paths": len(returned_paths),
        "subgraph_nodes": len(relation_subgraph.get("nodes", [])),
        "subgraph_edges": len(relation_subgraph.get("edges", [])),
    }
    limits = {
        "max_matched_relations": budget["max_matched_relations"],
        "max_relation_paths": budget["max_relation_paths"],
        "max_subgraph_nodes": budget["max_subgraph_nodes"],
        "max_subgraph_edges": budget["max_subgraph_edges"],
    }
    truncated = bool(reasons) or any(
        original_counts[key] > returned_counts[key]
        for key in ("matched_relations", "relation_paths", "subgraph_nodes", "subgraph_edges")
    )
    if not truncated:
        return {"truncated": False}
    return {
        "truncated": True,
        "detail_level": detail_level,
        "limits": limits,
        "original_counts": original_counts,
        "returned_counts": returned_counts,
        "reasons": sorted(reasons),
    }


def _raw_graph_counts(relations: list[dict[str, Any]], paths: list[dict[str, Any]]) -> dict[str, int]:
    nodes: set[str] = set()
    edges: set[str] = set()
    for relation in relations:
        edge = _ensure_edge_id(dict(relation))
        edges.add(edge["edge_id"])
        nodes.update([str(edge.get("from") or ""), str(edge.get("to") or "")])
    for path in paths:
        nodes.update(str(node) for node in (path.get("path") or path.get("nodes") or []))
        for edge in path.get("edges") or []:
            if isinstance(edge, dict):
                normalized = _ensure_edge_id(dict(edge))
                edges.add(normalized["edge_id"])
                nodes.update([str(normalized.get("from") or ""), str(normalized.get("to") or "")])
            elif edge:
                edges.add(str(edge))
    return {
        "matched_relations": len(relations),
        "relation_paths": len(paths),
        "subgraph_nodes": len([node for node in nodes if node]),
        "subgraph_edges": len(edges),
    }


def _ensure_edge_id(edge: dict[str, Any]) -> dict[str, Any]:
    if "edge_id" not in edge or not edge.get("edge_id"):
        edge["edge_id"] = f"{edge.get('from', '')}__{edge.get('relation_type', '')}__{edge.get('to', '')}"
    return edge


def _relation_type_priority(relation_type: str) -> int:
    order = {
        "returns_attribute": 0,
        "reads_from": 1,
        "mapped_to_field": 2,
        "requires_param": 3,
        "supports_skill": 4,
        "invokes_query": 4,
        "uses_query": 4,
        "related_query": 4,
        "has_attribute": 5,
        "targets_object_type": 5,
        "sourced_from_table": 6,
        "has_field": 7,
        "joins_on": 9,
    }
    return order.get(relation_type, 8)


def _node_priority(node: dict[str, Any]) -> tuple[int, str]:
    source = str(node.get("source") or "")
    object_type = str(node.get("object_type") or "")
    if source == "matched_object" or object_type == "ObjectType":
        priority = 0
    elif source == "matched_attribute" or object_type == "Attribute":
        priority = 1
    elif object_type == "QueryCapability":
        priority = 2
    elif object_type == "SkillCapability":
        priority = 3
    elif object_type == "DataTable":
        priority = 4
    elif object_type == "DataField":
        priority = 5
    elif object_type == "Parameter":
        priority = 6
    else:
        priority = 9
    return (priority, str(node.get("node_id") or ""))


def _edge_priority(edge: dict[str, Any]) -> tuple[int, float, str]:
    return (
        _relation_type_priority(str(edge.get("relation_type") or "")),
        -_numeric_score(edge.get("score")),
        str(edge.get("edge_id") or ""),
    )


def _edge_has_datafield(edge: dict[str, Any]) -> bool:
    return _edge_datafield_id(edge) != ""


def _edge_datafield_id(edge: dict[str, Any]) -> str:
    for node_id in (edge.get("from"), edge.get("to")):
        object_type, object_id = _split_node_id(str(node_id or ""))
        if object_type == "DataField":
            return object_id
    return ""


def _edge_attribute_id(edge: dict[str, Any]) -> str:
    for node_id in (edge.get("from"), edge.get("to")):
        object_type, object_id = _split_node_id(str(node_id or ""))
        if object_type == "Attribute":
            return object_id
    return ""


def _edge_table_id(edge: dict[str, Any]) -> str:
    for node_id in (edge.get("from"), edge.get("to")):
        object_type, object_id = _split_node_id(str(node_id or ""))
        if object_type == "DataTable":
            return object_id
    datafield = _edge_datafield_id(edge)
    return datafield.split(".", 1)[0] if "." in datafield else ""


def _normalize_period(period: Any) -> str:
    return str(period or "").lower()


def _period_code(value: Any) -> str:
    if isinstance(value, dict):
        for container in (value, value.get("properties") or {}, value.get("params") or {}):
            if isinstance(container, dict) and container.get("period_code"):
                return _normalize_period(container.get("period_code"))
        for key in ("node_id", "id", "from", "to", "object_id"):
            detected = _period_code_from_text(str(value.get(key) or ""))
            if detected:
                return detected
        return ""
    return _period_code_from_text(str(value or ""))


def _period_code_from_text(value: str) -> str:
    text = value.lower()
    for code in PERIOD_CODES:
        if re.search(rf"(?<![a-z0-9]){re.escape(code)}(?![a-z0-9])", text):
            return code
        if f"_{code}_" in text or text.endswith(f"_{code}") or f"_{code}." in text:
            return code
    return ""


def _period_mismatch(value: Any, period: Any) -> bool:
    normalized = _normalize_period(period)
    if not normalized:
        return False
    code = _period_code(value)
    return bool(code and code != normalized)


def _has_period_template_token(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _has_period_template_token(value.get(key))
            for key in ("edge_id", "from", "to", "node_id", "id", "object_id")
        )
    text = str(value or "").lower()
    return "_xx" in text or "retxx" in text or "近xx" in text or "近x" in text


def _is_period_match_field(value: str, period: Any) -> bool:
    text = str(value or "").lower()
    if period != "1y":
        return False
    return any(term.lower() in text for term in PERIOD_1Y_TERMS)


def _is_period_template_field(value: str) -> bool:
    text = str(value or "").lower()
    return any(term.lower() in text for term in PERIOD_TEMPLATE_TERMS) or any(
        table in text for table in ("dws_fund_perf_xx", "dws_fund_risk retxx", "dws_fund_risk_retxx")
    )


def _is_period_mismatch_field(value: str, period: Any) -> bool:
    text = str(value or "").lower()
    if period != "1y":
        return False
    if _is_period_match_field(text, period) or _is_period_template_field(text):
        return False
    return any(term.lower() in text for term in PERIOD_MISMATCH_TERMS)


def _is_noise_field(value: str) -> bool:
    text = str(value or "")
    normalized = text.replace(" ", "")
    return any(term in normalized for term in ENUM_NOISE_TERMS)


def _is_dim_fund_info_table(table: str) -> bool:
    return str(table or "").lower() == "dim_fund_info"


def _is_core_dim_fund_field(field_id: str) -> bool:
    text = str(field_id or "").lower()
    return any(term.lower() in text for term in CORE_DIM_FUND_FIELDS)


def _unique(values: Any) -> list[Any]:
    rows = []
    seen = set()
    for value in values:
        if value in (None, "") or value in seen:
            continue
        seen.add(value)
        rows.append(value)
    return rows


def _unique_expansion_rows(values: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in values:
        key = item.get("expanded_table", "")
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return rows


def _period_name_zh_from_code(period: str) -> str:
    names = {
        "1w": "近一周",
        "1m": "近一月",
        "3m": "近三个月",
        "6m": "近六月",
        "1y": "近一年",
        "2y": "近两年",
        "3y": "近三年",
        "5y": "近五年",
        "10y": "近十年",
        "20y": "近二十年",
        "ytd": "今年以来",
        "si": "成立以来",
    }
    return names.get(period, "")


def _period_expansion_warnings(summary: dict[str, Any]) -> list[str]:
    if not summary.get("period_expansion"):
        return []
    period_name = summary["period_expansion"].get("period_name_zh") or summary["period_expansion"].get("period")
    return [f"部分表/字段由原始表说明中的 xx 周期模板展开而来，当前已根据 period={summary.get('period')} 使用{period_name}版本。"]


def build_relation_subgraph(
    matched_objects: list[dict[str, Any]],
    matched_relations: list[dict[str, Any]],
    relation_paths: list[dict[str, Any]],
    matched_attributes: list[dict[str, Any]] | None = None,
    candidate_queries: list[dict[str, Any]] | None = None,
    candidate_skills: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """把匹配对象、直接关系和路径规整成标准子图结构。

    输入可能来自不同仓储，节点/边格式并不完全一致；这里统一生成 nodes、edges、
    paths 三段数据，并通过 node_id/edge_id 去重，便于前端或下游代理可视化。
    """

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    paths: list[dict[str, Any]] = []

    def add_node(value: Any, source: str) -> str | None:
        """规范化并登记一个节点，返回 node_id。"""

        node = _normalize_node(value, source)
        if not node:
            return None
        existing = nodes.get(node["node_id"])
        if existing:
            if not existing.get("name") and node.get("name"):
                existing["name"] = node["name"]
            return node["node_id"]
        nodes[node["node_id"]] = node
        return node["node_id"]

    def add_edge(value: Any, source: str) -> str | None:
        """规范化并登记一条边，同时确保边两端节点存在。"""

        edge = _normalize_edge(value, source)
        if not edge:
            return None
        add_node(edge["from"], source)
        add_node(edge["to"], source)
        edges.setdefault(edge["edge_id"], edge)
        return edge["edge_id"]

    for item in matched_objects:
        add_node(item, "matched_object")

    for item in matched_attributes or []:
        add_node(_attribute_node(item), "matched_attribute")

    for query in candidate_queries or []:
        add_node(
            {
                "object_type": "QueryCapability",
                "object_id": query.get("query_id", ""),
                "object_name": query.get("description", ""),
            },
            "candidate_query",
        )

    for skill in candidate_skills or []:
        add_node(
            {
                "object_type": "SkillCapability",
                "object_id": skill.get("skill_id", ""),
                "object_name": skill.get("skill_name", ""),
            },
            "candidate_skill",
        )

    for relation in matched_relations:
        add_edge(relation, "matched_relations")

    for item in relation_paths:
        path_nodes = []
        for node in item.get("path") or item.get("nodes") or []:
            node_id = add_node(node, "path")
            if node_id:
                path_nodes.append(node_id)

        path_edges = []
        for edge in item.get("edges") or []:
            edge_id = add_edge(edge, "relation_paths")
            if edge_id:
                path_edges.append(edge_id)

        paths.append(
            {
                "path": path_nodes,
                "edges": path_edges,
                "score": _numeric_score(item.get("score")),
            }
        )

    subgraph = {
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
        "paths": paths,
    }
    if context:
        return _limit_relation_subgraph(subgraph, context)
    return subgraph


def _normalize_node(value: Any, source: str) -> dict[str, Any] | None:
    """把字符串或对象字典规范化为子图节点。"""

    if isinstance(value, str):
        node_id = value
        name = ""
    elif isinstance(value, dict):
        node_id = _node_id(value)
        name = str(value.get("name") or value.get("object_name") or "")
    else:
        return None

    if not node_id:
        return None

    object_type, object_id = _split_node_id(node_id)
    node = {
        "node_id": node_id,
        "object_type": object_type,
        "object_id": object_id,
        "source": source,
    }
    if name:
        node["name"] = name
    period_code = _period_code(node_id)
    if period_code:
        node["period_code"] = period_code
    return node


def _normalize_edge(value: Any, source: str) -> dict[str, Any] | None:
    """把字符串或对象字典规范化为子图边。"""

    if isinstance(value, str):
        parts = value.split("__", 2)
        if len(parts) != 3:
            return None
        return {
            "edge_id": value,
            "from": parts[0],
            "to": parts[2],
            "relation_type": parts[1],
            "score": 0.0,
            "source": source,
        }
    if not isinstance(value, dict):
        return None

    from_node = _node_id(value.get("from"))
    to_node = _node_id(value.get("to"))
    relation_type = str(value.get("relation_type") or "")
    if not from_node or not to_node or not relation_type:
        return None

    edge_id = str(value.get("edge_id") or f"{from_node}__{relation_type}__{to_node}")
    edge = {
        "edge_id": edge_id,
        "from": from_node,
        "to": to_node,
        "relation_type": relation_type,
        "score": _numeric_score(value.get("score")),
        "source": source,
    }
    period_code = _period_code(value)
    if period_code:
        edge["period_code"] = period_code
    if isinstance(value.get("properties"), dict):
        edge["properties"] = dict(value["properties"])
    return edge


def _node_id(value: Any) -> str:
    """从不同节点表示中提取稳定 node_id。"""

    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    explicit = value.get("node_id") or value.get("id")
    if explicit:
        return str(explicit)
    object_type = value.get("object_type")
    object_id = value.get("object_id")
    if object_type and object_id:
        return f"{object_type}:{object_id}"
    return ""


def _split_node_id(node_id: str) -> tuple[str, str]:
    """把 object_type:object_id 形式的 node_id 拆成类型和业务 ID。"""

    if ":" not in node_id:
        return "", node_id
    object_type, object_id = node_id.split(":", 1)
    return object_type, object_id


def _numeric_score(value: Any) -> float:
    """把可选分数字段转换为 float，缺失或非法时按 0 处理。"""

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _object_params(item: dict[str, Any]) -> dict[str, Any]:
    """从对象元数据中提取查询参数，并为基金对象补 fund_code。"""

    params = dict(item.get("params") or {})
    if item.get("object_type") == "Fund" and item.get("object_id"):
        params.setdefault("fund_code", item["object_id"])
    return params


def _best_mention(question: str, item: dict[str, Any]) -> str:
    """选择最能解释命中的 mention，优先使用问句中真实出现的别名。"""

    for value in [item.get("object_id"), item.get("object_name"), *(item.get("aliases") or [])]:
        if value and str(value) in question:
            return str(value)
    return str(item.get("object_id") or "")


def _score_to_confidence(score: Any, base: float) -> float:
    """把仓储启发式分数压缩为 0 到 0.95 之间的置信度。"""

    try:
        numeric = float(score)
    except (TypeError, ValueError):
        return base
    return round(min(0.95, base + numeric / 20), 3)


def _candidate_invocation_reasons(
    query: dict[str, Any],
    attribute_names: set[Any],
    resolved_param_names: set[str],
    missing_params: list[str],
) -> list[str]:
    """生成人类可读的候选调用匹配原因。"""

    reasons = [f"target_object_type matched: {query.get('target_object_type')}"]
    outputs = set(query.get("output_attributes") or [])
    covered_outputs = sorted(name for name in outputs.intersection(attribute_names) if name)
    if covered_outputs:
        reasons.append(f"output_attributes covered: {','.join(covered_outputs)}")
    required = [name for name in (query.get("required_params") or []) if name in resolved_param_names]
    if required:
        reasons.append(f"required_params resolved: {','.join(required)}")
    if missing_params:
        reasons.append(f"required_params missing: {','.join(missing_params)}")
    scope = query.get("permission_scope")
    if scope:
        reasons.append(f"permission_scope matched: {scope}")
    return reasons


def _suggested_question(missing: list[str]) -> str:
    """根据缺失参数生成追问建议。"""

    if "period" in missing:
        return "请补充查询区间，例如近一年、近三个月、今年或成立以来。"
    return "请补充必要查询参数：" + "、".join(missing)
