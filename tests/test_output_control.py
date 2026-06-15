from __future__ import annotations

import json

from oag_task_planner_helpers import frame, retrieve


def test_standard_output_is_task_plan_without_detail_modes():
    result = retrieve(frame())

    assert result["status"] == "success"
    assert "task_graph" in result
    assert "fact_requirements" in result
    assert "candidate_invocations" in result
    assert "truncation" not in result
    assert "detail_level" not in result
    assert "candidate_queries" not in result
    assert "relation_subgraph" not in result


def test_task_graph_has_frontend_friendly_chinese_fields():
    result = retrieve(frame())

    assert all(node.get("label_zh") for node in result["task_graph"]["nodes"])
    assert all(node.get("description_zh") for node in result["task_graph"]["nodes"])
    assert all(edge.get("label_zh") for edge in result["task_graph"]["edges"])
    assert all(edge.get("reason_zh") for edge in result["task_graph"]["edges"])


def test_candidate_invocation_dedup_by_skill_and_params():
    result = retrieve(frame())
    keys = [
        (
            invocation["skill_id"],
            tuple(
                sorted(
                    (
                        key,
                        tuple(value) if isinstance(value, list) else value,
                    )
                    for key, value in invocation["params"].items()
                )
            ),
        )
        for invocation in result["candidate_invocations"]
    ]

    assert len(keys) == len(set(keys))


def test_standard_output_has_no_schema_evidence():
    result = retrieve(frame())
    text = json.dumps(result, ensure_ascii=False)

    assert "schema_evidence" not in result
    assert "matched_relations" not in result
    assert "relation_paths" not in result
    assert "DataTable:" not in text
    assert "DataField:" not in text
    assert "QueryCapability:" not in text
