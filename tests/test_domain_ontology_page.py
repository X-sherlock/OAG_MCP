from __future__ import annotations

import json
import threading
import urllib.error
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ontology_editor import app as app_module
from ontology_editor import domain_store
from ontology_editor.app import app
from ontology_editor.ddl_compactor import analyze_ddl_documents
from ontology_editor.llm_client import (
    BailianLLMClient,
    BailianLLMConfig,
    LLMClientError,
    LLMJSONRepairRequired,
    LLMRequestCancelled,
    LightAppLLMClient,
    LightAppLLMConfig,
    cancel_llm_request,
    llm_config_status,
    load_llm_config,
    parse_json_content,
)


client = TestClient(app)


def sample_plan() -> dict:
    return {
        "summary_zh": "客服工单领域包含客户、工单和处理人，核心关系是客户提交工单、处理人处理工单。",
        "objects": [
            {"object_type": "Customer", "object_type_zh": "客户", "description": "提交工单的客户。"},
            {"object_type": "Ticket", "object_type_zh": "工单", "description": "客户服务请求。"},
        ],
        "attributes": [
            {"attribute_name": "ticket_status", "attribute_name_zh": "工单状态", "object_types": ["Ticket"], "value_type": "string", "description": "工单处理状态。"}
        ],
        "relationships": [
            {
                "source": "ObjectType:Customer",
                "target": "ObjectType:Ticket",
                "relation_type": "submits",
                "relation_name_zh": "提交",
                "reason_zh": "客户会提交工单。",
            }
        ],
        "open_questions": [],
        "revision_notes": [],
    }


def sample_sections() -> dict:
    return {
        "domain": {"domain_name": "客服工单", "description": "客服工单处理领域。"},
        "object_types": [
            {"object_type": "Customer", "object_type_zh": "客户", "description": "提交工单的客户。", "enabled": True},
            {"object_type": "Ticket", "object_type_zh": "工单", "description": "客户服务请求。", "enabled": True},
        ],
        "attributes": [
            {
                "attribute_name": "ticket_status",
                "attribute_name_zh": "工单状态",
                "description": "工单处理状态。",
                "value_type": "string",
                "object_types": ["Ticket"],
                "enabled": True,
            }
        ],
        "relation_types": [
            {"relation_type": "submits", "relation_name_zh": "提交", "description": "客户提交工单。", "enabled": True}
        ],
        "schema_graph_edges": [
            {
                "from": "ObjectType:Customer",
                "to": "ObjectType:Ticket",
                "relation_type": "submits",
                "reason_zh": "客户会提交工单。",
                "score": 0.9,
            }
        ],
    }


def test_llm_config_status_does_not_return_api_key(tmp_path):
    config = tmp_path / "llm_config.local.yaml"
    config.write_text(
        "\n".join(
            [
                'api_key: "sk-secret"',
                'base_url: "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"',
                'model: "qwen3.5-plus-2026-04-20"',
            ]
        ),
        encoding="utf-8",
    )

    status = llm_config_status(config)

    assert status["configured"] is True
    assert status["has_api_key"] is True
    assert "api_key" not in status
    assert "sk-secret" not in json.dumps(status)
    assert load_llm_config(config).api_key == "sk-secret"


def test_llm_client_parses_json_chat_response(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "```json\n{\"ok\": true}\n```"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client_obj = BailianLLMClient(BailianLLMConfig(api_key="sk-test", base_url="https://example.test/compatible-mode/v1"))
    result = client_obj.json_chat([{"role": "user", "content": "return json"}], purpose="test")

    assert result == {"ok": True}
    assert captured["url"].endswith("/chat/completions")
    assert captured["auth"] == "Bearer sk-test"
    assert captured["timeout"] == 180


def test_llm_json_parser_repairs_common_missing_commas():
    parsed = parse_json_content(
        """
        {
          "relationships": [
            {"source": "A", "target": "B"}
            {"source": "B", "target": "C"}
          ],
          "summary_zh": "ok"
        }
        """
    )

    assert len(parsed["relationships"]) == 2
    assert parsed["relationships"][1]["target"] == "C"


def test_llm_client_exposes_invalid_json_for_explicit_repair(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": self.payload}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode("utf-8")))
        if len(calls) == 1:
            return FakeResponse('{"ok": true "broken": true}')
        return FakeResponse('{"ok": true, "broken": false}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client_obj = BailianLLMClient(BailianLLMConfig(api_key="sk-test", base_url="https://example.test"))
    messages = [{"role": "user", "content": "return json"}]
    with pytest.raises(LLMJSONRepairRequired) as exc_info:
        client_obj.json_chat(messages, purpose="test")
    assert exc_info.value.repair_payload()["invalid_content"]

    result = client_obj.repair_json_chat(messages, exc_info.value.content, "test", exc_info.value.parse_error)
    assert result == {"ok": True, "broken": False}
    assert len(calls) == 2
    assert "修复后的合法 JSON" in calls[1]["messages"][-1]["content"]


def test_llm_client_reports_http_error(monkeypatch):
    def fake_urlopen(_request, timeout=None):
        raise urllib.error.HTTPError("https://example.test", 401, "Unauthorized", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client_obj = BailianLLMClient(BailianLLMConfig(api_key="sk-test", base_url="https://example.test"))

    with pytest.raises(LLMClientError):
        client_obj.json_chat([{"role": "user", "content": "x"}], purpose="test")


def test_bailian_client_streams_json_response(monkeypatch):
    captured = {}

    class StreamResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            return iter(
                [
                    b'data: {"choices":[{"delta":{"content":"{\\"ok\\":"},"finish_reason":null}]}\n',
                    b'data: {"choices":[{"delta":{"content":"true}"},"finish_reason":"stop"}]}\n',
                    b'data: [DONE]\n',
                ]
            )

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["accept"] = request.get_header("Accept")
        captured["timeout"] = timeout
        return StreamResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client_obj = BailianLLMClient(BailianLLMConfig(api_key="sk-test", base_url="https://example.test"))

    result = client_obj.json_chat([{"role": "user", "content": "return json"}], purpose="test")

    assert result == {"ok": True}
    assert captured["payload"]["stream"] is True
    assert captured["payload"]["enable_thinking"] is False
    assert captured["payload"]["stream_options"] == {"include_usage": True}
    assert captured["accept"] == "text/event-stream, application/json"
    assert captured["timeout"] == 180


def test_light_app_client_calls_use_as_tool_once_with_runtime_payload(monkeypatch):
    captured = {"urls": [], "json": {}}

    class StreamResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            content = json.dumps({"ok": True})
            return iter(
                [
                    b"event: chat_started\n",
                    b'data: {"content":"conversation-1"}\n',
                    b"event: chunk\n",
                    b'data: {"content":"partial"}\n',
                    b"event: message\n",
                    b'data: {"additional_kwargs":{"node_id":"worker","node_output":{"output":"intermediate"}}}\n',
                    b"event: message\n",
                    f'data: {json.dumps({"additional_kwargs": {"node_id": "end", "node_output": {"output": content}}})}\n'.encode("utf-8"),
                    b"event: done\n",
                    b"data: {}\n",
                ]
            )

    def fake_urlopen(request, timeout):
        captured["urls"].append(request.full_url)
        assert request.get_header("Authorization") == "Bearer secret-token"
        assert request.get_header("X-request-id") == "domain-request-1234"
        assert timeout == 180
        captured["json"]["use_as_tool"] = json.loads(request.data.decode("utf-8"))
        return StreamResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client_obj = LightAppLLMClient(
        LightAppLLMConfig(
            endpoint_url="https://factory.example.test/chatabc/use_as_tool",
            session_id="3e747787-7e1d-4f57-bc1e-8c870d89447f",
            api_key="secret-token",
        )
    )
    runtime = {"task": "plan", "domain_input": {"ddl_compact": "# oag-ddl-v1\nT|ticket\nC|id:integer\nP|id"}}
    result = client_obj.json_chat(
        [{"role": "user", "content": json.dumps(runtime)}],
        purpose="domain ontology plan",
        request_id="domain-request-1234",
    )

    assert result == {"ok": True}
    assert captured["urls"] == ["https://factory.example.test/chatabc/use_as_tool"]
    payload = captured["json"]["use_as_tool"]
    assert payload == {
        "session_id": "3e747787-7e1d-4f57-bc1e-8c870d89447f",
        "txt": json.dumps(runtime),
        "stream": True,
        "config_variables": [],
    }
    prompt_value = json.loads(payload["txt"])
    assert prompt_value["domain_input"]["ddl_compact"].startswith("# oag-ddl-v1")
    assert "ddl_documents" not in prompt_value["domain_input"]


def test_light_app_returns_immediately_on_end_node(monkeypatch):
    class EndNodeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            yield b"event: message\n"
            yield b'data: {"additional_kwargs":{"node_id":"end","node_output":{"output":{"ok":true}}}}\n'
            raise AssertionError("stream must not be read after the end node")

    monkeypatch.setattr("urllib.request.urlopen", lambda _request, timeout: EndNodeResponse())
    client_obj = LightAppLLMClient(
        LightAppLLMConfig(
            endpoint_url="https://factory.example.test/chatabc/use_as_tool",
            session_id="3e747787-7e1d-4f57-bc1e-8c870d89447f",
        )
    )

    result = client_obj.json_chat([{"role": "user", "content": "{}"}], purpose="test")

    assert result == {"ok": True}


def test_light_app_cancel_closes_response_and_sends_stop_command(monkeypatch):
    read_started = threading.Event()
    response_closed = threading.Event()
    captured_stop = {}

    class BlockingResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def __iter__(self):
            read_started.set()
            response_closed.wait(2)
            raise OSError("closed")

        def close(self):
            response_closed.set()

    class StopResponse:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout):
        if request.full_url == "https://factory.example.test/stop":
            body = json.loads(request.data.decode("utf-8"))
            captured_stop.update(body)
            return StopResponse()
        return BlockingResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client_obj = LightAppLLMClient(
        LightAppLLMConfig(
            endpoint_url="https://factory.example.test/run",
            session_id="db809799-40b6-443c-8355-f3c38e94bd03",
            cancel_url="https://factory.example.test/stop",
        )
    )
    errors = []

    def invoke():
        try:
            client_obj.json_chat(
                [{"role": "user", "content": "{}"}],
                purpose="domain ontology plan",
                request_id="domain-cancel-1234",
            )
        except Exception as exc:  # noqa: BLE001 - assert the worker's terminal exception below.
            errors.append(exc)

    worker = threading.Thread(target=invoke)
    worker.start()
    assert read_started.wait(1)
    result = cancel_llm_request("domain-cancel-1234")
    worker.join(2)

    assert result["cancelled"] is True
    assert result["response_closed"] is True
    assert result["stop_command_sent"] is True
    assert captured_stop == {
        "session_id": "db809799-40b6-443c-8355-f3c38e94bd03",
        "action": "stop",
    }
    assert errors and isinstance(errors[0], LLMRequestCancelled)


def test_domain_plan_api_uses_mocked_llm(monkeypatch):
    class FakeClient:
        def json_chat(self, _messages, *, purpose):
            assert purpose == "domain ontology plan"
            return deepcopy(sample_plan())

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "客服工单",
                "objects": [{"object_type": "Customer", "object_type_zh": "客户"}],
                "attributes": [],
                "bulk_text": "",
            }
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["plan"]["summary_zh"]
    assert data["plan"]["relationships"][0]["relation_type"] == "submits"


def test_domain_plan_api_uses_light_app_settings_and_ddl_context(monkeypatch):
    captured = {}

    class FakeLightAppClient:
        def __init__(self, config):
            captured["config"] = config

        def json_chat(self, messages, *, purpose, request_id):
            captured["messages"] = messages
            captured["purpose"] = purpose
            captured["request_id"] = request_id
            return deepcopy(sample_plan())

    monkeypatch.setattr(app_module, "LightAppLLMClient", FakeLightAppClient)
    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "客服工单",
                "objects": [],
                "attributes": [],
                "bulk_text": "",
                "ddl_documents": [
                    {
                        "name": "ticket.sql",
                        "content": "CREATE TABLE ticket (id BIGINT PRIMARY KEY, customer_id BIGINT);",
                    }
                ],
            },
            "llm": {
                "provider": "innovation_factory",
                "endpoint_url": "https://factory.example.test/app",
                "session_id": "0f527dd3-ecec-48d4-82d0-71080e15435c",
                "cancel_url": "https://factory.example.test/stop",
                "api_key": "session-secret",
                "request_id": "domain-api-request-1234",
            },
        },
    )

    assert response.status_code == 200
    assert captured["config"].endpoint_url == "https://factory.example.test/app"
    assert captured["config"].session_id == "0f527dd3-ecec-48d4-82d0-71080e15435c"
    assert captured["config"].cancel_url == "https://factory.example.test/stop"
    assert captured["request_id"] == "domain-api-request-1234"
    runtime_payload = json.loads(captured["messages"][-1]["content"])
    assert runtime_payload["domain_input"]["ddl_compact"].startswith("# oag-ddl-v1")
    assert "ticket" in runtime_payload["domain_input"]["ddl_compact"]
    assert "CREATE TABLE" not in runtime_payload["domain_input"]["ddl_compact"]
    assert "ddl_documents" not in runtime_payload["domain_input"]
    assert any("foreign-key" in item for item in runtime_payload["constraints"])


def test_ddl_compactor_extracts_keys_comments_and_compact_text():
    ddl = """
    CREATE TABLE customers (
      id BIGINT PRIMARY KEY,
      name VARCHAR(80) COMMENT '客户名称'
    );
    CREATE TABLE orders (
      id BIGINT PRIMARY KEY,
      customer_id BIGINT NOT NULL,
      amount DECIMAL(18,2),
      CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    analysis = analyze_ddl_documents([{"name": "orders.sql", "content": ddl}])

    assert analysis["summary"]["table_count"] == 2
    assert analysis["summary"]["column_count"] == 5
    assert analysis["summary"]["foreign_key_count"] == 1
    assert analysis["summary"]["compact_bytes"] < analysis["summary"]["raw_bytes"]
    assert "T|customers" in analysis["compact_text"]
    assert "name:string::客户名称" in analysis["compact_text"]
    assert "F|orders(customer_id)>customers(id)" in analysis["compact_text"]
    assert "ENGINE" not in analysis["compact_text"]


def test_ddl_compactor_handles_quoted_names_defaults_and_inline_reference():
    ddl = """
    CREATE TABLE [sales].[customer] (
      [customer_id] BIGINT PRIMARY KEY,
      [display_name] VARCHAR(120) NOT NULL,
      [settings] JSON DEFAULT '{"locale":"zh-CN","alerts":true}',
      [created_at] TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE [sales].[orders] (
      [order_id] BIGINT PRIMARY KEY,
      [customer_id] BIGINT NOT NULL REFERENCES [sales].[customer]([customer_id]),
      [amount] DECIMAL(18, 2) NOT NULL DEFAULT 0,
      [remark] VARCHAR(200) DEFAULT '逗号,分号;仍在字符串中'
    );
    """

    analysis = analyze_ddl_documents([{"name": "quoted.sql", "content": ddl}])

    assert analysis["summary"]["table_count"] == 2
    assert analysis["summary"]["column_count"] == 8
    assert analysis["summary"]["foreign_key_count"] == 1
    assert analysis["summary"]["diagnostic_count"] == 0
    customer_table = next(item for item in analysis["schema"]["tables"] if item["name"] == "sales.customer")
    settings_column = next(item for item in customer_table["columns"] if item[0] == "settings")
    assert settings_column == ["settings", "object", ['default=\'{"locale":"zh-CN","alerts":true}\'']]
    assert "F|sales.orders(customer_id)>sales.customer(customer_id)" in analysis["compact_text"]


def test_ddl_compactor_handles_cross_file_alter_foreign_keys_and_comment_on():
    master = """
    CREATE TABLE support.app_user (
      user_id BIGSERIAL PRIMARY KEY,
      login_name VARCHAR(64) NOT NULL UNIQUE
    );
    """
    business = """
    CREATE TABLE support.ticket (
      ticket_id BIGSERIAL PRIMARY KEY,
      requester_id BIGINT NOT NULL,
      subject VARCHAR(200) NOT NULL
    );
    ALTER TABLE support.ticket ADD CONSTRAINT fk_requester
      FOREIGN KEY (requester_id) REFERENCES support.app_user(user_id) ON DELETE RESTRICT;
    COMMENT ON TABLE support.ticket IS '客服工单';
    COMMENT ON COLUMN support.ticket.subject IS '工单主题';
    """

    analysis = analyze_ddl_documents(
        [
            {"name": "master.sql", "content": master},
            {"name": "business.ddl", "content": business},
        ]
    )

    assert analysis["summary"]["table_count"] == 2
    assert analysis["summary"]["foreign_key_count"] == 1
    assert analysis["summary"]["diagnostic_count"] == 0
    assert "T|support.ticket|客服工单" in analysis["compact_text"]
    assert "subject:string:not_null:工单主题" in analysis["compact_text"]
    assert "F|support.ticket(requester_id)>support.app_user(user_id)|ON DELETE RESTRICT" in analysis["compact_text"]


def test_ddl_compactor_reports_unclosed_ddl_but_keeps_valid_statements():
    ddl = """
    CREATE TABLE valid_table (id BIGINT PRIMARY KEY);
    CREATE TABLE broken_table (id BIGINT, label VARCHAR(20);
    """

    analysis = analyze_ddl_documents([{"name": "partial.sql", "content": ddl}])

    assert analysis["summary"]["table_count"] == 1
    assert analysis["summary"]["diagnostic_count"] == 1
    assert "未闭合的括号" in analysis["diagnostics"][0]["message"]


def test_ddl_compactor_handles_hudi_external_table_syntax():
    ddl = """
    CREATE EXTERNALTABLE IF NOT EXISTS bigdata_ifund.customer (
      customer_id BIGINT PRIMARY KEY COMMENT '客户标识',
      customer_name VARCHAR(120) NOT NULL
    )
    USING hudi
    TBLPROPERTIES ('hoodie.table.name'='customer')
    LOCATION 'hdfs://warehouse/customer'
    COMMENT='客户主数据';
    """

    analysis = analyze_ddl_documents([{"name": "hudi.sql", "content": ddl}])

    assert analysis["summary"]["table_count"] == 1
    assert analysis["summary"]["column_count"] == 2
    assert analysis["summary"]["diagnostic_count"] == 0
    assert "T|bigdata_ifund.customer|客户主数据" in analysis["compact_text"]


def test_ddl_compactor_handles_clickhouse_on_cluster_and_tail_primary_key():
    ddl = """
    CREATE TABLE bigdata_ifund.ads_fund_info ON CLUSTER default_cluster (
      COD_FUND String COMMENT '基金代码',
      NAM_FUND String COMMENT '基金名称',
      DAT_ESTABLISH Nullable(Date) COMMENT '成立日期',
      TAGS Array(String),
      UPDATE_TIME DateTime DEFAULT now()
    )
    ENGINE = ReplicatedMergeTree
    PRIMARY KEY COD_FUND
    ORDER BY COD_FUND
    SETTINGS index_granularity = 8192
    COMMENT '基金信息宽表';
    """

    analysis = analyze_ddl_documents([{"name": "clickhouse.sql", "content": ddl}])

    assert analysis["summary"]["table_count"] == 1
    assert analysis["summary"]["column_count"] == 5
    assert analysis["summary"]["diagnostic_count"] == 0
    assert "T|bigdata_ifund.ads_fund_info|基金信息宽表" in analysis["compact_text"]
    assert "P|COD_FUND" in analysis["compact_text"]
    assert "TAGS:array" in analysis["compact_text"]
    assert "DAT_ESTABLISH:date" in analysis["compact_text"]
    assert "UPDATE_TIME:datetime:default=now()" in analysis["compact_text"]


def test_ddl_analysis_api_reports_token_budget_and_execution_mode():
    response = client.post(
        "/api/domain-ontology/analyze-ddl",
        json={
            "ddl_documents": [
                {"name": "ticket.ddl", "content": "CREATE TABLE ticket(id BIGINT PRIMARY KEY, status VARCHAR(20));"}
            ]
        },
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["table_count"] == 1
    assert summary["estimated_tokens"] > 0
    assert summary["execution_mode"] == "single"
    assert summary["chunk_count"] == 1


def test_ddl_compactor_keeps_complete_schema_when_input_exceeds_budget():
    ddl = "\n".join(
        f"CREATE TABLE t{index} (id BIGINT PRIMARY KEY, value_{index} VARCHAR(200));"
        for index in range(6)
    )

    analysis = analyze_ddl_documents(
        [{"name": "many.sql", "content": ddl}],
        single_call_token_budget=20,
    )

    assert analysis["summary"]["execution_mode"] == "single"
    assert analysis["summary"]["over_single_call_token_budget"] is True
    assert analysis["summary"]["chunk_count"] == 1
    assert len(analysis["chunks"][0]["tables"]) == 6


def test_ddl_compactor_keeps_single_wide_table_in_one_complete_context():
    ddl = "CREATE TABLE wide_table (id BIGINT PRIMARY KEY, " + ", ".join(
        f"column_{index} VARCHAR(100)" for index in range(65)
    ) + ");"

    analysis = analyze_ddl_documents([{"name": "wide.sql", "content": ddl}])

    assert analysis["summary"]["execution_mode"] == "single"
    assert analysis["summary"]["chunk_count"] == 1
    assert len(analysis["chunks"][0]["tables"]) == 1
    assert len(analysis["chunks"][0]["tables"][0]["columns"]) == 66
    assert analysis["chunks"][0]["tables"][0]["primary_key"] == ["id"]


def test_domain_plan_uses_one_complete_ddl_call(monkeypatch):
    fake_analysis = {
        "schema": {
            "format": "oag_compact_ddl_v1",
            "tables": [
                {"name": "customer", "columns": [["id", "integer"]]},
                {"name": "orders", "columns": [["id", "integer"]]},
            ],
            "foreign_keys": [],
        },
        "compact_text": "# oag-ddl-v1\nT|customer\nC|id:integer\nT|orders\nC|id:integer",
        "summary": {
            "execution_mode": "single",
            "chunk_count": 1,
            "table_count": 2,
            "column_count": 2,
            "foreign_key_count": 0,
            "estimated_tokens": 80_000,
        },
        "diagnostics": [],
        "chunks": [{
            "format": "oag_compact_ddl_v1",
            "tables": [
                {"name": "customer", "columns": [["id", "integer"]]},
                {"name": "orders", "columns": [["id", "integer"]]},
            ],
            "foreign_keys": [],
        }],
    }
    calls = []

    class FakeClient:
        def json_chat(self, messages, *, purpose):
            payload = json.loads(messages[-1]["content"])
            calls.append(payload["domain_input"]["ddl_compact"])
            return {
                "summary_zh": "完整规划",
                "objects": [
                    {"object_type": "Customer", "object_type_zh": "Customer", "description": ""},
                    {"object_type": "Order", "object_type_zh": "Order", "description": ""},
                ],
                "attributes": [],
                "relationships": [],
                "open_questions": [],
                "revision_notes": [],
            }

    monkeypatch.setattr(app_module, "analyze_ddl_documents", lambda _documents: deepcopy(fake_analysis))
    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)
    response = client.post(
        "/api/domain-ontology/plan",
        json={"domain_input": {"domain_name": "订单", "ddl_documents": [{"name": "x.sql", "content": "CREATE TABLE x(id INT);"}]}},
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert "T|customer" in calls[0]
    assert "T|orders" in calls[0]
    assert {item["object_type"] for item in response.json()["plan"]["objects"]} == {"Customer", "Order"}
    assert response.json()["plan"]["ddl_processing"]["execution_mode"] == "single"


def test_domain_plan_api_rejects_too_many_ddl_documents():
    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "过大批次",
                "ddl_documents": [{"name": f"t{index}.sql", "content": "select 1"} for index in range(201)],
            }
        },
    )

    assert response.status_code == 400
    assert "200" in response.json()["detail"]["error"]


def test_domain_plan_api_rejects_invalid_factory_session_id():
    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {"domain_name": "客服工单", "bulk_text": "客户提交工单"},
            "llm": {
                "provider": "innovation_factory",
                "endpoint_url": "https://factory.example.test",
                "session_id": "not-a-uuid",
                "request_id": "domain-missing-agent-1234",
            },
        },
    )

    assert response.status_code == 400
    assert "session_id" in response.json()["detail"]["error"]


def test_domain_light_app_prompt_endpoint_exposes_single_prompt():
    response = client.get("/api/domain-ontology/light-app-prompt")

    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt_count"] == 1
    assert payload["input_field"] == "txt"
    assert payload["request_contract"]["endpoint"] == "/chatabc/use_as_tool"
    assert payload["request_contract"]["config_variables"] == []
    assert "ddl_compact" in payload["prompt"]
    assert "# Runtime Input Contract" in payload["prompt"]
    assert "# Example Runtime txt" in payload["prompt"]
    assert "# Example Output" in payload["prompt"]
    assert "只返回一个合法 JSON" in payload["prompt"]
    assert "{{domain_payload}}" not in payload["prompt"]
    assert "不需要读取上传文件" in payload["prompt"]
    assert app_module.domain_ontology_system_prompt() in payload["prompt"]
    assert all(constraint in payload["prompt"] for constraint in app_module.domain_ontology_constraints())
    runtime_example = json.loads(payload["request_example"]["txt"])
    assert runtime_example["task"] == "domain_ontology_unified_planning"
    assert {"objects", "attributes", "relationships"}.issubset(runtime_example["required_output_schema"])
    assert "不能只返回新增或修改项" in payload["prompt"]
    assert payload["output_example"]["relationships"][0]["source"] == "ObjectType:Customer"
    assert payload["stream_events"] == ["chat_started", "chunk", "message", "failed", "done"]


def test_domain_plan_api_returns_repair_payload_for_invalid_json(monkeypatch):
    class FakeClient:
        def json_chat(self, _messages, *, purpose):
            raise LLMJSONRepairRequired(
                "domain ontology plan returned non-JSON content: broken",
                content='{"summary_zh": "broken"',
                parse_error="Expecting ',' delimiter",
                purpose=purpose,
            )

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={"domain_input": {"domain_name": "客服工单", "objects": [{"object_type": "Customer"}], "attributes": [], "bulk_text": ""}},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["repairable"] is True
    assert detail["repair_payload"]["invalid_content"]


def test_domain_plan_repair_api_uses_repair_payload(monkeypatch):
    class FakeClient:
        def repair_json_chat(self, _messages, invalid_content, purpose, original_error):
            assert purpose == "domain ontology plan"
            assert "broken" in invalid_content
            assert "delimiter" in original_error
            return deepcopy(sample_plan())

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan-repair",
        json={
            "domain_input": {"domain_name": "客服工单", "objects": [{"object_type": "Customer"}], "attributes": [], "bulk_text": ""},
            "previous_plan": None,
            "feedback": "",
            "repair_payload": {"invalid_content": "broken", "parse_error": "Expecting delimiter"},
        },
    )

    assert response.status_code == 200
    assert response.json()["plan"]["summary_zh"]


def test_domain_plan_api_normalizes_bare_relationship_endpoints(monkeypatch):
    plan = {
        "summary_zh": "在线课程领域包含学生、课程和课程状态。",
        "objects": [
            {"object_type": "Student", "object_type_zh": "学生", "description": "学习课程的用户。"},
            {"object_type": "Course", "object_type_zh": "课程", "description": "在线课程。"},
        ],
        "attributes": [
            {
                "attribute_name": "course_status",
                "attribute_name_zh": "课程状态",
                "object_types": ["ObjectType:Course"],
                "value_type": "string",
                "description": "课程当前状态。",
            }
        ],
        "relationships": [
            {
                "source": "Student",
                "target": "Course",
                "relation_type": "enrolls",
                "relation_name_zh": "报名课程",
                "reason_zh": "学生可以报名课程。",
            },
            {
                "source": "Course",
                "target": "course_status",
                "relation_type": "has_attribute",
                "relation_name_zh": "拥有属性",
                "reason_zh": "课程需要状态字段。",
            },
        ],
        "open_questions": [],
        "revision_notes": [],
    }

    class FakeClient:
        def json_chat(self, _messages, *, purpose):
            assert purpose == "domain ontology plan"
            return deepcopy(plan)

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={"domain_input": {"domain_name": "在线课程", "objects": [], "attributes": [], "bulk_text": "学生报名课程"}},
    )

    assert response.status_code == 200
    data = response.json()["plan"]
    assert data["attributes"][0]["object_types"] == ["Course"]
    assert data["relationships"][0]["source"] == "ObjectType:Student"
    assert data["relationships"][0]["target"] == "ObjectType:Course"
    assert data["relationships"][1]["source"] == "ObjectType:Course"
    assert data["relationships"][1]["target"] == "Attribute:course_status"


def test_domain_plan_api_always_requests_and_uses_complete_plan(monkeypatch):
    captured = {}

    class FakeClient:
        def json_chat(self, messages, *, purpose):
            assert purpose == "domain ontology plan"
            payload = json.loads(messages[1]["content"])
            captured["schema"] = payload["required_output_schema"]
            captured["previous_plan"] = payload["previous_plan"]
            return {
                "summary_zh": "债券投资分析需要围绕价格、收益率和风险指标建立属性级关系。",
                "objects": [
                    {"object_type": "BondQuote", "object_type_zh": "债券行情", "description": "债券行情数据。"}
                ],
                "attributes": [
                    {
                        "attribute_name": "yield_to_maturity",
                        "attribute_name_zh": "到期收益率",
                        "object_types": ["BondQuote"],
                        "value_type": "number",
                        "description": "按当前价格持有至到期的年化收益率。",
                    },
                    {
                        "attribute_name": "credit_spread",
                        "attribute_name_zh": "信用利差",
                        "object_types": ["BondQuote"],
                        "value_type": "number",
                        "description": "债券收益率相对无风险收益率的利差。",
                    },
                ],
                "relationships": [
                    {
                        "source": "yield_to_maturity",
                        "target": "credit_spread",
                        "relation_type": "risk_companion",
                        "relation_name_zh": "风险伴随指标",
                        "reason_zh": "到期收益率和信用利差共同支持债券信用风险分析。",
                    }
                ],
                "open_questions": [],
                "revision_notes": [],
            }

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "债券投资分析",
                "objects": [{"object_type": "BondQuote", "object_type_zh": "债券行情", "description": "债券行情数据。"}],
                "attributes": [
                    {
                        "attribute_name": "yield_to_maturity",
                        "attribute_name_zh": "到期收益率",
                        "object_types": ["BondQuote"],
                        "value_type": "number",
                        "description": "按当前价格持有至到期的年化收益率。",
                    },
                    {
                        "attribute_name": "credit_spread",
                        "attribute_name_zh": "信用利差",
                        "object_types": ["BondQuote"],
                        "value_type": "number",
                        "description": "债券收益率相对无风险收益率的利差。",
                    },
                ],
                "bulk_text": "债券行情记录到期收益率，信用利差用于风险分析。",
            },
            "previous_plan": {
                "objects": [{"object_type": "HugeObject"}],
                "attributes": [{"attribute_name": "huge_attribute"}],
                "relationships": [{"source": "Attribute:a", "target": "Attribute:b", "relation_type": "related"}],
            },
        },
    )

    assert response.status_code == 200
    assert "objects" in captured["schema"]
    assert "attributes" in captured["schema"]
    assert captured["previous_plan"]["objects"] == [{"object_type": "HugeObject"}]
    assert captured["previous_plan"]["attributes"] == [{"attribute_name": "huge_attribute"}]
    data = response.json()["plan"]
    assert data["objects"][0]["object_type"] == "BondQuote"
    assert {item["attribute_name"] for item in data["attributes"]} == {"yield_to_maturity", "credit_spread"}
    assert data["relationships"][0]["source"] == "Attribute:yield_to_maturity"
    assert data["relationships"][0]["target"] == "Attribute:credit_spread"


def test_domain_replan_accepts_complete_plan_with_previous_and_new_relationships(monkeypatch):
    previous_plan = sample_plan()
    previous_plan["attributes"].append(
        {"attribute_name": "priority", "attribute_name_zh": "优先级", "object_types": ["Ticket"], "value_type": "string", "description": "工单优先级。"}
    )

    class FakeClient:
        def json_chat(self, messages, *, purpose):
            assert purpose == "domain ontology plan"
            payload = json.loads(messages[1]["content"])
            assert payload["user_feedback"] == "增加工单状态与优先级的关系"
            assert payload["previous_plan"]["objects"] == previous_plan["objects"]
            assert payload["previous_plan"]["attributes"] == previous_plan["attributes"]
            return {
                "summary_zh": "补充工单状态与优先级之间的影响关系。",
                "objects": deepcopy(previous_plan["objects"]),
                "attributes": deepcopy(previous_plan["attributes"]),
                "relationships": [
                    *deepcopy(previous_plan["relationships"]),
                    {
                        "source": "ticket_status",
                        "target": "priority",
                        "relation_type": "influences_priority",
                        "relation_name_zh": "影响优先级",
                        "reason_zh": "工单状态变化会影响处理优先级。",
                    }
                ],
                "open_questions": [],
                "revision_notes": [],
            }

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "客服工单",
                "objects": previous_plan["objects"],
                "attributes": previous_plan["attributes"],
                "bulk_text": "客服工单处理。",
            },
            "previous_plan": previous_plan,
            "feedback": "增加工单状态与优先级的关系",
        },
    )

    assert response.status_code == 200
    relationships = response.json()["plan"]["relationships"]
    assert any(item["relation_type"] == "submits" for item in relationships)
    assert any(item["relation_type"] == "influences_priority" for item in relationships)


def test_domain_replan_removes_relationship_by_returning_complete_new_state(monkeypatch):
    previous_plan = sample_plan()
    previous_plan["attributes"].append(
        {"attribute_name": "priority", "attribute_name_zh": "优先级", "object_types": ["Ticket"], "value_type": "string", "description": "工单优先级。"}
    )
    previous_plan["relationships"].append(
        {
            "source": "Attribute:ticket_status",
            "target": "Attribute:priority",
            "relation_type": "influences_priority",
            "relation_name_zh": "影响优先级",
            "reason_zh": "原先认为状态影响优先级。",
        }
    )

    class FakeClient:
        def json_chat(self, messages, *, purpose):
            assert purpose == "domain ontology plan"
            payload = json.loads(messages[1]["content"])
            assert "deleted_relationships" not in payload["required_output_schema"]
            assert len(payload["previous_plan"]["relationships"]) == 2
            return {
                "summary_zh": "删除状态影响优先级关系，保留其他关系。",
                "objects": deepcopy(previous_plan["objects"]),
                "attributes": deepcopy(previous_plan["attributes"]),
                "relationships": [deepcopy(previous_plan["relationships"][0])],
                "open_questions": [],
                "revision_notes": ["反馈指出优先级由人工指定，已移除状态影响优先级关系。"],
            }

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "客服工单",
                "objects": previous_plan["objects"],
                "attributes": previous_plan["attributes"],
                "bulk_text": "客服工单处理。",
            },
            "previous_plan": previous_plan,
            "feedback": "删除状态影响优先级关系",
        },
    )

    assert response.status_code == 200
    plan = response.json()["plan"]
    assert any(item["relation_type"] == "submits" for item in plan["relationships"])
    assert not any(item["relation_type"] == "influences_priority" for item in plan["relationships"])
    assert "已移除" in plan["revision_notes"][0]
    assert "deleted_relationships" not in plan


def test_domain_plan_api_infers_feedback_relationship_endpoint_nodes(monkeypatch):
    captured = {}

    class FakeClient:
        def json_chat(self, messages, *, purpose):
            assert purpose == "domain ontology plan"
            payload = json.loads(messages[1]["content"])
            captured["schema"] = payload["required_output_schema"]
            return {
                "summary_zh": "根据反馈补充办公室对象，并建立员工所属办公室关系。",
                "objects": [
                    {"object_type": "Employee", "object_type_zh": "员工", "description": "组织成员。"},
                    {"object_type": "Office", "object_type_zh": "办公室", "description": "员工办公地点。"},
                ],
                "attributes": [],
                "relationships": [
                    {
                        "source": "ObjectType:Employee",
                        "target": "ObjectType:Office",
                        "relation_type": "belongs_to",
                        "relation_name_zh": "所属办公室",
                        "reason_zh": "员工需要关联办公地点。",
                    }
                ],
                "open_questions": [],
                "revision_notes": ["根据反馈新增 Office 对象及员工所属办公室关系。"],
            }

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/plan",
        json={
            "domain_input": {
                "domain_name": "组织管理",
                "objects": [{"object_type": "Employee", "object_type_zh": "员工", "description": "组织成员。"}],
                "attributes": [],
                "bulk_text": "员工管理。",
            },
            "previous_plan": sample_plan(),
            "feedback": "增加办公室，员工需要关联办公室。",
        },
    )

    assert response.status_code == 200
    assert "objects" in captured["schema"]
    data = response.json()["plan"]
    assert {"Employee", "Office"}.issubset({item["object_type"] for item in data["objects"]})
    assert any(item["target"] == "ObjectType:Office" for item in data["relationships"])
    assert any("Office" in item for item in data["revision_notes"])


def test_domain_generate_api_writes_independent_yaml_and_returns_graph(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())

    class FakeClient:
        def json_chat(self, _messages, *, purpose):
            raise AssertionError(f"generate should not call LLM client: {purpose}")

    monkeypatch.setattr(app_module, "BailianLLMClient", FakeClient)

    response = client.post(
        "/api/domain-ontology/generate",
        json={"domain_input": {"domain_name": "客服工单", "description": "测试领域"}, "plan": sample_plan(), "feedback": "保留客户提交工单关系"},
    )

    assert response.status_code == 200
    data = response.json()
    domain_id = data["domain_id"]
    version_id = data["write"]["version_id"]
    domain_dir = domain_store.DOMAINS_DIR / domain_id
    assert (domain_dir / "domain.yaml").exists()
    assert (domain_dir / "versions" / version_id / "plan.yaml").exists()
    assert (domain_dir / "versions" / version_id / "object_types.yaml").exists()
    assert data["graph"]["version_id"] == version_id
    assert data["graph"]["plan"]["summary_zh"] == sample_plan()["summary_zh"]
    assert data["graph"]["domain_input"]["domain_name"] == "客服工单"
    assert data["graph"]["feedback"] == "保留客户提交工单关系"
    versions = domain_store.list_domain_versions(domain_id)
    assert versions[0]["operation_summary"] == "保留客户提交工单关系"
    assert data["graph"]["kind"] == "domain_graph"
    assert any(node["data"]["id"] == "ObjectType:Ticket" for node in data["graph"]["nodes"])
    assert any(edge["data"]["type"] == "has_attribute" for edge in data["graph"]["edges"])
    assert any(edge["data"]["type"] == "submits" for edge in data["graph"]["edges"])


def test_domain_generate_uses_complete_plan_without_restoring_omitted_input_items(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    domain_input = {
        "domain_name": "债券投资分析",
        "objects": [
            {"object_type": "Bond", "object_type_zh": "债券", "description": "债券。"},
            {"object_type": "CashflowSchedule", "object_type_zh": "现金流计划", "description": "现金流安排。"},
        ],
        "attributes": [
            {
                "attribute_name": "bond_code",
                "attribute_name_zh": "债券代码",
                "object_types": ["Bond"],
                "value_type": "string",
                "description": "债券代码。",
            },
            {
                "attribute_name": "cashflow_id",
                "attribute_name_zh": "现金流编号",
                "object_types": ["CashflowSchedule"],
                "value_type": "string",
                "description": "现金流计划唯一标识。",
            },
        ],
    }
    replanned = {
        "summary_zh": "删除现金流计划对象及其属性和关系。",
        "objects": [domain_input["objects"][0]],
        "attributes": [domain_input["attributes"][0]],
        "relationships": [],
        "open_questions": [],
        "revision_notes": ["已删除现金流计划对象及其对应属性和关系。"],
    }

    response = client.post(
        "/api/domain-ontology/generate",
        json={"domain_input": domain_input, "plan": replanned, "feedback": "删除现金流计划对象及其对应的属性和关系"},
    )

    assert response.status_code == 200
    graph = response.json()["graph"]
    node_ids = {node["data"]["id"] for node in graph["nodes"]}
    assert "ObjectType:Bond" in node_ids
    assert "Attribute:bond_code" in node_ids
    assert "ObjectType:CashflowSchedule" not in node_ids
    assert "Attribute:cashflow_id" not in node_ids
    assert not any(edge["data"]["type"] == "generates_cashflow" for edge in graph["edges"])


def test_domain_graph_api_reconstructs_plan_for_existing_domain_without_saved_plan(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    created = domain_store.create_domain_from_sections({"domain_name": "客服工单"}, deepcopy(sample_sections()))

    response = client.get(f"/api/domain-ontology/{created['domain_id']}/graph")

    assert response.status_code == 200
    graph = response.json()
    assert graph["plan"]["objects"][0]["object_type"] == "Customer"
    assert graph["plan"]["attributes"][0]["attribute_name"] == "ticket_status"
    assert graph["plan"]["relationships"][0]["relation_type"] == "submits"
    assert graph["domain_input"]["domain_name"] == "客服工单"
    assert graph["feedback"] == ""


def test_domain_graph_api_returns_latest_yaml_for_refill_after_updates(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    created = domain_store.create_domain_from_sections(
        {"domain_name": "客服工单", "objects": [{"object_type": "Customer"}]},
        deepcopy(sample_sections()),
        sample_plan(),
        "",
    )
    domain_id = created["domain_id"]
    domain_store.upsert_domain_node(
        domain_id,
        "ObjectType",
        "Office",
        {"object_type": "Office", "object_type_zh": "办公室", "description": "处理工单的办公地点。"},
    )
    domain_store.upsert_domain_node(
        domain_id,
        "RelationType",
        "assigned_to",
        {"relation_type": "assigned_to", "relation_name_zh": "分配到", "description": "工单分配到办公室。"},
    )
    domain_store.upsert_domain_edge(
        domain_id,
        "",
        "ObjectType:Ticket",
        "ObjectType:Office",
        "assigned_to",
        {"reason_zh": "工单需要分配处理办公室。"},
    )

    response = client.get(f"/api/domain-ontology/{domain_id}/graph")

    assert response.status_code == 200
    graph = response.json()
    assert {item["object_type"] for item in graph["domain_input"]["objects"]} == {"Customer", "Ticket", "Office"}
    assert {item["object_type"] for item in graph["plan"]["objects"]} == {"Customer", "Ticket", "Office"}
    assert any(item["relation_type"] == "assigned_to" for item in graph["plan"]["relationships"])


def test_domain_generate_creates_versions_and_checkout_reverts_current(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    first = domain_store.create_domain_from_sections(
        {"domain_name": "客服工单"},
        deepcopy(sample_sections()),
        sample_plan(),
        "",
    )
    second_sections = deepcopy(sample_sections())
    second_sections["object_types"].append({"object_type": "Office", "object_type_zh": "办公室", "description": "处理地点。"})
    second_sections["relation_types"].append({"relation_type": "assigned_to", "relation_name_zh": "分配到", "description": "工单分配到办公室。"})
    second_sections["schema_graph_edges"].append(
        {
            "from": "ObjectType:Ticket",
            "to": "ObjectType:Office",
            "relation_type": "assigned_to",
            "reason_zh": "工单需要分配处理办公室。",
        }
    )
    second = domain_store.create_domain_from_sections(
        {"domain_name": "客服工单"},
        second_sections,
        sample_plan(),
        "增加办公室",
        first["domain_id"],
        first["version_id"],
    )

    domains = domain_store.list_domains()
    assert len(domains) == 1
    assert domains[0]["current_version_id"] == second["version_id"]
    assert len(domains[0]["versions"]) == 2

    current_graph = client.get(f"/api/domain-ontology/{first['domain_id']}/graph").json()
    assert any(node["data"]["id"] == "ObjectType:Office" for node in current_graph["nodes"])

    checkout_response = client.post(
        f"/api/domain-ontology/{first['domain_id']}/checkout",
        params={"version_id": first["version_id"]},
    )
    assert checkout_response.status_code == 200
    reverted_graph = client.get(f"/api/domain-ontology/{first['domain_id']}/graph").json()
    assert reverted_graph["version_id"] == first["version_id"]
    assert not any(node["data"]["id"] == "ObjectType:Office" for node in reverted_graph["nodes"])


def test_domain_version_note_api_updates_version_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    created = domain_store.create_domain_from_sections({"domain_name": "客服工单"}, deepcopy(sample_sections()))

    response = client.post(
        f"/api/domain-ontology/{created['domain_id']}/version-note",
        json={"version_id": created["version_id"], "note": "这是稳定基线版本"},
    )

    assert response.status_code == 200
    versions = domain_store.list_domain_versions(created["domain_id"])
    assert versions[0]["note"] == "这是稳定基线版本"


def test_domain_version_delete_marks_deleted_and_reparents_children(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    first = domain_store.create_domain_from_sections({"domain_name": "客服工单"}, deepcopy(sample_sections()), sample_plan())
    second = domain_store.create_domain_from_sections(
        {"domain_name": "客服工单"},
        deepcopy(sample_sections()),
        sample_plan(),
        "第二版：增加处理办公室",
        first["domain_id"],
        first["version_id"],
    )
    third = domain_store.create_domain_from_sections(
        {"domain_name": "客服工单"},
        deepcopy(sample_sections()),
        sample_plan(),
        "第三版：调整派单关系",
        first["domain_id"],
        second["version_id"],
    )

    response = client.delete(
        f"/api/domain-ontology/{first['domain_id']}/version/{second['version_id']}",
        params={"mode": "reparent"},
    )

    assert response.status_code == 200
    versions = {item["version_id"]: item for item in domain_store.list_domain_versions(first["domain_id"])}
    assert versions[second["version_id"]]["deleted"] is True
    assert versions[third["version_id"]]["parent_version_id"] == first["version_id"]

    cascade_response = client.delete(
        f"/api/domain-ontology/{first['domain_id']}/version/{third['version_id']}",
        params={"mode": "cascade"},
    )

    assert cascade_response.status_code == 200
    versions = {item["version_id"]: item for item in domain_store.list_domain_versions(first["domain_id"])}
    assert versions[third["version_id"]]["deleted"] is True
    assert domain_store.current_version_id(first["domain_id"]) == first["version_id"]


def test_domain_manual_edit_creates_child_version(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    created = domain_store.create_domain_from_sections({"domain_name": "客服工单"}, deepcopy(sample_sections()))

    response = client.post(
        f"/api/domain-ontology/{created['domain_id']}/node",
        json={
            "node_type": "ObjectType",
            "node_id": "Office",
            "data": {"object_type": "Office", "object_type_zh": "办公室", "description": "处理地点。"},
        },
    )

    assert response.status_code == 200
    new_version_id = response.json()["version_id"]
    assert new_version_id != created["version_id"]
    versions = domain_store.list_domain_versions(created["domain_id"])
    assert len(versions) == 2
    assert versions[-1]["parent_version_id"] == created["version_id"]
    assert versions[-1]["change_type"] == "manual"
    assert versions[-1]["manual_change"]["action"] == "upsert_node"
    assert versions[-1]["operation_summary"] == "新增/修改节点：ObjectType:Office"

    graph = client.get(f"/api/domain-ontology/{created['domain_id']}/graph").json()
    assert graph["version_id"] == new_version_id
    assert any(node["data"]["id"] == "ObjectType:Office" for node in graph["nodes"])


def test_domain_edit_api_is_scoped_to_domain_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(domain_store, "DOMAINS_DIR", (tmp_path / "domains").resolve())
    created = domain_store.create_domain_from_sections({"domain_name": "客服工单"}, deepcopy(sample_sections()))
    domain_id = created["domain_id"]

    node_response = client.post(
        f"/api/domain-ontology/{domain_id}/node",
        json={
            "node_type": "Attribute",
            "node_id": "priority",
            "data": {"attribute_name": "priority", "attribute_name_zh": "优先级", "object_types": ["Ticket"], "value_type": "string"},
        },
    )
    assert node_response.status_code == 200

    edge_response = client.post(
        f"/api/domain-ontology/{domain_id}/edge",
        json={
            "source": "ObjectType:Ticket",
            "target": "Attribute:priority",
            "relation_type": "has_attribute",
            "properties": {"reason_zh": "工单有优先级。"},
        },
    )
    assert edge_response.status_code == 200

    graph_response = client.get(f"/api/domain-ontology/{domain_id}/graph")
    assert graph_response.status_code == 200
    graph = graph_response.json()
    assert any(node["data"]["id"] == "Attribute:priority" for node in graph["nodes"])
    assert (domain_store.DOMAINS_DIR / domain_id / "versions" / created["version_id"] / "attributes.yaml").exists()

    delete_response = client.delete(
        f"/api/domain-ontology/{domain_id}/node/{'Attribute:priority'}",
        params={"force": "true"},
    )
    assert delete_response.status_code == 200


def test_domain_ontology_frontend_static_contracts():
    response = client.get("/domain-ontology")
    assert response.status_code == 200
    assert "/domain-static/domain_app.js" in response.text
    assert "/domain-static/domain_style.css" in response.text
    assert "/static/app.js" not in response.text

    html = (app_module.PROJECT_ROOT / "ontology_editor" / "domain_static" / "index.html").read_text(encoding="utf-8")
    source = (app_module.PROJECT_ROOT / "ontology_editor" / "domain_static" / "domain_app.js").read_text(encoding="utf-8")
    style = (app_module.PROJECT_ROOT / "ontology_editor" / "domain_static" / "domain_style.css").read_text(encoding="utf-8")
    legacy_source = (app_module.PROJECT_ROOT / "ontology_editor" / "static" / "app.js").read_text(encoding="utf-8")

    for text in [
        "领域本体关系规划",
        "生成规划方案",
        "确认生成关系图",
        "按反馈重新规划",
        "graphApplyInputBtn",
        "graphFeedbackPanel",
        "graphLegend",
        "versionDialog",
        "versionDetailResizeHandle",
        "refillPlanActions",
        "graphSpacingControl",
        "appModal",
        "lightAppUrl",
        "lightAppCancelUrl",
        "lightAppPromptText",
        "llmConfigDialog",
        "llmConfigSaveBtn",
        "大模型API",
        "创新工厂API",
        "ddlFiles",
        "ddlDropzone",
        "ddlAnalysisPanel",
        "ddlAnalysisMetrics",
        "cancelLlmBtn",
      ]:
        assert text in html
    for text in [
        "/api/domain-ontology/plan",
        "/api/domain-ontology/plan-repair",
        "/api/domain-ontology/generate",
        "currentDomainId",
        "currentDomainVersionId",
        "version-tree",
        "version-map",
        "versionOperationText",
        "bindVersionGraphPan",
        "deleteVersion",
        "domainGraphPresetPositions",
        "setRefillPlanActions",
        "setGraphSpacing",
        "defaultGraphSpacing",
        "objectRowsCollapsed",
        "attributeRowsCollapsed",
        "renderCollapsedRowsNotice",
        "已回填",
        "展开全部",
        "收起列表",
        "formMode",
        "wasExistingMode",
        "applyDomainInput(data, true)",
        "requestDomainPlan",
        "applyPlanResult",
        "openAppModal",
        "closeAppModal",
        "generationFeedback",
        "saveVersionNote",
        "selectedElement",
        "/api/domain-ontology/light-app-prompt",
        "/api/domain-ontology/cancel",
        "/api/domain-ontology/analyze-ddl",
        "addDdlFiles",
        "analyzeDdlDocuments",
        "renderDdlAnalysis",
        "ddl_documents",
        "cancelActiveLlmRequest",
        "readLlmSettings",
        "persistProviderSettings",
        "domainOntology.lightAppUrl",
        "lightAppSessionId",
        "createSessionId",
        "ensureLightAppSession",
    ]:
        assert text in source
    assert "window.alert" not in source
    assert "window.confirm" not in source
    assert "window.prompt" not in source
    assert "state.domainInput = readDomainInput();" in source
    assert "state.loadedDomainInput && !state.domainInputApplied" not in source
    assert "!input.description && !input.objects.length && !input.attributes.length" in source
    assert "大模型接入配置已保存" in source
    assert "百炼配置已就绪" not in source
    assert "model-config-panel" not in html
    assert "/chatabc/upload_file" not in html
    assert "/chatabc/init_session" not in html
    assert "/chatabc/chat" not in html
    assert "/chatabc/use_as_tool" in html
    assert "新领域本体关系规划" not in html
    assert "step-strip" not in html
    assert "domain-ontology-panel" not in style
    assert "step-strip" not in style
    assert "graph-canvas" in style
    assert "graph-spacing-control" in style
    assert "collapsed-rows-notice" in style
    assert "collapsed-extra-row" in style
    assert "app-modal-card" in style
    assert "plan-diff-summary" in style
    assert "diff-badge" in style
    assert "version-dialog-card" in style
    assert "version-change-json" in style
    assert "provider-switch" in style
    assert "ddl-dropzone" in style
    assert "ddl-analysis-metrics" in style
    assert "loading-hint" in style
    assert "llm-config-dialog-card" in style
    assert "api-status-btn" in style
    assert 'id: "domain_ontology"' not in legacy_source
