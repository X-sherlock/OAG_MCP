# OAG 事实规划主链路设计

## 新定位

OAG 当前定位为“基于前置语义结果的本体事实规划器”。它不负责完整自然语言理解，不查询真实业务数据，不执行业务 SQL，也不生成最终回答。OAG 的职责是根据前置节点输出的 `semantic_frame`，结合本体对象、属性、关系和 Skill 能力，生成本次回答需要的大模型可消费任务子图。

## 输入结构

正式输入是 `semantic_frame`。`raw_question` 仅作为追踪字段，不作为 OAG 自行理解自然语言的依据。

```json
{
  "semantic_frame": {
    "raw_question": "分析000001近一年的表现",
    "domain": "finance_market",
    "task_type": "analyze",
    "intent": "performance_overview",
    "target_objects": [
      {
        "object_type": "Fund",
        "instance_ref": {"fund_code": "000001"},
        "role": "analysis_subject"
      }
    ],
    "constraints": {"period": "1y"},
    "mentioned_attributes": [],
    "relation_queries": [],
    "filters": [],
    "ranking": [],
    "comparison": {},
    "limit": null,
    "options": {}
  },
  "user_context": {
    "permission_scopes": ["fund_public_data:read"],
    "debug": false
  }
}
```

缺少 `semantic_frame` 时返回 `SEMANTIC_FRAME_REQUIRED`，不会回退到 `question` 自然语言解析。

### semantic_frame 字段说明

- `raw_question`：原始问题，仅用于追踪和展示。
- `domain`：当前固定为 `finance_market`。
- `task_type`：通用任务原语，支持 `query`、`analyze`、`compare`、`rank`、`screen`、`recommend`、`profile`、`explain`、`summarize`。
- `intent`：宽泛业务意图，例如 `performance_overview`、`benchmark_comparison`、`peer_comparison`、`fund_profile`、`fund_recommendation`。
- `target_objects`：目标对象列表，支持单个 `Fund`、多个 `Fund` 和 `FundSet`。
- `constraints`：周期、报告日期、数据日期等约束，例如 `{"period": "1y"}`。
- `mentioned_attributes`：上游语义识别出的标准属性名。
- `relation_queries`：显式对象关系查询，例如 `{"relation_type":"managed_by","target_object_type":"FundManager"}`。
- `filters`：集合筛选条件，例如 `{"attribute":"max_drawdown","operator":"<=","value":0.1}`。
- `ranking`：集合排序条件，例如 `{"attribute":"return_rate","direction":"desc"}`。
- `comparison`：比较设置，例如 `{"mode":"side_by_side","attributes":["return_rate"],"target_object_policy":"all_targets"}`。
- `limit`：集合排序、筛选或推荐返回数量。
- `options`：规划策略开关，例如 `allow_relation_expansion`、`allow_peer_expansion`、`include_supporting_context`。

### 目标对象结构

单基金查询：

```json
[{"object_type":"Fund","instance_ref":{"fund_code":"000001"},"role":"analysis_subject"}]
```

多基金比较：

```json
[
  {"object_type":"Fund","instance_ref":{"fund_code":"000001"},"role":"comparison_subject"},
  {"object_type":"Fund","instance_ref":{"fund_code":"000002"},"role":"comparison_subject"}
]
```

基金集合任务：

```json
[{"object_type":"FundSet","instance_ref":{"fund_universe":"all_funds"},"role":"candidate_set"}]
```

## 场景规划矩阵

| 场景 | task_type / intent | 主要事实 | 主要 Skill |
| --- | --- | --- | --- |
| 单基金指标查询 | `query` + 显式属性 | `metric_value` | `get_fund_metric_values` |
| 单基金综合分析 | `analyze / performance_overview` | `return_rate`、`benchmark_return`、`excess_return`、`max_drawdown` | `get_fund_metric_values`、`get_fund_benchmark_facts` |
| 基准比较 | `compare / benchmark_comparison` | `metric_value`、`benchmark_metric_value`、`excess_metric_value`，`has_benchmark` 支撑上下文 | `get_fund_metric_values`、`get_fund_benchmark_facts`、`get_fund_profile_facts` |
| 同类比较 | `compare / peer_comparison` | `peer_rank`、`peer_average`，`belongs_to_category` 支撑上下文 | `get_fund_peer_ranking_facts` |
| 对象关系查询 | `query` + `relation_queries` | `relation_instance` | `get_fund_profile_facts` |
| 多基金比较 | `compare / fund_comparison` | 每个 Fund 的 `metric_value`，派生 `comparison_result` | `get_fund_metric_values`、`compare_funds_by_metric` |
| 集合排序 | `rank / fund_ranking` | `entity_set`、`metric_ranking` | `rank_funds_by_metric` |
| 集合筛选 | `screen / fund_screening` | `entity_set`、`filter_condition` | `screen_funds_by_metric_condition` |
| 基金推荐 | `recommend / fund_recommendation` | `entity_set`、`metric_ranking`、`filter_condition` | `recommend_funds_by_risk_return` |
| 画像查询 | `profile / fund_profile` | `object_profile`、核心 `relation_instance` | `get_fund_profile_facts` |
| 费率/分红/持仓/配置 | `query` + 对应 intent | `fee_fact`、`dividend_fact`、`holding_fact`、`allocation_fact` | `get_fund_fee_facts`、`get_fund_dividend_facts`、`get_fund_holding_facts` |
| 信息不足 | 未知 intent 且无属性/条件 | 无事实需求 | 返回 `need_clarification` 和中文诊断 |

## 输出结构

OAG 内部仍只维护一份完整规划结果。对外输出通过投影器拆成两类消费者视图：

- `agent_plan`：面向后续智能体执行 Skill 调用，默认用于 MCP 工具和服务层调用。
- `editor_plan`：面向 ontology_editor 展示、调试和关系治理，保留完整任务图、诊断和调试证据。

`editor_plan` 保持原有完整结构：

```json
{
  "status": "success",
  "domain": "finance_market",
  "raw_question": "...",
  "semantic_frame_summary": {},
  "target_instances": [],
  "fact_requirements": [],
  "candidate_invocations": [],
  "task_graph": {"nodes": [], "edges": []},
  "coverage_summary": {},
  "missing_params": [],
  "warnings": []
}
```

`task_graph` 是由本次事实需求和候选 Skill 反向构造的任务子图，不是全局本体图的一跳/两跳截取。`editor_plan` 的任务图用于页面展示、点击高亮、治理排查和高级调试，因此继续包含 `Parameter` 节点、`requires_param` 边、`diagnostics`、`warnings` 和可选 `debug_evidence`。

`agent_plan` 是稳定的执行投影，不返回 `task_graph`、`debug_evidence`、`normalized_semantic_frame`、`sent_semantic_frame`、完整 `subject` 对象或完整 `attribute` 对象。后续智能体应只消费 `agent_plan`，根据 `skill_calls` 调用 Skill，再结合 Skill 返回数据完成分析总结。

`agent_plan` 字段如下：

```json
{
  "status": "success",
  "task": {
    "raw_question": "...",
    "domain": "finance_market",
    "task_type": "query",
    "intent": "holding_analysis",
    "constraints": {"period": "1y"}
  },
  "targets": [
    {
      "target_id": "TargetInstance:Fund:1",
      "object_type": "Fund",
      "label_zh": "基金 000001",
      "instance_ref": {"fund_code": "000001"},
      "role": "analysis_subject"
    }
  ],
  "facts": [
    {
      "fact_id": "FactRequirement:fr_stock_name_000001_1y",
      "fact_type": "holding_fact",
      "fact_type_zh": "持仓事实",
      "target_id": "TargetInstance:Fund:1",
      "attribute": "stock_name",
      "attribute_zh": "股票名称",
      "predicate": null,
      "target_object_type": null,
      "constraints": {"period": "1y"},
      "priority": "required",
      "source": "intent_template",
      "reason_zh": "持仓查询需要获取主要持仓名称事实。"
    }
  ],
  "skill_calls": [
    {
      "skill_id": "get_fund_holding_facts",
      "skill_name_zh": "获取基金持仓与配置事实",
      "description_zh": "获取基金持仓、行业配置和资产配置事实声明。",
      "params": {"fund_code": "000001"},
      "missing_params": ["report_date"],
      "covers": ["FactRequirement:fr_stock_name_000001_1y"],
      "covers_required_count": 1,
      "covers_optional_count": 0,
      "coverage_score": 1,
      "coverage_reason_zh": "该 Skill 支持基金持仓事实查询。",
      "call_status": "blocked_missing_params"
    }
  ],
  "coverage": {
    "coverage_status": "full_coverage",
    "required_fact_count": 4,
    "covered_required_fact_count": 4,
    "uncovered_required_facts": [],
    "optional_fact_count": 0,
    "covered_optional_fact_count": 0,
    "message_zh": "必需事实均有 Skill 覆盖，规划可以继续执行。"
  },
  "execution": {
    "execution_status": "blocked_missing_params",
    "ready_skill_count": 0,
    "blocked_skill_count": 1,
    "message_zh": "存在 Skill 调用缺失参数，需要补充后再执行。",
    "blocking_issues": []
  },
  "uncovered_facts": [],
  "issues": []
}
```

`coverage_status` 和 `execution_status` 必须分开理解：

- `coverage_status` 回答“有没有 Skill 能力覆盖事实”。例如 `full_coverage` 表示必需事实均有 Skill 能覆盖。
- `execution_status` 回答“当前是否能直接执行 Skill 调用”。例如 `blocked_missing_params` 表示虽然有 Skill 能覆盖事实，但调用参数还不完整。

缺失参数只在两个位置保留：`skill_calls[].missing_params` 作为机器可读参数列表，`execution.blocking_issues` 作为聚合阻断原因。`issues` 只收敛非阻断 warning、权限或未覆盖事实等对智能体有用的问题，并按 `code + skill_id + fact_id + message_zh` 去重。

输出视图通过 `output_view` 切换：

- MCP 工具 `oag_retrieve_context(..., output_view="agent")` 默认返回 `agent_plan`。
- 服务层 `retrieve_context(..., output_view="agent")` 默认返回 `agent_plan`。
- `output_view="editor"` 返回完整 `editor_plan`。
- ontology_editor 的 `/api/oag/plan` 默认使用 `editor`，也支持 body 或 query 中传 `output_view=agent|editor`。

`task_graph` 不进入 `agent_plan`，因为它服务于页面展示和本体治理，不是后续智能体执行 Skill 的必要输入；保留它会把参数节点、解释边、调试证据和重复语义框架一起暴露给执行节点，增加下游提示词和状态管理成本。

## Fact Requirement 来源

事实需求来源分三类：

1. `explicit_attribute`：`mentioned_attributes` 中用户显式提到的属性，优先级最高，默认生成 required fact。
2. `intent_template`：当没有显式属性且 `intent` 命中 `intent_profiles.yaml` 时，使用 `fact_requirements_template` 补全宽泛问题所需事实。
3. `operation_rule`：对 `rank`、`screen`、`recommend`、`compare` 等操作型任务，根据 `ranking`、`filters`、`target_objects` 和 `constraints` 生成集合、排序或过滤事实。

显式属性不会强制展开完整意图模板。

## 本体关系作用

本阶段开始，本体关系不再只是展示连线，而是事实规划依据。关系参与五类决策：

1. 事实扩展：例如 `return_rate compared_with benchmark_return` 可补充基准收益事实。
2. 对象关系事实：例如 `Fund managed_by FundManager` 可生成 `relation_instance`。
3. Skill 覆盖判断：Skill 通过 `provides_fact_types`、`supported_subject_types`、`supported_attributes`、`supported_relations` 覆盖事实。
4. task_graph 解释路径：标准任务图展示本次相关的属性关系、对象关系和 Skill 覆盖边。
5. diagnostics：发现缺少中文原因、适用范围、Skill 能力声明或节点引用错误。

`relation_types.yaml` 按用途分层：

- `object_structure`：对象结构关系，如 `managed_by`、`issued_by`、`has_benchmark`、`tracks_index`、`belongs_to_category`、`has_fee`、`has_dividend`。
- `metric_semantics`：指标语义关系，如 `compared_with`、`derives`、`ranked_by_peer`、`risk_companion`、`return_companion`、`benchmark_metric_of`、`peer_metric_of`。
- `task_intent`：任务和意图关系，如 `requires_attribute`、`optional_attribute`、`uses_metric_role`、`uses_operation`、`requires_fact_type`。
- `skill_capability`：Skill 能力关系，如 `provides_fact_type`、`supports_attribute`、`supports_subject_type`、`requires_param`、`returns_attribute`、`requires_permission`。
- `implementation_evidence`：实现证据关系，如 `implemented_by_query`、`reads_from`、`has_field`、`mapped_to_field`。

标准 `task_graph` 只包含本次问题相关的对象、属性、事实需求、Skill、约束和解释关系；`DataTable`、`DataField`、`QueryCapability` 继续只作为 `debug_evidence` 或种子图实现证据，不进入标准任务图。

## 关系扩展策略

OAG 在初始事实需求基础上做受控 1 跳关系扩展。`applicable_tasks` 和 `applicable_intents` 仍保留为兼容字段，但它们只表示“相关范围”，不能单独等价为“允许自动扩展”。真正控制扩展的是 `schema_graph_edges.yaml` 和 `relation_types.yaml` 上的策略字段：

- `planning_role`：关系在规划中的角色，例如 `metric_context`、`benchmark_context`、`peer_context`、`risk_context`、`profile_context`、`object_dependency`、`implementation_evidence`。
- `auto_expand_mode`：是否允许自动扩展。`contextual` 表示满足触发策略才扩展；`explicit_only` 表示只有显式属性或显式关系查询才触发；`dependency_only` 表示只作为内部依赖；`debug_only` 只进调试证据；`disabled` 不参与规划。
- `answer_visibility`：扩展结果是否进入标准事实和任务图。`answer_fact` 进入回答事实；`supporting_context` 作为支撑上下文弱展示；`hidden_dependency` 不进入标准任务图；`debug_only` 只进入调试证据。
- `expansion_priority`：扩展事实的默认优先级，支持 `required`、`optional`、`supporting`、`debug`。
- `trigger_policy`：进一步限制任务、意图、源属性、源事实类型、已有事实类型、是否需要显式属性或关系查询。
- `expansion_limits`：限制每个源属性、全局数量和扩展深度。

扩展前会检查：

- `relation_type` 是否属于可进入 task_graph 的语义关系或对象关系。
- 边的 `auto_expand_mode` 是否允许本次规划触发。
- 边的 `trigger_policy.tasks` 是否包含当前 `semantic_frame.task_type`。
- 边的 `trigger_policy.intents` 是否包含当前 `semantic_frame.intent`；未给出 intent 时不强制过滤。
- 边的 `trigger_policy.source_attributes`、`source_fact_types`、`requires_existing_fact_types` 是否满足当前事实需求。
- 扩展源事实是否来自 required fact，用户显式属性不会被降级。
- 目标事实是否已存在，已存在时只补充关系解释边，不重复生成事实。
- 每个 required fact 默认最多扩展 3 个 optional fact，全局默认最多 8 个关系扩展事实。

关系扩展事实默认 `priority=optional`，除非边配置 `expansion_priority` 或兼容字段 `default_priority`。每条扩展事实和 task_graph 关系边都携带中文 `reason_zh`。

关系分层执行规则：

- 指标语义扩展：`compared_with`、`derives`、`ranked_by_peer`、`risk_companion`、`return_companion`、`benchmark_metric_of`、`peer_metric_of` 默认是 `contextual + answer_fact`，只在任务、意图和源指标匹配时补充指标事实。
- 对象依赖关系：`has_benchmark`、`belongs_to_category` 默认是 `contextual + supporting_context`。基准关系只在已有基准收益、超额收益、跟踪误差或信息比率事实时触发；分类关系只在同类排名、同类均值、排序、推荐或筛选任务中触发。
- 对象画像关系：`managed_by`、`issued_by`、`has_fee`、`has_dividend`、`has_position`、`has_asset_allocation` 等默认是 `explicit_only`。普通最大回撤、夏普、收益率查询不会自动拉入基金经理、基金公司、费率、分红、持仓或资产配置。
- Skill 能力关系：`provides_fact_type`、`supports_attribute`、`supports_subject_type`、`supports_relation` 等只用于覆盖匹配或覆盖路径展示，不作为业务事实扩展。
- 实现证据关系：`implemented_by_query`、`reads_from`、`sourced_from_table`、`has_field`、`mapped_to_field`、`joins_on` 是 `debug_only`，不进入标准任务图。

对象画像关系默认不自动扩展，是为了避免“只要本体有关系就拉成大图”。例如用户问“查询000001近一年最大回撤和夏普”时，答案需要的是风险指标和少量同类/风险伴随事实；基金经理、基金公司、费率、分红、持仓和资产配置虽然与基金有关，但不是该指标查询的事实需求。

典型示例：

- 最大回撤和夏普查询：required facts 是 `max_drawdown`、`sharpe_ratio`；optional facts 可包含 `volatility`、`calmar_ratio`、`peer_drawdown_rank`、`peer_sharpe_rank`；不生成 `managed_by`、`issued_by`、`has_fee`、`has_dividend`、`has_position`、`has_asset_allocation` answer facts。
- 跑赢基准查询：required facts 是 `return_rate`、`benchmark_return`、`excess_return`；`has_benchmark` 可作为 `supporting_context`，不触发基金经理、基金公司、费率或分红。
- 同类排名查询：required facts 是 `rank` 或具体同类排名事实；`belongs_to_category` 可作为 `supporting_context`，不作为 required answer fact。
- 基金经理查询：`mentioned_attributes=["fund_manager"]` 或 `relation_queries=[{"relation_type":"managed_by"}]` 会生成 required `relation_instance managed_by`，并由 `get_fund_profile_facts` 覆盖。

## relation_instance 事实

当 `semantic_frame` 明确表达对象关系查询，或 `mentioned_attributes` 使用关系别名时，OAG 生成 `relation_instance` 事实。

示例：`mentioned_attributes=["fund_manager"]` 会映射为：

```json
{
  "fact_type": "relation_instance",
  "subject": {"object_type": "Fund", "subject_id": "Fund:000001"},
  "predicate": "managed_by",
  "target_object_type": "FundManager",
  "priority": "required",
  "reason_zh": "用户需要查询基金与基金经理之间的管理关系。"
}
```

也支持显式 `semantic_frame.relation_queries`，例如 `{"relation_type": "managed_by", "target_object_type": "FundManager"}`。

## Skill 覆盖匹配

Skill 匹配基于能力声明，不基于名称猜测。一个 Skill 覆盖事实需求至少需要满足：

1. `provides_fact_types` 覆盖事实类型。
2. `supported_subject_types` 覆盖事实主体类型。
3. `supported_attributes` 覆盖属性。
4. `input_params` 可由 `semantic_frame.target_objects.instance_ref`、`constraints` 或其他结构化字段填充。
5. `permission_scope` 在 `user_context.permission_scopes` 中。

对 `relation_instance`，Skill 满足以下任一条件即可覆盖关系维度：

- `supported_relations` 包含对应 `predicate`，如 `managed_by`。
- `supported_attributes` 包含实际存在的关系目标属性，如 `manager_name`、`company_name`、`benchmark_name`、`fund_type`。
- Skill 同时声明 `object_profile` 和 `relation_instance` 相关事实能力。

输出的 `candidate_invocations` 包含 `skill_id`、`skill_name_zh`、`description_zh`、`covers_fact_requirements`、`params`、`missing_params`、`coverage_score`、`covers_required_count`、`covers_optional_count`、`coverage_reason_zh` 和 `uncovered_reason_zh`。

`coverage_score` 是按事实优先级加权后的覆盖比例：required fact 权重高于 optional fact。`coverage_reason_zh` 用中文说明 Skill 为什么能覆盖这些事实。

## coverage_summary 状态

`coverage_summary` 用于表达事实需求是否可执行，字段包括：

- `required_fact_count`
- `covered_required_fact_count`
- `uncovered_required_facts`
- `optional_fact_count`
- `covered_optional_fact_count`
- `uncovered_optional_facts`
- `supporting_context_count`
- `covered_supporting_context_count`
- `uncovered_supporting_context`
- `derived_fact_count`
- `covered_derived_fact_count`
- `uncovered_derived_facts`
- `skill_count`
- `has_permission_blocked_facts`
- `coverage_status`
- `coverage_message_zh`

`coverage_status` 取值：

- `full_coverage`：required facts 全部覆盖。
- `partial_coverage`：required facts 部分覆盖。
- `no_coverage`：required facts 无覆盖。
- `need_clarification`：语义不足，无法规划事实。
- `permission_blocked`：主要事实被权限阻断。

多基金比较中的 `comparison_result` 可以由所有比较主体的同一指标事实派生。若每个主体的基础 `metric_value` 都已覆盖，派生事实计入 `covered_derived_fact_count`；如果存在 `compare_funds_by_metric`，也可以直接覆盖 `comparison_result`。

## 诊断规则

规划输出包含 `diagnostics`。诊断不会替代事实需求，而是解释为何无法规划或为何覆盖不足，典型规则包括：

1. `SEMANTIC_FRAME_TARGET_MISSING`：缺少目标对象。
2. `COMPARE_TARGET_TOO_FEW`：比较任务少于两个 Fund。
3. `FUNDSET_TARGET_MISSING`：排序、筛选或推荐任务缺少 FundSet。
4. `UNKNOWN_CONDITION_ATTRIBUTE`：ranking 或 filters 中属性不存在。
5. `UNKNOWN_RELATION_QUERY`：relation_queries 中关系不存在或不支持。
6. `FACT_REQUIREMENTS_EMPTY`：没有生成事实需求。
7. `CANDIDATE_INVOCATIONS_EMPTY`：有事实需求但没有 Skill 覆盖。
8. `REQUIRED_FACT_UNCOVERED`：必需事实未覆盖。
9. `RELATION_INSTANCE_UNCOVERED`：关系事实没有 profile Skill 覆盖。
10. `FUNDSET_RANKING_SKILL_MISSING`：FundSet 排序缺少 Skill。
11. `FUNDSET_SCREENING_SKILL_MISSING`：FundSet 筛选缺少 Skill。
12. `MULTI_TARGET_FACT_MISSING`：多主体任务丢失了某个目标对象的事实需求。
13. `INTENT_TEMPLATE_MISSING`：未知 intent 无模板且无显式属性。
14. `SKILL_PARAMS_MISSING`：候选 Skill 缺少调用参数。

每条诊断都提供 `message_zh` 和 `suggestion_zh`，前端必须展示，不允许静默空白。

## 完整样例

多基金比较输入：

```json
{
  "raw_question": "比较000001和000002近一年收益",
  "domain": "finance_market",
  "task_type": "compare",
  "intent": "fund_comparison",
  "target_objects": [
    {"object_type":"Fund","instance_ref":{"fund_code":"000001"},"role":"comparison_subject"},
    {"object_type":"Fund","instance_ref":{"fund_code":"000002"},"role":"comparison_subject"}
  ],
  "constraints": {"period":"1y"},
  "mentioned_attributes": ["return_rate"],
  "comparison": {"mode":"side_by_side","attributes":["return_rate"],"target_object_policy":"all_targets"}
}
```

关键 `fact_requirements`：

- `Fund:000001` 的 `return_rate / metric_value`。
- `Fund:000002` 的 `return_rate / metric_value`。
- `comparison_result / return_rate`，可由两个已覆盖的指标事实派生，或由 `compare_funds_by_metric` 直接覆盖。

基金推荐输入：

```json
{
  "raw_question": "推荐近一年收益高、回撤低的基金",
  "domain": "finance_market",
  "task_type": "recommend",
  "intent": "fund_recommendation",
  "target_objects": [{"object_type":"FundSet","instance_ref":{"fund_universe":"all_funds"},"role":"candidate_set"}],
  "constraints": {"period":"1y"},
  "ranking": [{"attribute":"return_rate","direction":"desc"},{"attribute":"max_drawdown","direction":"asc"}],
  "filters": [{"attribute":"max_drawdown","operator":"<=","value":0.1}],
  "limit": 10
}
```

关键 `fact_requirements`：

- `entity_set`：候选基金集合。
- `metric_ranking / return_rate desc`。
- `metric_ranking / max_drawdown asc`。
- `filter_condition / max_drawdown <= 0.1`。
- 候选 Skill：`recommend_funds_by_risk_return`，可联合覆盖集合、排序和筛选事实。

## ontology diagnostics

`oag_mcp.ontology_diagnostics.diagnose_ontology()` 提供轻量诊断能力，当前不暴露 HTTP API。诊断结果面向后续 ontology_editor 展示，统一包含：

- `diagnostic_type`
- `severity`
- `node_id` 或 `edge_id`
- `diagnostic_message_zh`
- `suggested_action_zh`

当前覆盖诊断项：

1. Attribute 没有任何启用 Skill 声明覆盖。
2. Skill 没有 `provides_fact_types`。
3. Skill 没有 `supported_attributes`。
4. Skill 没有 `supported_subject_types`。
5. IntentProfile 没有 `fact_requirements_template`。
6. 关系边引用了不存在的节点。
7. 语义扩展边缺少 `reason_zh`。
8. 语义扩展边缺少 `applicable_tasks` 或 `applicable_intents`。
9. 规划结果中的 required fact 没有任何 Skill 覆盖。

## 不再使用 compact 作为核心设计

旧链路先召回大图，再用 `compact/standard/full` 裁剪输出。新链路先生成小而准的事实需求，再由事实需求和 Skill 反向构造任务子图，因此不需要把过大的结果裁剪成 compact。排查问题时使用 `debug=true` 返回 `debug_evidence`，但这不是正常消费主结果。

## 不再保留 question fallback

自然语言理解应由前置意图识别节点完成。保留 `question` fallback 会让 OAG 同时承担解析和规划两类职责，导致事实需求来源不清、测试不可控、能力边界模糊。因此 OAG 入口要求 `semantic_frame`，`raw_question` 只用于追踪和审计。

## 中文展示字段约定

后端输出中凡是未来可能展示给前端的内容，都提供中文字段，例如：

`label_zh`、`description_zh`、`reason_zh`、`warning_zh`、`diagnostic_message_zh`、`suggested_action_zh`、`message_zh`、`display_name_zh`、`skill_name_zh`。

英文技术字段仍保留给机器消费，但前端不应直接展示 `fact_requirement_id`、`supported_attributes`、`provides_fact_types` 等内部字段名。
