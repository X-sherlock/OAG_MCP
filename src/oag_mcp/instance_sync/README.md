# Instance Sync

`instance_sync` 是未来从 MRS Hudi 结构化数据生成 OAG 实例节点和关系，并写入 MySQL 的扩展点。

当前实现只读取 `ontology/instance_rules.yaml` 并输出同步计划。未配置真实数据源连接时会明确失败，不会伪造基金、指标、持仓或关系数据。

非结构化研报、新闻、政策文件规则保持 `enabled: false`，由后续文档解析管道补充。
