# OAG_MCP_JAVA

Java OAG V2 planner for the same core contract used by the Python runtime.

## Scope

- Keeps service / logic / dao layering.
- Uses Java 8 compatible source and target.
- Reads ontology metadata, attributes, intent profiles, and Skill capability declarations from MySQL.
- Builds `candidateFactPool`, validates selected facts, completes deterministic dependencies, and binds Skills.
- Does not query ClickHouse, MRS, Hudi, or real business data.

## API

```text
POST /oag/retrieve-context
```

Request body:

```json
{
  "rawQuestion": "分析000001近一年表现",
  "semanticFrame": {
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
  "recognizedIntents": [
    {"intent_name": "performance_overview", "confidence": 0.92}
  ],
  "selectorMode": "rule"
}
```

Response includes V2 fields:

- `ontologySubgraph`
- `candidateFactPool`
- `selectedFacts`
- `validationResult`
- `dependencyCompletion`
- `skillBindings`
- `agentPlan`
- `editorPlan`

Compatibility fields remain:

- `factRequirements`
- `candidateInvocations`
- `retrievalSummary`
- `missingParams`

## Environment

```text
OAG_DB_HOST=127.0.0.1
OAG_DB_PORT=3306
OAG_DB_NAME=oag_meta
OAG_DB_USER=root
OAG_DB_PASSWORD=
OAG_DOMAIN=finance_market
OAG_MCP_JAVA_PORT=8080
```

## Compile

```bash
mvn -q -DskipTests compile
```
