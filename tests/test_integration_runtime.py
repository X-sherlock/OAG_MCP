from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from oag_mcp.config import load_config
from oag_mcp.repositories import (
    MySQLGraphRepository,
    MySQLMetadataRepository,
    MySQLTextRepository,
)
from oag_mcp.service import create_context_service


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    os.getenv("OAG_RUN_MYSQL_INTEGRATION") != "1",
    reason="Set OAG_RUN_MYSQL_INTEGRATION=1 when real MySQL is available.",
)
def test_mysql_only_backend_seed_and_retrieve_context():
    """真实 MySQL 集成测试。

    默认跳过，只有显式设置 OAG_RUN_MYSQL_INTEGRATION=1 且环境变量指向可用数据库时
    才运行。测试覆盖 seed 脚本、三类 MySQL 仓储和服务层端到端召回。
    """

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "seed_ontology.py")],
        check=True,
        cwd=PROJECT_ROOT,
    )

    config = load_config()
    ontology = MySQLMetadataRepository(config.tdsql)
    text = MySQLTextRepository(config.tdsql)
    graph = MySQLGraphRepository(config.tdsql)

    ontology.ping()
    text.ping()
    graph.ping()

    assert ontology.domain_enabled("finance_market")
    objects = ontology.get_objects_by_ids("finance_market", ["003095"])
    assert objects == []

    attributes = ontology.get_attributes_by_names(
        "finance_market", ["return_rate", "max_drawdown", "volatility"]
    )
    assert {item["attribute_name"] for item in attributes} == {
        "return_rate",
        "max_drawdown",
        "volatility",
    }

    queries = ontology.get_query_capabilities("finance_market")
    assert "fund_perf_interval_query" in {item["query_id"] for item in queries}
    skills = ontology.get_skill_capabilities("finance_market")
    assert "fund_performance_analysis" in {item["skill_id"] for item in skills}

    assert text.search_objects("finance_market", "基金", top_k=5)
    matched_attributes = text.search_attributes("finance_market", "最大回撤", top_k=20)
    assert "max_drawdown" in {item["attribute_name"] for item in matched_attributes}

    entity = [{"object_type": "ObjectType", "object_id": "Fund"}]
    assert graph.recall_relations("finance_market", entity, max_hops=2, top_k=10)
    assert graph.recall_paths("finance_market", entity, max_hops=2, top_k=10)

    result = create_context_service().retrieve_context(
        question="分析003095近一年收益率和最大回撤表现",
        user_context={"permission_scopes": ["fund_public_data:read"]},
    )

    assert result["status"] == "success"
    assert result["matched_objects"]
    assert result["matched_objects"][0]["node_id"] == "ObjectType:Fund"
    assert result["matched_attributes"]
    assert result["resolved_params"]["fund_code"] == "003095"
    assert result["resolved_params"]["period"] == "1y"
    assert result["relation_subgraph"]["nodes"]
    assert result["relation_subgraph"]["edges"]
    assert "Fund:003095" not in {node["node_id"] for node in result["relation_subgraph"]["nodes"]}
