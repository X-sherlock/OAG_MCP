import re


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


INTENTS = {
    "performance_overview": {
        "task_type": "analyze",
        "required_attributes": ["return_rate", "benchmark_return", "excess_return", "max_drawdown"],
    },
    "risk_overview": {
        "task_type": "analyze",
        "required_attributes": ["max_drawdown", "volatility"],
    },
    "benchmark_comparison": {
        "task_type": "compare",
        "required_attributes": ["return_rate", "benchmark_return", "excess_return"],
    },
    "peer_comparison": {
        "task_type": "compare",
        "required_attributes": ["rank", "percentile"],
    },
    "fund_profile": {
        "task_type": "profile",
        "required_attributes": ["fund_name", "fund_type", "manager_name", "company_name", "benchmark_name"],
    },
    "fee_analysis": {"task_type": "query", "required_attributes": ["fee_value"]},
    "dividend_analysis": {"task_type": "query", "required_attributes": ["dividend_per_share"]},
    "holding_analysis": {"task_type": "query", "required_attributes": ["stock_name"]},
    "asset_allocation_analysis": {"task_type": "query", "required_attributes": ["stock_asset_ratio"]},
    "fund_comparison": {"task_type": "compare", "required_attributes": ["return_rate"]},
    "fund_ranking": {"task_type": "rank", "required_attributes": ["return_rate"]},
    "fund_screening": {"task_type": "screen", "required_attributes": ["max_drawdown"]},
    "fund_recommendation": {
        "task_type": "recommend",
        "required_attributes": ["return_rate", "max_drawdown"],
    },
}

ATTRIBUTE_ALIASES = {
    "return_rate": ["收益率", "收益", "回报率", "回报", "涨幅"],
    "annualized_return": ["年化收益率", "年化收益", "年化回报"],
    "benchmark_return": ["基准收益率", "基准收益"],
    "excess_return": ["超额收益率", "超额收益"],
    "max_drawdown": ["最大回撤", "回撤"],
    "volatility": ["波动率", "波动"],
    "standard_deviation": ["标准差"],
    "sharpe_ratio": ["夏普比率", "夏普", "Sharpe"],
    "sortino_ratio": ["Sortino", "索提诺"],
    "calmar_ratio": ["Calmar", "卡玛"],
    "tracking_error": ["跟踪误差", "跟踪偏离"],
    "information_ratio": ["信息比率", "信息比"],
    "var": ["VaR", "风险价值"],
    "cvar": ["CVaR", "条件风险价值"],
    "downside_risk": ["下行风险"],
    "rank": ["排名", "名次", "排第几"],
    "percentile": ["百分位", "分位"],
    "peer_return_rank": ["同类收益排名"],
    "peer_risk_rank": ["同类风险排名"],
    "peer_sharpe_rank": ["同类夏普排名"],
    "peer_drawdown_rank": ["同类回撤排名"],
    "fund_name": ["基金名称", "产品名称"],
    "fund_type": ["基金类型", "产品类型"],
    "manager_name": ["基金经理", "经理姓名"],
    "company_name": ["基金公司", "管理人名称"],
    "benchmark_name": ["业绩比较基准", "基准名称"],
    "tracking_index_name": ["跟踪指数", "指数名称"],
    "fee_value": ["费率", "申购费", "赎回费", "管理费", "托管费"],
    "dividend_per_share": ["每份分红", "每股派息", "分红金额"],
    "dividend_date": ["分红日期", "派息日"],
    "stock_name": ["股票持仓", "重仓股", "持仓股票"],
    "stock_nav_ratio": ["股票持仓占比", "股票占比"],
    "bond_name": ["债券持仓", "重仓债券", "持仓债券"],
    "bond_nav_ratio": ["债券持仓占比", "债券占比"],
    "holding_industry": ["持仓行业", "行业配置"],
    "stock_asset_ratio": ["股票仓位", "股票资产占比"],
    "bond_asset_ratio": ["债券仓位", "债券资产占比"],
    "cash_asset_ratio": ["现金仓位", "现金资产占比"],
}

PERIOD_ALIASES = [
    ("20y", ["近二十年", "二十年", "近20年"]),
    ("10y", ["近十年", "十年", "近10年"]),
    ("5y", ["近五年", "五年", "近5年"]),
    ("3y", ["近三年", "三年", "近3年"]),
    ("2y", ["近两年", "两年", "近2年"]),
    ("1y", ["近一年", "最近一年", "一年", "近1年"]),
    ("6m", ["近六月", "六个月", "近6月"]),
    ("3m", ["近三个月", "三个月", "近3月"]),
    ("1m", ["近一月", "一个月", "近1月"]),
    ("1w", ["近一周", "一周", "近1周"]),
    ("ytd", ["今年以来", "本年以来", "YTD"]),
    ("si", ["成立以来", "设立以来", "SI"]),
]

RELATION_RULES = [
    ("managed_by", "FundManager", "manager_name", ["基金经理", "谁管理"]),
    ("issued_by", "FundCompany", "company_name", ["基金公司", "管理人公司"]),
    ("has_benchmark", "Benchmark", "benchmark_name", ["业绩比较基准", "基准名称"]),
    ("belongs_to_category", "FundCategory", "fund_type", ["基金分类", "基金类型"]),
    ("tracks_index", "Index", "tracking_index_name", ["跟踪指数", "跟踪哪个指数"]),
    ("has_fee", "FundFee", "fee_value", ["申购费", "赎回费", "管理费", "托管费"]),
    ("has_dividend", "Dividend", "dividend_per_share", ["分红", "派息"]),
    ("has_position", "FundPosition", "stock_name", ["持仓", "重仓股", "重仓债"]),
    ("has_asset_allocation", "AssetAllocation", "stock_asset_ratio", ["资产配置", "仓位"]),
]


def _unique(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _contains_any(text, words, ignore_case=False):
    source = text
    if ignore_case:
        source = text.lower()
    for word in words:
        candidate = word.lower() if ignore_case else word
        if candidate in source:
            return True
    return False


def _extract_attributes(query):
    matched = []
    lower_query = query.lower()
    for name, aliases in ATTRIBUTE_ALIASES.items():
        if _contains_any(lower_query, aliases, True):
            matched.append(name)
    return _unique(matched)


def _extract_period(query):
    lower_query = query.lower()
    for code, aliases in PERIOD_ALIASES:
        if _contains_any(lower_query, aliases, True):
            return code
    return None


def _extract_report_date(query):
    match = re.search(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})日?", query)
    if match:
        year, month, day = map(int, match.groups())
        return "%04d-%02d-%02d" % (year, month, day)
    if _contains_any(query, ["最新", "当前", "最近一期", "最新一期"]):
        return "latest"
    return None


def _extract_fund_codes(query):
    return _unique(re.findall(r"(?<!\d)(\d{6})(?!\d)", query))


def _extract_limit(query):
    match = re.search(r"(?:前|top\s*)(\d{1,3})", query, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _fund_universe(query):
    mappings = [
        ("bond_funds", ["债券基金", "债基"]),
        ("equity_funds", ["股票基金", "股票型基金"]),
        ("index_funds", ["指数基金", "ETF"]),
        ("money_market_funds", ["货币基金", "货基"]),
        ("mixed_funds", ["混合基金", "混合型基金"]),
    ]
    for universe, aliases in mappings:
        if _contains_any(query, aliases, True):
            return universe
    return "all_public_funds"


def _ranking(query, attributes):
    if not _contains_any(query, [
        "最高", "最低", "最好", "最差", "排名", "排序", "top",
        "收益高", "回报高", "回撤低", "波动低", "夏普高",
    ], True):
        return []
    rows = []
    if "return_rate" in attributes or _contains_any(query, ["收益高", "收益最高", "回报高"]):
        rows.append({"attribute": "return_rate", "direction": "desc"})
    if "max_drawdown" in attributes or "回撤" in query:
        direction = "asc" if _contains_any(query, ["回撤低", "回撤最小", "回撤最低"]) else "desc"
        rows.append({"attribute": "max_drawdown", "direction": direction})
    if "volatility" in attributes or "波动" in query:
        direction = "asc" if _contains_any(query, ["波动低", "波动最小", "波动最低"]) else "desc"
        rows.append({"attribute": "volatility", "direction": direction})
    if "sharpe_ratio" in attributes or "夏普" in query:
        rows.append({"attribute": "sharpe_ratio", "direction": "desc"})
    if rows:
        return rows
    return [{"attribute": attributes[0] if attributes else "return_rate", "direction": "desc"}]


def _filters(query, attributes):
    filters = []
    patterns = [
        (r"(?:低于|小于|不超过|至多)\s*(\d+(?:\.\d+)?)\s*%", "<="),
        (r"(?:高于|大于|不少于|至少)\s*(\d+(?:\.\d+)?)\s*%", ">="),
    ]
    attribute = attributes[0] if attributes else "max_drawdown"
    for pattern, operator in patterns:
        match = re.search(pattern, query)
        if match:
            filters.append({
                "attribute": attribute,
                "operator": operator,
                "value": float(match.group(1)) / 100.0,
            })
            break
    return filters


def _relation_queries(query):
    rows = []
    for relation_type, target_type, attribute, aliases in RELATION_RULES:
        if _contains_any(query, aliases):
            rows.append({
                "relation_type": relation_type,
                "target_object_type": target_type,
                "attribute_name": attribute,
            })
    return rows


def main(query, intentID, reason=""):
    """Code-node entrypoint. Returns variables that can be bound to OAG MCP."""
    query = (query or "").strip()
    intent_id = str(intentID or "").strip()
    intent_id = INTENT_ID_MAP.get(intent_id, intent_id)
    if intent_id not in INTENTS:
        raise ValueError("Unsupported intentID: " + intent_id)

    config = INTENTS[intent_id]
    task_type = config["task_type"]
    explicit_attributes = _extract_attributes(query)
    fund_codes = _extract_fund_codes(query)
    period = _extract_period(query)
    report_date = _extract_report_date(query)

    constraints = {}
    if period:
        constraints["period"] = period
    if report_date:
        constraints["report_date"] = report_date

    if task_type in ("rank", "screen", "recommend"):
        target_objects = [{
            "object_type": "FundSet",
            "instance_ref": {"fund_universe": _fund_universe(query)},
            "role": "candidate_set",
        }]
    else:
        role = "comparison_subject" if task_type == "compare" and len(fund_codes) > 1 else "analysis_subject"
        target_objects = []
        for code in fund_codes:
            target_objects.append({
                "object_type": "Fund",
                "instance_ref": {"fund_code": code},
                "role": role,
            })
        if not target_objects:
            target_objects = [{"object_type": "Fund", "instance_ref": {}, "role": role}]

    ranking = _ranking(query, explicit_attributes) if task_type in ("rank", "recommend") else []
    filters = _filters(query, explicit_attributes)
    limit = _extract_limit(query)

    if task_type in ("rank", "recommend") and not ranking:
        ranking = [{"attribute": "return_rate", "direction": "desc"}]
    if task_type == "screen" and not filters:
        filters = []

    # Current Java planner chooses explicit attributes OR the intent template.
    # With explicit metrics, merge the template's required baseline here.
    mentioned_attributes = []
    if explicit_attributes and task_type not in ("rank", "screen", "recommend"):
        mentioned_attributes = _unique(explicit_attributes + config["required_attributes"])

    comparison = {}
    if task_type == "compare" and len(fund_codes) > 1:
        comparison = {
            "mode": "side_by_side",
            "attributes": explicit_attributes or config["required_attributes"],
            "target_object_policy": "all_targets",
        }

    semantic_frame = {
        "domain": "finance_market",
        "raw_question": query,
        "task_type": task_type,
        "intent": intent_id,
        "target_objects": target_objects,
        "constraints": constraints,
        "mentioned_attributes": mentioned_attributes,
        "relation_queries": _relation_queries(query),
        "filters": filters,
        "ranking": ranking,
        "comparison": comparison,
        "recognition": {
            "intent_id": intent_id,
            "reason": reason or "",
            "explicit_attributes": explicit_attributes,
        },
        "options": {
            "allow_relation_expansion": True,
            "allow_peer_expansion": True,
            "include_supporting_context": True,
        },
    }
    if limit is not None:
        semantic_frame["limit"] = limit

    return {
        "semantic_frame": semantic_frame,
        "question": query,
        "domain": "finance_market",
        "user_context": {"permission_scopes": ["fund_public_data:read"]},
        "output_view": "agent",
        "options": {"output_view": "agent"},
    }
