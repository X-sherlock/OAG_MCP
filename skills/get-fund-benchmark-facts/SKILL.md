---
name: get-fund-benchmark-facts
description: Query fund return, excess return, and derived benchmark return from ifundtest.ifund_all_info through Java. Use when OAG needs benchmark_metric_value or excess_metric_value facts.
---

# 获取基金基准事实

Java skill_id: `get_fund_benchmark_facts`。返回基金收益、超额收益，并由两者派生基准收益。仅表示 `ifund_all_info` 内部业绩基准口径，不支持任意外部指数收益序列。

执行示例：

```powershell
'{"fund_code":"000001","period":"1y"}' | python script.py
```

只调用本目录的 `script.py`，由脚本转发到 Java Skill API；不得直连数据库，不得拼接 SQL，不得在 skill 节点生成最终分析结论。

## 从 OAG MCP 输出构造输入

只从前置 OAG MCP 节点输出 `{output}` 取值，不要编造基金、指标、周期、筛选条件或结果。输入匹配优先级固定如下：

1. `agentPlan.skill_calls[]`
2. `agent_plan.skill_calls[]`
3. `editor_plan.candidate_invocations[]`
4. `candidateInvocations[]`
5. `candidate_invocations[]`

先找到 `skill_id` 等于 `get_fund_benchmark_facts` 或 `get-fund-benchmark-facts` 的调用，并优先使用该调用的 `params`。只有 `params` 缺字段时，才从 OAG 的 `targets`、`targetInstances`、`facts`、`factRequirements`、`task.constraints`、`normalizedSemanticFrame` 或 `normalized_semantic_frame` 中补齐。不要从自然语言问题中猜值。

需要构造的业务 JSON：

- `fund_code`: 从匹配调用参数或 Fund target 中提取。
- `period`: 从参数、任务约束或事实约束中提取。没有显式 `period` 时使用 OAG/ontology 默认值 `1y`。
- `attributes`: 可忽略；Java 固定尝试返回 `return_rate`、`excess_return`、`benchmark_return`。

常用别名：`fund`、`fund_id`、`code` 可映射为 `fund_code`；`metric`、`metrics`、`attribute` 可映射为 `attributes` 或 `attribute`；`time_range`、`interval` 可映射为 `period`；`candidate_funds` 可映射为 `fund_universe`。

## 能力边界

可返回事实字段：`return_rate`、`excess_return`、`benchmark_return`。支持周期：`1w`、`1m`、`3m`、`6m`、`1y`、`2y`、`3y`、`5y`、`si`。

识别但当前不支持的基准类字段包括 `tracking_error`、`information_ratio`、任意外部指数明细或完整基准收益序列；这些只能作为 unsupported 返回，不得伪造。

## 缺参与 unsupported 处理

缺少 `fund_code` 时不调用；周期不在白名单时不调用并返回 `UNSUPPORTED_PERIOD`。

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

