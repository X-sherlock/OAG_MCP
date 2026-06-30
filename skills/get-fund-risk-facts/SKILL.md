---
name: get-fund-risk-facts
description: Query or derive fund risk facts from ifundtest.ifund_all_info through Java. Use for Calmar ratio, drawdown, volatility, Sharpe, and explicit unsupported risk details.
---

# 获取基金风险事实

Java skill_id: `get_fund_risk_facts`。查询或派生风险指标；`calmar_ratio` 由 `return_rate` 和 `max_drawdown` 派生并带 `derived_from`。

执行示例：

```powershell
'{"fund_code":"000001","period":"1y","attributes":["calmar_ratio","downside_risk"]}' | python script.py
```

只调用本目录的 `script.py`，由脚本转发到 Java Skill API；不得直连数据库，不得拼接 SQL，不得在 skill 节点生成最终分析结论。

## 从 OAG MCP 输出构造输入

只从前置 OAG MCP 节点输出 `{output}` 取值，不要编造基金、指标、周期、筛选条件或结果。输入匹配优先级固定如下：

1. `agentPlan.skill_calls[]`
2. `agent_plan.skill_calls[]`
3. `editor_plan.candidate_invocations[]`
4. `candidateInvocations[]`
5. `candidate_invocations[]`

先找到 `skill_id` 等于 `get_fund_risk_facts` 或 `get-fund-risk-facts` 的调用，并优先使用该调用的 `params`。只有 `params` 缺字段时，才从 OAG 的 `targets`、`targetInstances`、`facts`、`factRequirements`、`task.constraints`、`normalizedSemanticFrame` 或 `normalized_semantic_frame` 中补齐。不要从自然语言问题中猜值。

需要构造的业务 JSON：

- `fund_code`: 从匹配调用参数或 Fund target 中提取。
- `period`: 从参数、任务约束或事实约束中提取。没有显式 `period` 时使用 OAG/ontology 默认值 `1y`。
- `attributes`: 从参数或事实属性中提取；未指定时 Java 默认返回 `max_drawdown`、`volatility`、`standard_deviation`、`sharpe_ratio`、`calmar_ratio`。

常用别名：`fund`、`fund_id`、`code` 可映射为 `fund_code`；`metric`、`metrics`、`attribute` 可映射为 `attributes` 或 `attribute`；`time_range`、`interval` 可映射为 `period`；`candidate_funds` 可映射为 `fund_universe`。

## 能力边界

可返回字段：`max_drawdown`、`drawdown`、`volatility`、`standard_deviation`、`sharpe_ratio`、`calmar_ratio`。周期支持与 `get_fund_metric_values` 的风险周期指标一致。

`downside_risk`、`max_drawdown_peak_date`、`max_drawdown_trough_date`、`max_drawdown_recovery_days`、`sortino_ratio`、`var`、`cvar` 当前为 `ifund_all_info` 不支持字段；调用 Java 后应以 `data_source_status: unsupported_by_ifund_all_info`、`unsupported_attributes`、`missing_attributes` 暴露，不得伪造。

## 缺参与 unsupported 处理

缺少 `fund_code` 时不调用；周期不支持时不调用并返回 `UNSUPPORTED_PERIOD`。

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

