package com.example.oagmcp.logic;

import static com.example.oagmcp.util.Java8Collections.*;

import com.example.oagmcp.OAG_MCP;
import com.example.oagmcp.dao.OntologyYamlDao;
import com.example.oagmcp.vo.OAGVO;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class SemanticFramePlannerOntologyYamlTest {

    private final OAGLogic logic = new OAGLogic(new OntologyYamlDao(), new ObjectMapper(), "finance_market");

    @Test
    void performanceOverviewUsesRealIntentTemplateAndSkills() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(mapOf(
                "task_type", "analyze",
                "intent", "performance_overview",
                "question", "000001 近一年综合表现怎么样",
                "constraints", mapOf("period", "1y"),
                "target_objects", listOf(fundTarget("000001"))
        )));

        assertThat(result.status).isEqualTo("success");
        assertThat(result.factRequirements)
                .extracting(item -> item.attributeName)
                .contains("return_rate", "benchmark_return", "excess_return", "max_drawdown", "volatility", "sharpe_ratio");
        assertThat(result.factRequirements)
                .filteredOn(item -> "intent_template".equals(item.source))
                .extracting(item -> item.factType)
                .contains("metric_value", "benchmark_metric_value", "excess_metric_value");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("get_fund_metric_values", "get_fund_benchmark_facts");
        assertThat(result.coverageSummary).containsEntry("coverage_status", "full_coverage");
        assertThat(result.editorPlan).containsKeys("normalized_semantic_frame", "fact_requirements", "task_graph", "coverage_summary");
        assertThat(result.agentPlan).containsKeys("task", "facts", "skill_calls", "coverage", "execution");
    }

    @Test
    void profileTaskUsesOntologyRelationsAsFactRequirements() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(mapOf(
                "task_type", "profile",
                "question", "000001 的基金经理、基金公司和基准是谁",
                "target_objects", listOf(fundTarget("000001"))
        )));

        assertThat(result.status).isEqualTo("success");
        assertThat(result.normalizedSemanticFrame).containsEntry("intent", "fund_profile");
        assertThat(result.factRequirements)
                .filteredOn(item -> "relation_instance".equals(item.factType))
                .extracting(item -> item.predicate)
                .contains("managed_by", "issued_by", "has_benchmark", "belongs_to_category");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("get_fund_profile_facts");
    }

    @Test
    void recommendationUsesRealFundSetSkillDeclarations() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(mapOf(
                "task_type", "recommend",
                "intent", "fund_recommendation",
                "question", "推荐近一年收益高且回撤低的基金",
                "constraints", mapOf("period", "1y", "limit", 5),
                "target_objects", listOf(fundSetTarget()),
                "ranking", listOf(mapOf("attribute", "return_rate", "direction", "desc")),
                "filters", listOf(mapOf("attribute", "max_drawdown", "operator", "<=", "value", 0.2))
        )));

        assertThat(result.status).isEqualTo("success");
        assertThat(result.factRequirements)
                .extracting(item -> item.factType)
                .contains("entity_set", "metric_ranking", "filter_condition");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("recommend_funds_by_risk_return");
        assertThat(result.diagnostics)
                .filteredOn(item -> "FUND_SET_TARGET_MISSING".equals(item.get("diagnostic_code")))
                .isEmpty();
    }

    @Test
    void screenTaskDoesNotApplyAnalyzeOnlyBenchmarkExpansion() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(mapOf(
                "task_type", "screen",
                "intent", "fund_screening",
                "question", "筛选近一年收益率大于 10% 的基金",
                "constraints", mapOf("period", "1y"),
                "target_objects", listOf(fundSetTarget()),
                "filters", listOf(mapOf("attribute", "return_rate", "operator", ">=", "value", 0.1))
        )));

        assertThat(result.status).isEqualTo("success");
        assertThat(result.candidateInvocations)
                .extracting(item -> item.skillId)
                .contains("screen_funds_by_metric_condition");
        assertThat(result.factRequirements)
                .filteredOn(item -> "relation_expansion".equals(item.source))
                .extracting(item -> item.attributeName)
                .doesNotContain("benchmark_return", "excess_return");
    }

    @Test
    void relationExpansionCanBeDisabledBySemanticFrameOptions() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(mapOf(
                "task_type", "analyze",
                "question", "000001 近一年收益率",
                "constraints", mapOf("period", "1y"),
                "mentioned_attributes", listOf("return_rate"),
                "target_objects", listOf(fundTarget("000001")),
                "options", mapOf("allow_relation_expansion", false)
        )));

        assertThat(result.status).isEqualTo("success");
        assertThat(result.factRequirements)
                .filteredOn(item -> "relation_expansion".equals(item.source))
                .isNotEmpty();
        assertThat(result.factRequirements)
                .extracting(item -> item.attributeName)
                .contains("benchmark_return", "excess_return");
    }

    @Test
    void unknownRelationQueryIsSemanticFrameInvalid() {
        OAGVO.RetrieveResponse result = logic.retrieveContext(request(mapOf(
                "task_type", "query",
                "question", "000001 的未知关系",
                "target_objects", listOf(fundTarget("000001")),
                "relation_queries", listOf(mapOf("relation_type", "not_a_relation"))
        )));

        assertThat(result.status).isEqualTo("need_clarification");
        assertThat(result.errorCode).isEqualTo("FACT_REQUIREMENTS_INSUFFICIENT");
        assertThat(result.editorPlan).containsKey("diagnostics");
        assertThat(result.agentPlan).containsKeys("task", "facts", "skill_calls", "coverage", "execution");
    }

    @Test
    void outputViewDefaultsToAgentAndCanSwitchToEditor() {
        OAGVO.RetrieveRequest defaultRequest = request(mapOf(
                "task_type", "query",
                "question", "000001 近一年收益率",
                "constraints", mapOf("period", "1y"),
                "mentioned_attributes", listOf("return_rate"),
                "target_objects", listOf(fundTarget("000001"))
        ));
        Map<String, Object> agent = logic.retrieveContextView(defaultRequest);

        assertThat(agent).containsKeys("task", "targets", "facts", "skill_calls", "coverage", "execution");
        assertThat(agent).doesNotContainKeys("task_graph", "normalized_semantic_frame", "debug_evidence");

        OAGVO.RetrieveRequest editorRequest = request(mapOf(
                "task_type", "query",
                "question", "000001 近一年收益率",
                "constraints", mapOf("period", "1y"),
                "mentioned_attributes", listOf("return_rate"),
                "target_objects", listOf(fundTarget("000001"))
        ));
        editorRequest.options = mapOf("output_view", "editor");
        Map<String, Object> editor = logic.retrieveContextView(editorRequest);

        assertThat(editor).containsKeys("normalized_semantic_frame", "fact_requirements", "candidate_invocations", "task_graph", "coverage_summary");
        assertThat(editor).doesNotContainKey("skill_calls");
    }

    @Test
    void mcpToolDefaultsToAgentView() {
        OAG_MCP app = new OAG_MCP(logic);
        Map<String, Object> result = app.oagRetrieveContext(
                mapOf(
                        "task_type", "query",
                        "question", "000001 近一年收益率",
                        "constraints", mapOf("period", "1y"),
                        "mentioned_attributes", listOf("return_rate"),
                        "target_objects", listOf(fundTarget("000001"))
                ),
                null,
                null,
                "finance_market",
                mapOf("permission_scopes", listOf("fund_public_data:read")),
                null,
                mapOf()
        );

        assertThat(result).containsKeys("skill_calls", "coverage", "execution");
        assertThat(result).doesNotContainKeys("task_graph", "normalized_semantic_frame");
    }

    private OAGVO.RetrieveRequest request(Map<String, Object> frame) {
        OAGVO.RetrieveRequest request = new OAGVO.RetrieveRequest();
        request.semanticFrame = frame;
        request.userContext = mapOf("permission_scopes", listOf("fund_public_data:read"));
        return request;
    }

    private Map<String, Object> fundTarget(String fundCode) {
        return mapOf(
                "object_type", "Fund",
                "instance_ref", mapOf("fund_code", fundCode),
                "role", "analysis_subject"
        );
    }

    private Map<String, Object> fundSetTarget() {
        return mapOf(
                "object_type", "FundSet",
                "instance_ref", mapOf("universe", "all_public_funds"),
                "role", "candidate_set"
        );
    }
}
