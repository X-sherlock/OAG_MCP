from __future__ import annotations

from typing import Any

from oag_mcp.config import OAGConfigError
from oag_mcp.errors import OAGRepositoryError
from oag_mcp.service import create_context_service, error_response

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("The MCP server requires the 'mcp' package. Install project dependencies.") from exc


# FastMCP 实例名会出现在客户端可见的 MCP Server 元信息中。
mcp = FastMCP("OAG MCP Server")


@mcp.tool()
def oag_retrieve_context(
    question: str,
    intent: str = "structured_query",
    domain: str = "finance_market",
    user_context: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """返回 OAG 上下文，不查询业务数据、不生成 SQL、不执行写操作。

    该工具只做“面向后续查询/技能调用的上下文准备”：识别对象、属性、关系路径、
    候选查询、候选调用参数和缺失参数提示。真正的数据查询应由调用端基于返回的
    candidate_invocations 再决定是否执行。
    """

    try:
        # 每次请求创建服务实例，可以让环境配置和仓储连接保持简单、无共享状态。
        return create_context_service().retrieve_context(
            question=question,
            intent=intent,
            domain=domain,
            user_context=user_context,
            options=options,
        )
    except (OAGConfigError, OAGRepositoryError, ValueError) as exc:
        # MCP 工具入口统一返回结构化错误，避免异常直接泄漏给客户端。
        return error_response(domain=domain, question=question, intent=intent, message=str(exc))


def main() -> None:
    """以 stdio transport 启动 MCP Server，供桌面端或代理进程拉起。"""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
