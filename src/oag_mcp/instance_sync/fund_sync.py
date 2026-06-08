from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oag_mcp.instance_sync.base import InstanceSyncSource, InstanceSyncWarning


@dataclass
class FundInstanceSync:
    """基金领域实例同步编排器。

    rules 来自 ontology/instance_rules.yaml，source 抽象真实实例数据来源。当前版本
    先提供计划输出和配置检查，等接入真实读取器后再在 run 中生成节点/边。
    """

    rules: list[dict[str, Any]]
    source: InstanceSyncSource

    def plan(self) -> list[str]:
        """根据同步规则生成可读执行计划，不访问真实数据源。"""

        messages: list[str] = []
        for rule in self.rules:
            if not rule.get("enabled", True):
                # 禁用规则仍在计划里展示，便于维护者确认哪些能力暂不参与同步。
                reason = rule.get("disabled_reason") or "规则已禁用"
                messages.append(f"跳过 {rule['rule_id']}: {reason}")
                continue
            target = rule.get("object_type") or (
                f"{rule.get('from_object_type')} -> {rule.get('to_object_type')}"
            )
            messages.append(
                f"待同步 {rule['rule_id']}: {target}, 来源表 {', '.join(rule.get('source_tables') or [])}"
            )
        return messages

    def run(self) -> list[str]:
        """执行实例同步。

        当前只做数据源配置校验；当真实 MRS Hudi 读取器接入后，本方法应按规则读取
        源表并产出/写入图节点和边。
        """

        if not self.source.configured():
            raise InstanceSyncWarning(f"实例同步未配置数据源连接：{self.source.describe()}")
        # TODO: 接入真实 MRS Hudi 读取器后，在这里根据 instance_rules 生成节点和边。
        return self.plan()
