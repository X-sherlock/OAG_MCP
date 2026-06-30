import json


INTENT_ID_MAP = {
    "1": "performance_overview",
    "2": "risk_overview",
    "3": "benchmark_comparison",
    "4": "peer_comparison",
    "5": "fund_profile",
    "6": "fee_analysis",
    "7": "dividend_analysis",
    "8": "holding_analysis",
    "9": "asset_allocation_analysis",
    "10": "fund_comparison",
    "11": "fund_ranking",
    "12": "fund_screening",
    "13": "fund_recommendation",
    "14": "fund_attribute_query",
}


TASK_TYPE_BY_INTENT = {
    "performance_overview": "analyze",
    "risk_overview": "analyze",
    "benchmark_comparison": "compare",
    "peer_comparison": "compare",
    "fund_profile": "profile",
    "fee_analysis": "query",
    "dividend_analysis": "query",
    "holding_analysis": "query",
    "asset_allocation_analysis": "query",
    "fund_comparison": "compare",
    "fund_ranking": "rank",
    "fund_screening": "screen",
    "fund_recommendation": "recommend",
    "fund_attribute_query": "query",
}


ATTR_MAP = {
    "COD_FUND": "fund_code",
    "NAM_FUND": "fund_name",
    "NAM_FUND_SHORT": "fund_short_name",
    "COD_FUND_TYP": "fund_type",
    "COD_FUND_STS": "fund_status",
    "COD_FUND_RSK_LVL": "risk_level",
    "COD_FUND_LIVE_STS": "sale_status",
    "COD_PURC_STS": "purchase_status",
    "COD_REDM_STS": "redemption_status",
    "IND_PENS_FUND": "pension_fund_flag",
    "IND_IDX_FUND": "index_fund_flag",
    "IND_FOF": "fof_flag",
    "IND_ETF": "etf_flag",
    "COD_BONS_TYP": "dividend_mode",
    "AMT_FUND_SCL": "fund_size",
    "DATE_FUND_MKT": "listing_date",
    "DATE_FUND_CRT": "inception_date",
    "最小购买额": "minimum_purchase_amount",
    "最低购买额": "minimum_purchase_amount",
    "最低申购金额": "minimum_purchase_amount",
    "最小申购金额": "minimum_purchase_amount",
    "申购起点": "minimum_purchase_amount",
    "起购金额": "minimum_purchase_amount",
    "AMT_IDV_FST_PURC_MIN": "minimum_purchase_amount",
    "最低认购金额": "minimum_subscription_amount",
    "认购起点": "minimum_subscription_amount",
    "AMT_IDV_FST_SSCR_MIN": "minimum_subscription_amount",
    "最小定投额": "minimum_aip_amount",
    "定投起点": "minimum_aip_amount",
    "AMT_AIP_MIN": "minimum_aip_amount",
    "最大定投额": "maximum_aip_amount",
    "AMT_AIP_MAX": "maximum_aip_amount",
    "VLU_DCNT_PURC": "purchase_discount",
    "VLU_DCNT_AIP": "aip_discount",
    "VLU_DCNT_SSCR": "subscription_discount",
    "购买状态": "purchase_status",
    "申购状态": "purchase_status",
    "是否可购买": "purchase_status",
    "赎回状态": "redemption_status",
    "是否可赎回": "redemption_status",
    "申购折扣": "purchase_discount",
    "申购费率折扣": "purchase_discount",
    "定投折扣": "aip_discount",
    "认购折扣": "subscription_discount",
    "基金规模": "fund_size",
    "成立日期": "inception_date",
    "上市日期": "listing_date",
    "单位净值": "unit_nav",
    "VLU_FUND_NAV": "unit_nav",
    "最新净值": "unit_nav",
    "累计净值": "accumulated_nav",
    "VLU_FUND_NAV_ACML": "accumulated_nav",
    "每万份收益": "ten_thousand_income",
    "AMT_TEN_THOU_EARN": "ten_thousand_income",
    "万份收益": "ten_thousand_income",
    "七日年化": "seven_day_annualized_yield",
    "七日年化收益率": "seven_day_annualized_yield",
    "VLU_SEVEN_DAY_YEAR_RATE": "seven_day_annualized_yield",
    "VLU_SEVN_DAY_YEAR_RATE": "seven_day_annualized_yield",
    "平均年化收益率": "average_annualized_return",
    "VLU_ANNL_MEAN_YLD": "average_annualized_return",
    "收益率": "return_rate",
    "VLU_NAV_GRTH_THIS_DAY": "daily_return",
    "VLU_NAV_GRTH_WEEK": "return_rate",
    "VLU_NAV_GRTH_MTH": "return_rate",
    "VLU_NAV_GRTH_3_MTH": "return_rate",
    "VLU_NAV_GRTH_6_MTH": "return_rate",
    "VLU_NAV_GRTH_YEAR": "return_rate",
    "VLU_NAV_GRTH_2_YEAR": "return_rate",
    "VLU_NAV_GRTH_3_YEAR": "return_rate",
    "VLU_NAV_GRTH_4_YEAR": "return_rate",
    "VLU_NAV_GRTH_5_YEAR": "return_rate",
    "VLU_NAV_GRTH_THIS_YEAR": "return_rate",
    "收益": "return_rate",
    "回报率": "return_rate",
    "涨幅": "return_rate",
    "超额收益": "excess_return",
    "VLU_EX_BM_WEEK": "excess_return",
    "VLU_EX_BM_MTH": "excess_return",
    "VLU_EX_BM_3_MTH": "excess_return",
    "VLU_EX_BM_6_MTH": "excess_return",
    "VLU_EX_BM_YEAR": "excess_return",
    "VLU_EX_BM_2_YEAR": "excess_return",
    "VLU_EX_BM_3_YEAR": "excess_return",
    "VLU_EX_BM_5_YEAR": "excess_return",
    "VLU_EX_BM_CRT": "excess_return",
    "最大回撤": "max_drawdown",
    "VLU_MAX_DD_THIS_YEAR": "max_drawdown",
    "VLU_MAX_DD_MTH": "max_drawdown",
    "VLU_MAX_DD_3_MTH": "max_drawdown",
    "VLU_MAX_DD_6_MTH": "max_drawdown",
    "VLU_MAX_DD_YEAR": "max_drawdown",
    "VLU_MAX_DD_2_YEAR": "max_drawdown",
    "VLU_MAX_DD_3_YEAR": "max_drawdown",
    "VLU_MAX_DD_YEAR_CRT": "max_drawdown",
    "回撤": "max_drawdown",
    "波动率": "volatility",
    "VLU_STD_THIS_YEAR": "volatility",
    "VLU_STD_MTH": "volatility",
    "VLU_STD_3_MTH": "volatility",
    "VLU_STD_6_MTH": "volatility",
    "VLU_STD_YEAR": "volatility",
    "VLU_STD_2_YEAR": "volatility",
    "VLU_STD_3_YEAR": "volatility",
    "VLU_STD_YEAR_CRT": "volatility",
    "波动": "volatility",
    "标准差": "volatility",
    "夏普": "sharpe_ratio",
    "夏普比率": "sharpe_ratio",
    "VLU_SHARP_THIS_YEAR": "sharpe_ratio",
    "VLU_SHARP_MTH": "sharpe_ratio",
    "VLU_SHARP_3_MTH": "sharpe_ratio",
    "VLU_SHARP_6_MTH": "sharpe_ratio",
    "VLU_SHARP_YEAR": "sharpe_ratio",
    "VLU_SHARP_2_YEAR": "sharpe_ratio",
    "VLU_SHARP_3_YEAR": "sharpe_ratio",
    "VLU_SHARP_YEAR_CRT": "sharpe_ratio",
    "同类排名": "rank",
    "排名": "rank",
    "收益率同类排名": "peer_return_rank",
    "ID_RET_KIND_WEEK_RANK": "peer_return_rank",
    "ID_RET_KIND_MTH_RANK": "peer_return_rank",
    "ID_RET_KIND_3_MTH_RANK": "peer_return_rank",
    "ID_RET_KIND_6_MTH_RANK": "peer_return_rank",
    "ID_RET_KIND_YEAR_RANK": "peer_return_rank",
    "ID_RET_KIND_2_YEAR_RANK": "peer_return_rank",
    "ID_RET_KIND_3_YEAR_RANK": "peer_return_rank",
    "ID_RET_KIND_4_YEAR_RANK": "peer_return_rank",
    "ID_RET_KIND_5_YEAR_RANK": "peer_return_rank",
    "最大回撤同类排名": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_THIS_YEAR": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_MTH": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_3_MTH": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_6_MTH": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_YEAR": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_2_YEAR": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_3_YEAR": "peer_drawdown_rank",
    "ID_VLU_MAX_DD_KIND_RANK_CRT": "peer_drawdown_rank",
    "波动率同类排名": "peer_volatility_rank",
    "ID_STD_KIND_RANK_THIS_YEAR": "peer_volatility_rank",
    "ID_STD_KIND_RANK_MTH": "peer_volatility_rank",
    "ID_STD_KIND_RANK_3_MTH": "peer_volatility_rank",
    "ID_STD_KIND_RANK_6_MTH": "peer_volatility_rank",
    "ID_STD_KIND_RANK_YEAR": "peer_volatility_rank",
    "ID_STD_KIND_RANK_2_YEAR": "peer_volatility_rank",
    "ID_STD_KIND_RANK_3_YEAR": "peer_volatility_rank",
    "ID_STD_KIND_RANK_YEAR_CRT": "peer_volatility_rank",
    "夏普比率同类排名": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_THIS_YEAR": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_MTH": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_3_MTH": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_6_MTH": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_YEAR": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_2_YEAR": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_3_YEAR": "peer_sharpe_rank",
    "ID_SHARP_KIND_RANK_CRT": "peer_sharpe_rank",
    "基金经理": "manager_name",
    "基金经理姓名": "manager_name",
    "基金经理从业天数": "manager_tenure_days",
    "从业天数": "manager_tenure_days",
    "管理规模": "manager_scale",
    "任期回报": "manager_term_return",
    "开始管理日期": "management_start_date",
    "NAM_MAGR_1": "manager_name",
    "NAM_MAGR_2": "manager_name",
    "NAM_MAGR_3": "manager_name",
    "NAM_MAGR_4": "manager_name",
    "NAM_MAGR_5": "manager_name",
    "DAYS_OF_MAGR_1": "manager_tenure_days",
    "DAYS_OF_MAGR_2": "manager_tenure_days",
    "DAYS_OF_MAGR_3": "manager_tenure_days",
    "DAYS_OF_MAGR_4": "manager_tenure_days",
    "DAYS_OF_MAGR_5": "manager_tenure_days",
    "AMT_MAGR_SCL_1": "manager_scale",
    "AMT_MAGR_SCL_2": "manager_scale",
    "AMT_MAGR_SCL_3": "manager_scale",
    "AMT_MAGR_SCL_4": "manager_scale",
    "AMT_MAGR_SCL_5": "manager_scale",
    "VLU_MAGR_TERM_RET_1": "manager_term_return",
    "VLU_MAGR_TERM_RET_2": "manager_term_return",
    "VLU_MAGR_TERM_RET_3": "manager_term_return",
    "VLU_MAGR_TERM_RET_4": "manager_term_return",
    "VLU_MAGR_TERM_RET_5": "manager_term_return",
    "DATE_STRT_1": "management_start_date",
    "DATE_STRT_2": "management_start_date",
    "DATE_STRT_3": "management_start_date",
    "DATE_STRT_4": "management_start_date",
    "DATE_STRT_5": "management_start_date",
    "股票资产占比": "stock_asset_ratio",
    "PCT_STOCK_ASSET": "stock_asset_ratio",
    "股票仓位": "stock_asset_ratio",
    "债券资产占比": "bond_asset_ratio",
    "PCT_BOND_ASSET": "bond_asset_ratio",
    "债券仓位": "bond_asset_ratio",
    "现金资产占比": "cash_asset_ratio",
    "PCT_CCY_ASSET": "cash_asset_ratio",
    "现金仓位": "cash_asset_ratio",
    "其他资产占比": "other_asset_ratio",
    "PCT_OTHER_ASSET": "other_asset_ratio",
    "基金资产占比": "fund_asset_ratio",
    "PCT_FUND_ASSET": "fund_asset_ratio",
    "基金公司": "company_name",
    "基金公司名称": "company_name",
    "NAM_CMPY": "company_name",
    "是否ETF": "etf_flag",
    "ETF标识": "etf_flag",
    "是否FOF": "fof_flag",
    "FOF标识": "fof_flag",
    "是否指数基金": "index_fund_flag",
    "指数基金标识": "index_fund_flag",
    "是否养老金产品": "pension_fund_flag",
    "养老金产品标识": "pension_fund_flag",
}


SUPPORTED_ATTRIBUTES = {
    "accumulated_nav", "adjusted_nav", "aip_discount", "alpha", "annualized_return",
    "arithmetic_average_return", "asset_net_value", "asset_total_value",
    "average_annualized_return", "avg_holder_share", "benchmark_name",
    "benchmark_return", "beta", "bond_asset_ratio", "bond_code", "bond_market_value",
    "bond_name", "bond_nav_ratio", "calmar_ratio", "cash_asset_ratio",
    "company_code", "company_name", "custodian", "cvar", "daily_return",
    "dividend_adjusted_return", "dividend_date", "dividend_mode",
    "dividend_per_share", "downside_capture", "downside_deviation",
    "downside_risk", "drawdown", "employee_holder_ratio", "etf_flag",
    "excess_return", "fee_effective_date", "fee_type", "fee_value", "fof_flag",
    "fund_asset_ratio", "fund_code", "fund_name", "fund_short_name", "fund_size",
    "fund_status", "fund_type", "geometric_average_return", "holder_count",
    "holding_industry", "inception_date", "inception_return", "index_fund_flag",
    "individual_holder_ratio", "industry_code", "industry_market_value",
    "industry_name", "industry_nav_ratio", "information_ratio",
    "institutional_holder_ratio", "investment_style", "investment_type",
    "is_etf", "is_fof", "is_index_fund", "is_pension", "issue_date",
    "listing_date", "management_start_date", "manager_id", "manager_name",
    "manager_resume", "manager_scale", "manager_tenure_days",
    "manager_term_return", "maturity_date", "max_drawdown",
    "max_drawdown_peak_date", "max_drawdown_recovery_days",
    "max_drawdown_trough_date", "maximum_aip_amount", "minimum_aip_amount",
    "minimum_purchase_amount", "minimum_redeem_share",
    "minimum_subscription_amount", "nav_date", "news_sentiment",
    "other_asset_ratio", "peer_average", "peer_drawdown_rank",
    "peer_return_rank", "peer_risk_rank", "peer_sharpe_rank",
    "peer_volatility_rank", "pension_fund_flag", "percentile", "policy_impact",
    "purchase_discount", "purchase_status", "rank", "redeem_status",
    "redemption_status", "report_summary", "return_rate", "risk_level",
    "sale_status", "seven_day_annualized_yield", "sharpe_ratio",
    "sortino_ratio", "stable_monthly_dividend", "stable_quarterly_dividend",
    "stable_yearly_dividend", "standard_deviation", "stock_asset_ratio",
    "stock_code", "stock_market_value", "stock_name", "stock_nav_ratio",
    "subscription_discount", "ten_thousand_income", "tracking_error",
    "tracking_index_code", "tracking_index_name", "unit_nav", "upside_capture",
    "var", "volatility", "ytd_return",
}


SUPPORTED_OBJECT_TYPES = {
    "AssetAllocation", "Benchmark", "Dividend", "Fund", "FundCategory",
    "FundCompany", "FundFee", "FundIssue", "FundManager", "FundPosition",
    "FundSet", "HolderStructure", "HoldingBond", "HoldingFund",
    "HoldingIndustry", "HoldingStock", "Index", "Industry", "MoneyFundIncome",
    "NetValue", "News", "PeerRanking", "PerformanceMetric", "PolicyDocument",
    "ResearchReport", "RiskMetric", "SinglePeriodPerformance",
}


OBJECT_TYPE_MAP = {
    "fund": "Fund",
    "基金": "Fund",
    "基金产品": "Fund",
    "FundProduct": "Fund",
    "FundInfo": "Fund",
    "fundset": "FundSet",
    "基金集合": "FundSet",
    "FundUniverse": "FundSet",
}


OPERATOR_MAP = {
    ">": "gt",
    ">=": "gte",
    "<": "lt",
    "<=": "lte",
    "=": "eq",
    "==": "eq",
    "!=": "ne",
    "大于": "gt",
    "高于": "gt",
    "超过": "gt",
    "不低于": "gte",
    "至少": "gte",
    "小于": "lt",
    "低于": "lt",
    "少于": "lt",
    "不超过": "lte",
    "至多": "lte",
    "等于": "eq",
}


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def _strip_json_fence(text):
    value = _text(text)
    if value.startswith("```json"):
        value = value[7:]
    elif value.startswith("```"):
        value = value[3:]
    value = value.strip()
    if value.endswith("```"):
        value = value[:-3]
    return value.strip()


def _extract_json_text(text):
    value = _strip_json_fence(text)
    if value.startswith("{") and value.endswith("}"):
        return value
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        return value[start:end + 1]
    return value


def _parse_semantic_frame(llm_output):
    if isinstance(llm_output, dict):
        parsed = llm_output
    else:
        json_text = _extract_json_text(llm_output)
        try:
            parsed = json.loads(json_text)
        except Exception:
            raise ValueError("LLM语义补全节点没有输出可解析的JSON对象")
        if isinstance(parsed, str):
            parsed = json.loads(_extract_json_text(parsed))
    if not isinstance(parsed, dict):
        raise ValueError("LLM语义补全节点输出必须是JSON对象")
    if isinstance(parsed.get("semantic_frame"), dict):
        envelope = parsed
        parsed = parsed.get("semantic_frame")
        recognition = _dict_or_empty(parsed.get("recognition"))
        if not recognition.get("intentID") and envelope.get("intentID") is not None:
            recognition["intentID"] = envelope.get("intentID")
        if not recognition.get("intent_id") and envelope.get("intent_id") is not None:
            recognition["intent_id"] = envelope.get("intent_id")
        if not recognition.get("reason") and envelope.get("reason") is not None:
            recognition["reason"] = envelope.get("reason")
        if not parsed.get("intent") and envelope.get("intent") is not None:
            parsed["intent"] = envelope.get("intent")
        if not parsed.get("task_type") and envelope.get("task_type") is not None:
            parsed["task_type"] = envelope.get("task_type")
        parsed["recognition"] = recognition
    return parsed


def _dict_or_empty(value):
    if isinstance(value, dict):
        return value
    return {}


def _list_or_empty(value):
    if isinstance(value, list):
        return value
    return []


def _unique_strings(values):
    result = []
    items = _list_or_empty(values)
    for item in items:
        text = _text(item)
        if text and text not in result:
            result.append(text)
    return result


def _normalize_attr(value):
    if isinstance(value, dict):
        if value.get("attribute") is not None:
            value = value.get("attribute")
        elif value.get("attribute_name") is not None:
            value = value.get("attribute_name")
        elif value.get("name") is not None:
            value = value.get("name")
        elif value.get("field") is not None:
            value = value.get("field")
    text = _text(value)
    return ATTR_MAP.get(text, text)


def _supported_attr(value):
    return value in SUPPORTED_ATTRIBUTES


def _normalize_attr_list(values):
    result = []
    items = _list_or_empty(values)
    for item in items:
        attr = _normalize_attr(item)
        if attr and _supported_attr(attr) and attr not in result:
            result.append(attr)
    return result


def _unknown_attrs_from_list(values):
    result = []
    items = _list_or_empty(values)
    for item in items:
        attr = _normalize_attr(item)
        if attr and not _supported_attr(attr) and attr not in result:
            result.append(attr)
    return result


def _intent_from_id(intent_id):
    text = _text(intent_id)
    return INTENT_ID_MAP.get(text, text)


def _normalize_intent(frame_intent, intent_id):
    intent = _text(frame_intent)
    mapped = _intent_from_id(intent_id)
    if intent in INTENT_ID_MAP:
        intent = INTENT_ID_MAP.get(intent)
    if not intent:
        intent = mapped
    if not intent:
        raise ValueError("LLM语义补全节点输出缺少 semantic_frame.intent 或 intentID")
    return intent


def _normalize_task_type(intent, task_type):
    current = _text(task_type)
    if current:
        return current
    return TASK_TYPE_BY_INTENT.get(intent, "query")


def _normalize_target_objects(target_objects, task_type):
    rows = []
    source = _list_or_empty(target_objects)
    for item in source:
        if not isinstance(item, dict):
            continue
        row = {}
        object_type = _text(item.get("object_type"))
        if not object_type:
            object_type = "FundSet" if task_type in ("rank", "screen", "recommend") else "Fund"
        object_type = OBJECT_TYPE_MAP.get(object_type, object_type)
        if object_type not in SUPPORTED_OBJECT_TYPES:
            object_type = "FundSet" if task_type in ("rank", "screen", "recommend") else "Fund"
        row["object_type"] = object_type
        row["instance_ref"] = _dict_or_empty(item.get("instance_ref"))
        role = _text(item.get("role"))
        if not role:
            role = "candidate_set" if object_type.endswith("Set") else "analysis_subject"
        row["role"] = role
        rows.append(row)
    if rows:
        return rows
    if task_type in ("rank", "screen", "recommend"):
        return [{
            "object_type": "FundSet",
            "instance_ref": {"fund_universe": "all_public_funds"},
            "role": "candidate_set",
        }]
    return [{
        "object_type": "Fund",
        "instance_ref": {},
        "role": "analysis_subject",
    }]


def _normalize_filter_rows(rows):
    result = []
    source = _list_or_empty(rows)
    for item in source:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if row.get("attribute") is not None:
            row["attribute"] = _normalize_attr(row.get("attribute"))
        if row.get("attribute_name") is not None and row.get("attribute") is None:
            row["attribute"] = _normalize_attr(row.get("attribute_name"))
        if row.get("attribute") is not None and not _supported_attr(row.get("attribute")):
            continue
        operator = _text(row.get("operator"))
        if operator in OPERATOR_MAP:
            row["operator"] = OPERATOR_MAP.get(operator)
        result.append(row)
    return result


def _normalize_ranking_rows(rows):
    result = []
    source = _list_or_empty(rows)
    for item in source:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if row.get("attribute") is not None:
            row["attribute"] = _normalize_attr(row.get("attribute"))
        if row.get("attribute_name") is not None and row.get("attribute") is None:
            row["attribute"] = _normalize_attr(row.get("attribute_name"))
        if row.get("attribute") is not None and not _supported_attr(row.get("attribute")):
            continue
        direction = _text(row.get("direction")).lower()
        if direction in ("ascending", "升序", "从低到高"):
            row["direction"] = "asc"
        elif direction in ("descending", "降序", "从高到低"):
            row["direction"] = "desc"
        result.append(row)
    return result


def _normalize_comparison(value):
    comparison = _dict_or_empty(value)
    if comparison.get("attributes") is not None:
        comparison["attributes"] = _normalize_attr_list(comparison.get("attributes"))
    return comparison


def _normalize_relation_queries(rows):
    result = []
    source = _list_or_empty(rows)
    for item in source:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if row.get("target_object_type") is not None:
            target_type = _text(row.get("target_object_type"))
            row["target_object_type"] = OBJECT_TYPE_MAP.get(target_type, target_type)
            if row["target_object_type"] not in SUPPORTED_OBJECT_TYPES:
                continue
        if row.get("attribute_name") is not None:
            row["attribute_name"] = _normalize_attr(row.get("attribute_name"))
            if row["attribute_name"] and not _supported_attr(row["attribute_name"]):
                row["attribute_name"] = ""
        result.append(row)
    return result


def _unknown_attrs_from_rows(rows):
    result = []
    source = _list_or_empty(rows)
    for item in source:
        if not isinstance(item, dict):
            continue
        attr = None
        if item.get("attribute") is not None:
            attr = _normalize_attr(item.get("attribute"))
        elif item.get("attribute_name") is not None:
            attr = _normalize_attr(item.get("attribute_name"))
        if attr and not _supported_attr(attr) and attr not in result:
            result.append(attr)
    return result


def _ensure_period_default(frame, task_type):
    attrs = _unique_strings(frame.get("mentioned_attributes"))
    constraints = _dict_or_empty(frame.get("constraints"))
    if constraints.get("period"):
        frame["constraints"] = constraints
        return

    interval_attrs = [
        "return_rate",
        "annualized_return",
        "excess_return",
        "benchmark_return",
        "max_drawdown",
        "volatility",
        "standard_deviation",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "tracking_error",
        "information_ratio",
        "rank",
        "percentile",
        "peer_return_rank",
        "peer_risk_rank",
        "peer_sharpe_rank",
        "peer_drawdown_rank",
        "peer_volatility_rank",
    ]
    need_period = task_type in ("rank", "screen", "recommend")
    if not need_period:
        for attr in attrs:
            if attr in interval_attrs:
                need_period = True
                break
    if need_period:
        constraints["period"] = "1y"
    frame["constraints"] = constraints


def _ensure_report_date_default(frame, task_type):
    constraints = _dict_or_empty(frame.get("constraints"))
    if constraints.get("report_date"):
        frame["constraints"] = constraints
        return
    if task_type in ("holding", "asset_allocation"):
        constraints["report_date"] = "latest"
    intent = _text(frame.get("intent"))
    if intent in ("holding_analysis", "asset_allocation_analysis"):
        constraints["report_date"] = "latest"
    frame["constraints"] = constraints


def _normalize_limit(frame, task_type):
    if frame.get("limit") is not None:
        return
    if task_type in ("rank", "recommend"):
        frame["limit"] = 20
    elif task_type == "screen":
        frame["limit"] = 50


def _normalize_options(frame):
    options = _dict_or_empty(frame.get("options"))
    if "allow_relation_expansion" not in options:
        options["allow_relation_expansion"] = True
    if "allow_peer_expansion" not in options:
        options["allow_peer_expansion"] = True
    if "include_supporting_context" not in options:
        options["include_supporting_context"] = True
    frame["options"] = options


def _first_intent_id(frame, intent_id):
    if _text(intent_id):
        return _text(intent_id)
    if frame.get("intentID") is not None:
        return frame.get("intentID")
    if frame.get("intent_id") is not None:
        return frame.get("intent_id")
    recognition = _dict_or_empty(frame.get("recognition"))
    if recognition.get("intentID") is not None:
        return recognition.get("intentID")
    if recognition.get("intent_id") is not None:
        return recognition.get("intent_id")
    return ""


def _first_reason(frame, reason):
    if _text(reason):
        return _text(reason)
    if frame.get("reason") is not None:
        return frame.get("reason")
    recognition = _dict_or_empty(frame.get("recognition"))
    if recognition.get("reason") is not None:
        return recognition.get("reason")
    return ""


def _normalize_frame(frame, query, intent_id, reason):
    resolved_intent_id = _first_intent_id(frame, intent_id)
    resolved_reason = _first_reason(frame, reason)
    intent = _normalize_intent(frame.get("intent"), resolved_intent_id)
    task_type = _normalize_task_type(intent, frame.get("task_type"))

    frame["domain"] = _text(frame.get("domain")) or "finance_market"
    frame["raw_question"] = _text(frame.get("raw_question")) or _text(query)
    frame["intent"] = intent
    frame["task_type"] = task_type
    frame["target_objects"] = _normalize_target_objects(frame.get("target_objects"), task_type)
    frame["constraints"] = _dict_or_empty(frame.get("constraints"))
    dropped_unknown_attributes = []
    for attr in _unknown_attrs_from_list(frame.get("mentioned_attributes")):
        if attr not in dropped_unknown_attributes:
            dropped_unknown_attributes.append(attr)
    for attr in _unknown_attrs_from_rows(frame.get("filters")):
        if attr not in dropped_unknown_attributes:
            dropped_unknown_attributes.append(attr)
    for attr in _unknown_attrs_from_rows(frame.get("ranking")):
        if attr not in dropped_unknown_attributes:
            dropped_unknown_attributes.append(attr)
    comparison_before = _dict_or_empty(frame.get("comparison"))
    for attr in _unknown_attrs_from_list(comparison_before.get("attributes")):
        if attr not in dropped_unknown_attributes:
            dropped_unknown_attributes.append(attr)
    frame["mentioned_attributes"] = _normalize_attr_list(frame.get("mentioned_attributes"))
    frame["relation_queries"] = _normalize_relation_queries(frame.get("relation_queries"))
    frame["filters"] = _normalize_filter_rows(frame.get("filters"))
    frame["ranking"] = _normalize_ranking_rows(frame.get("ranking"))
    frame["comparison"] = _normalize_comparison(frame.get("comparison"))

    recognition = _dict_or_empty(frame.get("recognition"))
    recognition["intent_id"] = intent
    if _text(resolved_intent_id):
        recognition["intentID"] = _text(resolved_intent_id)
    recognition["reason"] = _text(resolved_reason)
    if dropped_unknown_attributes:
        recognition["dropped_unknown_attributes"] = dropped_unknown_attributes
    frame["recognition"] = recognition

    _ensure_period_default(frame, task_type)
    _ensure_report_date_default(frame, task_type)
    _normalize_limit(frame, task_type)
    _normalize_options(frame)
    return frame


def main(llm_output, query="", intentID="", reason=""):
    semantic_frame = _parse_semantic_frame(llm_output)
    semantic_frame = _normalize_frame(semantic_frame, query, intentID, reason)
    return {
        "semantic_frame": semantic_frame,
        "question": semantic_frame.get("raw_question") or _text(query),
        "domain": "finance_market",
        "user_context": {"permission_scopes": ["fund_public_data:read"]},
        "output_view": "agent",
        "options": {"output_view": "agent"},
    }
