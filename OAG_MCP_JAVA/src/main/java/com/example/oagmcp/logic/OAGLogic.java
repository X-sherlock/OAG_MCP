package com.example.oagmcp.logic;

import static com.example.oagmcp.util.Java8Collections.*;

import com.example.oagmcp.dao.OAGDAO;
import com.example.oagmcp.vo.OAGVO;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Locale;
import java.util.Map;

@Service
public class OAGLogic {

    private final OAGDAO dao;
    private final ObjectMapper objectMapper;
    private final String defaultDomain;

    public OAGLogic(@Qualifier("ontologyYamlDao") OAGDAO dao,
                    ObjectMapper objectMapper,
                    @Value("${oag.domain:finance_market}") String defaultDomain) {
        this.dao = dao;
        this.objectMapper = objectMapper;
        this.defaultDomain = defaultDomain;
    }

    public OAGVO.RetrieveResponse retrieveContext(OAGVO.RetrieveRequest request) {
        return new SemanticFramePlanner(dao, objectMapper, defaultDomain).retrieveContext(request);
    }

    public Map<String, Object> retrieveContextView(OAGVO.RetrieveRequest request) {
        OAGVO.RetrieveResponse response = retrieveContext(request);
        return projectResponse(response, outputView(request));
    }

    public Map<String, Object> projectResponse(OAGVO.RetrieveResponse response, String outputView) {
        if (response == null) {
            return mapOf();
        }
        if ("editor".equals(outputView)) {
            return response.editorPlan;
        }
        return response.agentPlan;
    }

    private String outputView(OAGVO.RetrieveRequest request) {
        Map<String, Object> options = request == null || request.options == null ? mapOf() : request.options;
        Object value = options.get("output_view");
        if (value == null) {
            value = options.get("outputView");
        }
        String outputView = value == null ? "" : String.valueOf(value).trim().toLowerCase(Locale.ROOT);
        return "editor".equals(outputView) ? "editor" : "agent";
    }
}
