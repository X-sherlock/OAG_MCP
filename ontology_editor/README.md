# OAG Ontology Editor

轻量级 OAG 事实规划与本体关系治理工作台，用于调试 Python OAG 主链路生成的事实规划，并维护 `ontology/*.yaml` 中的对象、属性、事实类型、关系、查询能力、Skill、Intent、数据源、表和字段配置。

这个工具不查询真实基金业务数据，不执行真实指标查询，不生成 mock 业务结果，也不会在启动或保存时自动 seed。

## 启动方式

安装依赖：

```bash
pip install fastapi uvicorn PyYAML pydantic
```

启动：

```bash
python ontology_editor/app.py
```

或：

```bash
uvicorn ontology_editor.app:app --reload --host 127.0.0.1 --port 8010
```

访问：

```text
http://127.0.0.1:8010
```

## 页面用途

- 在“OAG 规划调试”中输入或粘贴 semantic_frame，调用 Python OAG 事实规划主链路，展示事实需求、Skill 覆盖情况和任务子图。
- 以 Cytoscape.js 图谱展示本次 task_graph 或当前 OAG ontology。
- 展示 `ObjectType`、`Attribute`、`RelationType`、`QueryCapability`、`SkillCapability`、`IntentProfile`、`DataSource`、`DataTable`、`DataField`、`PeriodVariant`、`InstanceRule` 节点。
- 展示 `schema_graph_edges.yaml` 显式边，以及从 Skill、Intent、Query、Attribute、Table schema 等 YAML 推导出的 inferred edges。
- 辅助编辑意图事实模板、属性语义扩展关系、对象关系和 Skill 覆盖能力，并写回本地 YAML 文件。

页面现在默认进入“OAG 事实规划与本体关系治理工作台”首页，不会一打开就加载大图。优先选择 OAG 规划调试或治理入口；需要全图浏览时进入“本体核心图”。

## OAG 规划调试视图

“OAG 规划调试”是本阶段核心入口。它提供问题输入和 JSON 输入两种模式：

- 问题输入模式只要求填写原始问题。页面会基于问题自动生成 `semantic_frame` 草稿，识别任务类型、业务意图、基金代码、目标集合、周期、常见指标、关系查询、筛选/排序/比较条件和返回数量。
- “结构化草稿（可选校正）”默认折叠，仅用于排查或覆盖自动识别结果，不再要求工作台用户逐项手动选择语义字段。
- JSON 模式用于直接粘贴 semantic_frame，适合排查上游意图识别输出。
- 示例场景按钮覆盖“分析某基金近一年表现”“查询某基金最大回撤和夏普”“查询某基金经理”“查询某基金公司”“查询某基金业绩基准”“比较两只基金收益”“推荐收益高、回撤低的基金”“筛选最大回撤低于10%的基金”“查询同类排名”“查询费率”“查询分红”“查询持仓配置”。
- 点击“生成事实规划”会调用 `/api/oag/plan`，不会查询真实业务数据，也不会调用大模型。
- Editor 默认请求 `output_view=editor` 对应的完整 `editor_plan`，用于保留任务图、诊断、缺失参数、调试证据和中文展示字段；MCP 或后续智能体默认消费精简的 `agent_plan`。
- 规划结果会在原始输出中保留 `sent_semantic_frame`，用于确认页面实际发送给后端的结构化输入。

规划结果在右侧 Inspector 中展示：

- 规划状态：规划成功、需要补充信息或规划失败。
- 目标对象：本次问题作用于哪些对象。
- 事实需求数量：本次回答需要多少事实。
- 必须事实覆盖：必须查询事实中有多少已被 Skill 覆盖。
- 辅助事实覆盖：辅助参考事实中有多少已被 Skill 覆盖。
- 候选 Skill 数量：本次可参与调用的 Skill 数量。
- 缺失参数和未覆盖事实：提示是否需要补参数或补能力声明。
- 中文诊断：展示无法规划、目标对象不足、FundSet 缺失、属性或关系不存在、Skill 覆盖缺口等原因和建议。

事实需求列表的含义：

- 事实名称：本次需要获取或判断的业务事实。
- 事实类型：指标值事实、基准指标事实、超额收益事实、同类排名事实、对象关系事实等。
- 查询对象：事实作用的基金、基金集合、基金经理、基金公司等对象。
- 指标/关系：事实对应的指标属性或对象关系。
- 优先级：必须查询或辅助参考。
- 来源：显式属性、意图模板、关系扩展、操作规则或显式关系查询。
- 需要原因：OAG 为什么需要该事实，用中文 reason 展示。
- 覆盖状态：通过候选 Skill 和覆盖摘要判断。

右侧执行摘要展示覆盖情况、事实需求、缺口诊断和任务图说明，不再重复展示候选 Skill 调用列表。点击事实或图中的 Skill 会高亮任务子图中的对应节点并查看细节。任务子图只展示规划相关节点，不展示 DataTable、DataField、QueryCapability；实现证据只放在“高级调试”折叠区。

“原始数据”和“高级调试”仍展示完整 `editor_plan`，包括 `normalized_semantic_frame`、`target_instances`、`fact_requirements`、`candidate_invocations`、`task_graph`、`coverage_summary`、`diagnostics`、`warnings`、`debug_evidence` 和页面补充的 `sent_semantic_frame`。这些字段服务于 Editor 调试和本体治理，不要求后续智能体消费。

任务子图中常见节点含义：

- 语义输入：本次 semantic_frame。
- 任务类型：分析、比较、排序、筛选、推荐、解释、查询。
- 意图模板：命中的宽泛意图配置。
- 目标对象：基金、基金集合、基金经理、基金公司等。
- 约束条件：周期、报告日期、排序或筛选条件等。
- 事实需求：OAG 需要满足的事实。
- 指标属性：事实关联的本体属性。
- 排序/筛选条件：集合任务中的 `ranking` 和 `filters`。
- Skill 能力：可覆盖事实的能力声明。

任务子图中常见边含义：

- 需要事实：语义输入需要某个事实。
- 拥有属性：事实关联某个指标属性。
- 关系扩展：本体关系触发了补充事实。
- 由 Skill 覆盖：某个 Skill 可获取或生成该事实。
- 需要参数：调用 Skill 前还缺参数。
- 使用约束：事实或任务受周期、筛选等条件约束。

## 工作台任务入口

左侧“主功能入口”提供常用工作流：

- OAG 规划调试：输入 semantic_frame 并生成事实规划。
- 本体核心图：保留现有图谱浏览、聚焦和编辑能力。
- 意图模板：维护 `intent_profiles.yaml` 中的事实需求模板。
- 关系治理：维护 `schema_graph_edges.yaml` 中的属性语义扩展边和对象关系边。
- Skill 覆盖：维护 `skills.yaml` 中的事实覆盖能力声明。
- 诊断中心：查看意图模板、Skill 能力、关系边、属性覆盖和必须事实覆盖问题。
- YAML 文件：查看文件状态、导出 YAML 和进入高级文件维护。

点击任务卡片后，左侧只显示该任务的候选节点；选择具体节点后，中间画布才加载 focus 子图。

## 浏览模式和编辑模式

默认是浏览模式：

- 可以搜索、聚焦、跳转、查看 Inspector。
- 右侧核心表单和“原始数据”只读。
- 保存、删除、新增节点、创建边等写操作不可用。

点击“进入编辑模式”后才允许写入 YAML。进入时页面会提示：编辑会修改 `ontology/*.yaml`，保存前会自动备份。退出编辑模式、切换任务、刷新图谱或切换选中对象时，如果当前对象有未保存修改，会提示保存、放弃或取消。

## 未保存修改和 Diff 预览

编辑核心表单或“原始数据”后，顶部会显示：

- `未保存修改：1`
- 当前编辑对象 id

左侧 YAML 文件列表会在对应文件名后显示 `*`。点击保存时，页面先比较原始数据和当前数据，弹出简洁变更预览：

- changed fields
- added fields
- removed fields

确认后才调用 `/api/graph/node` 或 `/api/graph/edge` 写回 YAML。保存失败时 dirty 状态会保留。

## 会修改的 YAML 文件

仅允许读写以下白名单文件：

- `ontology/attributes.yaml`
- `ontology/data_sources.yaml`
- `ontology/fact_types.yaml`
- `ontology/instance_rules.yaml`
- `ontology/intent_profiles.yaml`
- `ontology/object_types.yaml`
- `ontology/period_variants.yaml`
- `ontology/queries.yaml`
- `ontology/relation_types.yaml`
- `ontology/schema_graph_edges.yaml`
- `ontology/skills.yaml`
- `ontology/table_schemas.yaml`

如果误写为 `table_shcemas.yaml`，后端不会创建或使用该错误文件，只会提示应使用 `table_schemas.yaml`。

## 编辑节点

1. 点击“进入编辑模式”。
2. 点击图中的节点。
3. 在右侧 Inspector 修改核心字段，或在“原始数据”标签页直接编辑。
4. 点击“保存当前修改”或 Inspector 内的“保存”。
5. 在 Diff 预览中确认保存。
4. 后端会根据节点类型写入对应 YAML，例如：
   - `SkillCapability` 写入 `skills.yaml`
   - `ObjectType` 写入 `object_types.yaml`
   - `Attribute` 写入 `attributes.yaml`
   - `QueryCapability` 写入 `queries.yaml`
   - `IntentProfile` 写入 `intent_profiles.yaml`
   - `DataTable` / `DataField` 写入 `table_schemas.yaml`

Skill 节点支持编辑 Skill 名称、说明、启用状态、目标对象、输入参数、输出属性、能提供的事实类型、支持对象类型、支持属性、权限范围等字段。

新增节点默认使用向导，不再要求手写完整原始数据。当前支持 `SkillCapability`、`Attribute`、`IntentProfile`、`QueryCapability`、`RelationType`、`FactType`、`ObjectType`、`DataTable`、`DataField` 等类型。向导下拉和多选数据来自 `/api/options`。

## 维护意图事实模板

进入“意图模板”后，左侧列表展示意图中文名和默认事实数量。点击某个意图可以维护：

- 意图中文名和适用对象。
- 默认事实模板中的事实类型、属性、优先级和中文原因。
- 新增事实需求、删除事实需求、调整“必须查询 / 辅助参考”。

保存前会展示中文变更预览，确认后写回 `intent_profiles.yaml` 并保留备份。保存后可以回到“OAG 规划调试”，选择该意图生成示例规划。

## 维护语义扩展关系

进入“关系治理”后，页面按属性语义扩展关系和对象关系展示核心边：

- 属性语义扩展关系用于说明一个指标为什么会扩展到另一个指标，例如区间收益率扩展到基准收益率、超额收益率或同类排名。
- 对象关系用于说明业务对象之间的关系，例如基金到基金经理、基金公司、业绩比较基准、基金分类或跟踪指数。

新增或编辑关系边时填写起点节点、终点节点、关系类型、适用任务、适用意图、默认优先级、规划角色、自动扩展模式、答案可见性、扩展优先级、触发策略、扩展限制、权重和中文原因。保存写回 `schema_graph_edges.yaml` 并保留备份。诊断中心会提示缺少中文原因、引用不存在节点、缺少规划策略字段或对象画像关系过度自动扩展的问题。

关系扩展策略字段含义：

- `planning_role`：关系在事实规划中的角色，例如 `risk_context`、`benchmark_context`、`peer_context`、`profile_context`、`implementation_evidence`。
- `auto_expand_mode`：`contextual` 表示满足触发策略才自动扩展；`explicit_only` 表示只有用户显式查询属性或关系才触发；`dependency_only` 只作为内部依赖；`debug_only` 只作为调试证据；`disabled` 不参与规划。
- `answer_visibility`：`answer_fact` 会进入回答事实；`supporting_context` 作为支撑上下文进入任务图；`hidden_dependency` 不进入标准任务图；`debug_only` 只进入调试证据。
- `expansion_priority`：扩展事实的优先级，支持 `required`、`optional`、`supporting`、`debug`。
- `trigger_policy`：用 JSON/YAML 对象约束任务、意图、源属性、源事实类型、已有事实类型，以及是否需要显式属性或关系查询。
- `expansion_limits`：限制每个源属性、全局数量和扩展深度。

关系分层维护建议：

- 指标语义扩展边用于从一个指标补充另一个指标，例如最大回撤补充波动率、Calmar 或同类回撤排名，通常使用 `contextual + answer_fact`。
- 对象依赖边用于基准和同类上下文，例如 `has_benchmark`、`belongs_to_category`，通常使用 `contextual + supporting_context`。
- 对象画像边用于基金经理、基金公司、费率、分红、持仓、资产配置等背景事实，默认使用 `explicit_only`。普通指标查询不应自动扩展这些关系，否则任务子图会变成背景大图。
- 实现证据边用于查询、表、字段和血缘，只进入 debug evidence，不进入标准任务图。

示例：

- “查询000001近一年最大回撤和夏普”：required facts 是 `max_drawdown`、`sharpe_ratio`；可选补充 `volatility`、`calmar_ratio`、`peer_drawdown_rank`、`peer_sharpe_rank`；默认不展示基金经理、基金公司、费率、分红、持仓和资产配置。
- “000001近一年有没有跑赢基准”：required facts 是 `return_rate`、`benchmark_return`、`excess_return`；`has_benchmark` 可作为 `supporting_context`。
- “000001近一年同类排名怎么样”：生成 `rank` 或具体同类排名事实；`belongs_to_category` 可作为 `supporting_context`，不作为 required answer fact。
- “000001的基金经理是谁”：显式触发 `managed_by` relation_instance，任务图展示 `Fund -> FundManager`，由 `get_fund_profile_facts` 覆盖。

## 维护 Skill 覆盖能力

进入“Skill 覆盖”后，左侧展示 Skill 中文名、能提供的事实类型数量、支持属性数量和启用状态。点击 Skill 可以维护：

- 能提供的事实类型。
- 支持的对象类型。
- 支持的指标/属性。
- 支持的对象关系。
- 输入参数。
- 权限要求。

保存前会展示中文变更预览，确认后写回 `skills.yaml` 并保留备份。保存后可以回到“OAG 规划调试”生成事实规划，观察覆盖评分和覆盖理由是否变化。

## 编辑边

显式边来自 `schema_graph_edges.yaml`，可点击边后编辑 `source`、`target`、`relation_type` 和属性。

新增边：

1. 进入编辑模式。
2. 点击顶部“创建边”，或在 Inspector 中选择“创建出边 / 创建入边”。
3. 在表单中选择 `source`、`target`、`relation_type`。
4. 填写可选 properties JSON。
5. 保存后写入 `schema_graph_edges.yaml`。

注意：新增或修改显式边时，`relation_type` 必须已经存在于 `relation_types.yaml`，后端不会自动创建关系类型。

画布连边方式仍保留；选中 source 节点后也可以通过创建边流程快速带入 source。

## Inspector

右侧 Inspector 拆分为四个标签：

- 概览：基本信息和核心表单。
- 关联关系：当前子图中的相关边，支持跳转、删除显式边、新增同类关系。
- 上下游影响：通过 `/api/node-context/{node_id}` 展示上游/下游、被 Intent/Skill 使用情况、相关 Attribute/Query/DataTable、删除影响和主键引用提示。
- 原始数据：高级编辑入口，编辑模式下可修改。

节点快捷操作会根据类型变化。例如 ObjectType 支持新增属性、Skill、Query；Attribute 支持关联 Skill、Query、DataField；Skill 支持启用/禁用和复制模板。

## 图谱展示

默认布局改为 `semantic` 语义分层布局，不引入额外布局库。前端按当前 `view_mode` 对节点类型分列，例如：

- requirement：`IntentProfile -> ObjectType -> Attribute -> SkillCapability -> QueryCapability`
- skill：`ObjectType -> SkillCapability -> Attribute -> QueryCapability -> DataTable`
- table_mapping：`ObjectType / Attribute -> DataField -> DataTable`

工具栏仍可切换 `cose`、`breadthfirst`、`concentric`、`grid`。节点标签使用两行卡片式内容：短名称 + 类型/状态，不显示长 description。

边聚合默认开启，会通过 `/api/graph?aggregate_edges=true` 合并重复的 `source/target/relation_type` 边并显示 bundle 计数。overview/requirement 视图还支持前端虚拟 `AttributeGroup` 和 `SkillGroup` 折叠，组节点不会写入 YAML。

选中节点后可在 Inspector 中查看到 Skill、DataTable、Intent 的当前子图最短路径；路径会高亮，其他元素淡化。

## 校验

点击“校验”会调用现有 `src/oag_ontology_loader/loader.py` 与 `validator.py`，并额外检查引用完整性，包括：

- `schema_graph_edges.yaml` 中 source/target 节点是否存在。
- Skill 输出属性、支持属性和相关 Query 是否存在。
- Intent 默认属性和 Skill 引用是否存在。
- Query 目标对象、输出属性和源表是否存在。
- Attribute 对象类型和源表是否存在。
- `table_schemas.yaml` 是否能形成 DataTable/DataField 节点。
- `period_variants.yaml` 是否包含支持 `xx` 模板展开的 period 列表。

校验结果会显示在右侧 Validation Panel，不再只输出 JSON。每条结果展示 severity、message，并尽量从 message 中推断可定位节点。

## 诊断中心

`GET /api/diagnostics` 返回面向 OAG 事实规划的检查项：

- 意图模板问题。
- Skill 能力声明问题。
- 关系边问题。
- 属性覆盖问题。
- 必须事实覆盖问题。
- 旧图谱编辑器兼容检查项。

诊断中心展示错误数量、警告数量、提示数量和检查项总数。每条诊断展示问题类型、严重程度、涉及对象、中文问题说明、中文修复建议，并提供定位和编辑入口。点击定位会跳转到对应意图、Skill、关系边或节点。

## 前端中文展示字段规范

- 用户可见标题、按钮、表头、图例、提示、错误信息和诊断建议都使用中文业务说明。
- 后端英文技术字段只在“原始数据”或“高级调试”折叠区出现。
- 事实类型展示为“指标值事实、对象关系事实、同类排名事实”等中文含义。
- 优先级展示为“必须查询 / 辅助参考”。
- 任务子图节点和边优先使用 `label_zh` 和中文原因。

## Seed

点击“执行 seed”时，前端会二次确认。后端会先执行 validate：

- validate 有 error 时禁止 seed。
- validate 通过后，通过 subprocess 执行 `scripts/seed_ontology.py`。
- stdout、stderr、return_code 会返回页面展示。
- seed 使用当前进程环境变量中的 `OAG_TDSQL_HOST`、`OAG_TDSQL_PORT`、`OAG_TDSQL_USER`、`OAG_TDSQL_PASSWORD`、`OAG_TDSQL_DATABASE`、`OAG_DOMAIN`。

服务启动、刷新图谱、保存 YAML 都不会自动执行 seed。

## 备份机制

每次写入前，后端都会把原文件备份到：

```text
ontology/.backups/
```

备份文件名包含原文件名和时间戳。写入使用同目录临时文件和原子替换，避免写一半导致 YAML 损坏。

## 导出

点击“导出 YAML”会下载一个 zip，包含当前白名单内的 ontology YAML 文件。

## 快捷键

- `Ctrl+S`：保存当前修改。
- `Esc`：关闭弹窗或清除选择。
- `F`：聚焦当前节点 1 跳。
- `Shift+F`：聚焦当前节点 2 跳。
- `/`：聚焦搜索框。
- `Delete`：删除当前选中节点或边，必须确认。
- `Ctrl+Z`：提示暂不支持撤销，请使用备份或放弃修改。

## 常见问题

- 页面打不开：确认已安装 `fastapi`、`uvicorn`、`PyYAML`、`pydantic`，并使用 `127.0.0.1:8010` 访问。
- 图谱为空：先打开 `/api/graph` 查看是否有 YAML 解析错误。
- 保存失败：右侧“原始数据”必须是合法 JSON，列表和对象字段也必须用 JSON 语法。
- inferred edge 不能直接删除：它来自其他 YAML 字段，请修改对应 YAML 来源；只有 explicit edge 会写在 `schema_graph_edges.yaml`。
- 新增边失败：确认 source/target 节点存在，且 relation_type 已在 `relation_types.yaml` 定义。
