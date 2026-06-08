package com.example.oagmcp;

import com.example.oagmcp.logic.OAGLogic;
import com.example.oagmcp.vo.OAGVO;
import org.mybatis.spring.annotation.MapperScan;
import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.LinkedHashMap;
import java.util.Map;

@SpringBootApplication
@MapperScan("com.example.oagmcp.dao")
public class OAG_MCP {

    private final OAGLogic logic;

    public OAG_MCP(OAGLogic logic) {
        this.logic = logic;
    }

    public static void main(String[] args) {
        SpringApplication.run(OAG_MCP.class, args);
    }

    @ToolMapping(name = "oag_retrieve_context", description = "Retrieve compact OAG context for a fund analysis question.")
    @McpTool(name = "oag_retrieve_context", description = "Retrieve compact OAG context for a fund analysis question.")
    public OAGVO.RetrieveResponse oagRetrieveContext(
            @McpToolParam(description = "Natural language question, for example: analyze 000001 over the last year.", required = true)
            String question,
            @McpToolParam(description = "Intent name. Defaults to structured_query.", required = false)
            String intent,
            @McpToolParam(description = "OAG domain. Defaults to finance_market.", required = false)
            String domain,
            @McpToolParam(description = "Caller context such as permission scopes or pre-resolved params.", required = false)
            Map<String, Object> user_context,
            @McpToolParam(description = "Output options. compact is the default detail level.", required = false)
            Map<String, Object> options) {
        OAGVO.RetrieveRequest request = new OAGVO.RetrieveRequest();
        request.question = question;
        request.intent = intent == null || intent.isBlank() ? "structured_query" : intent;
        request.domain = domain;
        request.userContext = user_context == null ? new LinkedHashMap<>() : user_context;
        request.options = options == null ? new LinkedHashMap<>() : options;
        return logic.retrieveContext(request);
    }

    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.METHOD)
    public @interface ToolMapping {
        String name();
        String description() default "";
    }
}
