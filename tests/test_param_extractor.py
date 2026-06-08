from __future__ import annotations

from oag_mcp.param_extractor import (
    PERIOD_AND_DATE_RANGE_WARNING,
    PERIOD_AND_TRADING_DAYS_WARNING,
    extract_params,
)


def params(question: str) -> dict:
    """测试辅助函数：只关心参数字典时隐藏 warnings 结构。"""

    return extract_params(question).params


def test_extracts_period_one_year():
    # 覆盖中文“一年”自然周期表达，确保映射为标准 period 编码。
    assert params("分析003095近一年收益率")["period"] == "1y"


def test_extracts_period_six_months_digit():
    # 数字月份和中文月份需要走同一套编码，便于查询能力复用。
    assert params("分析003095近6个月收益率")["period"] == "6m"


def test_extracts_period_past_half_year():
    # “过去半年”是常见口语化表达，不能只支持“近6个月”。
    assert params("分析003095过去半年收益率")["period"] == "6m"


def test_extracts_period_ytd():
    # 今年以来统一映射为 YTD，后续工具可按交易日历解释真实起点。
    assert params("分析003095今年以来收益率")["period"] == "YTD"


def test_extracts_period_since_inception():
    # 成立以来映射为 SI，表示起点依赖具体基金成立日期。
    assert params("分析003095成立以来收益率")["period"] == "SI"


def test_extracts_period_twenty_years_chinese():
    # 长周期中文数字需要被识别，避免只覆盖较短周期。
    assert params("分析003095近二十年收益率")["period"] == "20y"


def test_extracts_period_twenty_years_digit():
    # 同一个业务周期的阿拉伯数字写法也应得到相同编码。
    assert params("分析003095近20年收益率")["period"] == "20y"


def test_extracts_year_since_start_date():
    # “某年以来”只提供 start_date，不强行填充 end_date。
    assert params("分析003095 2024年以来收益率")["start_date"] == "2024-01-01"


def test_extracts_year_range_with_dao():
    # 年份区间会扩展为完整自然年边界。
    result = params("分析003095 2024年到2025年收益率")
    assert result["start_date"] == "2024-01-01"
    assert result["end_date"] == "2025-12-31"


def test_extracts_year_range_with_zhi():
    # “至”和“到”在中文问题里等价，二者都应支持。
    result = params("分析003095 2024年至2025年收益率")
    assert result["start_date"] == "2024-01-01"
    assert result["end_date"] == "2025-12-31"


def test_extracts_iso_date_range():
    # ISO 风格日期区间保持原有年月日，并补齐格式。
    result = params("分析003095 2024-01-01到2024-12-31收益率")
    assert result["start_date"] == "2024-01-01"
    assert result["end_date"] == "2024-12-31"


def test_extracts_slash_date_range():
    # 斜杠日期输入也被规范化为 YYYY-MM-DD。
    result = params("分析003095 2024/01/01到2024/12/31收益率")
    assert result["start_date"] == "2024-01-01"
    assert result["end_date"] == "2024-12-31"


def test_extracts_trading_days():
    # 交易日窗口单独输出 trading_days，不等同于自然周期 period。
    assert params("分析003095近30个交易日收益率")["trading_days"] == 30


def test_extracts_fund_code_from_matched_objects():
    # 对象召回阶段已经解析出的 fund_code 应被参数抽取结果继承。
    result = extract_params(
        "分析003095近一年收益率",
        matched_objects=[
            {
                "object_type": "Fund",
                "object_id": "003095",
                "params": {"fund_code": "003095"},
            }
        ],
    )

    assert result.params["fund_code"] == "003095"
    assert result.params["period"] == "1y"


def test_warns_when_period_and_date_range_coexist():
    # 同时给出自然周期和显式日期区间时不裁决优先级，只透出 warning。
    result = extract_params("003095近一年，2024-01-01到2024-12-31的收益率")

    assert result.params["period"] == "1y"
    assert result.params["start_date"] == "2024-01-01"
    assert result.params["end_date"] == "2024-12-31"
    assert PERIOD_AND_DATE_RANGE_WARNING in result.warnings


def test_warns_when_period_and_trading_days_coexist():
    # 自然周期和交易日周期也存在口径差异，需要提醒后续工具明确优先级。
    result = extract_params("003095近一年近30个交易日收益率")

    assert result.params["period"] == "1y"
    assert result.params["trading_days"] == 30
    assert PERIOD_AND_TRADING_DAYS_WARNING in result.warnings
