package com.example.oagmcp.logic;

import static com.example.oagmcp.util.Java8Collections.*;

import com.example.oagmcp.dao.OntologyYamlDao;
import com.example.oagmcp.vo.OAGVO;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class SemanticFramePlannerTest {

    private final OAGLogic logic = new OAGLogic(new OntologyYamlDao(), new ObjectMapper(), "finance_market");

    @Test
    void semanticFrameIsRequired() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(new OAGVO.RetrieveRequest());

        assertThat(result.status).isEqualTo("error");
        assertThat(result.errorCode).isEqualTo("SEMANTIC_FRAME_REQUIRED");
        assertThat(result.coverageSummary).containsEntry("coverage_status", "no_coverage");
        assertThat(result.agentPlan).containsKeys("task", "facts", "skill_calls", "coverage", "execution");
    }

    @Test
    void explicitMetricSemanticFrameBuildsFactPlanAndAgentPlan() {
        OAGVO.RetrieveRequest request = request(frame(
                "查询000001近一年最大回撤和夏普",
                "query",
                null,
                listOf("max_drawdown", "sharpe_ratio"),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        ));

        OAGVO.RetrieveResponse result = logic.retrieveContext(request);

        assertThat(result.status).isEqualTo("success");
        assertThat(result.semanticFrameSummary).containsEntry("task_type", "query");
        assertThat(result.factRequirements)
                .extracting(item -> item.attributeName)
                .contains("max_drawdown", "sharpe_ratio");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("get_fund_metric_values");
        assertThat(result.coverageSummary).containsEntry("coverage_status", "full_coverage");
        assertThat(result.taskGraph.get("nodes")).asList().isNotEmpty();
        assertThat(result.agentPlan).containsKeys("task", "targets", "facts", "skill_calls", "coverage", "execution");
    }

    @Test
    void relationExpansionAddsBenchmarkFactsFromGraphEdges() {
        OAGVO.RetrieveRequest request = request(frame(
                "000001近一年收益怎么样",
                "analyze",
                "performance_overview",
                listOf("return_rate"),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        ));

        OAGVO.RetrieveResponse result = logic.retrieveContext(request);

        assertThat(result.factRequirements)
                .filteredOn(item -> "relation_expansion".equals(item.source))
                .extracting(item -> item.attributeName)
                .contains("benchmark_return", "excess_return");
        assertThat(result.factRequirements)
                .filteredOn(item -> "relation_expansion".equals(item.source))
                .filteredOn(item -> !"relation_instance".equals(item.factType))
                .allSatisfy(item -> assertThat(item.expandedFrom).containsKeys("source_attribute", "target_attribute", "relation_type", "reason_zh"));
        assertThat(result.taskGraph.get("edges")).asList()
                .anySatisfy(edge -> assertThat(map(edge)).containsEntry("relation_type", "compared_with"));
    }

    @Test
    void optionalFactsAreCoveredWhenSkillCapabilityExists() {
        OAGVO.RetrieveResponse benchmark = logic.retrieveContext(request(frame(
                "000001近一年收益怎么样",
                "analyze",
                "performance_overview",
                listOf("return_rate"),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        )));
        OAGVO.RetrieveResponse risk = logic.retrieveContext(request(frame(
                "分析000001近一年收益率和最大回撤表现",
                "analyze",
                "risk_overview",
                listOf("return_rate", "max_drawdown"),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        )));

        assertThat(coveredOptionalAttributes(benchmark))
                .contains("benchmark_return", "excess_return");
        assertThat(coveredOptionalAttributes(risk))
                .contains("peer_drawdown_rank", "peer_sharpe_rank", "calmar_ratio");
        assertThat(benchmark.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("get_fund_benchmark_facts");
        assertThat(risk.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("get_fund_peer_ranking_facts", "get_fund_risk_facts");
    }

    @Test
    void benchmarkAndPeerRelationsAreSupportingContext() {
        OAGVO.RetrieveResponse benchmark = logic.retrieveContext(request(frame(
                "000001近一年有没有跑赢基准",
                "compare",
                "benchmark_comparison",
                listOf(),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        )));
        OAGVO.RetrieveResponse peer = logic.retrieveContext(request(frame(
                "000001近一年同类排名怎么样",
                "compare",
                "peer_comparison",
                listOf(),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        )));

        assertThat(benchmark.status).as(benchmark.messageZh).isEqualTo("success");
        assertThat(peer.status).as(peer.messageZh).isEqualTo("success");
        assertThat(benchmark.factRequirements)
                .as("benchmark predicates")
                .extracting(item -> item.predicate)
                .contains("has_benchmark");
        assertThat(benchmark.factRequirements)
                .filteredOn(item -> "has_benchmark".equals(item.predicate))
                .singleElement()
                .satisfies(item -> {
                    assertThat(item.priority).isEqualTo("supporting");
                    assertThat(item.answerVisibility).isEqualTo("supporting_context");
                });
        assertThat(peer.factRequirements)
                .filteredOn(item -> "belongs_to_category".equals(item.predicate))
                .singleElement()
                .satisfies(item -> {
                    assertThat(item.priority).isEqualTo("supporting");
                    assertThat(item.answerVisibility).isEqualTo("supporting_context");
                });
    }

    @Test
    void profileScenarioIncludesCoreObjectRelations() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(frame(
                "000001的基本信息",
                "profile",
                "fund_profile",
                listOf(),
                mapOf(),
                listOf(fundTarget("000001"))
        )));

        assertThat(result.factRequirements)
                .filteredOn(item -> "relation_instance".equals(item.factType))
                .extracting(item -> item.predicate)
                .contains("managed_by", "issued_by", "has_benchmark", "belongs_to_category");
        assertThat(result.taskGraph.get("edges")).asList()
                .anySatisfy(edge -> assertThat(map(edge)).containsEntry("relation_type", "managed_by"));
    }

    @Test
    void holdingScenarioReportsUnsupportedDetailWithoutReadySkill() {
        OAGVO.RetrieveRequest request = request(frame(
                "000001当前持仓如何",
                "query",
                "holding_analysis",
                listOf("stock_name"),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        ));

        OAGVO.RetrieveResponse result = logic.retrieveContext(request);

        assertThat(result.agentPlan).containsEntry("status", "unsupported");
        assertThat(result.factRequirements)
                .extracting(item -> item.factType)
                .contains("holding_fact");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .doesNotContain("get_fund_holding_facts");
        assertThat(result.diagnostics)
                .noneSatisfy(item -> assertThat(item).containsEntry("diagnostic_code", "SKILL_PARAMS_MISSING"));
        assertThat(list(result.agentPlan.get("issues")))
                .noneSatisfy(item -> assertThat(map(item)).containsEntry("diagnostic_code", "SKILL_PARAMS_MISSING"));
    }

    @Test
    void fundSetRankingPlansRankingSkillFromSemanticFrame() {
        Map<String, Object> semanticFrame = frame(
                "近一年收益率最高的基金有哪些",
                "rank",
                "fund_ranking",
                listOf(),
                mapOf("period", "1y"),
                listOf(row(
                        "object_type", "FundSet",
                        "instance_ref", mapOf("fund_universe", "all_funds"),
                        "role", "candidate_set"
                ))
        );
        semanticFrame.put("ranking", listOf(row("attribute", "return_rate", "direction", "desc")));
        semanticFrame.put("limit", 10);

        OAGVO.RetrieveResponse result = logic.retrieveContext(request(semanticFrame));

        assertThat(result.factRequirements)
                .extracting(item -> item.factType)
                .contains("metric_ranking");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("rank_funds_by_metric");
        assertThat(result.agentPlan.get("coverage")).asInstanceOf(org.assertj.core.api.InstanceOfAssertFactories.MAP)
                .containsEntry("coverage_status", "full_coverage");
    }

    @Test
    void screeningAndRecommendationUseFundSetOperations() {
        Map<String, Object> screening = fundSetFrame("筛选近一年最大回撤低于10%的基金", "screen", "fund_screening");
        screening.put("filters", listOf(row("attribute", "max_drawdown", "operator", "<=", "value", 0.1)));
        Map<String, Object> recommendation = fundSetFrame("推荐近一年收益高、回撤低的基金", "recommend", "fund_recommendation");
        recommendation.put("ranking", listOf(row("attribute", "return_rate", "direction", "desc")));
        recommendation.put("filters", listOf(row("attribute", "max_drawdown", "operator", "<=", "value", 0.1)));
        recommendation.put("limit", 10);

        OAGVO.RetrieveResponse screenResult = logic.retrieveContext(request(screening));
        OAGVO.RetrieveResponse recommendResult = logic.retrieveContext(request(recommendation));

        assertThat(screenResult.factRequirements)
                .extracting(item -> item.factType)
                .contains("filter_condition");
        assertThat(screenResult.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("screen_funds_by_metric_condition");
        assertThat(recommendResult.factRequirements)
                .extracting(item -> item.factType)
                .contains("entity_set", "metric_ranking", "filter_condition");
        assertThat(recommendResult.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("recommend_funds_by_risk_return");
    }

    @Test
    void multiFundComparisonKeepsAllTargetsAndDerivedComparisonFact() {
        Map<String, Object> semanticFrame = frame(
                "比较000001和000002近一年收益",
                "compare",
                "fund_comparison",
                listOf("return_rate"),
                mapOf("period", "1y"),
                listOf(
                        row("object_type", "Fund", "instance_ref", mapOf("fund_code", "000001"), "role", "comparison_subject"),
                        row("object_type", "Fund", "instance_ref", mapOf("fund_code", "000002"), "role", "comparison_subject")
                )
        );
        semanticFrame.put("comparison", row("mode", "side_by_side", "attributes", listOf("return_rate"), "target_object_policy", "all_targets"));

        OAGVO.RetrieveResponse result = logic.retrieveContext(request(semanticFrame));

        assertThat(result.factRequirements)
                .filteredOn(item -> "return_rate".equals(item.attributeName))
                .extracting(item -> item.subject.subjectId)
                .contains("Fund:000001", "Fund:000002");
        assertThat(result.factRequirements)
                .extracting(item -> item.factType)
                .contains("comparison_result");
        assertThat(result.taskGraph.get("nodes")).asList()
                .extracting(node -> map(node).get("instance_ref"))
                .anySatisfy(ref -> assertThat(map(ref)).containsEntry("fund_code", "000001"));
    }

    @Test
    void scenarioIntentsMarkUnavailableDetailsUnsupportedButKeepAllocationReady() {
        OAGVO.RetrieveResponse allocation = logic.retrieveContext(request(frame(
                "000001资产配置",
                "query",
                "asset_allocation_analysis",
                listOf(),
                mapOf("report_date", "latest"),
                listOf(fundTarget("000001"))
        )));

        assertThat(allocation.factRequirements)
                .extracting(fact -> fact.factType)
                .contains("allocation_fact");
        assertThat(allocation.candidateInvocations)
                .extracting(invocation -> invocation.skillId)
                .contains("get_fund_allocation_facts");

        List<Map<String, Object>> unsupportedCases = listOf(
                row("intent", "fee_analysis", "fact_type", "fee_fact", "raw_question", "000001费率是多少", "attributes", listOf("fee_value", "fee_type"), "relation_type", "has_fee", "target_object_type", "FundFee"),
                row("intent", "dividend_analysis", "fact_type", "dividend_fact", "raw_question", "000001有没有分红", "attributes", listOf("dividend_per_share")),
                row("intent", "holding_analysis", "fact_type", "holding_fact", "raw_question", "000001股票持仓是什么", "attributes", listOf("stock_name"))
        );

        for (Map<String, Object> item : unsupportedCases) {
            @SuppressWarnings("unchecked")
            List<String> attributes = (List<String>) item.get("attributes");
            Map<String, Object> semanticFrame = frame(
                    String.valueOf(item.get("raw_question")),
                    "query",
                    String.valueOf(item.get("intent")),
                    attributes,
                    mapOf(),
                    listOf(fundTarget("000001"))
            );
            if (item.containsKey("relation_type")) {
                semanticFrame.put("relation_queries", listOf(row(
                        "relation_type", item.get("relation_type"),
                        "target_object_type", item.get("target_object_type"),
                        "attribute_name", attributes.get(0)
                )));
            }
            semanticFrame.put("options", mapOf(
                    "allow_relation_expansion", true,
                    "allow_peer_expansion", true,
                    "include_supporting_context", true
            ));
            OAGVO.RetrieveResponse result = logic.retrieveContext(request(semanticFrame));

            assertThat(result.agentPlan).as(String.valueOf(item.get("intent"))).containsEntry("status", "unsupported");
            assertThat(result.factRequirements)
                    .extracting(fact -> fact.factType)
                    .contains(String.valueOf(item.get("fact_type")));
            assertThat(result.candidateInvocations).isEmpty();
        }
    }

    @Test
    void unknownIntentAndInvalidSemanticFrameAreReported() {
        OAGVO.RetrieveResponse explicitUnknownIntent = logic.retrieveContext(request(frame(
                "查询000001近一年收益",
                "query",
                "unknown_intent",
                listOf("return_rate"),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        )));
        OAGVO.RetrieveResponse unclearUnknownIntent = logic.retrieveContext(request(frame(
                "帮我看看",
                "query",
                "unknown_intent",
                listOf(),
                mapOf(),
                listOf(fundTarget("000001"))
        )));
        OAGVO.RetrieveResponse invalidAttribute = logic.retrieveContext(request(frame(
                "查询未知属性",
                "query",
                null,
                listOf("not_exists"),
                mapOf(),
                listOf(fundTarget("000001"))
        )));
        OAGVO.RetrieveResponse invalidTarget = logic.retrieveContext(request(frame(
                "查询未知对象",
                "query",
                null,
                listOf("return_rate"),
                mapOf(),
                listOf(row("object_type", "NotAType", "instance_ref", mapOf(), "role", "analysis_subject"))
        )));

        assertThat(explicitUnknownIntent.status).isEqualTo("success");
        assertThat(explicitUnknownIntent.warnings)
                .anySatisfy(item -> assertThat(map(item)).containsEntry("warning_code", "UNKNOWN_INTENT"));
        assertThat(unclearUnknownIntent.status).isEqualTo("need_clarification");
        assertThat(unclearUnknownIntent.coverageSummary).containsEntry("coverage_status", "need_clarification");
        assertThat(invalidAttribute.status).isEqualTo("error");
        assertThat(invalidAttribute.errorCode).isEqualTo("SEMANTIC_FRAME_INVALID");
        assertThat(invalidTarget.status).isEqualTo("error");
        assertThat(invalidTarget.errorCode).isEqualTo("SEMANTIC_FRAME_INVALID");
    }

    @Test
    void fundSetTaskWithoutExplicitFundSetReturnsDiagnostic() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(frame(
                "近一年收益率最高的基金有哪些",
                "rank",
                "fund_ranking",
                listOf(),
                mapOf("period", "1y"),
                listOf(fundTarget("000001"))
        )));

        assertThat(result.diagnostics)
                .anySatisfy(item -> assertThat(item).containsEntry("diagnostic_code", "FUNDSET_TARGET_MISSING"));
    }

    private OAGVO.RetrieveRequest request(Map<String, Object> semanticFrame) {
        OAGVO.RetrieveRequest request = new OAGVO.RetrieveRequest();
        request.semanticFrame = semanticFrame;
        request.userContext = new LinkedHashMap<>();
        request.userContext.put("permission_scopes", listOf("fund_public_data:read"));
        return request;
    }

    private Map<String, Object> frame(String rawQuestion,
                                      String taskType,
                                      String intent,
                                      List<String> mentionedAttributes,
                                      Map<String, Object> constraints,
                                      List<Map<String, Object>> targets) {
        Map<String, Object> frame = new LinkedHashMap<>();
        frame.put("domain", "finance_market");
        frame.put("raw_question", rawQuestion);
        frame.put("task_type", taskType);
        frame.put("intent", intent);
        frame.put("target_objects", targets);
        frame.put("constraints", constraints);
        frame.put("mentioned_attributes", mentionedAttributes);
        frame.put("relation_queries", listOf());
        frame.put("filters", listOf());
        frame.put("ranking", listOf());
        frame.put("comparison", mapOf());
        return frame;
    }

    private Map<String, Object> fundTarget(String fundCode) {
        return row("object_type", "Fund", "instance_ref", mapOf("fund_code", fundCode), "role", "analysis_subject");
    }

    private List<String> coveredOptionalAttributes(OAGVO.RetrieveResponse response) {
        java.util.Set<String> coveredIds = new java.util.LinkedHashSet<>();
        for (OAGVO.CandidateInvocation invocation : response.candidateInvocations) {
            coveredIds.addAll(invocation.coversFactRequirements);
        }
        java.util.List<String> attrs = new java.util.ArrayList<>();
        for (OAGVO.FactRequirement fact : response.factRequirements) {
            if ("optional".equals(fact.priority) && coveredIds.contains(fact.factRequirementId) && fact.attributeName != null) {
                attrs.add(fact.attributeName);
            }
        }
        return attrs;
    }

    private Map<String, Object> fundSetFrame(String rawQuestion, String taskType, String intent) {
        return frame(
                rawQuestion,
                taskType,
                intent,
                listOf(),
                mapOf("period", "1y"),
                listOf(row("object_type", "FundSet", "instance_ref", mapOf("fund_universe", "all_funds"), "role", "candidate_set"))
        );
    }

    private static Map<String, Object> row(Object... pairs) {
        Map<String, Object> row = new LinkedHashMap<>();
        for (int index = 0; index + 1 < pairs.length; index += 2) {
            row.put(String.valueOf(pairs[index]), pairs[index + 1]);
        }
        return row;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private List<Object> list(Object value) {
        return (List<Object>) value;
    }
}
