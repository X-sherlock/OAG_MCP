package com.example.oagmcp.logic;

import com.example.oagmcp.dao.FundSkillDAO;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class FundSkillLogic {

    private static final String SOURCE = "ifundtest.ifund_all_info";
    private static final Set<String> SUPPORTED_SKILLS = new LinkedHashSet<>(Arrays.asList(
            "get_fund_profile_facts",
            "get_fund_purchase_rules",
            "get_fund_metric_values",
            "get_fund_benchmark_facts",
            "get_fund_peer_ranking_facts",
            "get_fund_manager_facts",
            "get_fund_allocation_facts",
            "get_fund_fee_facts",
            "get_fund_dividend_facts",
            "get_fund_holding_facts",
            "get_fund_risk_facts",
            "screen_funds_by_metric_condition",
            "rank_funds_by_metric",
            "compare_funds_by_metric",
            "recommend_funds_by_risk_return"
    ));

    private static final Map<String, String> PROFILE_FIELDS = fields(
            "fund_code", "COD_FUND", "fund_name", "NAM_FUND", "fund_short_name", "NAM_FUND_SHORT",
            "fund_type", "COD_FUND_TYP", "fund_status", "COD_FUND_STS", "risk_level", "COD_FUND_RSK_LVL",
            "sale_status", "COD_FUND_LIVE_STS", "purchase_status", "COD_PURC_STS",
            "redemption_status", "COD_REDM_STS", "pension_fund_flag", "IND_PENS_FUND",
            "index_fund_flag", "IND_IDX_FUND", "fof_flag", "IND_FOF", "etf_flag", "IND_ETF",
            "dividend_mode", "COD_BONS_TYP", "fund_size", "AMT_FUND_SCL",
            "listing_date", "DATE_FUND_MKT", "inception_date", "DATE_FUND_CRT", "company_name", "NAM_CMPY"
    );
    private static final Map<String, String> PURCHASE_FIELDS = fields(
            "minimum_subscription_amount", "AMT_IDV_FST_SSCR_MIN",
            "minimum_purchase_amount", "AMT_IDV_FST_PURC_MIN",
            "minimum_aip_amount", "AMT_AIP_MIN", "maximum_aip_amount", "AMT_AIP_MAX",
            "purchase_discount", "VLU_DCNT_PURC", "aip_discount", "VLU_DCNT_AIP",
            "subscription_discount", "VLU_DCNT_SSCR"
    );
    private static final Map<String, String> ALLOCATION_FIELDS = fields(
            "stock_asset_ratio", "PCT_STOCK_ASSET", "cash_asset_ratio", "PCT_CCY_ASSET",
            "bond_asset_ratio", "PCT_BOND_ASSET", "other_asset_ratio", "PCT_OTHER_ASSET",
            "fund_asset_ratio", "PCT_FUND_ASSET"
    );
    private static final Map<String, Map<String, String>> METRIC_FIELDS = periodFields(
            "return_rate", periods(
                    "1w", "VLU_NAV_GRTH_WEEK", "1m", "VLU_NAV_GRTH_MTH", "3m", "VLU_NAV_GRTH_3_MTH",
                    "6m", "VLU_NAV_GRTH_6_MTH", "1y", "VLU_NAV_GRTH_YEAR", "2y", "VLU_NAV_GRTH_2_YEAR",
                    "3y", "VLU_NAV_GRTH_3_YEAR", "4y", "VLU_NAV_GRTH_4_YEAR", "5y", "VLU_NAV_GRTH_5_YEAR",
                    "ytd", "VLU_NAV_GRTH_THIS_YEAR"
            ),
            "max_drawdown", periods(
                    "1m", "VLU_MAX_DD_MTH", "3m", "VLU_MAX_DD_3_MTH", "6m", "VLU_MAX_DD_6_MTH",
                    "1y", "VLU_MAX_DD_YEAR", "2y", "VLU_MAX_DD_2_YEAR", "3y", "VLU_MAX_DD_3_YEAR",
                    "ytd", "VLU_MAX_DD_THIS_YEAR", "si", "VLU_MAX_DD_YEAR_CRT"
            ),
            "volatility", periods(
                    "1m", "VLU_STD_MTH", "3m", "VLU_STD_3_MTH", "6m", "VLU_STD_6_MTH",
                    "1y", "VLU_STD_YEAR", "2y", "VLU_STD_2_YEAR", "3y", "VLU_STD_3_YEAR",
                    "ytd", "VLU_STD_THIS_YEAR", "si", "VLU_STD_YEAR_CRT"
            ),
            "standard_deviation", periods(
                    "1m", "VLU_STD_MTH", "3m", "VLU_STD_3_MTH", "6m", "VLU_STD_6_MTH",
                    "1y", "VLU_STD_YEAR", "2y", "VLU_STD_2_YEAR", "3y", "VLU_STD_3_YEAR",
                    "ytd", "VLU_STD_THIS_YEAR", "si", "VLU_STD_YEAR_CRT"
            ),
            "sharpe_ratio", periods(
                    "1m", "VLU_SHARP_MTH", "3m", "VLU_SHARP_3_MTH", "6m", "VLU_SHARP_6_MTH",
                    "1y", "VLU_SHARP_YEAR", "2y", "VLU_SHARP_2_YEAR", "3y", "VLU_SHARP_3_YEAR",
                    "ytd", "VLU_SHARP_THIS_YEAR", "si", "VLU_SHARP_YEAR_CRT"
            ),
            "drawdown", periods(
                    "1m", "VLU_MAX_DD_MTH", "3m", "VLU_MAX_DD_3_MTH", "6m", "VLU_MAX_DD_6_MTH",
                    "1y", "VLU_MAX_DD_YEAR", "2y", "VLU_MAX_DD_2_YEAR", "3y", "VLU_MAX_DD_3_YEAR",
                    "ytd", "VLU_MAX_DD_THIS_YEAR", "si", "VLU_MAX_DD_YEAR_CRT"
            )
    );
    private static final Map<String, String> FIXED_METRICS = fields(
            "unit_nav", "VLU_FUND_NAV", "accumulated_nav", "VLU_FUND_NAV_ACML",
            "ten_thousand_income", "AMT_TEN_THOU_EARN", "seven_day_annualized_yield", "VLU_SEVN_DAY_YEAR_RATE",
            "average_annualized_return", "VLU_ANNL_MEAN_YLD", "annualized_return", "VLU_ANNL_MEAN_YLD",
            "daily_return", "VLU_NAV_GRTH_THIS_DAY"
    );
    private static final Set<String> UNSUPPORTED_IFUND_ATTRIBUTES = new LinkedHashSet<>(Arrays.asList(
            "sortino_ratio",
            "var",
            "cvar",
            "downside_risk",
            "max_drawdown_peak_date",
            "max_drawdown_trough_date",
            "max_drawdown_recovery_days",
            "tracking_error",
            "information_ratio",
            "fee_type",
            "fee_value",
            "fee_effective_date",
            "dividend_per_share",
            "dividend_date",
            "stable_monthly_dividend",
            "stable_quarterly_dividend",
            "stable_yearly_dividend",
            "stock_code",
            "stock_name",
            "stock_market_value",
            "stock_nav_ratio",
            "bond_code",
            "bond_name",
            "bond_market_value",
            "bond_nav_ratio",
            "holding_industry",
            "asset_total_value",
            "asset_net_value",
            "percentile",
            "rank",
            "peer_risk_rank",
            "peer_average"
    ));
    private static final Map<String, String> EXCESS_FIELDS = periods(
            "1w", "VLU_EX_BM_WEEK", "1m", "VLU_EX_BM_MTH", "3m", "VLU_EX_BM_3_MTH",
            "6m", "VLU_EX_BM_6_MTH", "1y", "VLU_EX_BM_YEAR", "2y", "VLU_EX_BM_2_YEAR",
            "3y", "VLU_EX_BM_3_YEAR", "5y", "VLU_EX_BM_5_YEAR", "si", "VLU_EX_BM_CRT"
    );
    private static final Map<String, Map<String, String>> PEER_FIELDS = periodFields(
            "peer_return_rank", periods(
                    "1w", "ID_RET_KIND_WEEK_RANK", "1m", "ID_RET_KIND_MTH_RANK",
                    "3m", "ID_RET_KIND_3_MTH_RANK", "6m", "ID_RET_KIND_6_MTH_RANK",
                    "1y", "ID_RET_KIND_YEAR_RANK", "2y", "ID_RET_KIND_2_YEAR_RANK",
                    "3y", "ID_RET_KIND_3_YEAR_RANK", "4y", "ID_RET_KIND_4_YEAR_RANK",
                    "5y", "ID_RET_KIND_5_YEAR_RANK"
            ),
            "peer_drawdown_rank", periods(
                    "1m", "ID_VLU_MAX_DD_KIND_RANK_MTH", "3m", "ID_VLU_MAX_DD_KIND_RANK_3_MTH",
                    "6m", "ID_VLU_MAX_DD_KIND_RANK_6_MTH", "1y", "ID_VLU_MAX_DD_KIND_RANK_YEAR",
                    "2y", "ID_VLU_MAX_DD_KIND_RANK_2_YEAR", "3y", "ID_VLU_MAX_DD_KIND_RANK_3_YEAR",
                    "ytd", "ID_VLU_MAX_DD_KIND_RANK_THIS_YEAR", "si", "ID_VLU_MAX_DD_KIND_RANK_CRT"
            ),
            "peer_volatility_rank", periods(
                    "1m", "ID_STD_KIND_RANK_MTH", "3m", "ID_STD_KIND_RANK_3_MTH",
                    "6m", "ID_STD_KIND_RANK_6_MTH", "1y", "ID_STD_KIND_RANK_YEAR",
                    "2y", "ID_STD_KIND_RANK_2_YEAR", "3y", "ID_STD_KIND_RANK_3_YEAR",
                    "ytd", "ID_STD_KIND_RANK_THIS_YEAR", "si", "ID_STD_KIND_RANK_YEAR_CRT"
            ),
            "peer_sharpe_rank", periods(
                    "1m", "ID_SHARP_KIND_RANK_MTH", "3m", "ID_SHARP_KIND_RANK_3_MTH",
                    "6m", "ID_SHARP_KIND_RANK_6_MTH", "1y", "ID_SHARP_KIND_RANK_YEAR",
                    "2y", "ID_SHARP_KIND_RANK_2_YEAR", "3y", "ID_SHARP_KIND_RANK_3_YEAR",
                    "ytd", "ID_SHARP_KIND_RANK_THIS_YEAR", "si", "ID_SHARP_KIND_RANK_CRT"
            )
    );

    private final FundSkillDAO dao;

    public FundSkillLogic(FundSkillDAO dao) {
        this.dao = dao;
    }

    public Map<String, Object> execute(String skillId, Map<String, Object> input) {
        if (!SUPPORTED_SKILLS.contains(skillId)) {
            throw new IllegalArgumentException("Unsupported skill_id: " + skillId);
        }
        Map<String, Object> data;
        switch (skillId) {
            case "get_fund_profile_facts":
                data = fixedFacts(skillId, input, PROFILE_FIELDS);
                break;
            case "get_fund_purchase_rules":
                data = fixedFacts(skillId, input, PURCHASE_FIELDS);
                break;
            case "get_fund_metric_values":
                data = metricFacts(skillId, input);
                break;
            case "get_fund_benchmark_facts":
                data = benchmarkFacts(skillId, input);
                break;
            case "get_fund_peer_ranking_facts":
                data = peerFacts(skillId, input);
                break;
            case "get_fund_manager_facts":
                data = managerFacts(input);
                break;
            case "get_fund_allocation_facts":
                data = allocationFacts(skillId, input);
                break;
            case "get_fund_fee_facts":
                data = unsupportedFactSkill(skillId, input, Arrays.asList("fee_type", "fee_value", "fee_effective_date"));
                break;
            case "get_fund_dividend_facts":
                data = dividendFacts(skillId, input);
                break;
            case "get_fund_holding_facts":
                data = unsupportedFactSkill(skillId, input, Arrays.asList("stock_name", "stock_nav_ratio", "bond_name", "bond_nav_ratio", "holding_industry"));
                break;
            case "get_fund_risk_facts":
                data = riskFacts(skillId, input);
                break;
            case "screen_funds_by_metric_condition":
                data = screenFunds(input);
                break;
            case "rank_funds_by_metric":
                data = rankFunds(input);
                break;
            case "compare_funds_by_metric":
                data = compareFunds(input);
                break;
            case "recommend_funds_by_risk_return":
                data = recommendFunds(input);
                break;
            default:
                throw new IllegalArgumentException("Unsupported skill_id: " + skillId);
        }
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("success", true);
        response.put("skill_id", skillId);
        response.put("input", input);
        response.putAll(data);
        return response;
    }

    public Map<String, Object> error(String skillId, Map<String, Object> input, String message) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("success", false);
        response.put("skill_id", skillId);
        response.put("input", input == null ? Collections.emptyMap() : input);
        response.put("message", message);
        return response;
    }

    private FundIdentity resolveFundIdentity(Map<String, Object> input) {
        String fundCode = optionalString(input, "fund_code");
        if (StringUtils.hasText(fundCode)) {
            return FundIdentity.resolved(fundCode, Collections.<Map<String, Object>>emptyList());
        }
        String fundName = optionalString(input, "fund_name");
        if (!StringUtils.hasText(fundName)) {
            fundName = optionalString(input, "fund_short_name");
        }
        if (!StringUtils.hasText(fundName)) {
            throw new IllegalArgumentException("fund_code is required");
        }
        List<Map<String, Object>> matches = dao.selectFundsByName(
                fundName,
                Arrays.asList("COD_FUND", "NAM_FUND", "NAM_FUND_SHORT")
        );
        if (matches == null || matches.isEmpty()) {
            return FundIdentity.notFound(fundName);
        }
        if (matches.size() > 1) {
            return FundIdentity.ambiguous(fundName, matches);
        }
        return FundIdentity.resolved(String.valueOf(matches.get(0).get("COD_FUND")), matches);
    }

    private Map<String, Object> fundResolutionResult(FundIdentity fund) {
        Map<String, Object> result = map(
                "facts", new ArrayList<Map<String, Object>>(),
                "missing_attributes", new ArrayList<String>(),
                "not_found", fund.notFound,
                "source", SOURCE,
                "fund_lookup_status", fund.ambiguous ? "ambiguous_fund" : "not_found",
                "fund_lookup_input", fund.inputName
        );
        if (fund.ambiguous) {
            result.put("fund_candidates", fund.matches);
        }
        return result;
    }

    private Map<String, Object> fixedFacts(String skillId, Map<String, Object> input, Map<String, String> fields) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        List<String> attributes = attributes(input, new ArrayList<>(fields.keySet()));
        Map<String, String> selected = selectFields(attributes, fields);
        Map<String, Object> row = dao.selectFund(fundCode, columns(selected.values(), "COD_FUND"));
        return factResult(skillId, fundCode, selected, row, null);
    }

    private Map<String, Object> metricFacts(String skillId, Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        List<String> defaults = Arrays.asList("return_rate", "max_drawdown", "volatility", "sharpe_ratio");
        List<String> attributes = attributes(input, defaults);
        String period = normalizePeriod(optionalString(input, "period"));
        Map<String, String> selected = new LinkedHashMap<>();
        List<MetricSpec> unsupported = new ArrayList<>();
        for (String attribute : attributes) {
            if (FIXED_METRICS.containsKey(attribute)) {
                selected.put(attribute, FIXED_METRICS.get(attribute));
            } else {
                MetricSpec spec = metricSpec(attribute, period);
                if (spec.supported) {
                    selected.put(attribute, spec.column);
                } else {
                    unsupported.add(spec);
                }
            }
        }
        Map<String, Object> row = dao.selectFund(fundCode, columns(selected.values(), "COD_FUND"));
        Map<String, Object> result = factResult(skillId, fundCode, selected, row, period);
        addUnsupportedSpecs(result, unsupported);
        return result;
    }

    private Map<String, Object> benchmarkFacts(String skillId, Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        String period = requiredPeriod(input);
        MetricSpec returnSpec = metricSpec("return_rate", period);
        String excessColumn = EXCESS_FIELDS.get(period);
        if (!returnSpec.supported || excessColumn == null) {
            MetricSpec excessSpec = excessColumn == null
                    ? new MetricSpec("excess_return", null, false, "unsupported_period", new ArrayList<>(EXCESS_FIELDS.keySet()))
                    : new MetricSpec("excess_return", excessColumn, true);
            return unsupportedCollectionResult("facts", Arrays.asList(returnSpec, excessSpec), Arrays.asList("return_rate", "excess_return", "benchmark_return"));
        }
        String returnColumn = returnSpec.column;
        Map<String, Object> row = dao.selectFund(fundCode, Arrays.asList("COD_FUND", returnColumn, excessColumn));
        List<Map<String, Object>> facts = new ArrayList<>();
        if (row != null) {
            BigDecimal fundReturn = decimal(row.get(returnColumn));
            BigDecimal excessReturn = decimal(row.get(excessColumn));
            addFact(facts, skillId, fundCode, "return_rate", period, fundReturn);
            addFact(facts, skillId, fundCode, "excess_return", period, excessReturn);
            if (fundReturn != null && excessReturn != null) {
                addFact(facts, skillId, fundCode, "benchmark_return", period, fundReturn.subtract(excessReturn));
            }
        }
        return map("facts", facts, "missing_attributes", missing(Arrays.asList("return_rate", "excess_return", "benchmark_return"), facts), "not_found", row == null, "source", SOURCE);
    }

    private Map<String, Object> peerFacts(String skillId, Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        String period = requiredPeriod(input);
        List<String> attributes = attributes(input, Arrays.asList("peer_return_rank", "peer_drawdown_rank", "peer_sharpe_rank"));
        Map<String, String> selected = new LinkedHashMap<>();
        List<MetricSpec> unsupported = new ArrayList<>();
        for (String attribute : attributes) {
            MetricSpec spec = metricSpec(attribute, period);
            if (spec.supported) {
                selected.put(attribute, spec.column);
            } else {
                unsupported.add(spec);
            }
        }
        Map<String, Object> row = dao.selectFund(fundCode, columns(selected.values(), "COD_FUND"));
        Map<String, Object> result = factResult(skillId, fundCode, selected, row, period);
        addUnsupportedSpecs(result, unsupported);
        return result;
    }

    private Map<String, Object> allocationFacts(String skillId, Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        List<String> attributes = attributes(input, Arrays.asList("stock_asset_ratio", "cash_asset_ratio", "bond_asset_ratio", "fund_asset_ratio", "other_asset_ratio"));
        Map<String, String> selected = new LinkedHashMap<>();
        List<String> unsupported = new ArrayList<>();
        for (String attribute : attributes) {
            if (ALLOCATION_FIELDS.containsKey(attribute)) {
                selected.put(attribute, ALLOCATION_FIELDS.get(attribute));
            } else if (UNSUPPORTED_IFUND_ATTRIBUTES.contains(attribute)) {
                unsupported.add(attribute);
            } else {
                throw new IllegalArgumentException("Unsupported attribute: " + attribute);
            }
        }
        Map<String, Object> row = dao.selectFund(fundCode, columns(selected.values(), "COD_FUND"));
        Map<String, Object> result = factResult(skillId, fundCode, selected, row, null);
        addUnsupported(result, unsupported);
        return result;
    }

    private Map<String, Object> dividendFacts(String skillId, Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        List<String> attributes = attributes(input, Arrays.asList("dividend_per_share", "dividend_date", "stable_monthly_dividend", "stable_quarterly_dividend", "stable_yearly_dividend"));
        Map<String, String> selected = new LinkedHashMap<>();
        List<String> unsupported = new ArrayList<>();
        for (String attribute : attributes) {
            if ("dividend_mode".equals(attribute)) {
                selected.put(attribute, "COD_BONS_TYP");
            } else if (UNSUPPORTED_IFUND_ATTRIBUTES.contains(attribute)) {
                unsupported.add(attribute);
            } else {
                throw new IllegalArgumentException("Unsupported attribute: " + attribute);
            }
        }
        Map<String, Object> row = dao.selectFund(fundCode, columns(selected.values(), "COD_FUND"));
        Map<String, Object> result = factResult(skillId, fundCode, selected, row, null);
        addUnsupported(result, unsupported);
        return result;
    }

    private Map<String, Object> riskFacts(String skillId, Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        String period = requiredPeriod(input);
        List<String> attributes = attributes(input, Arrays.asList("max_drawdown", "volatility", "standard_deviation", "sharpe_ratio", "calmar_ratio"));
        Map<String, String> selected = new LinkedHashMap<>();
        List<MetricSpec> unsupported = new ArrayList<>();
        boolean needsCalmar = false;
        for (String attribute : attributes) {
            if ("calmar_ratio".equals(attribute)) {
                needsCalmar = true;
                MetricSpec returnSpec = metricSpec("return_rate", period);
                MetricSpec drawdownSpec = metricSpec("max_drawdown", period);
                if (returnSpec.supported && drawdownSpec.supported) {
                    selected.put("return_rate", returnSpec.column);
                    selected.put("max_drawdown", drawdownSpec.column);
                } else {
                    unsupported.add(returnSpec);
                    unsupported.add(drawdownSpec);
                }
            } else if (FIXED_METRICS.containsKey(attribute)) {
                selected.put(attribute, FIXED_METRICS.get(attribute));
            } else {
                MetricSpec spec = metricSpec(attribute, period);
                if (spec.supported) {
                    selected.put(attribute, spec.column);
                } else {
                    unsupported.add(spec);
                }
            }
        }
        Map<String, Object> row = dao.selectFund(fundCode, columns(selected.values(), "COD_FUND"));
        Map<String, Object> result = factResult(skillId, fundCode, selected, row, period);
        if (needsCalmar && row != null) {
            addCalmarFact((List<Map<String, Object>>) result.get("facts"), skillId, fundCode, period,
                    row.get(metricColumn(METRIC_FIELDS, "return_rate", period)),
                    row.get(metricColumn(METRIC_FIELDS, "max_drawdown", period)));
            ((List<String>) result.get("missing_attributes")).remove("return_rate");
            ((List<String>) result.get("missing_attributes")).remove("max_drawdown");
            if (!hasFact((List<Map<String, Object>>) result.get("facts"), "calmar_ratio")) {
                ((List<String>) result.get("missing_attributes")).add("calmar_ratio");
            }
        }
        addUnsupportedSpecs(result, unsupported);
        return result;
    }

    private Map<String, Object> unsupportedFactSkill(String skillId, Map<String, Object> input, List<String> defaults) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        Map<String, Object> row = dao.selectFund(fundCode, Collections.singletonList("COD_FUND"));
        List<String> attributes = attributes(input, defaults);
        Map<String, Object> result = map(
                "facts", new ArrayList<Map<String, Object>>(),
                "missing_attributes", row == null ? new ArrayList<String>() : new ArrayList<>(attributes),
                "not_found", row == null,
                "source", SOURCE
        );
        if (row != null) {
            addUnsupported(result, attributes);
        }
        return result;
    }

    private Map<String, Object> managerFacts(Map<String, Object> input) {
        FundIdentity fund = resolveFundIdentity(input);
        if (!fund.resolved) {
            return fundResolutionResult(fund);
        }
        String fundCode = fund.fundCode;
        List<String> columns = new ArrayList<>();
        columns.add("COD_FUND");
        for (int index = 1; index <= 5; index++) {
            columns.add("NAM_MAGR_" + index);
            columns.add("COD_SEX_" + index);
            columns.add("DAYS_OF_MAGR_" + index);
            columns.add("AMT_MAGR_SCL_" + index);
            columns.add("VLU_MAGR_TERM_RET_" + index);
            columns.add("DATE_STRT_" + index);
        }
        Map<String, Object> row = dao.selectFund(fundCode, columns);
        List<Map<String, Object>> managers = new ArrayList<>();
        if (row != null) {
            for (int index = 1; index <= 5; index++) {
                Object name = row.get("NAM_MAGR_" + index);
                if (!StringUtils.hasText(name == null ? "" : String.valueOf(name))) {
                    continue;
                }
                managers.add(map(
                        "display_order", index,
                        "manager_name", name,
                        "gender_code", row.get("COD_SEX_" + index),
                        "manager_tenure_days", row.get("DAYS_OF_MAGR_" + index),
                        "manager_scale", row.get("AMT_MAGR_SCL_" + index),
                        "manager_term_return", row.get("VLU_MAGR_TERM_RET_" + index),
                        "management_start_date", row.get("DATE_STRT_" + index)
                ));
            }
        }
        return map("managers", managers, "not_found", row == null, "source", SOURCE);
    }

    private Map<String, Object> rankFunds(Map<String, Object> input) {
        String attribute = requiredString(input, "attribute");
        String period = requiredPeriod(input);
        MetricSpec spec = metricSpec(attribute, period);
        if (!spec.supported) {
            return unsupportedCollectionResult("ranking", Collections.singletonList(spec), Collections.singletonList(attribute));
        }
        String column = spec.column;
        boolean descending = !"asc".equalsIgnoreCase(optionalString(input, "direction"));
        int limit = boundedInt(input.get("limit"), 20, 1, 100);
        List<Map<String, Object>> rows = dao.selectFunds(stringList(input, "fund_universe", false), Arrays.asList("COD_FUND", "NAM_FUND", column));
        rows.removeIf(row -> decimal(row.get(column)) == null);
        rows.sort(metricComparator(column, descending));
        List<Map<String, Object>> ranking = new ArrayList<>();
        for (int index = 0; index < Math.min(limit, rows.size()); index++) {
            Map<String, Object> row = rows.get(index);
            ranking.add(map("rank", index + 1, "fund_code", row.get("COD_FUND"), "fund_name", row.get("NAM_FUND"), "attribute", attribute, "period", period, "value", row.get(column)));
        }
        return map("ranking", ranking, "facts", new ArrayList<Map<String, Object>>(), "missing_attributes", new ArrayList<String>(), "not_found", false, "source", SOURCE);
    }

    private Map<String, Object> screenFunds(Map<String, Object> input) {
        String period = requiredPeriod(input);
        Object rawFilters = input.get("filters");
        if (!(rawFilters instanceof List) || ((List<?>) rawFilters).isEmpty()) {
            throw new IllegalArgumentException("filters must be a non-empty array");
        }
        List<Map<String, Object>> filters = castMaps((List<?>) rawFilters);
        LinkedHashSet<String> columns = new LinkedHashSet<>(Arrays.asList("COD_FUND", "NAM_FUND"));
        List<MetricSpec> unsupported = new ArrayList<>();
        for (Map<String, Object> filter : filters) {
            MetricSpec spec = metricSpec(requiredString(filter, "attribute"), period);
            if (spec.supported) {
                columns.add(spec.column);
            } else {
                unsupported.add(spec);
            }
            validateOperator(requiredString(filter, "operator"));
            if (!filter.containsKey("value")) {
                throw new IllegalArgumentException("filter.value is required");
            }
        }
        if (!unsupported.isEmpty()) {
            return unsupportedCollectionResult("funds", unsupported, specAttributes(unsupported), "filters", filters);
        }
        List<Map<String, Object>> rows = dao.selectFunds(stringList(input, "fund_universe", false), new ArrayList<>(columns));
        List<Map<String, Object>> funds = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            if (matchesAll(row, filters, period)) {
                funds.add(map("fund_code", row.get("COD_FUND"), "fund_name", row.get("NAM_FUND")));
            }
        }
        return map("filters", filters, "funds", funds, "facts", new ArrayList<Map<String, Object>>(), "missing_attributes", new ArrayList<String>(), "not_found", false, "source", SOURCE);
    }

    private Map<String, Object> compareFunds(Map<String, Object> input) {
        List<String> fundCodes = stringList(input, "fund_codes", true);
        String period = requiredPeriod(input);
        List<String> attributes = stringList(input, "attributes", true);
        Map<String, String> selected = new LinkedHashMap<>();
        List<MetricSpec> unsupported = new ArrayList<>();
        for (String attribute : attributes) {
            MetricSpec spec = metricSpec(attribute, period);
            if (spec.supported) {
                selected.put(attribute, spec.column);
            } else {
                unsupported.add(spec);
            }
        }
        List<Map<String, Object>> rows = dao.selectFunds(fundCodes, columns(selected.values(), "COD_FUND", "NAM_FUND"));
        List<Map<String, Object>> comparisons = new ArrayList<>();
        Set<String> found = new LinkedHashSet<>();
        for (Map<String, Object> row : rows) {
            String fundCode = String.valueOf(row.get("COD_FUND"));
            found.add(fundCode);
            Map<String, Object> metrics = new LinkedHashMap<>();
            for (Map.Entry<String, String> entry : selected.entrySet()) {
                metrics.put(entry.getKey(), row.get(entry.getValue()));
            }
            comparisons.add(map("fund_code", fundCode, "fund_name", row.get("NAM_FUND"), "period", period, "metrics", metrics));
        }
        List<String> missing = new ArrayList<>(fundCodes);
        missing.removeAll(found);
        Map<String, Object> result = map("comparisons", comparisons, "missing_fund_codes", missing, "facts", new ArrayList<Map<String, Object>>(), "missing_attributes", specAttributes(unsupported), "not_found", rows.isEmpty(), "source", SOURCE);
        addUnsupportedSpecs(result, unsupported);
        return result;
    }

    private Map<String, Object> recommendFunds(Map<String, Object> input) {
        String period = requiredPeriod(input);
        MetricSpec returnSpec = metricSpec("return_rate", period);
        MetricSpec drawdownSpec = metricSpec("max_drawdown", period);
        MetricSpec sharpeSpec = metricSpec("sharpe_ratio", period);
        MetricSpec volatilitySpec = metricSpec("volatility", period);
        List<MetricSpec> unsupported = new ArrayList<>();
        for (MetricSpec spec : Arrays.asList(returnSpec, drawdownSpec, sharpeSpec, volatilitySpec)) {
            if (!spec.supported) {
                unsupported.add(spec);
            }
        }
        if (!unsupported.isEmpty()) {
            return unsupportedCollectionResult("recommendations", unsupported, specAttributes(unsupported));
        }
        String returnColumn = returnSpec.column;
        String drawdownColumn = drawdownSpec.column;
        String sharpeColumn = sharpeSpec.column;
        String volatilityColumn = volatilitySpec.column;
        List<Map<String, Object>> rows = dao.selectFunds(
                stringList(input, "fund_universe", false),
                Arrays.asList("COD_FUND", "NAM_FUND", returnColumn, drawdownColumn, sharpeColumn, volatilityColumn)
        );
        rows.removeIf(row -> decimal(row.get(returnColumn)) == null || decimal(row.get(drawdownColumn)) == null || decimal(row.get(sharpeColumn)) == null || decimal(row.get(volatilityColumn)) == null);
        rows.sort(metricComparator(sharpeColumn, true)
                .thenComparing(metricComparator(returnColumn, true))
                .thenComparing(metricComparator(drawdownColumn, false))
                .thenComparing(metricComparator(volatilityColumn, false)));
        int limit = boundedInt(input.get("limit"), 10, 1, 100);
        List<Map<String, Object>> recommendations = new ArrayList<>();
        for (int index = 0; index < Math.min(limit, rows.size()); index++) {
            Map<String, Object> row = rows.get(index);
            recommendations.add(map(
                    "rank", index + 1, "fund_code", row.get("COD_FUND"), "fund_name", row.get("NAM_FUND"),
                    "period", period, "return_rate", row.get(returnColumn),
                    "max_drawdown", row.get(drawdownColumn), "sharpe_ratio", row.get(sharpeColumn),
                    "volatility", row.get(volatilityColumn)
            ));
        }
        return map(
                "method", "sharpe_ratio desc, return_rate desc, max_drawdown asc, volatility asc",
                "recommendations", recommendations,
                "facts", new ArrayList<Map<String, Object>>(),
                "missing_attributes", new ArrayList<String>(),
                "not_found", false,
                "source", SOURCE,
                "disclaimer", "仅基于结构化历史指标排序，不构成投资建议。"
        );
    }

    private Map<String, Object> factResult(String skillId, String fundCode, Map<String, String> selected, Map<String, Object> row, String period) {
        List<Map<String, Object>> facts = new ArrayList<>();
        if (row != null) {
            for (Map.Entry<String, String> entry : selected.entrySet()) {
                addFact(facts, skillId, fundCode, entry.getKey(), period, row.get(entry.getValue()));
            }
        }
        return map("facts", facts, "missing_attributes", missing(new ArrayList<>(selected.keySet()), facts), "not_found", row == null, "source", SOURCE);
    }

    private void addFact(List<Map<String, Object>> facts, String skillId, String fundCode, String attribute, String period, Object value) {
        if (value == null) {
            return;
        }
        facts.add(map(
                "fact_requirement_id", null, "object_type", "Fund", "instance_ref", fundCode,
                "attribute_name", attribute, "period", period, "value", value, "unit", null,
                "as_of_date", null, "source", SOURCE, "producer_skill", skillId
        ));
    }

    private List<String> missing(List<String> attributes, List<Map<String, Object>> facts) {
        Set<String> present = new LinkedHashSet<>();
        for (Map<String, Object> fact : facts) {
            present.add(String.valueOf(fact.get("attribute_name")));
        }
        List<String> missing = new ArrayList<>(attributes);
        missing.removeAll(present);
        return missing;
    }

    private boolean matchesAll(Map<String, Object> row, List<Map<String, Object>> filters, String period) {
        for (Map<String, Object> filter : filters) {
            String attribute = String.valueOf(filter.get("attribute"));
            String operator = String.valueOf(filter.get("operator"));
            MetricSpec spec = metricSpec(attribute, period);
            BigDecimal actual = spec.supported ? decimal(row.get(spec.column)) : null;
            BigDecimal expected = decimal(filter.get("value"));
            if (actual == null || expected == null || !compare(actual.compareTo(expected), operator)) {
                return false;
            }
        }
        return true;
    }

    private boolean compare(int comparison, String operator) {
        switch (operator) {
            case "eq": return comparison == 0;
            case "ne": return comparison != 0;
            case "gt": return comparison > 0;
            case "gte": return comparison >= 0;
            case "lt": return comparison < 0;
            case "lte": return comparison <= 0;
            default: throw new IllegalArgumentException("Unsupported operator: " + operator);
        }
    }

    private void validateOperator(String operator) {
        if (!Arrays.asList("eq", "ne", "gt", "gte", "lt", "lte").contains(operator)) {
            throw new IllegalArgumentException("Unsupported operator: " + operator);
        }
    }

    private Comparator<Map<String, Object>> metricComparator(final String column, final boolean descending) {
        return (left, right) -> {
            BigDecimal l = decimal(left.get(column));
            BigDecimal r = decimal(right.get(column));
            int value = l == null ? (r == null ? 0 : 1) : (r == null ? -1 : l.compareTo(r));
            return descending ? -value : value;
        };
    }

    private Map<String, String> selectFields(List<String> attributes, Map<String, String> available) {
        Map<String, String> selected = new LinkedHashMap<>();
        for (String attribute : attributes) {
            String column = available.get(attribute);
            if (column == null) {
                throw new IllegalArgumentException("Unsupported attribute: " + attribute);
            }
            selected.put(attribute, column);
        }
        return selected;
    }

    private String metricColumn(Map<String, Map<String, String>> available, String attribute, String period) {
        Map<String, String> periods = available.get(attribute);
        if (periods == null) {
            throw new IllegalArgumentException("Unsupported metric attribute: " + attribute);
        }
        String column = periods.get(normalizePeriod(period));
        if (column == null) {
            throw new IllegalArgumentException("Metric " + attribute + " does not support period: " + period);
        }
        return column;
    }

    private MetricSpec metricSpec(String attribute, String period) {
        if (FIXED_METRICS.containsKey(attribute)) {
            return new MetricSpec(attribute, FIXED_METRICS.get(attribute), true);
        }
        if (METRIC_FIELDS.containsKey(attribute)) {
            return metricSpecFromPeriodMap(attribute, period, METRIC_FIELDS.get(attribute));
        }
        if (PEER_FIELDS.containsKey(attribute)) {
            return metricSpecFromPeriodMap(attribute, period, PEER_FIELDS.get(attribute));
        }
        if (UNSUPPORTED_IFUND_ATTRIBUTES.contains(attribute)) {
            return new MetricSpec(attribute, null, false, "unsupported_by_ifund_all_info", Collections.<String>emptyList());
        }
        throw new IllegalArgumentException("Unsupported metric attribute: " + attribute);
    }

    private MetricSpec metricSpecFromPeriodMap(String attribute, String period, Map<String, String> periods) {
        String normalized = normalizePeriod(period);
        String column = periods.get(normalized);
        if (column != null) {
            return new MetricSpec(attribute, column, true);
        }
        return new MetricSpec(attribute, null, false, "unsupported_period", new ArrayList<>(periods.keySet()));
    }

    private Map<String, Object> unsupportedCollectionResult(String key, List<MetricSpec> specs, List<String> missingAttributes) {
        return unsupportedCollectionResult(key, specs, missingAttributes, null, null);
    }

    private Map<String, Object> unsupportedCollectionResult(String key, List<MetricSpec> specs, List<String> missingAttributes, String extraKey, Object extraValue) {
        Map<String, Object> result = map(key, new ArrayList<Map<String, Object>>(), "facts", new ArrayList<Map<String, Object>>(), "missing_attributes", new ArrayList<>(missingAttributes), "not_found", false, "source", SOURCE);
        if (extraKey != null) {
            result.put(extraKey, extraValue);
        }
        addUnsupportedSpecs(result, specs);
        return result;
    }

    private void addUnsupported(Map<String, Object> result, List<String> unsupported) {
        if (unsupported == null || unsupported.isEmpty()) {
            return;
        }
        Object rawMissing = result.get("missing_attributes");
        if (rawMissing instanceof List) {
            @SuppressWarnings("unchecked")
            List<Object> missing = (List<Object>) rawMissing;
            for (String attribute : unsupported) {
                if (!missing.contains(attribute)) {
                    missing.add(attribute);
                }
            }
        }
        result.put("data_source_status", "unsupported_by_ifund_all_info");
        result.put("unsupported_attributes", new ArrayList<>(new LinkedHashSet<>(unsupported)));
    }

    private void addUnsupportedSpecs(Map<String, Object> result, List<MetricSpec> specs) {
        if (specs == null || specs.isEmpty()) {
            return;
        }
        LinkedHashSet<String> unsupportedAttributes = new LinkedHashSet<>();
        LinkedHashSet<String> closestPeriods = new LinkedHashSet<>();
        boolean hasUnsupportedPeriod = false;
        boolean hasUnsupportedData = false;
        for (MetricSpec spec : specs) {
            if (spec == null || spec.supported) {
                continue;
            }
            unsupportedAttributes.add(spec.attribute);
            if ("unsupported_period".equals(spec.dataSourceStatus)) {
                hasUnsupportedPeriod = true;
                closestPeriods.addAll(spec.closestSupportedPeriods);
            } else {
                hasUnsupportedData = true;
            }
        }
        Object rawMissing = result.get("missing_attributes");
        if (rawMissing instanceof List) {
            @SuppressWarnings("unchecked")
            List<Object> missing = (List<Object>) rawMissing;
            for (String attribute : unsupportedAttributes) {
                if (!missing.contains(attribute)) {
                    missing.add(attribute);
                }
            }
        }
        if (hasUnsupportedPeriod) {
            result.put("data_source_status", "unsupported_period");
            result.put("closest_supported_periods", new ArrayList<>(closestPeriods));
        } else if (hasUnsupportedData) {
            result.put("data_source_status", "unsupported_by_ifund_all_info");
        }
        if (!unsupportedAttributes.isEmpty()) {
            result.put("unsupported_attributes", new ArrayList<>(unsupportedAttributes));
        }
    }

    private List<String> specAttributes(List<MetricSpec> specs) {
        LinkedHashSet<String> attributes = new LinkedHashSet<>();
        for (MetricSpec spec : specs) {
            if (spec != null) {
                attributes.add(spec.attribute);
            }
        }
        return new ArrayList<>(attributes);
    }

    private void addCalmarFact(List<Map<String, Object>> facts, String skillId, String fundCode, String period, Object returnValue, Object drawdownValue) {
        BigDecimal returnRate = decimal(returnValue);
        BigDecimal drawdown = decimal(drawdownValue);
        if (returnRate == null || drawdown == null || BigDecimal.ZERO.compareTo(drawdown) == 0) {
            return;
        }
        BigDecimal denominator = drawdown.abs();
        if (BigDecimal.ZERO.compareTo(denominator) == 0) {
            return;
        }
        facts.add(map(
                "fact_requirement_id", null, "object_type", "Fund", "instance_ref", fundCode,
                "attribute_name", "calmar_ratio", "period", period,
                "value", returnRate.divide(denominator, 8, RoundingMode.HALF_UP), "unit", null,
                "as_of_date", null, "source", SOURCE, "producer_skill", skillId,
                "derived_from", Arrays.asList("return_rate", "max_drawdown")
        ));
    }

    private boolean hasFact(List<Map<String, Object>> facts, String attribute) {
        for (Map<String, Object> fact : facts) {
            if (attribute.equals(fact.get("attribute_name"))) {
                return true;
            }
        }
        return false;
    }

    private List<String> attributes(Map<String, Object> input, List<String> defaults) {
        List<String> values = stringList(input, "attributes", false);
        return values.isEmpty() ? defaults : values;
    }

    private List<String> stringList(Map<String, Object> input, String key, boolean required) {
        Object raw = input.get(key);
        if (raw == null && "fund_universe".equals(key)) {
            raw = input.get("fund_codes");
        }
        if (raw == null) {
            if (required) {
                throw new IllegalArgumentException(key + " is required");
            }
            return new ArrayList<>();
        }
        if (raw instanceof String) {
            raw = Collections.singletonList(raw);
        }
        if (!(raw instanceof List)) {
            throw new IllegalArgumentException(key + " must be an array");
        }
        LinkedHashSet<String> values = new LinkedHashSet<>();
        for (Object item : (List<?>) raw) {
            if (!StringUtils.hasText(item == null ? "" : String.valueOf(item))) {
                throw new IllegalArgumentException(key + " must contain non-empty strings");
            }
            values.add(String.valueOf(item).trim());
        }
        if (required && values.isEmpty()) {
            throw new IllegalArgumentException(key + " must not be empty");
        }
        return new ArrayList<>(values);
    }

    private String requiredString(Map<String, Object> input, String key) {
        String value = optionalString(input, key);
        if (!StringUtils.hasText(value)) {
            throw new IllegalArgumentException(key + " is required");
        }
        return value;
    }

    private String requiredPeriod(Map<String, Object> input) {
        return normalizePeriod(requiredString(input, "period"));
    }

    private String normalizePeriod(String value) {
        if (!StringUtils.hasText(value)) {
            return value;
        }
        String period = value.trim();
        if ("12m".equalsIgnoreCase(period)) {
            return "1y";
        }
        if ("YTD".equalsIgnoreCase(period)) {
            return "ytd";
        }
        if ("SI".equalsIgnoreCase(period)) {
            return "si";
        }
        return period;
    }

    private String optionalString(Map<String, Object> input, String key) {
        Object value = input.get(key);
        return value == null ? "" : String.valueOf(value).trim();
    }

    private int boundedInt(Object value, int fallback, int minimum, int maximum) {
        int parsed = value == null ? fallback : Integer.parseInt(String.valueOf(value));
        return Math.max(minimum, Math.min(maximum, parsed));
    }

    private BigDecimal decimal(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return value instanceof BigDecimal ? (BigDecimal) value : new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private List<Map<String, Object>> castMaps(List<?> values) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Object value : values) {
            if (!(value instanceof Map)) {
                throw new IllegalArgumentException("filters must contain objects");
            }
            Map<String, Object> row = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : ((Map<?, ?>) value).entrySet()) {
                row.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            rows.add(row);
        }
        return rows;
    }

    private List<String> columns(Iterable<String> selected, String... required) {
        LinkedHashSet<String> columns = new LinkedHashSet<>(Arrays.asList(required));
        for (String column : selected) {
            columns.add(column);
        }
        return new ArrayList<>(columns);
    }

    private static Map<String, String> fields(String... values) {
        Map<String, String> map = new LinkedHashMap<>();
        for (int index = 0; index < values.length; index += 2) {
            map.put(values[index], values[index + 1]);
        }
        return Collections.unmodifiableMap(map);
    }

    private static Map<String, String> periods(String... values) {
        return fields(values);
    }

    private static Map<String, Map<String, String>> periodFields(Object... values) {
        Map<String, Map<String, String>> map = new LinkedHashMap<>();
        for (int index = 0; index < values.length; index += 2) {
            @SuppressWarnings("unchecked")
            Map<String, String> periodMap = (Map<String, String>) values[index + 1];
            map.put(String.valueOf(values[index]), periodMap);
        }
        return Collections.unmodifiableMap(map);
    }

    private static Map<String, Object> map(Object... values) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (int index = 0; index < values.length; index += 2) {
            map.put(String.valueOf(values[index]), values[index + 1]);
        }
        return map;
    }

    private static final class MetricSpec {
        private final String attribute;
        private final String column;
        private final boolean supported;
        private final String dataSourceStatus;
        private final List<String> closestSupportedPeriods;

        private MetricSpec(String attribute, String column, boolean supported) {
            this(attribute, column, supported, null, Collections.<String>emptyList());
        }

        private MetricSpec(String attribute, String column, boolean supported, String dataSourceStatus, List<String> closestSupportedPeriods) {
            this.attribute = attribute;
            this.column = column;
            this.supported = supported;
            this.dataSourceStatus = dataSourceStatus;
            this.closestSupportedPeriods = closestSupportedPeriods == null ? Collections.<String>emptyList() : closestSupportedPeriods;
        }
    }

    private static final class FundIdentity {
        private final boolean resolved;
        private final boolean notFound;
        private final boolean ambiguous;
        private final String fundCode;
        private final String inputName;
        private final List<Map<String, Object>> matches;

        private FundIdentity(boolean resolved, boolean notFound, boolean ambiguous, String fundCode, String inputName, List<Map<String, Object>> matches) {
            this.resolved = resolved;
            this.notFound = notFound;
            this.ambiguous = ambiguous;
            this.fundCode = fundCode;
            this.inputName = inputName;
            this.matches = matches == null ? new ArrayList<Map<String, Object>>() : matches;
        }

        private static FundIdentity resolved(String fundCode, List<Map<String, Object>> matches) {
            return new FundIdentity(true, false, false, fundCode, "", matches);
        }

        private static FundIdentity notFound(String inputName) {
            return new FundIdentity(false, true, false, "", inputName, new ArrayList<Map<String, Object>>());
        }

        private static FundIdentity ambiguous(String inputName, List<Map<String, Object>> matches) {
            return new FundIdentity(false, false, true, "", inputName, matches);
        }
    }
}
