from __future__ import annotations


class OAGError(Exception):
    """OAG MCP 内部异常的统一基类。

    上层入口可以捕获这个基类来兜底处理所有 OAG 相关失败，同时又能通过子类
    区分配置问题、仓储访问问题等不同错误来源。
    """


class OAGConfigError(OAGError):
    """运行时配置缺失或格式非法时抛出。

    典型场景包括 TDSQL/MySQL 连接环境变量未设置、端口不是整数等；这类错误
    通常需要部署侧修正配置，而不是重试业务请求。
    """


class OAGRepositoryError(OAGError):
    """底层仓储无法提供数据时抛出。

    该异常用于屏蔽 MySQL 驱动、SQL 执行和连接可用性等实现细节，让服务层
    可以统一返回 MCP 友好的结构化错误响应。
    """
