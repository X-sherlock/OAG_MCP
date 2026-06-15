# OAG_MCP

OAG_MCP is a MySQL-only MCP Server for semantic-frame-driven ontology fact planning and downstream Skill recommendation in the fund domain.

Python OAG now treats `semantic_frame` as the only formal input. It does not parse natural language questions, query business data, execute business SQL, or generate final answers. Its standard output is the task-level `fact_requirements`, `candidate_invocations`, and `task_graph` needed by the next model or orchestration step.

Design details: [docs/oag_task_planning_design.md](docs/oag_task_planning_design.md).

The MCP tool name remains `oag_retrieve_context`.

## Responsibility Boundary

The online MCP Server only reads initialized MySQL ontology metadata and returns a fact-planning task graph for a structured `semantic_frame`:

- target instances
- fact requirements
- candidate invocations
- task graph
- coverage summary
- missing parameter hints

The online MCP Server does not:

- initialize the ontology graph
- read `ontology/*.yaml`
- read or require the `ontology/`, `sql/`, or `scripts/` directories
- seed data
- write MySQL
- execute business SQL
- query real fund business data
- calculate indicator values
- query real fund instances

Real business data lookup is handled by downstream Skills according to `candidate_invocations`.

## Fact Requirement Oriented Output

Compact output is ontology-first, fact-requirement-first, and Skill-orchestration-first.
It is not a table/field routing payload.

Compact output answers which ontology objects the question involves, which object
instance references were resolved, which ontology facts are required, which Skills can
provide those facts, which `fact_requirement_id` values each Skill invocation covers,
and which parameters are still missing.

Key compact fields:

- `target_instances`: ontology instance references inferred from the question.
- `fact_requirements`: required facts with `subject`, `predicate`, `attribute`,
  `constraints`, `priority`, `reason`, and `expected_output`.
- `fact_groups`: optional answer-structure groups over fact requirements.
- `candidate_invocations`: Skill calls with `covers_fact_requirements`,
  `expected_facts`, `params`, and `missing_params`.
- `retrieval_summary`: object types, intents, fact types, attributes, Skills, period,
  and fund code.

Compact output does not return physical schema evidence such as `DataTable`,
`DataField`, `source_tables`, `main_tables`, `matched_relations`, `relation_paths`,
or `relation_subgraph`.

`standard` may return `schema_evidence_summary` and `candidate_queries_summary`.
`full` or `debug=true` may return full `schema_evidence`, including
`candidate_queries`, `matched_relations`, `relation_paths`, and `relation_subgraph`.
Those fields are development/debugging evidence. Downstream LLM or workflow nodes
should select Skills from `candidate_invocations`; the selected Skill is responsible
for converting fact requirements into real data access.

## Modules

Runtime MCP module:

- `src/oag_mcp/server.py`: exposes MCP tool `oag_retrieve_context`
- `src/oag_mcp/service.py`: parses questions, retrieves OAG context, recommends Skills
- `src/oag_mcp/repositories.py`: read-only MySQL repositories
- `src/oag_mcp/config.py`: reads MySQL environment variables
- `src/oag_mcp/param_extractor.py`: extracts `fund_code`, `period`, and related params
- `src/oag_mcp/errors.py`: structured error handling

Offline ontology initialization module:

- `src/oag_ontology_loader/loader.py`: reads `ontology/*.yaml`
- `src/oag_ontology_loader/period_expander.py`: expands `xx` period templates into explicit logical period tables and fields
- `src/oag_ontology_loader/validator.py`: validates YAML sections
- `src/oag_ontology_loader/models.py`: ontology catalog model
- `src/oag_ontology_loader/mysql_writer.py`: writes metadata, aliases, graph nodes, and graph edges to MySQL
- `scripts/seed_ontology.py`: official YAML-to-MySQL seed entrypoint

`scripts/seed_demo_data.py` is kept only as a deprecated compatibility forwarder.

## Offline Ontology Initialization

Run this before starting or registering the MCP Server.

1. Create MySQL database and user:

```sql
CREATE DATABASE IF NOT EXISTS oag_meta
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'oag'@'localhost' IDENTIFIED BY 'oag_password';
CREATE USER IF NOT EXISTS 'oag'@'127.0.0.1' IDENTIFIED BY 'oag_password';

GRANT ALL PRIVILEGES ON oag_meta.* TO 'oag'@'localhost';
GRANT ALL PRIVILEGES ON oag_meta.* TO 'oag'@'127.0.0.1';
FLUSH PRIVILEGES;
```

2. Create OAG metadata tables:

```powershell
mysql -uoag -p oag_meta < sql/init_oag_meta.sql
```

3. Configure MySQL environment variables:

```powershell
$env:OAG_TDSQL_HOST="127.0.0.1"
$env:OAG_TDSQL_PORT="3306"
$env:OAG_TDSQL_USER="oag"
$env:OAG_TDSQL_PASSWORD="oag_password"
$env:OAG_TDSQL_DATABASE="oag_meta"
$env:OAG_DOMAIN="finance_market"
```

4. Seed ontology metadata from YAML into MySQL:

```powershell
python scripts/seed_ontology.py
```

By default, this seeds the schema-level ontology graph only. It does not write `sample_instances.yaml` or `sample_graph_edges.yaml`.

To include optional sample instance graph data for tests:

```powershell
python scripts/seed_ontology.py --include-sample
```

5. Verify MySQL contains initialized ontology data:

```sql
SELECT COUNT(*) FROM oag_graph_nodes;
SELECT COUNT(*) FROM oag_graph_edges;
SELECT COUNT(*) FROM oag_objects;
SELECT COUNT(*) FROM oag_attributes;
SELECT COUNT(*) FROM oag_query_capabilities;
SELECT COUNT(*) FROM oag_skill_capabilities;
SELECT COUNT(*) FROM oag_intent_profiles;
```

## Online MCP Startup

Start the MCP Server only after MySQL ontology initialization is complete.

```powershell
python -m oag_mcp.server
```

Large-model client registration:

```text
command = python
args = ["-m", "oag_mcp.server"]
```

The online runtime only needs:

- Python dependencies
- `command`
- `args`
- MySQL environment variables
- initialized MySQL ontology metadata

If the ontology graph changes, rerun:

```powershell
python scripts/seed_ontology.py
```

Then restart the MCP Server if the client keeps a long-lived process.

## Period Template Expansion

Some original table descriptions use `xx` as a period placeholder, for example
`dws_fund_perf_xx`, `dws_bm_perf_xx`, `dws_fund_risk retxx`, and fields such as
`区间回报（近xx)` or `最大回撤（近xx）`.

The offline ontology loader expands those templates during `python scripts/seed_ontology.py`
using `ontology/period_variants.yaml`. The online MCP Server does not read that YAML file and
does not interpret `xx` templates at runtime.

Runtime graph nodes use explicit logical names such as:

- `DataTable:dws_fund_perf_1y`
- `DataTable:dws_fund_risk_ret_1y`
- `DataTable:dws_bm_perf_3y`
- `DataField:dws_fund_perf_1y.区间回报（近一年)`

Compact runtime output does not return `xx` template table or field nodes. When
`resolved_params.period=1y`, period-aware filtering prefers nodes and edges with
`period_code=1y` and filters other expanded periods from compact output.

Expanded names are logical ontology names. They are not claimed to be real physical table
names unless a downstream Skill or data service confirms the physical naming rule. For
expanded nodes, `properties_json.params` keeps metadata such as `template_source_table`,
`template_source_field`, `period_code`, `period_name_zh`, `physical_table_name=null`, and
`physical_resolution_required=true`.

## Output Size Control

`oag_retrieve_context` uses `detail_level="compact"` and `debug=false` by default.
Compact output is intended for LLM workflow nodes and model factories: it keeps the
decision-critical objects, intents, fact requirements, Skill invocations, and missing
parameters without exposing physical table or field evidence.

Supported detail levels:

- `compact`: default; returns fact requirements and Skill invocations. It does not return
  candidate queries, source tables, matched relations, relation paths, or relation subgraph.
- `standard`: returns compact fields plus schema and query summaries.
- `full`: for graph debugging; returns full schema evidence. Use with `debug=true`
  to include diagnostic details such as filtering rules and truncation reasons.

Output control rules include:

- `DataField` nodes are not returned as `matched_objects`; fields only appear as full/debug schema evidence.
- Very short aliases such as `年`, `月`, `日`, `周`, `1`, and `0` do not trigger object matches.
- `resolved_params.period` is used to prioritize expanded period-specific graph nodes and
  edges before schema evidence is summarized or returned.
- `mapped_to_field`, `has_field`, `relation_paths`, and `relation_subgraph` are budgeted to
  prevent unbounded schema graph expansion.
- `truncation` reports whether output was clipped, the active limits, original counts,
  returned counts, and reasons such as `output_budget`, `period_filter`, or
  `datafield_noise_filter`.

Example compact call:

```powershell
python -c "import json; from oag_mcp.service import create_context_service; s=create_context_service(); r=s.retrieve_context('分析000001近一年的表现', {'permission_scopes':['fund_public_data:read']}); print(json.dumps(r, ensure_ascii=False, indent=2))"
```

Example full debug call:

```powershell
python -c "import json; from oag_mcp.service import create_context_service; s=create_context_service(); r=s.retrieve_context('分析000001近一年的表现', {'permission_scopes':['fund_public_data:read'], 'detail_level':'full', 'debug': True}); print(json.dumps(r, ensure_ascii=False, indent=2))"
```

## Smoke Test

```powershell
python -c "import json; from oag_mcp.service import create_context_service; s=create_context_service(); r=s.retrieve_context('分析003095近一年收益率和最大回撤表现', {'permission_scopes':['fund_public_data:read']}); print(json.dumps(r, ensure_ascii=False, indent=2))"
```

Expected response fields include:

- `matched_objects`
- `matched_attributes`
- `matched_intents`
- `target_instances`
- `fact_requirements`
- `fact_groups`
- `candidate_invocations`
- `resolved_params`
- `warnings`

If MySQL has not been initialized, the server returns a structured error or empty context with warnings. It will not auto-seed.

## Tests

```powershell
pytest -p no:cacheprovider
```

Optional real MySQL integration test:

```powershell
$env:OAG_RUN_MYSQL_INTEGRATION="1"
pytest -p no:cacheprovider tests\test_integration_runtime.py
```
