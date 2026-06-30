package com.example.oagmcp.logic;

import com.example.oagmcp.dao.FundSkillDAO;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class FundSkillLogicTest {

    @Test
    void metricSkillMapsWhitelistedPeriodColumn() {
        RecordingDao dao = new RecordingDao();
        dao.one.put("COD_FUND", "000001");
        dao.one.put("VLU_NAV_GRTH_YEAR", new BigDecimal("0.166"));
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> input = map(
                "fund_code", "000001",
                "period", "1y",
                "attributes", Arrays.asList("return_rate")
        );
        Map<String, Object> result = logic.execute("get_fund_metric_values", input);

        assertEquals(true, result.get("success"));
        assertTrue(dao.columns.contains("VLU_NAV_GRTH_YEAR"));
        assertEquals(1, ((List<?>) result.get("facts")).size());
    }

    @Test
    void unknownMetricIsRejectedBeforeDaoCall() {
        RecordingDao dao = new RecordingDao();
        FundSkillLogic logic = new FundSkillLogic(dao);

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> logic.execute("rank_funds_by_metric", map(
                        "attribute", "DROP TABLE ifund_all_info",
                        "period", "1y"
                ))
        );

        assertTrue(error.getMessage().contains("Unsupported metric attribute"));
        assertTrue(dao.columns.isEmpty());
    }

    @Test
    void recommendationUsesRiskReturnOrdering() {
        RecordingDao dao = new RecordingDao();
        dao.many.add(map("COD_FUND", "000001", "NAM_FUND", "A", "VLU_NAV_GRTH_YEAR", new BigDecimal("0.10"), "VLU_MAX_DD_YEAR", new BigDecimal("-0.05"), "VLU_SHARP_YEAR", new BigDecimal("1.2"), "VLU_STD_YEAR", new BigDecimal("0.10")));
        dao.many.add(map("COD_FUND", "000002", "NAM_FUND", "B", "VLU_NAV_GRTH_YEAR", new BigDecimal("0.18"), "VLU_MAX_DD_YEAR", new BigDecimal("-0.12"), "VLU_SHARP_YEAR", new BigDecimal("1.0"), "VLU_STD_YEAR", new BigDecimal("0.08")));
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("recommend_funds_by_risk_return", map("period", "1y"));
        List<?> rows = (List<?>) result.get("recommendations");

        assertEquals("000001", ((Map<?, ?>) rows.get(0)).get("fund_code"));
        assertTrue(((Map<?, ?>) rows.get(0)).containsKey("volatility"));
        assertTrue(dao.columns.contains("VLU_STD_YEAR"));
    }

    @Test
    void riskSkillDerivesCalmarFromReturnAndDrawdown() {
        RecordingDao dao = new RecordingDao();
        dao.one.put("COD_FUND", "000001");
        dao.one.put("VLU_NAV_GRTH_YEAR", new BigDecimal("0.1200"));
        dao.one.put("VLU_MAX_DD_YEAR", new BigDecimal("-0.0600"));
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("get_fund_risk_facts", map(
                "fund_code", "000001",
                "period", "1y",
                "attributes", Arrays.asList("calmar_ratio")
        ));

        List<?> facts = (List<?>) result.get("facts");
        Map<?, ?> calmar = (Map<?, ?>) facts.stream()
                .map(item -> (Map<?, ?>) item)
                .filter(item -> "calmar_ratio".equals(item.get("attribute_name")))
                .findFirst()
                .orElseThrow(AssertionError::new);
        assertEquals(new BigDecimal("2.00000000"), calmar.get("value"));
        assertEquals(Arrays.asList("return_rate", "max_drawdown"), calmar.get("derived_from"));
    }

    @Test
    void unsupportedIfundAttributeReturnsStructuredStatus() {
        RecordingDao dao = new RecordingDao();
        dao.one.put("COD_FUND", "000001");
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("get_fund_fee_facts", map(
                "fund_code", "000001",
                "attributes", Arrays.asList("fee_value")
        ));

        assertEquals(true, result.get("success"));
        assertEquals("unsupported_by_ifund_all_info", result.get("data_source_status"));
        assertEquals(Arrays.asList("fee_value"), result.get("unsupported_attributes"));
        assertEquals(Arrays.asList("fee_value"), result.get("missing_attributes"));
    }

    @Test
    void fundNotFoundReturnsNotFoundWithoutFakeFacts() {
        RecordingDao dao = new RecordingDao();
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("get_fund_profile_facts", map(
                "fund_code", "999999",
                "attributes", Arrays.asList("fund_name")
        ));

        assertEquals(true, result.get("success"));
        assertEquals(true, result.get("not_found"));
        assertTrue(((List<?>) result.get("facts")).isEmpty());
    }

    @Test
    void fundNameCanResolveSingleFundBeforeFetchingFacts() {
        RecordingDao dao = new RecordingDao();
        dao.nameMatches.add(map("COD_FUND", "000001", "NAM_FUND", "华夏成长混合", "NAM_FUND_SHORT", "华夏成长"));
        dao.one.put("COD_FUND", "000001");
        dao.one.put("VLU_NAV_GRTH_YEAR", new BigDecimal("0.1200"));
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("get_fund_metric_values", map(
                "fund_name", "华夏成长混合",
                "period", "12m",
                "attributes", Arrays.asList("return_rate")
        ));

        assertEquals(true, result.get("success"));
        assertEquals(1, ((List<?>) result.get("facts")).size());
        assertEquals("华夏成长混合", dao.nameLookup);
        assertTrue(dao.columns.contains("VLU_NAV_GRTH_YEAR"));
    }

    @Test
    void ambiguousFundNameReturnsStructuredLookupStatus() {
        RecordingDao dao = new RecordingDao();
        dao.nameMatches.add(map("COD_FUND", "000001", "NAM_FUND", "成长", "NAM_FUND_SHORT", "成长A"));
        dao.nameMatches.add(map("COD_FUND", "000002", "NAM_FUND", "成长", "NAM_FUND_SHORT", "成长B"));
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("get_fund_profile_facts", map(
                "fund_name", "成长",
                "attributes", Arrays.asList("fund_name")
        ));

        assertEquals(true, result.get("success"));
        assertEquals("ambiguous_fund", result.get("fund_lookup_status"));
        assertEquals(false, result.get("not_found"));
        assertEquals(2, ((List<?>) result.get("fund_candidates")).size());
        assertTrue(((List<?>) result.get("facts")).isEmpty());
    }

    @Test
    void unsupportedPeriodReturnsStructuredStatusInsteadOfFakeFacts() {
        RecordingDao dao = new RecordingDao();
        dao.one.put("COD_FUND", "000001");
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("get_fund_metric_values", map(
                "fund_code", "000001",
                "period", "2w",
                "attributes", Arrays.asList("return_rate")
        ));

        assertEquals(true, result.get("success"));
        assertEquals("unsupported_period", result.get("data_source_status"));
        assertEquals(Arrays.asList("return_rate"), result.get("unsupported_attributes"));
        assertTrue(((List<?>) result.get("closest_supported_periods")).contains("1w"));
        assertTrue(((List<?>) result.get("facts")).isEmpty());
    }

    @Test
    void screenFundsSupportsVolatilityMetric() {
        RecordingDao dao = new RecordingDao();
        dao.many.add(map("COD_FUND", "000001", "NAM_FUND", "A", "VLU_STD_YEAR", new BigDecimal("0.10")));
        dao.many.add(map("COD_FUND", "000002", "NAM_FUND", "B", "VLU_STD_YEAR", new BigDecimal("0.20")));
        FundSkillLogic logic = new FundSkillLogic(dao);

        Map<String, Object> result = logic.execute("screen_funds_by_metric_condition", map(
                "period", "1y",
                "filters", Arrays.asList(map("attribute", "volatility", "operator", "lte", "value", new BigDecimal("0.15")))
        ));

        List<?> rows = (List<?>) result.get("funds");
        assertEquals(1, rows.size());
        assertEquals("000001", ((Map<?, ?>) rows.get(0)).get("fund_code"));
        assertTrue(dao.columns.contains("VLU_STD_YEAR"));
    }

    @Test
    void missingFundCodeStillBlocksJavaSkillExecution() {
        RecordingDao dao = new RecordingDao();
        FundSkillLogic logic = new FundSkillLogic(dao);

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> logic.execute("get_fund_risk_facts", map("period", "1y"))
        );

        assertTrue(error.getMessage().contains("fund_code is required"));
    }

    private static Map<String, Object> map(Object... values) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int index = 0; index < values.length; index += 2) {
            result.put(String.valueOf(values[index]), values[index + 1]);
        }
        return result;
    }

    private static class RecordingDao implements FundSkillDAO {
        final Map<String, Object> one = new LinkedHashMap<>();
        final List<Map<String, Object>> many = new ArrayList<>();
        final List<Map<String, Object>> nameMatches = new ArrayList<>();
        final List<String> columns = new ArrayList<>();
        String nameLookup;

        @Override
        public Map<String, Object> selectFund(String fundCode, List<String> columns) {
            this.columns.addAll(columns);
            return one.isEmpty() ? null : one;
        }

        @Override
        public List<Map<String, Object>> selectFundsByName(String fundName, List<String> columns) {
            this.nameLookup = fundName;
            this.columns.addAll(columns);
            return new ArrayList<>(nameMatches);
        }

        @Override
        public List<Map<String, Object>> selectFunds(List<String> fundCodes, List<String> columns) {
            this.columns.addAll(columns);
            return new ArrayList<>(many);
        }
    }
}
