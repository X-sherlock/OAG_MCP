from __future__ import annotations

from copy import deepcopy
from typing import Any


AGENT_ONLY_BLOCKING_CODES = {"SKILL_PARAMS_MISSING"}


def to_editor_plan(full_plan: dict[str, Any]) -> dict[str, Any]:
    """Return the full internal planning result for editor/debug consumers."""

    return deepcopy(full_plan)


def to_agent_plan(full_plan: dict[str, Any]) -> dict[str, Any]:
    """Project the full OAG plan into a compact execution plan for agents."""

    if full_plan.get("oag_version") == "v2" and isinstance(full_plan.get("agent_plan"), dict):
        return deepcopy(full_plan["agent_plan"])

    plan = deepcopy(full_plan)
    facts = plan.get("fact_requirements") or []
    invocations = plan.get("candidate_invocations") or []
    coverage = plan.get("coverage_summary") or {}

    projected = {
        "status": plan.get("status", "success"),
        "task": _task(plan),
        "targets": [_target(item) for item in plan.get("target_instances") or []],
        "facts": [_fact(item) for item in facts],
        "skill_calls": [_skill_call(item, coverage) for item in invocations],
        "coverage": _coverage(plan, coverage),
        "execution": _execution(invocations),
        "uncovered_facts": _uncovered_facts(plan),
        "issues": _issues(plan),
    }
    if plan.get("error_code"):
        projected["error_code"] = plan.get("error_code")
    if plan.get("message_zh"):
        projected["message_zh"] = plan.get("message_zh")
    return projected


def project_plan(full_plan: dict[str, Any], output_view: str | None = None) -> dict[str, Any]:
    view = _normalize_output_view(output_view)
    if view == "editor":
        return to_editor_plan(full_plan)
    return to_agent_plan(full_plan)


def _normalize_output_view(output_view: str | None) -> str:
    view = str(output_view or "agent").strip().lower()
    if view in {"editor", "full", "debug"}:
        return "editor"
    if view in {"agent", "execution"}:
        return "agent"
    raise ValueError(f"Unsupported output_view: {output_view}")


def _task(plan: dict[str, Any]) -> dict[str, Any]:
    frame = plan.get("normalized_semantic_frame") or {}
    summary = plan.get("semantic_frame_summary") or {}
    return {
        "raw_question": plan.get("raw_question") or frame.get("raw_question") or "",
        "domain": frame.get("domain") or plan.get("domain") or "finance_market",
        "task_type": frame.get("task_type") or summary.get("task_type") or "",
        "intent": frame.get("intent") or summary.get("intent"),
        "constraints": dict(frame.get("constraints") or summary.get("constraints") or {}),
    }


def _target(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_id": item.get("target_instance_id") or item.get("target_id") or "",
        "object_type": item.get("object_type") or "",
        "label_zh": item.get("display_name_zh") or item.get("label_zh") or "",
        "instance_ref": dict(item.get("instance_ref") or {}),
        "role": item.get("role") or "",
    }


def _fact(item: dict[str, Any]) -> dict[str, Any]:
    attribute = item.get("attribute") if isinstance(item.get("attribute"), dict) else {}
    subject = item.get("subject") if isinstance(item.get("subject"), dict) else {}
    return {
        "fact_id": item.get("fact_requirement_id") or "",
        "fact_type": item.get("fact_type") or "",
        "fact_type_zh": item.get("fact_type_zh") or "",
        "target_id": subject.get("target_instance_id") or "",
        "attribute": item.get("attribute_name"),
        "attribute_zh": attribute.get("attribute_name_zh") or attribute.get("label_zh"),
        "predicate": item.get("predicate"),
        "target_object_type": item.get("target_object_type"),
        "constraints": dict(item.get("constraints") or {}),
        "priority": item.get("priority") or "",
        "source": item.get("source") or "",
        "reason_zh": item.get("reason_zh") or "",
    }


def _skill_call(item: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    missing = list(dict.fromkeys(item.get("missing_params") or []))
    covers = list(dict.fromkeys(item.get("covers_fact_requirements") or []))
    call_status = _call_status(item, coverage)
    return {
        "skill_id": item.get("skill_id") or "",
        "skill_name_zh": item.get("skill_name_zh") or item.get("skill_id") or "",
        "description_zh": item.get("description_zh") or "",
        "params": dict(item.get("params") or {}),
        "missing_params": missing,
        "covers": covers,
        "covers_required_count": int(item.get("covers_required_count") or 0),
        "covers_optional_count": int(item.get("covers_optional_count") or 0),
        "coverage_score": item.get("coverage_score") or 0,
        "coverage_reason_zh": item.get("coverage_reason_zh") or "",
        "call_status": call_status,
    }


def _call_status(item: dict[str, Any], coverage: dict[str, Any]) -> str:
    if item.get("disabled"):
        return "disabled"
    if item.get("permission_blocked") or coverage.get("coverage_status") == "permission_blocked":
        return "blocked_permission"
    if item.get("missing_params"):
        return "blocked_missing_params"
    if item.get("uncovered_reason_zh"):
        return "partial"
    return "ready"


def _coverage(plan: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "coverage_status": coverage.get("coverage_status") or _fallback_coverage_status(plan),
        "required_fact_count": int(coverage.get("required_fact_count") or 0),
        "covered_required_fact_count": int(coverage.get("covered_required_fact_count") or 0),
        "uncovered_required_facts": list(coverage.get("uncovered_required_facts") or []),
        "optional_fact_count": int(coverage.get("optional_fact_count") or 0),
        "covered_optional_fact_count": int(coverage.get("covered_optional_fact_count") or 0),
        "message_zh": coverage.get("coverage_message_zh") or "",
    }


def _fallback_coverage_status(plan: dict[str, Any]) -> str:
    if plan.get("status") == "need_clarification":
        return "need_clarification"
    if plan.get("status") == "error":
        return "no_coverage"
    return "full_coverage"


def _execution(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    skill_calls = [_skill_call(item, {}) for item in invocations]
    blocking_issues = []
    for call in skill_calls:
        if call["call_status"] == "blocked_missing_params":
            blocking_issues.append(
                {
                    "code": "SKILL_PARAMS_MISSING",
                    "skill_id": call["skill_id"],
                    "skill_name_zh": call["skill_name_zh"],
                    "missing_params": call["missing_params"],
                    "message_zh": "调用该 Skill 前需要补充参数：" + "、".join(call["missing_params"]),
                }
            )
        elif call["call_status"] == "blocked_permission":
            blocking_issues.append(
                {
                    "code": "SKILL_PERMISSION_BLOCKED",
                    "skill_id": call["skill_id"],
                    "skill_name_zh": call["skill_name_zh"],
                    "message_zh": "调用该 Skill 前需要补充权限。",
                }
            )

    ready_count = len([item for item in skill_calls if item["call_status"] == "ready"])
    blocked_count = len([item for item in skill_calls if item["call_status"].startswith("blocked_")])
    execution_status = _execution_status(skill_calls)
    return {
        "execution_status": execution_status,
        "ready_skill_count": ready_count,
        "blocked_skill_count": blocked_count,
        "message_zh": _execution_message(execution_status),
        "blocking_issues": _dedupe_issue_rows(blocking_issues),
    }


def _execution_status(skill_calls: list[dict[str, Any]]) -> str:
    if not skill_calls:
        return "no_skill_calls"
    statuses = {item["call_status"] for item in skill_calls}
    if "blocked_missing_params" in statuses:
        return "blocked_missing_params"
    if "blocked_permission" in statuses:
        return "blocked_permission"
    if statuses == {"ready"}:
        return "ready"
    if "ready" in statuses:
        return "partial"
    return sorted(statuses)[0]


def _execution_message(status: str) -> str:
    return {
        "ready": "Skill 调用参数齐全，可以执行。",
        "blocked_missing_params": "存在 Skill 调用缺失参数，需要补充后再执行。",
        "blocked_permission": "存在 Skill 调用权限不足，需要授权后再执行。",
        "partial": "部分 Skill 可执行，仍有部分调用未就绪。",
        "no_skill_calls": "当前没有可执行的 Skill 调用建议。",
        "disabled": "存在不可用的 Skill 调用建议。",
    }.get(status, "当前 Skill 调用状态需要人工确认。")


def _uncovered_facts(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = plan.get("uncovered_facts")
    if rows is not None:
        return list(rows)
    return list((plan.get("coverage_summary") or {}).get("uncovered_required_facts") or [])


def _issues(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in plan.get("diagnostics") or []:
        code = item.get("diagnostic_code") or item.get("code")
        if code in AGENT_ONLY_BLOCKING_CODES:
            continue
        rows.append(
            {
                "code": code,
                "severity": item.get("severity") or "warning",
                "skill_id": item.get("skill_id"),
                "fact_id": item.get("fact_requirement_id") or item.get("fact_id"),
                "message_zh": item.get("message_zh") or "",
                "suggestion_zh": item.get("suggestion_zh") or "",
            }
        )
    for item in plan.get("warnings") or []:
        code = item.get("warning_code") or item.get("code")
        if code in AGENT_ONLY_BLOCKING_CODES:
            continue
        rows.append(
            {
                "code": code,
                "severity": item.get("severity") or "warning",
                "skill_id": item.get("skill_id"),
                "fact_id": item.get("fact_requirement_id") or item.get("fact_id"),
                "message_zh": item.get("message_zh") or "",
                "suggestion_zh": item.get("suggestion_zh") or "",
            }
        )
    for item in _uncovered_facts(plan):
        rows.append(
            {
                "code": "REQUIRED_FACT_UNCOVERED",
                "severity": "warning",
                "skill_id": None,
                "fact_id": item.get("fact_requirement_id") or item.get("fact_id"),
                "message_zh": f"必需事实未覆盖：{item.get('label_zh') or item.get('fact_id') or item.get('fact_requirement_id')}。",
                "suggestion_zh": item.get("reason_zh") or "请补充对应 Skill。",
            }
        )
    return _dedupe_issue_rows(rows)


def _dedupe_issue_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for item in rows:
        key = (
            item.get("code"),
            item.get("skill_id"),
            item.get("fact_id"),
            item.get("message_zh"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
