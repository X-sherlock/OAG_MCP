#!/usr/bin/env python3
"""
Runtime script for get-fund-metric-values.

The script reads structured JSON from stdin, validates the skill contract,
calls the configured Java platform endpoint, and writes a standard JSON result
to stdout.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import requests


SKILL_ID = "get-fund-metric-values"
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

SUPPORTED_PERIODS = {
    "1w",
    "1m",
    "3m",
    "6m",
    "1y",
    "2y",
    "3y",
    "5y",
    "10y",
    "20y",
    "ytd",
    "si",
}

SUPPORTED_ATTRIBUTES = {
    "return_rate",
    "annualized_return",
    "max_drawdown",
    "volatility",
    "standard_deviation",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "var",
    "cvar",
    "downside_risk",
}


class SkillError(Exception):
    """Skill-level failure with a stable message."""


class JavaApiError(SkillError):
    """Java API integration failure."""


def make_output(
    *,
    success: bool,
    message: str,
    input_payload: Optional[Mapping[str, Any]] = None,
    facts: Optional[List[Mapping[str, Any]]] = None,
    missing_attributes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "message": message,
        "skill_id": SKILL_ID,
        "input": dict(input_payload or {}),
        "facts": list(facts or []),
        "missing_attributes": list(missing_attributes or []),
    }


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SkillError("config.json not found")

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as exc:
        raise SkillError(f"config.json is not valid JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise SkillError("config.json must contain a JSON object")

    endpoints = config.get("endpoints")
    if not isinstance(endpoints, dict):
        raise SkillError("config.json must contain an endpoints object")

    endpoint = endpoints.get(SKILL_ID)
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise SkillError(f"config.json endpoints.{SKILL_ID} is required")

    return config


def parse_stdin() -> Dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise SkillError("Input JSON is empty")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SkillError(f"Input is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise SkillError("Input JSON must be an object")

    return payload


def validate_and_normalize_input(payload: Mapping[str, Any]) -> Dict[str, Any]:
    fund_code = payload.get("fund_code")
    if not isinstance(fund_code, str) or not fund_code.strip():
        raise SkillError("fund_code is required and must be a non-empty string")

    period = payload.get("period")
    if not isinstance(period, str) or not period.strip():
        raise SkillError("period is required and must be a non-empty string")
    period = period.strip()
    if period not in SUPPORTED_PERIODS:
        supported = ", ".join(sorted(SUPPORTED_PERIODS))
        raise SkillError(f"Unsupported period: {period}. Supported periods: {supported}")

    attributes = payload.get("attributes")
    if not isinstance(attributes, list) or not attributes:
        raise SkillError("attributes is required and must be a non-empty array")

    invalid_type_indexes = [
        str(index)
        for index, item in enumerate(attributes)
        if not isinstance(item, str) or not item.strip()
    ]
    if invalid_type_indexes:
        raise SkillError(
            "attributes must contain only non-empty strings; invalid indexes: "
            + ", ".join(invalid_type_indexes)
        )

    normalized_attributes = [item.strip() for item in attributes]
    unsupported = [item for item in normalized_attributes if item not in SUPPORTED_ATTRIBUTES]
    if unsupported:
        raise SkillError(
            "Unsupported attributes: "
            + ", ".join(unsupported)
            + ". Supported attributes: "
            + ", ".join(sorted(SUPPORTED_ATTRIBUTES))
        )

    return {
        "fund_code": fund_code.strip(),
        "period": period,
        "attributes": normalized_attributes,
    }


def call_java_api(config: Mapping[str, Any], request_payload: Mapping[str, Any]) -> Dict[str, Any]:
    endpoint = config["endpoints"][SKILL_ID]
    timeout = config.get("timeout_seconds", 15)
    try:
        timeout_seconds = int(timeout)
    except (TypeError, ValueError) as exc:
        raise SkillError("config.json timeout_seconds must be an integer") from exc

    headers = {"Content-Type": "application/json"}
    token = os.environ.get("FUND_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=request_payload,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise JavaApiError(f"Java API request failed: {exc}") from exc

    if response.status_code != 200:
        body = response.text.strip()
        if len(body) > 500:
            body = body[:500] + "..."
        raise JavaApiError(
            f"Java API returned non-200 status: {response.status_code}; body: {body}"
        )

    try:
        result = response.json()
    except ValueError as exc:
        body = response.text.strip()
        if len(body) > 500:
            body = body[:500] + "..."
        raise JavaApiError(f"Java API returned non-JSON response: {body}") from exc

    if not isinstance(result, dict):
        raise JavaApiError("Java API response JSON must be an object")

    return result


def normalize_java_result(
    api_result: Mapping[str, Any], request_payload: Mapping[str, Any]
) -> Dict[str, Any]:
    code = str(api_result.get("code", ""))
    message = str(api_result.get("message", "")) or "success"

    if code != "0":
        raise JavaApiError(f"Java API returned failure code: {code}; message: {message}")

    data = api_result.get("data")
    if data is None:
        return make_output(
            success=True,
            message=message,
            input_payload=request_payload,
            facts=[],
            missing_attributes=list(request_payload.get("attributes", [])),
        )

    if not isinstance(data, dict):
        raise JavaApiError("Java API data field must be an object")

    facts = data.get("facts", [])
    if facts is None:
        facts = []
    if not isinstance(facts, list):
        raise JavaApiError("Java API data.facts must be an array")

    missing_attributes = data.get("missing_attributes", [])
    if missing_attributes is None:
        missing_attributes = []
    if not isinstance(missing_attributes, list):
        raise JavaApiError("Java API data.missing_attributes must be an array")

    sanitized_missing = [str(item) for item in missing_attributes]

    return make_output(
        success=True,
        message=message,
        input_payload=request_payload,
        facts=facts,
        missing_attributes=sanitized_missing,
    )


def main() -> int:
    input_payload: Dict[str, Any] = {}
    try:
        input_payload = parse_stdin()
        request_payload = validate_and_normalize_input(input_payload)
        config = load_config()
        api_result = call_java_api(config, request_payload)
        output = normalize_java_result(api_result, request_payload)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        try:
            sanitized_input = {}
            if isinstance(input_payload, dict):
                sanitized_input = {
                    key: input_payload[key]
                    for key in ("fund_code", "period", "attributes")
                    if key in input_payload
                }
            output = make_output(
                success=False,
                message=str(exc),
                input_payload=sanitized_input,
                facts=[],
                missing_attributes=[],
            )
            print(json.dumps(output, ensure_ascii=False, indent=2))
        except Exception:
            fallback = make_output(
                success=False,
                message="Unexpected skill failure",
                input_payload={},
                facts=[],
                missing_attributes=[],
            )
            print(json.dumps(fallback, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
