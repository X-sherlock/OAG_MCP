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

1. 点击图中的节点。
2. 在右侧 Inspector 修改核心字段，或直接编辑 Raw JSON。
3. 点击“保存当前修改”或 Inspector 内的“保存”。
4. 后端会根据节点类型写入对应 YAML，例如：
   - `SkillCapability` 写入 `skills.yaml`
   - `ObjectType` 写入 `object_types.yaml`
   - `Attribute` 写入 `attributes.yaml`
   - `QueryCapability` 写入 `queries.yaml`
   - `IntentProfile` 写入 `intent_profiles.yaml`
   - `DataTable` / `DataField` 写入 `table_schemas.yaml`

Skill 节点支持编辑 `skill_name`、`description`、`enabled`、`target_object_type`、`input_params`、`output_attributes`、`provides_fact_types`、`supported_subject_types`、`supported_attributes`、`permission_scope` 等字段。

## 编辑边

显式边来自 `schema_graph_edges.yaml`，可点击边后编辑 `source`、`target`、`relation_type` 和属性。

新增边：

1. 选中 source 节点。
2. 点击“创建边”。
3. 点击 target 节点。
4. 填写 `relation_type` 和属性 JSON。
5. 保存后写入 `schema_graph_edges.yaml`。

注意：新增或修改显式边时，`relation_type` 必须已经存在于 `relation_types.yaml`，后端不会自动创建关系类型。

## 校验

点击“校验”会调用现有 `src/oag_ontology_loader/loader.py` 与 `validator.py`，并额外检查引用完整性，包括：

- `schema_graph_edges.yaml` 中 source/target 节点是否存在。
- Skill 输出属性、支持属性和相关 Query 是否存在。
- Intent 默认属性和 Skill 引用是否存在。
- Query 目标对象、输出属性和源表是否存在。
- Attribute 对象类型和源表是否存在。
- `table_schemas.yaml` 是否能形成 DataTable/DataField 节点。
- `period_variants.yaml` 是否包含支持 `xx` 模板展开的 period 列表。

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

## 常见问题

- 页面打不开：确认已安装 `fastapi`、`uvicorn`、`PyYAML`、`pydantic`，并使用 `127.0.0.1:8010` 访问。
- 图谱为空：先打开 `/api/graph` 查看是否有 YAML 解析错误。
- 保存失败：右侧 Raw JSON 必须是合法 JSON，列表和对象字段也必须用 JSON 语法。
- inferred edge 不能直接删除：它来自其他 YAML 字段，请修改对应 YAML 来源；只有 explicit edge 会写在 `schema_graph_edges.yaml`。
- 新增边失败：确认 source/target 节点存在，且 relation_type 已在 `relation_types.yaml` 定义。
