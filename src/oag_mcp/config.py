from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from oag_mcp.errors import OAGConfigError
from oag_mcp.llm_config import _read_dotenv


@dataclass(frozen=True)
class TDSQLConfig:
    """TDSQL/MySQL 连接参数。

    该 MCP Server 当前只依赖 MySQL 协议访问元数据、别名索引和关系图数据；
    frozen=True 可以防止服务启动后配置被意外修改。
    """

    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class OAGConfig:
    """服务级配置对象。

    domain 目前默认固定在金融市场领域，但仍保留环境变量覆盖能力，便于后续
    扩展多领域本体时复用同一套加载逻辑。
    """

    tdsql: TDSQLConfig
    domain: str = "finance_market"


def load_config() -> OAGConfig:
    """从环境变量加载 MySQL-only MCP 配置。

    必填项缺失会立即抛出 OAGConfigError，使服务在真实请求前失败；这样可以
    避免运行到仓储访问阶段才暴露不完整配置。
    """

    dotenv_values = _read_dotenv(Path(__file__).resolve().parents[2])
    return OAGConfig(
        tdsql=TDSQLConfig(
            host=_required("OAG_TDSQL_HOST", dotenv_values),
            port=_required_int("OAG_TDSQL_PORT", dotenv_values),
            user=_required("OAG_TDSQL_USER", dotenv_values),
            password=_required("OAG_TDSQL_PASSWORD", dotenv_values),
            database=_required("OAG_TDSQL_DATABASE", dotenv_values),
        ),
        domain=_config_value("OAG_DOMAIN", dotenv_values, "finance_market"),
    )


def _config_value(name: str, dotenv_values: dict[str, str], default: str) -> str:
    value = os.getenv(name)
    if value is None:
        value = dotenv_values.get(name, default)
    return str(value or "").strip()


def _required(name: str, dotenv_values: dict[str, str]) -> str:
    """读取必填环境变量，并把空字符串视为未配置。"""

    value = _config_value(name, dotenv_values, "")
    if not value:
        raise OAGConfigError(f"Missing required environment variable: {name}")
    return value


def _required_int(name: str, dotenv_values: dict[str, str]) -> int:
    """读取必须为整数的环境变量，主要用于端口号等数值配置。"""

    value = _required(name, dotenv_values)
    try:
        return int(value)
    except ValueError as exc:
        raise OAGConfigError(f"Environment variable {name} must be an integer") from exc
