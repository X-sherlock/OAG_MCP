from __future__ import annotations

import pytest

from oag_mcp.config import load_config
from oag_mcp.errors import OAGConfigError
from oag_mcp.repositories import (
    MySQLGraphRepository,
    MySQLMetadataRepository,
    MySQLTextRepository,
)
from oag_mcp.service import create_context_service


MYSQL_ENV = {
    "OAG_TDSQL_HOST": "127.0.0.1",
    "OAG_TDSQL_PORT": "3306",
    "OAG_TDSQL_USER": "oag",
    "OAG_TDSQL_PASSWORD": "oag_password",
    "OAG_TDSQL_DATABASE": "oag_meta",
}


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """清空相关环境变量，保证配置测试不受本机真实环境影响。"""

    for name in [*MYSQL_ENV, "OAG_DOMAIN"]:
        monkeypatch.delenv(name, raising=False)


def _set_mysql_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """写入一组最小可用的 MySQL/TDSQL 环境变量。"""

    for name, value in MYSQL_ENV.items():
        monkeypatch.setenv(name, value)


def test_config_loads_mysql_only_settings(monkeypatch: pytest.MonkeyPatch):
    # 验证 load_config 只依赖 MySQL/TDSQL 环境变量，并正确转换端口类型。
    _clear_env(monkeypatch)
    _set_mysql_env(monkeypatch)

    config = load_config()

    assert config.tdsql.host == "127.0.0.1"
    assert config.tdsql.port == 3306
    assert config.tdsql.user == "oag"
    assert config.tdsql.password == "oag_password"
    assert config.tdsql.database == "oag_meta"
    assert config.domain == "finance_market"


def test_config_accepts_domain_override(monkeypatch: pytest.MonkeyPatch):
    # domain 可被环境变量覆盖；当前测试仍使用唯一支持的 finance_market。
    _clear_env(monkeypatch)
    _set_mysql_env(monkeypatch)
    monkeypatch.setenv("OAG_DOMAIN", "finance_market")

    assert load_config().domain == "finance_market"


def test_config_requires_mysql_environment(monkeypatch: pytest.MonkeyPatch):
    # 缺少必填配置应尽早失败，而不是创建半初始化的服务对象。
    _clear_env(monkeypatch)

    with pytest.raises(OAGConfigError, match="OAG_TDSQL_HOST"):
        load_config()


def test_factory_selects_mysql_repositories(monkeypatch: pytest.MonkeyPatch):
    # 默认服务工厂应选择 MySQL-backed 三类仓储，确保运行时没有隐式 fallback。
    _clear_env(monkeypatch)
    _set_mysql_env(monkeypatch)
    monkeypatch.setattr(MySQLMetadataRepository, "get_intent_profiles", lambda self, domain: [])
    monkeypatch.setattr(MySQLMetadataRepository, "get_skill_capabilities", lambda self, domain: [])

    service = create_context_service()

    assert isinstance(service.ontology_repository, MySQLMetadataRepository)
    assert isinstance(service.text_repository, MySQLTextRepository)
    assert isinstance(service.graph_repository, MySQLGraphRepository)
