# OAG Ontology Editor

轻量级 OAG 本体建模编辑辅助页面，用于查看和维护 `ontology/*.yaml` 中的对象、属性、关系、查询能力、Skill、Intent、数据源、表和字段配置。

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

- 以 Cytoscape.js 图谱展示当前 OAG ontology。
- 展示 `ObjectType`、`Attribute`、`RelationType`、`QueryCapability`、`SkillCapability`、`IntentProfile`、`DataSource`、`DataTable`、`DataField`、`PeriodVariant`、`InstanceRule` 节点。
- 展示 `schema_graph_edges.yaml` 显式边，以及从 Skill、Intent、Query、Attribute、Table schema 等 YAML 推导出的 inferred edges。
- 辅助编辑 YAML 配置并写回本地文件。

页面现在默认进入“本体建模工作台”轻量首页，不会一打开就加载大图。先选择建模任务，再从候选节点进入聚焦子图。

## 工作台任务入口

左侧“建模任务”提供常用建模流：

- 重构 Skill：进入 `skill` 视图，推荐选择 `SkillCapability`。
- 设计对象属性：进入 `object_attribute` 视图，推荐选择 `ObjectType`。
- 设计 Intent 编排：进入 `requirement` 视图，推荐选择 `IntentProfile`。
- 检查表字段映射：进入 `table_mapping` 视图，推荐选择 `Attribute` 或 `DataTable`，并展开 inferred/DataField。
- 全局检查：查看 Diagnostic 面板，不需要先加载全图。

点击任务卡片后，左侧只显示该任务的候选节点；选择具体节点后，中间画布才加载 focus 子图。

## 浏览模式和编辑模式

默认是浏览模式：

- 可以搜索、聚焦、跳转、查看 Inspector。
- 右侧核心表单和 Raw JSON 只读。
- 保存、删除、新增节点、创建边等写操作不可用。

点击“进入编辑模式”后才允许写入 YAML。进入时页面会提示：编辑会修改 `ontology/*.yaml`，保存前会自动备份。退出编辑模式、切换任务、刷新图谱或切换选中对象时，如果当前对象有未保存修改，会提示保存、放弃或取消。

## 未保存修改和 Diff 预览

编辑核心表单或 Raw JSON 后，顶部会显示：

- `未保存修改：1`
- 当前编辑对象 id

左侧 YAML 文件列表会在对应文件名后显示 `*`。点击保存时，页面先比较原始 Raw JSON 和当前 Raw JSON，弹出简洁变更预览：

- changed fields
- added fields
- removed fields

确认后才调用 `/api/graph/node` 或 `/api/graph/edge` 写回 YAML。保存失败时 dirty 状态会保留。

## 会修改的 YAML 文件

仅允许读写以下白名单文件：

- `ontology/attributes.yaml`
- `ontology/data_sources.yaml`
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
3. 在右侧 Inspector 修改核心字段，或在 Raw JSON 标签页直接编辑。
4. 点击“保存当前修改”或 Inspector 内的“保存”。
5. 在 Diff 预览中确认保存。
4. 后端会根据节点类型写入对应 YAML，例如：
   - `SkillCapability` 写入 `skills.yaml`
   - `ObjectType` 写入 `object_types.yaml`
   - `Attribute` 写入 `attributes.yaml`
   - `QueryCapability` 写入 `queries.yaml`
   - `IntentProfile` 写入 `intent_profiles.yaml`
   - `DataTable` / `DataField` 写入 `table_schemas.yaml`

Skill 节点支持编辑 `skill_name`、`description`、`enabled`、`target_object_type`、`input_params`、`output_attributes`、`provides_fact_types`、`supported_subject_types`、`supported_attributes`、`permission_scope` 等字段。

新增节点默认使用向导，不再要求手写完整 Raw JSON。当前支持 `SkillCapability`、`Attribute`、`IntentProfile`、`QueryCapability`、`RelationType`、`ObjectType`、`DataTable`、`DataField` 等类型。向导下拉和多选数据来自 `/api/options`。

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
- Raw JSON：高级编辑入口，编辑模式下可修改。

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

## Diagnostic 检查

`GET /api/diagnostics` 返回面向建模工作台的检查项：

- `orphan_nodes`
- `skills_without_attributes`
- `attributes_without_skill`
- `attributes_without_table_mapping`
- `intents_without_skill`
- `relation_types_unused`
- `disabled_skills_referenced`

左侧 Diagnostic 面板可按类型过滤，点击检查项可聚焦对应节点。

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
- 保存失败：右侧 Raw JSON 必须是合法 JSON，列表和对象字段也必须用 JSON 语法。
- inferred edge 不能直接删除：它来自其他 YAML 字段，请修改对应 YAML 来源；只有 explicit edge 会写在 `schema_graph_edges.yaml`。
- 新增边失败：确认 source/target 节点存在，且 relation_type 已在 `relation_types.yaml` 定义。
