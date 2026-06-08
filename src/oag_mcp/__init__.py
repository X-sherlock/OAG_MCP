"""OAG MCP Server 的 Python 包入口。

该模块只暴露包版本号，真实的 MCP 工具注册、上下文召回服务和存储适配器
分别放在 server.py、service.py 与 repositories.py 中，方便脚本和测试按需导入。
"""

# 明确 __all__ 可以避免通配符导入时把内部实现细节暴露给调用方。
__all__ = ["__version__"]

__version__ = "0.1.0"
