package com.example.oagmcp.logic;

import static com.example.oagmcp.util.Java8Collections.*;

import com.example.oagmcp.dao.OntologyYamlDao;
import com.example.oagmcp.vo.OAGVO;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

class AgentPlanExampleExportTest {

    private static final Path OUTPUT_DIR = Paths.get("..", "outputs", "agent_plan_examples");
    private static final Path CASES_FILE = OUTPUT_DIR.resolve("semantic_frame_cases.json");
    private static final Path JAVA_OUTPUT = OUTPUT_DIR.resolve("java_agent_plans.json");
    private static final TypeReference<List<Map<String, Object>>> CASES = new TypeReference<List<Map<String, Object>>>() {};

    private final ObjectMapper mapper = new ObjectMapper();
    private final OAGLogic logic = new OAGLogic(new OntologyYamlDao(), mapper, "finance_market");

    @Test
    void exportJavaAgentPlansForSharedExamples() throws Exception {
        Files.createDirectories(OUTPUT_DIR);
        Path casesFile = Paths.get(System.getProperty("oag.agentPlan.cases", CASES_FILE.toString()));
        Path javaOutput = Paths.get(System.getProperty("oag.agentPlan.javaOutput", JAVA_OUTPUT.toString()));
        List<Map<String, Object>> rows = mapper.readValue(casesFile.toFile(), CASES).stream()
                .map(this::withAgentPlan)
                .collect(Collectors.toList());
        Files.createDirectories(javaOutput.getParent());
        mapper.writerWithDefaultPrettyPrinter().writeValue(javaOutput.toFile(), rows);
    }

    private Map<String, Object> withAgentPlan(Map<String, Object> example) {
        OAGVO.RetrieveRequest request = new OAGVO.RetrieveRequest();
        request.semanticFrame = map(example.get("semantic_frame"));
        request.userContext = example.containsKey("user_context")
                ? map(example.get("user_context"))
                : mapOf("permission_scopes", listOf("fund_public_data:read"));
        request.options = mapOf("output_view", "agent");

        Map<String, Object> row = new LinkedHashMap<>();
        row.put("case_id", example.get("case_id"));
        row.put("title", example.get("title"));
        row.put("semantic_frame", request.semanticFrame);
        row.put("agent_plan", logic.retrieveContextView(request));
        return row;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }
}
