# OAG V2 Design

OAG V2 upgrades the planner from graph-edge/template driven fact generation to a controlled chain:

1. The upstream intent node produces `semantic_frame` and `recognized_intents`.
2. OAG recalls an `ontology_subgraph` from object types, attributes, relations, data-source metadata, and Skill capability declarations.
3. OAG deterministically builds `candidate_fact_pool`.
4. A selector chooses and ranks existing `fact_id` values from that pool. In `llm` mode, the LLM may only return candidate `fact_id` values and reasons.
5. OAG validates selected facts, rejects illegal `fact_id` values, applies fact budget limits, completes deterministic dependencies, and binds Skills using internal capability declarations.

The LLM never creates attributes, relations, facts, or Skill calls. Skill binding is deterministic because execution safety depends on local capability declarations, permissions, required params, and output fact schemas.

## Inputs

`oag_retrieve_context` accepts:

```json
{
  "raw_question": "分析000001近一年表现",
  "semantic_frame": {
    "raw_question": "分析000001近一年表现",
    "domain": "finance_market",
    "task_type": "analyze",
    "intent": "performance_overview",
    "target_objects": [
      {"object_type": "Fund", "instance_ref": {"fund_code": "000001"}, "role": "analysis_subject"}
    ],
    "constraints": {"period": "1y"},
    "mentioned_attributes": []
  },
  "recognized_intents": [
    {"intent_name": "performance_overview", "confidence": 0.92}
  ],
  "selector_mode": "rule",
  "planning_options": {"fact_budget": 20}
}
```

`semantic_frame` is the formal input. `raw_question` is retained for tracing and editor display.

## Outputs

The full editor/MCP output includes:

- `ontology_subgraph`
- `candidate_fact_pool`
- `selected_facts`
- `validation_result`
- `dependency_completion`
- `skill_bindings`
- `agent_plan`
- `editor_plan`

Compatibility fields remain: `fact_requirements`, `candidate_invocations`, `task_graph`, `coverage_summary`, `missing_params`, and `diagnostics`.

## Selector Modes

- `rule`: offline deterministic selection; no API key required.
- `mock`: test mode using `planning_options.selected_fact_ids`; illegal IDs are rejected.
- `llm`: calls Tongyi Bailian with the configured model and only accepts returned IDs that exist in `candidate_fact_pool`.

## Bailian Configuration

Use environment variables or `.env`; environment variables take priority.

```text
OAG_LLM_PROVIDER=bailian
OAG_LLM_MODEL=qwen3.7-max-2026-06-08
OAG_LLM_API_KEY=
OAG_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
OAG_LLM_TIMEOUT_SECONDS=60
OAG_LLM_TEMPERATURE=0.1
OAG_LLM_ENABLED=true
```

Missing `OAG_LLM_API_KEY` produces a structured `LLM_API_KEY_MISSING` error in `llm` mode. The editor only shows whether the key is configured.

## Editor V2

Open the OAG planning workbench and run a plan. The result inspector shows input, LLM status, ontology subgraph, candidate pool, selected facts, validation, dependency completion, Skill bindings, and both agent/editor plans. The `golden questions` button runs `ontology/golden_questions.yaml` through the rule selector.

## Java Contract

`OAG_MCP_JAVA` exposes `POST /oag/retrieve-context` via a service layer. Java keeps service / logic / dao separation and Java 8 compatibility. It plans ontology facts and deterministic Skill bindings from MySQL metadata; it does not query ClickHouse, MRS, Hudi, or any business data store.

## Golden Questions

Run:

```powershell
$env:PYTHONPATH='.;src;tests'
.\.venv\Scripts\python -m pytest -q tests\test_oag_v2_planner.py
```

The editor endpoint is:

```text
GET /api/oag/golden-questions
```
