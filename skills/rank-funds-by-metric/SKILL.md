---
name: rank-funds-by-metric
description: Rank all funds or a supplied fund universe by a supported period metric through Java and ifund_all_info.
---

# 按指标排序基金

Java skill_id: `rank_funds_by_metric`。对全量基金或给定基金池按单个指标排序，输出 `ranking`。

执行示例：

```powershell
'{"attribute":"return_rate","period":"1y","direction":"desc","limit":10}' | python script.py
```

只调用本目录的 `script.py`，由脚本转发到 Java Skill API；不得直连数据库，不得拼接 SQL，不得在 skill 节点生成最终分析结论。

## 从 OAG MCP 输出构造输入

只从前置 OAG MCP 节点输出 `{output}` 取值，不要编造基金、指标、周期、筛选条件或结果。输入匹配优先级固定如下：

1. `agentPlan.skill_calls[]`
2. `agent_plan.skill_calls[]`
3. `editor_plan.candidate_invocations[]`
4. `candidateInvocations[]`
5. `candidate_invocations[]`

先找到 `skill_id` 等于 `rank_funds_by_metric` 或 `rank-funds-by-metric` 的调用，并优先使用该调用的 `params`。只有 `params` 缺字段时，才从 OAG 的 `targets`、`targetInstances`、`facts`、`factRequirements`、`task.constraints`、`normalizedSemanticFrame` 或 `normalized_semantic_frame` 中补齐。不要从自然语言问题中猜值。

需要构造的业务 JSON：

- `attribute`: 从 `params.attribute`、`params.attributes[0]`、`params.ranking[0].attribute` 或 `ranking[0].attribute` 提取一个主排序指标。
- `period`: 从参数、ranking 或任务约束中提取。没有显式 `period` 时使用 OAG/ontology 默认值 `1y`。
- `direction`: 从参数或 ranking 中提取；没有时默认 `desc`。
- `limit`: 从参数、`top_k`、`top_n` 提取；没有时省略，Java 默认 20。
- `fund_universe`: 可从候选基金池或多个 Fund target 提取；没有时省略，表示全量基金排序。

常用别名：`fund`、`fund_id`、`code` 可映射为 `fund_code`；`metric`、`metrics`、`attribute` 可映射为 `attributes` 或 `attribute`；`time_range`、`interval` 可映射为 `period`；`candidate_funds` 可映射为 `fund_universe`。

## 能力边界

可排序字段：`return_rate`、`max_drawdown`、`drawdown`、`volatility`、`standard_deviation`、`sharpe_ratio`、`peer_return_rank`、`peer_drawdown_rank`、`peer_volatility_rank`、`peer_sharpe_rank`。排序只支持一个主指标。`annualized_return` 是固定年化字段，不适合作为周期排序指标，除非 Java 后续明确支持。

## 缺参与 unsupported 处理

缺少 `attribute` 时不调用。`period` 缺失时用默认 `1y`；属性在该周期不支持时不调用并返回 `UNSUPPORTED_PERIOD`。

如果无法构造合法输入，返回 `called:false` 的 `skill_result`，不要调用 `script.py`。如果 Java 返回 `data_source_status: "unsupported_by_ifund_all_info"`、`unsupported_attributes` 或 `missing_attributes`，必须原样保留在 `result` 中交给后续 synthesis 节点。

## 输出契约

本 skill 节点只负责执行数据获取，不做最终自然语言分析、评价或投资建议。最终输出必须是一个 JSON 对象，形态如下：

```json
{
  "node_type": "skill_result",
  "skill_id": "<snake_case_skill_id>",
  "called": true,
  "input": {},
  "result": {},
  "error": null
}
```

- 成功调用 `script.py` 时：`called=true`，`input` 为实际写入 stdin 的业务 JSON，`result` 为 `script.py` 打印的 JSON 对象，`error=null`。
- 缺少必填参数、没有匹配的 OAG 调用、属性或周期不支持时：不要调用 `script.py`，返回 `called=false`、`result=null`，并在 `error` 中写明 `code`、`message`、`missing_fields` 或 `unsupported_attributes`。
- 已调用 `script.py` 但脚本退出失败或 Java 返回 `success:false` 时：返回 `called=true`，保留脚本 JSON 到 `result`，并设置 `error.code="SKILL_EXECUTION_FAILED"`。
- 只能输出上述 JSON，不输出 Markdown、解释文本或额外包装。

