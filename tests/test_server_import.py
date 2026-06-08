from __future__ import annotations

import importlib.util
import sys


def test_server_exposes_oag_retrieve_context():
    # 先确认 mcp 依赖存在，再导入 server；否则 ImportError 会掩盖工具注册问题。
    assert importlib.util.find_spec("mcp") is not None

    from oag_mcp.server import oag_retrieve_context

    # MCP 工具函数必须是可调用对象，FastMCP 装饰器不应破坏直接测试调用能力。
    assert callable(oag_retrieve_context)


def test_server_import_does_not_import_ontology_loader():
    sys.modules.pop("oag_mcp.server", None)
    sys.modules.pop("oag_mcp.service", None)
    for name in list(sys.modules):
        if name.startswith("oag_ontology_loader"):
            sys.modules.pop(name, None)

    __import__("oag_mcp.server")

    assert "oag_ontology_loader" not in sys.modules


def test_runtime_graph_repository_has_no_seed_method():
    from oag_mcp.repositories import MySQLGraphRepository

    assert not hasattr(MySQLGraphRepository, "seed_graph")
