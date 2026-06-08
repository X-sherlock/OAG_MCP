# OAG_MCP_JAVA

极简 Java Spring Boot + MyBatis 版 OAG MCP 子工程。

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
    vo/OAGVO.java
  src/main/resources/
    application.yml
    com/example/oagmcp/dao/OAGDAO.xml
```

## 运行定位

- Java 运行时只读 TDSQL/MySQL 中已由 Python `seed_ontology.py` 初始化的 OAG 元数据表。
- 默认数据库名为 `ifundtest`，可通过 `OAG_DB_NAME` 覆盖。
- 不包含 Java seed，不读取 `ontology/*.yaml`，不写数据库。
- compact 默认输出聚焦 ontology-first / fact-requirement-first，不返回 `DataTable`、`DataField`、`sourceTables`。

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

示例问题：`分析000001近一年的表现`

期望核心语义：

- `resolved_params.fund_code = 000001`
- `resolved_params.period = 1y`
- `target_instances` 包含 `Fund` 和 `fund_code=000001`
- `fact_requirements` 包含 `fr_return_rate_1y`、`fr_benchmark_return_1y`、`fr_excess_return_1y`、`fr_max_drawdown_1y`、`fr_volatility_1y`、`fr_sharpe_ratio_1y`、`fr_rank_1y`
- `candidate_invocations` 包含 `get_fund_metric_values`、`get_fund_benchmark_facts`、`get_fund_peer_ranking_facts`
- required fact requirements 均被 `covers_fact_requirements` 覆盖
