from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class InstanceSyncWarning(RuntimeError):
    """实例同步无法执行时抛出的运行时提示。

    当前项目已定义同步规则，但真实 MRS Hudi 等数据源尚未接入；抛出 warning 类型
    可以让脚本以非零退出码提示用户，同时不把它误判为代码缺陷。
    """


class InstanceSyncSource(Protocol):
    """实例同步数据源协议。

    真正的数据源实现需要告诉同步器自己是否已配置，并提供一段可读描述用于错误
    提示；这样 FundInstanceSync 不必关心 Hudi、数据库或文件源的具体连接方式。
    """

    def configured(self) -> bool: ...

    def describe(self) -> str: ...


@dataclass(frozen=True)
class UnconfiguredInstanceSyncSource:
    """占位数据源实现，用于在未接入真实来源时生成明确提示。"""

    source_type: str = "hudi"

    def configured(self) -> bool:
        """占位源永远不可用，防止误以为实例同步已经真实执行。"""

        return False

    def describe(self) -> str:
        """返回面向 CLI 用户的未配置说明。"""

        return f"未配置 {self.source_type} 数据源连接"
