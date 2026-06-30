from __future__ import annotations

import json
import re
from typing import Any


PERIOD_RULES: list[tuple[str, str]] = [
    (r"近(?:一|1)周|一周|最近一周", "1w"),
    (r"近(?:两|2)周|两周|最近两周", "2w"),
    (r"近(?:一|1)个?月|一个月|最近一个月", "1m"),
    (r"近(?:三|3)个?月|三个月|最近三个月", "3m"),
    (r"近(?:半|六|6)年?个?月|半年|最近半年", "6m"),
    (r"近(?:十二|12)个?月|过去12个月", "1y"),
    (r"近(?:一|1)年|一年|过去一年|最近一年", "1y"),
    (r"近(?:两|2)年|两年", "2y"),
    (r"近(?:三|3)年|三年", "3y"),
    (r"近(?:五|5)年|五年", "5y"),
    (r"近(?:十|10)年|十年", "10y"),
    (r"近(?:二十|20)年|二十年", "20y"),
    (r"今年以来|本年以来|\bYTD\b", "ytd"),
    (r"成立以来|设立以来|\bSI\b", "si"),
    (r"最近20个交易日", "20d"),
    (r"最近60个交易日", "60d"),
]


ATTRIBUTE_RULES: list[tuple[str, str]] = [
    ("annualized_return", r"年化收益|年化回报"),
    ("return_rate", r"收益率|收益|回报率|回报|涨幅|涨了|涨得|赚钱|表现"),
    ("benchmark_return", r"基准收益|业绩基准收益|沪深300|中证500|中证偏股基金指数|大盘|市场"),
    ("excess_return", r"超额收益|跑赢|跑输|战胜|优势|强多少|高多少"),
    ("max_drawdown", r"最大回撤|回撤|跌得|下跌|抗跌|跌了|跌幅"),
    ("drawdown", r"连续下跌"),
    ("max_drawdown_peak_date", r"回撤发生|峰值"),
    ("max_drawdown_trough_date", r"回撤发生|谷值"),
    ("max_drawdown_recovery_days", r"修复.*多久|恢复.*多久"),
    ("volatility", r"波动率|波动|稳不稳|更稳|稳定|激进"),
    ("standard_deviation", r"标准差"),
    ("sharpe_ratio", r"夏普|Sharpe|性价比"),
    ("calmar_ratio", r"卡玛|Calmar|收益回撤比"),
    ("tracking_error", r"跟踪误差|走势差异|跟踪偏离"),
    ("information_ratio", r"信息比率|信息比"),
    ("downside_risk", r"下行风险"),
    ("rank", r"排名|排第几|排行|靠前|前10%|前20%"),
    ("percentile", r"分位|百分位|前10%|前20%"),
    ("peer_return_rank", r"同类收益排名|收益排名"),
    ("peer_risk_rank", r"风险控制排名|风险排名|回撤排名"),
    ("peer_sharpe_rank", r"夏普.*排名|夏普.*同类"),
    ("peer_drawdown_rank", r"回撤.*同类|同类.*回撤"),
    ("peer_average", r"同类平均|同类中位数"),
    ("fund_name", r"基金名称|产品名称"),
    ("fund_type", r"基金类型|什么基金类型|分类|品种"),
    ("fund_size", r"基金规模|规模"),
    ("inception_date", r"成立日期|什么时候成立"),
    ("manager_name", r"基金经理|经理是谁"),
    ("company_name", r"基金公司|哪家|管理人"),
    ("benchmark_name", r"业绩比较基准|比较基准|基准是什么|基准名称"),
    ("tracking_index_name", r"跟踪的指数|跟踪指数"),
    ("investment_type", r"投资范围|投资类型"),
    ("stock_name", r"前十大持仓|重仓|股票|持仓"),
    ("stock_nav_ratio", r"持仓占比|股票占比"),
    ("stock_asset_ratio", r"股票仓位|股票资产"),
    ("bond_asset_ratio", r"债券仓位|债券资产"),
    ("cash_asset_ratio", r"现金仓位|现金资产"),
    ("holding_industry", r"行业配置|行业"),
    ("fee_value", r"费率|申购费|赎回费|管理费|托管费"),
    ("fee_type", r"申购费|赎回费|管理费|托管费"),
    ("dividend_per_share", r"分红|派息"),
    ("dividend_date", r"分红.*时候|最近一次分红|分红日期"),
    ("risk_level", r"风险等级|风险偏好|稳健|低风险|风险大"),
    ("report_summary", r"公告|研报"),
    ("news_sentiment", r"新闻"),
]


RELATION_RULES: list[tuple[str, str, str, str]] = [
    ("managed_by", "FundManager", "manager_name", r"基金经理|经理是谁"),
    ("issued_by", "FundCompany", "company_name", r"基金公司|管理人"),
    ("has_benchmark", "Benchmark", "benchmark_name", r"业绩比较基准|比较基准|基准"),
    ("belongs_to_category", "FundCategory", "fund_type", r"基金类型|分类|品种|同类"),
    ("tracks_index", "Index", "tracking_index_name", r"跟踪的指数|跟踪指数"),
    ("has_fee", "FundFee", "fee_value", r"费率|申购费|赎回费|管理费|托管费"),
    ("has_dividend", "Dividend", "dividend_per_share", r"分红|派息"),
    ("has_position", "FundPosition", "stock_name", r"持仓|重仓|股票|债券|行业配置"),
    ("has_asset_allocation", "AssetAllocation", "stock_asset_ratio", r"资产配置|仓位"),
]


INTENT_DEFAULTS: dict[str, dict[str, Any]] = {
    "performance_overview": {"task_type": "analyze", "attrs": ["return_rate", "benchmark_return", "excess_return", "max_drawdown"]},
    "risk_overview": {"task_type": "analyze", "attrs": ["max_drawdown", "volatility"]},
    "benchmark_comparison": {"task_type": "compare", "attrs": ["return_rate", "benchmark_return", "excess_return"]},
    "peer_comparison": {"task_type": "compare", "attrs": ["rank", "percentile", "peer_average"]},
    "fund_profile": {"task_type": "profile", "attrs": ["fund_name", "fund_type", "manager_name", "company_name", "benchmark_name"]},
    "fee_analysis": {"task_type": "query", "attrs": ["fee_value"]},
    "dividend_analysis": {"task_type": "query", "attrs": ["dividend_per_share", "dividend_date"]},
    "holding_analysis": {"task_type": "query", "attrs": ["stock_name", "stock_nav_ratio"]},
    "asset_allocation_analysis": {"task_type": "query", "attrs": ["stock_asset_ratio", "bond_asset_ratio", "cash_asset_ratio"]},
    "fund_comparison": {"task_type": "compare", "attrs": ["return_rate"]},
    "fund_ranking": {"task_type": "rank", "attrs": ["return_rate"]},
    "fund_screening": {"task_type": "screen", "attrs": ["max_drawdown"]},
    "fund_recommendation": {"task_type": "recommend", "attrs": ["return_rate", "max_drawdown"]},
}


def semantic_frame_for(question: str, category: str = "") -> dict[str, Any]:
    task_type = infer_task_type(question, category)
    intent = infer_intent(question, category, task_type)
    fund_codes = extract_fund_codes(question)
    attrs = infer_attributes(question, category, intent, task_type)
    constraints = infer_constraints(question, category)
    target_objects = infer_targets(question, category, task_type, fund_codes)
    relation_queries = infer_relation_queries(question, intent)
    ranking = infer_ranking(question, task_type, attrs)
    filters = infer_filters(question, task_type, attrs)
    comparison = infer_comparison(question, task_type, fund_codes, attrs)
    limit = infer_limit(question, task_type)

    if not attrs:
        attrs = list(INTENT_DEFAULTS.get(intent, {}).get("attrs") or [])
    mentioned_attributes = [] if task_type in {"rank", "screen", "recommend"} else unique(attrs)

    frame: dict[str, Any] = {
        "domain": "finance_market",
        "raw_question": question,
        "task_type": task_type,
        "intent": intent,
        "target_objects": target_objects,
        "constraints": constraints,
        "mentioned_attributes": mentioned_attributes,
        "relation_queries": relation_queries,
        "filters": filters,
        "ranking": ranking,
        "comparison": comparison,
        "options": {
            "allow_relation_expansion": True,
            "allow_peer_expansion": True,
            "include_supporting_context": True,
        },
    }
    if limit is not None:
        frame["limit"] = limit
    return frame


def infer_task_type(question: str, category: str = "") -> str:
    if re.search(r"基金经理|基金公司|基金类型|基金规模|成立日期|跟踪的指数|投资范围|评级|公告|新闻|持仓|重仓|仓位|行业配置|申购费|赎回费|分红|派息", question):
        return "profile" if re.search(r"画像|概况|基本信息", question) else "query"
    if category == "筛选推荐类":
        return "recommend" if re.search(r"推荐|适合|收益高、波动低|稳健", question) else "screen"
    fund_codes = extract_fund_codes(question)
    if re.search(r"推荐|适合买吗|稳健型投资|长期持有价值|稳赚不赔", question):
        return "recommend"
    if not fund_codes and re.search(r"收益高、波动低|适合.*基金|稳健投资者", question):
        return "recommend"
    if re.search(r"找出|筛选|选出|过滤", question):
        return "screen"
    if re.search(r"排名前|排行|表现排名|哪个.*最高|前\d+%|前[一二三四五六七八九十]+", question) and not re.search(r"同类排名|排名如何|排名是多少|排第几|前十大持仓|前十.*持仓", question):
        return "rank"
    if re.search(r"比较|对比|相比|相对|跑赢|跑输|基准|沪深300|中证500|同类|和\d{6}|与\d{6}|谁的|哪个.*(?:更|最高|好|强)", question):
        return "compare"
    if re.search(r"画像|概况|基本信息", question):
        return "profile"
    if re.search(r"分析|表现|怎么样|如何|好不好|高不高|大不大|稳不稳|行不行", question):
        return "analyze"
    return "query"


def infer_intent(question: str, category: str, task_type: str) -> str:
    if category == "筛选推荐类":
        return "fund_recommendation" if task_type == "recommend" else "fund_screening"
    if task_type == "rank":
        return "fund_ranking"
    if task_type == "screen":
        return "fund_screening"
    if task_type == "recommend":
        return "fund_recommendation"
    if re.search(r"申购费|赎回费|费率|费用", question):
        return "fee_analysis"
    if re.search(r"分红|派息", question):
        return "dividend_analysis"
    if re.search(r"持仓|重仓|行业配置", question):
        return "holding_analysis"
    if re.search(r"仓位|资产配置|股票资产|债券资产|现金资产", question):
        return "asset_allocation_analysis"
    if re.search(r"基金经理|基金公司|基金类型|基金规模|成立日期|跟踪的指数|投资范围|评级|公告|新闻", question):
        return "fund_profile"
    if re.search(r"沪深300|中证500|中证偏股|基准|跑赢|跑输|超额|跟踪误差|信息比率|大盘|市场", question):
        return "benchmark_comparison"
    if re.search(r"同类|排名|分位|中位数", question):
        return "peer_comparison"
    codes = extract_fund_codes(question)
    if task_type == "compare" and len(codes) > 1:
        return "fund_comparison"
    if re.search(r"风险|回撤|波动|夏普|卡玛|下行|稳|激进|低风险", question):
        return "risk_overview"
    return "performance_overview"


def extract_fund_codes(question: str) -> list[str]:
    return unique(re.findall(r"(?<!\d)(\d{6})(?!\d)", question))


def extract_fund_name(question: str) -> str | None:
    quoted = re.search(r"[“\"']([^”\"']{2,40})[”\"']", question)
    if quoted:
        name = quoted.group(1).strip()
        return None if looks_like_non_fund_name(name) else name
    if re.search(r"这只基金|这基金|不存在基金", question):
        return None
    prefix = re.search(r"^([\u4e00-\u9fa5A-Za-z0-9]{2,40}?)(?:近|今年|去年|从|收益|最大|风险|和|有没有|跟踪|重仓|股票|债券|行业|分红|费率|成立|基金经理|基金公司|的)", question)
    if prefix:
        name = prefix.group(1).strip("，,。？? ")
        if name and not looks_like_non_fund_name(name):
            return name
    return None


def looks_like_non_fund_name(value: str) -> bool:
    if not value or re.fullmatch(r"\d+", value):
        return True
    if re.search(r"帮我|看看|查询|分析|推荐|找出|筛选", value):
        return True
    return bool(re.fullmatch(r"(?:近|过去|最近)?(?:一|二|三|四|五|六|七|八|九|十|十二|1|2|3|4|5|6|7|8|9|10|12)?(?:天|周|个月|月|年|季度)|今年以来|成立以来|YTD|SI", value, flags=re.IGNORECASE))


def infer_targets(question: str, category: str, task_type: str, fund_codes: list[str]) -> list[dict[str, Any]]:
    if not fund_codes and re.search(r"这只基金|这基金", question):
        role = "comparison_subject" if task_type == "compare" else "analysis_subject"
        return [{"object_type": "Fund", "instance_ref": {}, "role": role}]
    if task_type in {"rank", "screen", "recommend"}:
        return [{"object_type": "FundSet", "instance_ref": {"fund_universe": fund_universe(question)}, "role": "candidate_set"}]
    role = "comparison_subject" if task_type == "compare" and len(fund_codes) > 1 else "analysis_subject"
    if fund_codes:
        return [{"object_type": "Fund", "instance_ref": {"fund_code": code}, "role": role} for code in fund_codes]
    fund_name = extract_fund_name(question)
    if fund_name:
        return [{"object_type": "Fund", "instance_ref": {"fund_name": fund_name}, "role": role}]
    return [{"object_type": "Fund", "instance_ref": {}, "role": role}]


def fund_universe(question: str) -> str:
    if re.search(r"主动权益", question):
        return "active_equity_funds"
    if re.search(r"权益|股票", question):
        return "equity_funds"
    if re.search(r"债券|债基", question):
        return "bond_funds"
    if re.search(r"指数|ETF", question):
        return "index_funds"
    if re.search(r"混合", question):
        return "mixed_funds"
    return "all_public_funds"


def infer_constraints(question: str, category: str = "") -> dict[str, Any]:
    constraints: dict[str, Any] = {}
    for pattern, code in PERIOD_RULES:
        if re.search(pattern, question, re.IGNORECASE):
            constraints["period"] = code
            break
    range_match = re.search(r"从(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})日?到(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})日?", question)
    if range_match:
        y1, m1, d1, y2, m2, d2 = map(int, range_match.groups())
        constraints["date_range"] = {"start_date": f"{y1:04d}-{m1:02d}-{d1:02d}", "end_date": f"{y2:04d}-{m2:02d}-{d2:02d}"}
        constraints.setdefault("period", "custom")
    if "2025年上半年" in question:
        constraints["date_range"] = {"start_date": "2025-01-01", "end_date": "2025-06-30"}
        constraints.setdefault("period", "custom")
    if "去年全年" in question:
        constraints["date_range"] = {"relative": "last_calendar_year"}
        constraints.setdefault("period", "last_year")
    if re.search(r"最新|当前|最近一次", question) or re.search(r"持仓|仓位|资产配置", question):
        constraints.setdefault("report_date", "latest")
    if re.search(r"明天|未来|2099|近100年|必须保证|稳赚不赔|一定会涨|预测明天", question):
        constraints["test_flag"] = "invalid_or_future_or_compliance_risk"
    return constraints


def infer_attributes(question: str, category: str, intent: str, task_type: str) -> list[str]:
    attrs: list[str] = []
    for name, pattern in ATTRIBUTE_RULES:
        if re.search(pattern, question, re.IGNORECASE):
            attrs.append(name)
    if re.search(r"股票仓位|债券仓位|现金仓位|资产配置|股票资产|债券资产|现金资产", question):
        attrs = [item for item in attrs if item not in {"stock_name", "stock_nav_ratio", "bond_name", "bond_nav_ratio", "holding_industry"}]
    if "风险收益" in question:
        attrs.extend(["return_rate", "max_drawdown", "volatility", "sharpe_ratio"])
    if "高收益低回撤" in question or "收益高、波动低" in question:
        attrs.extend(["return_rate", "max_drawdown", "volatility"])
    if "谁表现更好" in question or "哪个收益" in question:
        attrs.append("return_rate")
    if "哪个更稳" in question:
        attrs.extend(["max_drawdown", "volatility"])
    if "适合低风险" in question or "稳健" in question:
        attrs.extend(["max_drawdown", "volatility", "risk_level"])
    if "同类" in question and not any(a in attrs for a in ["rank", "percentile", "peer_average"]):
        attrs.extend(["rank", "percentile", "peer_average"])
    if "基准" in question or "沪深300" in question or "中证500" in question:
        attrs.extend(["benchmark_return", "excess_return"])
    if task_type in {"rank", "screen", "recommend"} and not attrs:
        attrs.extend(INTENT_DEFAULTS.get(intent, {}).get("attrs") or ["return_rate"])
    return unique(attrs)


def infer_relation_queries(question: str, intent: str) -> list[dict[str, Any]]:
    rows = []
    for relation_type, target_type, attribute, pattern in RELATION_RULES:
        if re.search(pattern, question):
            if relation_type == "has_position" and re.search(r"股票仓位|债券仓位|现金仓位|资产配置|股票资产|债券资产|现金资产", question):
                continue
            rows.append({"relation_type": relation_type, "target_object_type": target_type, "attribute_name": attribute})
    if intent == "peer_comparison" and not any(row["relation_type"] == "belongs_to_category" for row in rows):
        rows.append({"relation_type": "belongs_to_category", "target_object_type": "FundCategory", "attribute_name": "fund_type"})
    if intent == "benchmark_comparison" and not any(row["relation_type"] == "has_benchmark" for row in rows):
        rows.append({"relation_type": "has_benchmark", "target_object_type": "Benchmark", "attribute_name": "benchmark_name"})
    return rows


def infer_ranking(question: str, task_type: str, attrs: list[str]) -> list[dict[str, Any]]:
    if task_type not in {"rank", "recommend"}:
        return []
    rows = []
    if re.search(r"收益|表现|年化", question):
        rows.append({"attribute": "return_rate", "direction": "desc"})
    if re.search(r"回撤.*小|回撤.*低|低回撤|回撤较小|后50%", question):
        rows.append({"attribute": "max_drawdown", "direction": "asc"})
    if re.search(r"波动低|稳健|稳定", question):
        rows.append({"attribute": "volatility", "direction": "asc"})
    if re.search(r"夏普", question):
        rows.append({"attribute": "sharpe_ratio", "direction": "desc"})
    if re.search(r"卡玛", question):
        rows.append({"attribute": "calmar_ratio", "direction": "desc"})
    if re.search(r"信息比率", question):
        rows.append({"attribute": "information_ratio", "direction": "desc"})
    if not rows and attrs:
        rows.append({"attribute": attrs[0], "direction": "desc"})
    return rows or [{"attribute": "return_rate", "direction": "desc"}]


def infer_filters(question: str, task_type: str, attrs: list[str]) -> list[dict[str, Any]]:
    if task_type not in {"screen", "recommend"}:
        return []
    rows = []
    for attr, alias in [("max_drawdown", r"最大回撤|回撤"), ("return_rate", r"收益率|年化收益率|收益"), ("volatility", r"波动")]:
        match = re.search(rf"(?:{alias}).*?(小于|低于|不超过|大于|高于|超过)\s*(\d+(?:\.\d+)?)\s*%", question)
        if match:
            op_text, value = match.groups()
            rows.append({"attribute": attr, "operator": "<=" if op_text in {"小于", "低于", "不超过"} else ">=", "value": float(value) / 100.0})
    if "收益率大于20%" in question:
        rows.append({"attribute": "return_rate", "operator": ">=", "value": 0.2})
    if "年化收益率大于15%" in question:
        rows.append({"attribute": "annualized_return", "operator": ">=", "value": 0.15})
    if "前10%" in question:
        rows.append({"attribute": "percentile", "operator": "<=", "value": 0.1})
    if "前20%" in question:
        rows.append({"attribute": "percentile", "operator": "<=", "value": 0.2})
    if "后50%" in question:
        rows.append({"attribute": "peer_drawdown_rank", "operator": ">=", "value": 0.5})
    if "回撤较小" in question or "低回撤" in question:
        rows.append({"attribute": "max_drawdown", "operator": "<=", "value": 0.1})
    if "波动低" in question:
        rows.append({"attribute": "volatility", "operator": "<=", "value": 0.15})
    return unique_dicts(rows)


def infer_comparison(question: str, task_type: str, fund_codes: list[str], attrs: list[str]) -> dict[str, Any]:
    if task_type != "compare":
        return {}
    comparison: dict[str, Any] = {"mode": "side_by_side", "attributes": unique(attrs or ["return_rate"]), "target_object_policy": "all_targets"}
    if re.search(r"沪深300|中证500|中证偏股基金指数|大盘|市场|基准", question):
        comparison["benchmark_refs"] = benchmark_refs(question)
    if re.search(r"同类|中位数|平均", question):
        comparison["peer_context"] = True
    return comparison


def benchmark_refs(question: str) -> list[dict[str, str]]:
    refs = [{"benchmark_name": name} for name in ["沪深300", "中证500", "中证偏股基金指数"] if name in question]
    if not refs and re.search(r"基准|大盘|市场", question):
        refs.append({"benchmark_name": "semantic_or_default_benchmark"})
    return refs


def infer_limit(question: str, task_type: str) -> int | None:
    if task_type not in {"rank", "screen", "recommend"}:
        return None
    match = re.search(r"前\s*(\d+)", question, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"前([一二三四五六七八九十]+)", question)
    if match:
        return chinese_number(match.group(1))
    return 10 if task_type == "recommend" else 20


def chinese_number(value: str) -> int:
    mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if value == "十":
        return 10
    if value.startswith("十"):
        return 10 + mapping.get(value[1:], 0)
    if "十" in value:
        tens, ones = value.split("十", 1)
        return mapping.get(tens, 1) * 10 + mapping.get(ones, 0)
    return mapping.get(value, 10)


def unique(values: list[Any]) -> list[Any]:
    result = []
    seen = set()
    for value in values:
        if value in (None, ""):
            continue
        key = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def unique_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return unique(values)
