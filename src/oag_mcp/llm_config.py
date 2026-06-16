from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ENV_FILE_NAME = ".env"


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str
    base_url: str
    timeout_seconds: float
    temperature: float
    enabled: bool

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.api_key)

    def status(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key),
            "base_url_configured": bool(self.base_url),
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
            "message_zh": "LLM 已配置，可用于候选事实选择。"
            if self.configured
            else "LLM 未配置或未启用；rule selector 可继续离线运行。",
        }


def load_llm_config(project_root: Path | None = None) -> LLMConfig:
    """Load OAG LLM settings from .env and environment variables.

    Values already present in the process environment win over .env values.
    The API key is never exposed by this module except as the in-process value
    needed by the LLM client.
    """

    values = _read_dotenv(project_root)
    return LLMConfig(
        provider=_config_value("OAG_LLM_PROVIDER", values, "bailian"),
        model=_config_value("OAG_LLM_MODEL", values, "qwen3.7-max-2026-06-08"),
        api_key=_config_value("OAG_LLM_API_KEY", values, ""),
        base_url=_config_value(
            "OAG_LLM_BASE_URL",
            values,
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        ),
        timeout_seconds=_float_value("OAG_LLM_TIMEOUT_SECONDS", values, 60.0),
        temperature=_float_value("OAG_LLM_TEMPERATURE", values, 0.1),
        enabled=_bool_value("OAG_LLM_ENABLED", values, True),
    )


def _config_value(name: str, values: dict[str, str], default: str) -> str:
    value = os.getenv(name)
    if value is None:
        value = values.get(name, default)
    return str(value or "").strip()


def _float_value(name: str, values: dict[str, str], default: float) -> float:
    value = _config_value(name, values, str(default))
    try:
        return float(value)
    except ValueError:
        return default


def _bool_value(name: str, values: dict[str, str], default: bool) -> bool:
    value = _config_value(name, values, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "on", "enabled"}


def _read_dotenv(project_root: Path | None) -> dict[str, str]:
    root = project_root or Path.cwd()
    env_path = root / ENV_FILE_NAME
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values
