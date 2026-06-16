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
    raw_question: str | None = None,
    semantic_frame: dict[str, Any] | None = None,
    recognized_intents: list[dict[str, Any]] | None = None,
    selector_mode: str = "rule",
    planning_options: dict[str, Any] | None = None,
    user_context: dict[str, Any] | None = None,
    output_view: str = "editor",
) -> dict[str, Any]:
    """Return the OAG V2 planning chain for a semantic_frame.

    semantic_frame 必须由前置意图识别节点提供；question/raw_question 仅作为
    追踪字段保留。LLM selector 只能选择 candidate_fact_pool 内的 fact_id，
    Skill 绑定始终由系统确定性完成。
    """

    try:
        # 每次请求创建服务实例，可以让环境配置和仓储连接保持简单、无共享状态。
        return create_context_service().retrieve_context(
            semantic_frame=semantic_frame,
            raw_question=raw_question,
            recognized_intents=recognized_intents,
            selector_mode=selector_mode,
            planning_options=planning_options,
            user_context=user_context,
            output_view=output_view,
        )
    except (OAGConfigError, OAGRepositoryError, ValueError) as exc:
        # MCP 工具入口统一返回结构化错误，避免异常直接泄漏给客户端。
        domain = (semantic_frame or {}).get("domain") or "finance_market"
        raw_question = (semantic_frame or {}).get("raw_question") or ""
        return error_response(domain=domain, question=raw_question, intent="", message=str(exc))


def main() -> None:
    """以 stdio transport 启动 MCP Server，供桌面端或代理进程拉起。"""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
