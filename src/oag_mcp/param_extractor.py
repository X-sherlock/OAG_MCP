from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


FUND_CODE_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


# 当一个问题同时命中多种时间表达时，参数抽取层不直接裁决优先级，而是把风险
# 上报给后续查询工具或编排层处理。
PERIOD_AND_DATE_RANGE_WARNING = "同时识别到周期和日期区间，后续查询工具应明确优先级"
PERIOD_AND_TRADING_DAYS_WARNING = "同时识别到自然周期和交易日周期，后续查询工具应明确优先级"

# 中文问句里的日期表达比较固定，这里用轻量正则覆盖目前的 MVP 场景。
DATE_PATTERN = r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"
YEAR_RANGE_PATTERN = re.compile(r"(?<!\d)(\d{4})年(?:到|至)(\d{4})年")
YEAR_SINCE_PATTERN = re.compile(r"(?<!\d)(\d{4})年以来")
DATE_RANGE_PATTERN = re.compile(rf"{DATE_PATTERN}(?:到|至){DATE_PATTERN}")
TRADING_DAYS_PATTERN = re.compile(r"(?:近|最近|过去)(\d+)个?交易日")

PERIOD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:近|最近|过去)一周"), "1w"),
    (re.compile(r"(?:近|最近|过去)(?:两|二)周"), "2w"),
    (re.compile(r"(?:近|最近|过去)(?:一|1)个?月"), "1m"),
    (re.compile(r"(?:近|最近|过去)(?:三|3)个?月"), "3m"),
    (re.compile(r"(?:近|最近|过去)(?:六|6)个?月|(?:过去)?半年"), "6m"),
    (re.compile(r"(?:近|最近|过去)(?:一|1)年"), "1y"),
    (re.compile(r"(?:近|最近|过去)(?:两|二|2)年"), "2y"),
    (re.compile(r"(?:近|最近|过去)(?:三|3)年"), "3y"),
    (re.compile(r"(?:近|最近|过去)(?:五|5)年"), "5y"),
    (re.compile(r"(?:近|最近|过去)(?:十|10)年"), "10y"),
    (re.compile(r"(?:近|最近|过去)(?:二十|20)年"), "20y"),
    (re.compile(r"今年以来|年初以来|本年以来|今年"), "YTD"),
    (re.compile(r"成立以来至今|成立以来|成立至今"), "SI"),
]


@dataclass(frozen=True)
class ParamExtractionResult:
    """参数抽取结果。

    params 是可直接传给候选查询的结构化参数，warnings 记录歧义或冲突，供 MCP
    响应透出给调用端。
    """

    params: dict[str, Any]
    warnings: list[str]


def extract_params(
    question: str,
    matched_objects: list[dict[str, Any]] | None = None,
) -> ParamExtractionResult:
    """从自然语言问题和已匹配对象中抽取查询参数。

    已匹配对象的 params 先写入结果，例如基金对象会携带 fund_code；随后再解析
    周期、日期区间和交易日数量，保证显式问句中的时间条件能补齐查询必填参数。
    """

    params: dict[str, Any] = {}
    warnings: list[str] = []

    for item in matched_objects or []:
        params.update(item.get("params") or {})

    fund_codes = FUND_CODE_PATTERN.findall(question)
    if fund_codes:
        params["fund_code"] = fund_codes[0]

    period = _extract_period(question)
    if period:
        params["period"] = period

    date_range = _extract_date_range(question)
    if date_range:
        params.update(date_range)

    trading_days = _extract_trading_days(question)
    if trading_days is not None:
        params["trading_days"] = trading_days

    if period and date_range:
        warnings.append(PERIOD_AND_DATE_RANGE_WARNING)
    if period and trading_days is not None:
        warnings.append(PERIOD_AND_TRADING_DAYS_WARNING)

    return ParamExtractionResult(params=params, warnings=warnings)


def _extract_period(question: str) -> str | None:
    """按预定义中文周期短语返回标准周期编码。"""

    for pattern, period in PERIOD_PATTERNS:
        if pattern.search(question):
            return period
    return None


def _extract_date_range(question: str) -> dict[str, str]:
    """识别显式日期区间、年份区间和“某年以来”表达。"""

    match = DATE_RANGE_PATTERN.search(question)
    if match:
        start_year, start_month, start_day, end_year, end_month, end_day = match.groups()
        return {
            "start_date": _format_date(start_year, start_month, start_day),
            "end_date": _format_date(end_year, end_month, end_day),
        }

    match = YEAR_RANGE_PATTERN.search(question)
    if match:
        start_year, end_year = match.groups()
        return {
            "start_date": f"{start_year}-01-01",
            "end_date": f"{end_year}-12-31",
        }

    match = YEAR_SINCE_PATTERN.search(question)
    if match:
        return {"start_date": f"{match.group(1)}-01-01"}

    return {}


def _extract_trading_days(question: str) -> int | None:
    """识别“近 N 个交易日”一类滚动交易日窗口。"""

    match = TRADING_DAYS_PATTERN.search(question)
    if not match:
        return None
    return int(match.group(1))


def _format_date(year: str, month: str, day: str) -> str:
    """把宽松匹配到的年月日规范化为 YYYY-MM-DD。"""

    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
