from __future__ import annotations

import sys
from pathlib import Path

# 脚本直接从源码树运行时，主动把 src 放到 import path，避免要求用户先安装包。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from oag_mcp.instance_sync.base import InstanceSyncWarning, UnconfiguredInstanceSyncSource
from oag_mcp.instance_sync.fund_sync import FundInstanceSync
from oag_ontology_loader.loader import load_ontology


def main() -> None:
    """打印实例同步计划，并在真实数据源未配置时以退出码 2 结束。

    这让发布包中的同步脚本可以先用于规则验收；后续接入 MRS Hudi 后，只需替换
    source 实现即可复用同一套命令入口。
    """

    catalog = load_ontology(PROJECT_ROOT / "ontology")
    sync = FundInstanceSync(
        rules=catalog.instance_rules,
        source=UnconfiguredInstanceSyncSource(source_type="MRS Hudi"),
    )
    for message in sync.plan():
        print(message)
    try:
        sync.run()
    except InstanceSyncWarning as exc:
        # 使用 SystemExit(2) 区分“配置未完成”和普通 Python 异常。
        print(str(exc))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
