from __future__ import annotations

from typing import Any

from oag_ontology_loader.models import OntologyCatalog


SEMANTIC_EDGE_TYPES = {
    "compared_with",
    "derives",
    "ranked_by_peer",
    "risk_companion",
    "return_companion",
    "benchmark_metric_of",
    "peer_metric_of",
}
OBJECT_PROFILE_EDGE_TYPES = {
    "managed_by",
    "issued_by",
    "managed_by_company",
    "tracks_index",
    "has_dividend",
    "has_fee",
    "has_asset_allocation",
    "has_position",
    "holds_asset",
}
PLANNED_EDGE_TYPES = SEMANTIC_EDGE_TYPES | OBJECT_PROFILE_EDGE_TYPES | {
    "has_benchmark",
    "belongs_to_category",
}


def diagnose_ontology(
    catalog: OntologyCatalog,
    planning_result: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    _diagnose_skills(catalog, diagnostics)
    _diagnose_attributes(catalog, diagnostics)
    _diagnose_intents(catalog, diagnostics)
    _diagnose_edges(catalog, diagnostics)
    if planning_result:
        _diagnose_planning_result(planning_result, diagnostics)
    return diagnostics


def _diagnose_skills(catalog: OntologyCatalog, diagnostics: list[dict[str, Any]]) -> None:
    for skill in catalog.skills:
        if not skill.get("enabled", True):
            continue
        skill_id = skill.get("skill_id", "<unknown>")
        if not skill.get("provides_fact_types"):
            diagnostics.append(
                _diagnostic(
                    "skill_missing_provides_fact_types",
                    "warning",
                    node_id=f"SkillCapability:{skill_id}",
                    message="Skill 缺少 provides_fact_types，OAG 无法可靠判断它能覆盖哪些事实类型。",
                    action="为该 Skill 补充 provides_fact_types，例如 metric_value、relation_instance 或 object_profile。",
                )
            )
        if not skill.get("supported_attributes"):
            diagnostics.append(
                _diagnostic(
                    "skill_missing_supported_attributes",
                    "warning",
                    node_id=f"SkillCapability:{skill_id}",
                    message="Skill 缺少 supported_attributes，OAG 无法可靠判断它支持哪些属性。",
                    action="为该 Skill 补充 supported_attributes，或在只按关系覆盖时补充 supported_relations。",
                )
            )
        if not skill.get("supported_subject_types"):
            diagnostics.append(
                _diagnostic(
                    "skill_missing_supported_subject_types",
                    "warning",
                    node_id=f"SkillCapability:{skill_id}",
                    message="Skill 缺少 supported_subject_types，OAG 无法可靠判断它支持哪些主体对象。",
                    action="为该 Skill 补充 supported_subject_types，例如 Fund 或 FundSet。",
                )
            )


def _diagnose_attributes(catalog: OntologyCatalog, diagnostics: list[dict[str, Any]]) -> None:
    covered_attributes = {
        attribute
        for skill in catalog.skills
        if skill.get("enabled", True)
        for attribute in skill.get("supported_attributes") or skill.get("output_attributes") or []
    }
    for attribute in catalog.attributes:
        attribute_name = attribute.get("attribute_name")
        if attribute_name and attribute_name not in covered_attributes:
            diagnostics.append(
                _diagnostic(
                    "attribute_without_skill_coverage",
                    "info",
                    node_id=f"Attribute:{attribute_name}",
                    message=f"属性 {attribute.get('attribute_name_zh') or attribute_name} 当前没有任何启用 Skill 声明覆盖。",
                    action="补充支持该属性的 Skill 能力声明，或确认该属性暂不参与事实规划。",
                )
            )


def _diagnose_intents(catalog: OntologyCatalog, diagnostics: list[dict[str, Any]]) -> None:
    for intent in catalog.intent_profiles:
        intent_name = intent.get("intent_name", "<unknown>")
        if not intent.get("fact_requirements_template"):
            diagnostics.append(
                _diagnostic(
                    "intent_missing_fact_requirements_template",
                    "warning",
                    node_id=f"IntentProfile:{intent_name}",
                    message="IntentProfile 缺少 fact_requirements_template，宽泛意图命中后无法生成稳定事实需求。",
                    action="为该意图补充 fact_requirements_template，并为每个事实填写 fact_type、attribute_name、priority 和 reason_zh。",
                )
            )


def _diagnose_edges(catalog: OntologyCatalog, diagnostics: list[dict[str, Any]]) -> None:
    nodes = _schema_node_ids(catalog)
    for edge in catalog.schema_graph_edges:
        edge_id = edge.get("edge_id", "<unknown>")
        from_node = edge.get("from")
        to_node = edge.get("to")
        if from_node not in nodes or to_node not in nodes:
            diagnostics.append(
                _diagnostic(
                    "relation_edge_unknown_node",
                    "error",
                    edge_id=edge_id,
                    message="关系边引用了不存在的节点，关系规划可能跳过该边或生成不可解释路径。",
                    action="检查 edge.from 和 edge.to 是否与对象、属性、事实类型、查询或表字段节点 ID 一致。",
                )
            )
        if edge.get("relation_type") in SEMANTIC_EDGE_TYPES:
            if not edge.get("reason_zh"):
                diagnostics.append(
                    _diagnostic(
                        "semantic_edge_missing_reason_zh",
                        "warning",
                        edge_id=edge_id,
                        message="语义扩展边缺少 reason_zh，前端无法解释为什么补充该事实。",
                        action="为该语义扩展边补充中文 reason_zh。",
                    )
                )
            if not edge.get("applicable_tasks") or not edge.get("applicable_intents"):
                diagnostics.append(
                    _diagnostic(
                        "semantic_edge_missing_applicability",
                        "warning",
                        edge_id=edge_id,
                        message="语义扩展边缺少 applicable_tasks 或 applicable_intents，扩展范围不够可控。",
                        action="补充 applicable_tasks 和 applicable_intents，限制该关系在哪些任务和意图下生效。",
                    )
                )
        if edge.get("relation_type") in PLANNED_EDGE_TYPES:
            if not edge.get("planning_role"):
                diagnostics.append(
                    _diagnostic(
                        "planning_edge_missing_planning_role",
                        "warning",
                        edge_id=edge_id,
                        message="参与事实规划的关系边缺少 planning_role，规划器无法解释它是指标上下文、对象依赖还是画像背景。",
                        action="为该关系边补充 planning_role，例如 metric_context、benchmark_context、peer_context 或 profile_context。",
                    )
                )
            if not edge.get("auto_expand_mode"):
                diagnostics.append(
                    _diagnostic(
                        "planning_edge_missing_auto_expand_mode",
                        "warning",
                        edge_id=edge_id,
                        message="参与事实规划的关系边缺少 auto_expand_mode，无法区分自动扩展、显式查询或依赖关系。",
                        action="为该关系边补充 auto_expand_mode，例如 contextual、explicit_only、dependency_only 或 debug_only。",
                    )
                )
            if edge.get("relation_type") in OBJECT_PROFILE_EDGE_TYPES and edge.get("auto_expand_mode") == "always":
                diagnostics.append(
                    _diagnostic(
                        "object_profile_relation_auto_expands_always",
                        "warning",
                        edge_id=edge_id,
                        message="对象画像关系不能默认 always 自动扩展，否则普通指标查询会拉入基金经理、公司、费率或持仓等背景对象。",
                        action="将对象画像关系改为 explicit_only；确需自动扩展时使用 contextual 并补充严格 trigger_policy。",
                    )
                )


def _diagnose_planning_result(planning_result: dict[str, Any], diagnostics: list[dict[str, Any]]) -> None:
    for fact in planning_result.get("coverage_summary", {}).get("uncovered_required_facts") or []:
        diagnostics.append(
            _diagnostic(
                "required_fact_without_skill_coverage",
                "error",
                node_id=fact.get("fact_requirement_id"),
                message=f"必需事实 {fact.get('label_zh') or fact.get('fact_requirement_id')} 没有任何 Skill 覆盖。",
                action="补充可覆盖该事实类型、主体类型和属性的 Skill，或调整事实需求优先级。",
            )
        )


def _schema_node_ids(catalog: OntologyCatalog) -> set[str]:
    nodes = {f"ObjectType:{item['object_type']}" for item in catalog.object_types}
    nodes.update(f"Attribute:{item['attribute_name']}" for item in catalog.attributes)
    nodes.update(f"FactType:{item['fact_type']}" for item in catalog.fact_types)
    nodes.update(f"QueryCapability:{item['query_id']}" for item in catalog.queries)
    nodes.update(f"SkillCapability:{item['skill_id']}" for item in catalog.skills)
    nodes.update(f"DataTable:{item['table_name']}" for item in catalog.table_schemas)
    for table in catalog.table_schemas:
        for field in table.get("fields", []):
            nodes.add(f"DataField:{table['table_name']}.{field['field_name']}")
    return nodes


def _diagnostic(
    diagnostic_type: str,
    severity: str,
    message: str,
    action: str,
    node_id: str | None = None,
    edge_id: str | None = None,
) -> dict[str, Any]:
    row = {
        "diagnostic_type": diagnostic_type,
        "severity": severity,
        "diagnostic_message_zh": message,
        "suggested_action_zh": action,
    }
    if node_id:
        row["node_id"] = node_id
    if edge_id:
        row["edge_id"] = edge_id
    return row
