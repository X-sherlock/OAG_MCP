from __future__ import annotations

import json
import re
import socket
import threading
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "llm_config.local.yaml"


class LLMConfigError(ValueError):
    pass


class LLMClientError(ValueError):
    pass


class LLMRequestCancelled(LLMClientError):
    pass


class LLMJSONRepairRequired(LLMClientError):
    def __init__(self, message: str, *, content: str, parse_error: str, purpose: str) -> None:
        super().__init__(message)
        self.content = content
        self.parse_error = parse_error
        self.purpose = purpose

    def repair_payload(self) -> dict[str, str]:
        return {
            "purpose": self.purpose,
            "parse_error": self.parse_error,
            "invalid_content": self.content[:30000],
        }


@dataclass(frozen=True)
class BailianLLMConfig:
    api_key: str
    base_url: str
    model: str = "qwen3.5-plus-2026-04-20"
    timeout_seconds: int = 180
    max_completion_tokens: int = 20480
    temperature: float = 0.2
    cancel_url: str = ""
    enable_thinking: bool = False


@dataclass(frozen=True)
class LightAppLLMConfig:
    endpoint_url: str
    session_id: str = ""
    cancel_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 600


@dataclass
class _ActiveLLMRequest:
    request_id: str
    cancel_callback: Callable[[], dict[str, Any]]
    cancelled: threading.Event
    response: Any = None


_ACTIVE_REQUESTS: dict[str, _ActiveLLMRequest] = {}
_ACTIVE_REQUESTS_LOCK = threading.Lock()


def validate_http_url(value: str, field_name: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise LLMConfigError(f"{field_name} must be a valid http or https URL")
    if parsed.username or parsed.password:
        raise LLMConfigError(f"{field_name} must not contain credentials")
    return url


def register_llm_request(request_id: str, cancel_callback: Callable[[], dict[str, Any]]) -> _ActiveLLMRequest | None:
    request_id = str(request_id or "").strip()
    if not request_id:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", request_id):
        raise LLMClientError("request_id format is invalid")
    active = _ActiveLLMRequest(request_id, cancel_callback, threading.Event())
    with _ACTIVE_REQUESTS_LOCK:
        if request_id in _ACTIVE_REQUESTS:
            raise LLMClientError(f"request_id is already active: {request_id}")
        _ACTIVE_REQUESTS[request_id] = active
    return active


def attach_llm_response(active: _ActiveLLMRequest | None, response: Any) -> None:
    if active is not None:
        active.response = response


def complete_llm_request(active: _ActiveLLMRequest | None) -> None:
    if active is None:
        return
    with _ACTIVE_REQUESTS_LOCK:
        if _ACTIVE_REQUESTS.get(active.request_id) is active:
            _ACTIVE_REQUESTS.pop(active.request_id, None)


def cancel_llm_request(request_id: str) -> dict[str, Any]:
    with _ACTIVE_REQUESTS_LOCK:
        active = _ACTIVE_REQUESTS.get(str(request_id or "").strip())
    if active is None:
        return {"found": False, "cancelled": False, "stop_command_sent": False}
    active.cancelled.set()
    response_closed = False
    if active.response is not None:
        try:
            active.response.close()
            response_closed = True
        except Exception:  # noqa: BLE001 - cancellation remains best-effort at the socket layer.
            response_closed = False
    stop_result: dict[str, Any]
    try:
        stop_result = active.cancel_callback()
    except Exception as exc:  # noqa: BLE001 - report cancellation transport failures to the caller.
        stop_result = {"stop_command_sent": False, "stop_error": str(exc)}
    return {
        "found": True,
        "cancelled": True,
        "response_closed": response_closed,
        **stop_result,
    }


def load_llm_config(path: Path | None = None) -> BailianLLMConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise LLMConfigError(f"LLM config file does not exist: {display_path(config_path)}")
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise LLMConfigError(f"LLM config YAML is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMConfigError("LLM config must be a YAML object")

    api_key = str(data.get("api_key") or "").strip()
    base_url = str(data.get("base_url") or "").strip()
    model = str(data.get("model") or "qwen3.5-plus-2026-04-20").strip()
    if not api_key:
        raise LLMConfigError("LLM config missing api_key")
    if not base_url or "{WorkspaceId}" in base_url:
        raise LLMConfigError("LLM config base_url must be set to a real Bailian compatible-mode endpoint")
    if not model:
        raise LLMConfigError("LLM config missing model")
    return BailianLLMConfig(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        timeout_seconds=max(120, int(data.get("timeout_seconds") or 180)),
        max_completion_tokens=int(data.get("max_completion_tokens") or 20480),
        temperature=float(data.get("temperature") if data.get("temperature") is not None else 0.2),
        cancel_url=str(data.get("cancel_url") or "").strip(),
        enable_thinking=data.get("enable_thinking") is True,
    )


def llm_config_status(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG_PATH
    exists = config_path.exists()
    data: dict[str, Any] = {}
    error = ""
    if exists:
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                data = loaded
            else:
                error = "LLM config must be a YAML object"
        except Exception as exc:  # noqa: BLE001 - status endpoint should report, not raise.
            error = str(exc)
    base_url = str(data.get("base_url") or "").strip()
    api_key = str(data.get("api_key") or "").strip()
    return {
        "config_path": display_path(config_path),
        "exists": exists,
        "configured": bool(exists and api_key and base_url and "{WorkspaceId}" not in base_url and not error),
        "has_api_key": bool(api_key),
        "base_url": base_url,
        "model": str(data.get("model") or "qwen3.5-plus-2026-04-20"),
        "has_cancel_url": bool(str(data.get("cancel_url") or "").strip()),
        "error": error,
    }


class BailianLLMClient:
    def __init__(self, config: BailianLLMConfig | None = None) -> None:
        self.config = config or load_llm_config()

    def json_chat(self, messages: list[dict[str, str]], *, purpose: str, request_id: str = "") -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_completion_tokens,
            "response_format": {"type": "json_object"},
            "enable_thinking": self.config.enable_thinking,
            "stream_options": {"include_usage": True},
        }
        active = register_llm_request(request_id, lambda: self._cancel_upstream(request_id))
        try:
            response = self._post(payload, active)
            self._raise_if_cancelled(active)
            content = self._extract_content(response)
            try:
                parsed = parse_json_content(content)
            except ValueError as exc:
                raise LLMJSONRepairRequired(
                    f"{purpose} returned non-JSON content: {exc}",
                    content=content,
                    parse_error=str(exc),
                    purpose=purpose,
                ) from exc
            if not isinstance(parsed, dict):
                raise LLMClientError(f"{purpose} returned JSON but not an object")
            return parsed
        finally:
            complete_llm_request(active)

    def repair_json_chat(
        self,
        messages: list[dict[str, str]],
        invalid_content: str,
        purpose: str,
        original_error: str,
        request_id: str = "",
    ) -> Any:
        repair_messages = [
            *messages,
            {"role": "assistant", "content": invalid_content[:20000]},
            {
                "role": "user",
                "content": (
                    "上一条回复不是合法 JSON，解析错误为："
                    f"{original_error}。\n"
                    "请只返回修复后的合法 JSON 对象，不要解释，不要 Markdown，不要省略字段。"
                ),
            },
        ]
        payload = {
            "model": self.config.model,
            "messages": repair_messages,
            "temperature": 0,
            "max_tokens": self.config.max_completion_tokens,
            "response_format": {"type": "json_object"},
            "enable_thinking": self.config.enable_thinking,
            "stream_options": {"include_usage": True},
        }
        active = register_llm_request(request_id, lambda: self._cancel_upstream(request_id))
        try:
            response = self._post(payload, active)
            self._raise_if_cancelled(active)
            repaired_content = self._extract_content(response)
            try:
                parsed = parse_json_content(repaired_content)
            except ValueError as repair_error:
                raise LLMClientError(
                    f"{purpose} returned non-JSON content: {original_error}; repair retry also failed: {repair_error}"
                ) from repair_error
            if not isinstance(parsed, dict):
                raise LLMClientError(f"{purpose} repair returned JSON but not an object")
            return parsed
        finally:
            complete_llm_request(active)

    def _post(self, payload: dict[str, Any], active: _ActiveLLMRequest | None = None) -> dict[str, Any]:
        url = f"{self.config.base_url}/chat/completions"
        payload = {**payload, "stream": True}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                attach_llm_response(active, response)
                if hasattr(response, "__iter__"):
                    content = parse_openai_compatible_stream(response, active)
                    return {"choices": [{"message": {"content": content}}]}
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:  # noqa: BLE001 - preserve the original HTTP failure.
                detail = str(exc)
            raise LLMClientError(f"Bailian API HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            if active is not None and active.cancelled.is_set():
                raise LLMRequestCancelled("LLM request was cancelled") from exc
            raise LLMClientError(f"Bailian API request failed: {exc}") from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"Bailian API returned invalid JSON: {raw[:500]}") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("Bailian API returned JSON but not an object")
        return parsed

    def _cancel_upstream(self, request_id: str) -> dict[str, Any]:
        if not self.config.cancel_url:
            return {
                "stop_command_sent": False,
                "stop_note": "OpenAI-compatible endpoint has no configured cancel_url; the active HTTP response was closed.",
            }
        return post_stop_command(self.config.cancel_url, self.config.api_key, request_id)

    @staticmethod
    def _raise_if_cancelled(active: _ActiveLLMRequest | None) -> None:
        if active is not None and active.cancelled.is_set():
            raise LLMRequestCancelled("LLM request was cancelled")

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("Bailian API response missing choices[0].message.content") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("Bailian API response content is empty")
        return content


class LightAppLLMClient:
    def __init__(self, config: LightAppLLMConfig) -> None:
        endpoint_url = validate_http_url(config.endpoint_url, "endpoint_url")
        self.config = LightAppLLMConfig(
            endpoint_url=endpoint_url.rstrip("/"),
            session_id=innovation_factory_session_id(config.session_id),
            cancel_url=validate_http_url(config.cancel_url, "cancel_url") if config.cancel_url else "",
            api_key=str(config.api_key or "").strip(),
            timeout_seconds=max(30, int(config.timeout_seconds or 180)),
        )

    def json_chat(self, messages: list[dict[str, str]], *, purpose: str, request_id: str = "") -> dict[str, Any]:
        runtime_payload = next(
            (item.get("content", "") for item in reversed(messages) if item.get("role") == "user"),
            "",
        )
        active = register_llm_request(
            request_id,
            lambda: self._cancel_upstream(request_id),
        )
        try:
            content = self._use_as_tool(runtime_payload, request_id, active)
            BailianLLMClient._raise_if_cancelled(active)
            try:
                parsed = parse_json_content(content)
            except ValueError as exc:
                raise LLMJSONRepairRequired(
                    f"{purpose} returned non-JSON content: {exc}",
                    content=content,
                    parse_error=str(exc),
                    purpose=purpose,
                ) from exc
            if not isinstance(parsed, dict):
                raise LLMClientError(f"{purpose} returned JSON but not an object")
            return parsed
        finally:
            complete_llm_request(active)

    def repair_json_chat(
        self,
        messages: list[dict[str, str]],
        invalid_content: str,
        purpose: str,
        original_error: str,
        request_id: str = "",
    ) -> dict[str, Any]:
        original_payload = next(
            (item.get("content", "") for item in reversed(messages) if item.get("role") == "user"),
            "",
        )
        repair_messages = [{
            "role": "user",
            "content": json.dumps(
                {
                    "original_domain_payload": original_payload,
                    "repair": True,
                    "parse_error": original_error,
                    "invalid_content": invalid_content[:20000],
                    "instruction": "依据原始规划任务，只返回修复后的合法 JSON 对象，不要解释，不要 Markdown，不要省略字段。",
                },
                ensure_ascii=False,
            ),
        }]
        return self.json_chat(repair_messages, purpose=purpose, request_id=request_id)

    def _use_as_tool(
        self,
        runtime_payload: str,
        request_id: str,
        active: _ActiveLLMRequest | None,
    ) -> str:
        payload = {
            "session_id": self.config.session_id,
            "txt": runtime_payload,
            "stream": True,
            "config_variables": [],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            innovation_factory_use_as_tool_url(self.config.endpoint_url),
            data=body,
            headers={
                **request_headers(self.config.api_key, request_id),
                "Accept": "text/event-stream, application/x-ndjson, application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                attach_llm_response(active, response)
                content = parse_innovation_factory_stream(response, active)
        except urllib.error.HTTPError as exc:
            detail = read_http_error(exc)
            raise LLMClientError(f"Innovation Factory use_as_tool HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            if active is not None and active.cancelled.is_set():
                raise LLMRequestCancelled("LLM request was cancelled") from exc
            raise LLMClientError(f"Innovation Factory use_as_tool request failed: {exc}") from exc
        if not content.strip():
            raise LLMClientError("Innovation Factory use_as_tool stream completed without message content")
        return content

    def _cancel_upstream(self, request_id: str) -> dict[str, Any]:
        cancel_url = self.config.cancel_url or self._url("/chatabc/stop")
        payload = {"session_id": self.config.session_id, "action": "stop"}
        return post_stop_command(cancel_url, self.config.api_key, request_id, payload)

    def _url(self, path: str) -> str:
        return f"{innovation_factory_base_url(self.config.endpoint_url)}{path}"


def innovation_factory_base_url(endpoint_url: str) -> str:
    base = endpoint_url.rstrip("/")
    for suffix in (
        "/chatabc/use_as_tool",
        "/use_as_tool",
        "/chatabc/init_session",
        "/chatabc/upload_file",
        "/chatabc/chat",
        "/chatabc/stop",
    ):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def innovation_factory_use_as_tool_url(endpoint_url: str) -> str:
    endpoint = endpoint_url.rstrip("/")
    if endpoint.endswith("/use_as_tool"):
        return endpoint
    return f"{innovation_factory_base_url(endpoint)}/chatabc/use_as_tool"


def innovation_factory_session_id(value: str = "") -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(candidate))
    except ValueError as exc:
        raise LLMConfigError("Innovation Factory session_id must be a valid UUID") from exc


def parse_innovation_factory_stream(response: Any, active: _ActiveLLMRequest | None) -> str:
    current_event = ""
    chunks: list[str] = []
    completed_message = ""
    for raw_line in response:
        if active is not None and active.cancelled.is_set():
            raise LLMRequestCancelled("LLM request was cancelled")
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            line = line.split(":", 1)[1].strip()
        if line == "[DONE]":
            break
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            item = {"content": line}
        if not isinstance(item, dict):
            item = {"content": str(item)}
        event = str(item.get("event") or current_event or "chunk").strip()
        content = stream_content(item)
        if event == "failed":
            raise LLMClientError(f"Innovation Factory use_as_tool failed: {content or item}")
        if event == "message":
            additional_kwargs = item.get("additional_kwargs")
            if isinstance(additional_kwargs, dict):
                if additional_kwargs.get("node_id") == "end":
                    output = nested_value(additional_kwargs, "node_output", "output")
                    if output is not None:
                        completed_message = stream_value_to_text(output)
                        break
            elif content:
                # Keep compatibility with the previous response shape, where
                # the completed message was returned as top-level content.
                completed_message = content
        elif event == "chunk" and content:
            chunks.append(content)
        elif event == "done":
            break
    return completed_message or "".join(chunks)


def parse_openai_compatible_stream(response: Any, active: _ActiveLLMRequest | None) -> str:
    chunks: list[str] = []
    reasoning_characters = 0
    finish_reason = ""
    for raw_line in response:
        if active is not None and active.cancelled.is_set():
            raise LLMRequestCancelled("LLM request was cancelled")
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or line.startswith("event:") or line.startswith(":"):
            continue
        if line.startswith("data:"):
            line = line.split(":", 1)[1].strip()
        if line == "[DONE]":
            break
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LLMClientError(f"Bailian API returned invalid stream JSON: {line[:500]}") from exc
        if not isinstance(item, dict):
            continue
        if item.get("error"):
            raise LLMClientError(f"Bailian API stream failed: {stream_value_to_text(item['error'])[:1000]}")
        choices = item.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            continue
        choice = choices[0]
        delta = choice.get("delta")
        if isinstance(delta, dict) and delta.get("content") is not None:
            chunks.append(stream_value_to_text(delta["content"]))
        if isinstance(delta, dict) and delta.get("reasoning_content") is not None:
            reasoning_characters += len(stream_value_to_text(delta["reasoning_content"]))
        message = choice.get("message")
        if isinstance(message, dict) and message.get("content") is not None:
            chunks.append(stream_value_to_text(message["content"]))
        if choice.get("finish_reason") is not None:
            finish_reason = str(choice.get("finish_reason") or "")
            break
    content = "".join(chunks)
    if not content.strip():
        detail = f"finish_reason={finish_reason or 'unknown'}, reasoning_characters={reasoning_characters}"
        raise LLMClientError(f"Bailian API stream completed without message content ({detail})")
    return content


def stream_value_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def stream_content(item: dict[str, Any]) -> str:
    value = item.get("content")
    if value is None:
        value = nested_value(item, "data", "content")
    if value is None:
        value = item.get("message")
    if value is None:
        return ""
    return stream_value_to_text(value)


def nested_value(value: Any, *path: Any) -> Any:
    current = value
    for key in path:
        try:
            current = current[key]
        except (KeyError, IndexError, TypeError):
            return None
    return current


def request_headers(api_key: str, request_id: str = "") -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


def post_stop_command(
    url: str,
    api_key: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(
        payload or {"action": "stop", "request_id": request_id, "input": {"action": "stop", "request_id": request_id}},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        validate_http_url(url, "cancel_url"),
        data=body,
        headers=request_headers(api_key, request_id),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = getattr(response, "status", 200)
            response.read()
    except urllib.error.HTTPError as exc:
        raise LLMClientError(f"Upstream stop command HTTP {exc.code}: {read_http_error(exc)}") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
        raise LLMClientError(f"Upstream stop command failed: {exc}") from exc
    return {"stop_command_sent": True, "stop_http_status": status}


def read_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")[:1000]
    except Exception:  # noqa: BLE001 - preserve the original HTTP failure.
        return str(exc)


def parse_json_content(content: str) -> Any:
    text = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        extracted = text[start : end + 1]
        if extracted != text:
            candidates.append(extracted)
    repaired_candidates = [repair_common_json_commas(candidate) for candidate in candidates]
    candidates.extend(candidate for candidate in repaired_candidates if candidate not in candidates)
    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError("empty JSON content")


def repair_common_json_commas(text: str) -> str:
    repaired = re.sub(r",(\s*[}\]])", r"\1", text)
    repaired = re.sub(r"([}\]])(\s*\n\s*)([{[])", r"\1,\2\3", repaired)
    repaired = re.sub(
        r'([}\]"0-9])(\s*\n\s*)("[-A-Za-z0-9_\u4e00-\u9fff]+"\s*:)',
        r"\1,\2\3",
        repaired,
    )
    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        return text


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())
