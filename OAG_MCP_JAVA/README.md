# OAG_MCP_JAVA

Java Spring Boot + MyBatis 版 OAG MCP 子工程。

当前 Java 版已升级为 `semantic_frame` 驱动的事实规划器，语义上对齐 Python 版 OAG 的新规划链路：MCP 工具不再以自然语言问题作为正式规划输入，而是消费前置意图识别节点产出的结构化 `semantic_frame`。

构建目标固定为 Java 8：`pom.xml` 使用 Spring Boot 2.7.x、MyBatis Spring Boot 2.x，并通过 `maven-compiler-plugin` 的 `release=8` 防止误用 Java 9+ 语法或标准库 API。

## 结构

```text
OAG_MCP_JAVA/
  pom.xml
  README.md
  src/main/java/com/example/oagmcp/
    OAG_MCP.java
    dao/OAGDAO.java
    dao/entity/OAGEntity.java
    logic/OAGLogic.java
    ontology/*.yaml
    vo/OAGVO.java
  src/main/resources/
    application.yml
    com/example/oagmcp/dao/OAGDAO.xml
```

## 运行定位

- Java 运行时直接读取 `src/main/java/com/example/oagmcp/ontology/*.yaml` 中内置的 OAG ontology 文件。
- 不通过 `application.yml` 配置 ontology 访问路径；`OntologyYamlDao` 固定从 classpath `/com/example/oagmcp/ontology/` 读取。
- 不包含 Java seed，不写数据库。
- Java 内部完整规划输出聚焦 `semantic_frame`、`fact_requirements`、`candidate_invocations`、`task_graph`、`coverage_summary`。
- Java planner 会从 `oag_graph_edges` 召回一跳本体关系边，按 `auto_expand_mode`、`trigger_policy`、`answer_visibility` 和扩展上限补充关系扩展事实。
- Java planner 同时生成 `editor_plan` 和 `agent_plan`：`editor_plan` 保留完整调试结构，`agent_plan` 面向 MCP/智能体执行消费。
- MCP 工具默认返回 `agent_plan`；传入 `output_view=editor` 时返回完整 `editor_plan`。
- 不返回旧 DataTable/DataField/sourceTables 召回结构。

## 环境变量

```text
OAG_DB_HOST=127.0.0.1
OAG_DB_PORT=3306
OAG_DB_NAME=ifundtest
OAG_DB_USER=root
OAG_DB_PASSWORD=
OAG_DOMAIN=finance_market
OAG_MCP_JAVA_PORT=8080
```

## 启动

```bash
mvn spring-boot:run
```

MCP 工具名：`oag_retrieve_context`。

核心参数：

- `semantic_frame`：必填，前置意图识别节点输出的结构化语义框架。
- `question`：可选，仅用于兼容和展示原始问题。
- `user_context.permission_scopes`：建议传入 `["fund_public_data:read"]`，否则需要权限的 Skill 会被标记为未授权。
- `output_view`：可选，默认 `agent`；传 `editor` 返回完整调试计划。
- `options.output_view`：可选，兼容 `output_view` 的配置式写法。

示例 `semantic_frame`：

```json
{
  "domain": "finance_market",
  "raw_question": "查询000001近一年最大回撤和夏普",
  "task_type": "query",
  "intent": null,
  "target_objects": [
    {
      "object_type": "Fund",
      "instance_ref": {"fund_code": "000001"},
      "role": "analysis_subject"
    }
  ],
  "constraints": {"period": "1y"},
  "mentioned_attributes": ["max_drawdown", "sharpe_ratio"],
  "relation_queries": [],
  "filters": [],
  "ranking": [],
  "comparison": {}
}
```

期望核心语义：

- 缺少 `semantic_frame` 时返回 `error_code = SEMANTIC_FRAME_REQUIRED`。
- `semantic_frame.target_objects`、对象类型和显式属性会按 MySQL 本体元数据校验；未知对象或属性返回 `SEMANTIC_FRAME_INVALID`。
- 未配置的 `intent` 不会直接失败；若有显式属性或操作条件，会以 `UNKNOWN_INTENT` warning 继续规划，否则返回 `FACT_REQUIREMENTS_INSUFFICIENT`。
- `semantic_frame_summary` 回显任务类型、目标对象、约束、显式属性、关系查询、筛选、排序和比较条件。
- `fact_requirements` 根据显式属性、意图模板、场景规则、排序/筛选/推荐操作和显式关系查询生成。
- `source = relation_expansion` 的事实来自 `oag_graph_edges`，会保留 `expanded_from` 或 `object_relation` 证据，并在 `task_graph` 中展示 Attribute/ObjectType 关系边。
- `semantic_frame.options.allow_relation_expansion=false` 会关闭本体关系扩展；未知 `relation_queries.relation_type` 会返回 `SEMANTIC_FRAME_INVALID` 和 `UNKNOWN_RELATION_QUERY` 诊断。
- `candidate_invocations` 按 Skill 的 `provides_fact_types`、`supported_subject_types`、`supported_attributes`、`supported_relations` 和权限上下文覆盖事实需求。
- `coverage_summary.coverage_status` 反映必需事实覆盖状态。
- `agent_plan.skill_calls` 给出可执行 Skill、参数、缺失参数和调用状态。

## 验证

```bash
mvn test
```

当前测试覆盖：

- `semantic_frame` 必填错误。
- 显式指标查询生成事实需求、候选 Skill、任务图和 `agent_plan`。
- 图边治理规则会把 `return_rate` 扩展为 `benchmark_return`、`excess_return` 等关系扩展事实。
- `output_view` 默认返回 `agent_plan`，并可切换到完整 `editor_plan`。
- `allow_relation_expansion=false` 会禁用关系扩展；未知关系查询会给出 `UNKNOWN_RELATION_QUERY`。
- YAML fixture 位于 `src/main/java/com/example/oagmcp/ontology/*.yaml`，校验 Java planner 与真实对象、属性、意图、Skill 和 `schema_graph_edges` 配置保持一致。
- 持仓场景基于 `semantic_frame.intent=holding_analysis` 生成持仓事实，并暴露缺失 `report_date`。
- FundSet 排序场景生成 `metric_ranking` 和 `rank_funds_by_metric`。
- 筛选、推荐、多基金比较、画像关系、费率、分红、持仓、资产配置、未知 intent 和非法 semantic_frame。
