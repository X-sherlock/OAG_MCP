package com.example.oagmcp;

import com.example.oagmcp.logic.OAGLogic;
import com.example.oagmcp.vo.OAGVO;
import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.util.StringUtils;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.LinkedHashMap;
import java.util.Map;

@SpringBootApplication
public class OAG_MCP {

    private final OAGLogic logic;

    public OAG_MCP(OAGLogic logic) {
        this.logic = logic;
    }

    public static void main(String[] args) {
        SpringApplication.run(OAG_MCP.class, args);
    }

    @ToolMapping(name = "oag_retrieve_context", description = "Plan OAG facts from a semantic_frame. Defaults to agent_plan; use output_view=editor for the full debug plan.")
    @McpTool(name = "oag_retrieve_context", description = "Plan OAG facts from a semantic_frame. Defaults to agent_plan; use output_view=editor for the full debug plan.")
    public Map<String, Object> oagRetrieveContext(
            @McpToolParam(description = "Structured semantic_frame emitted by the upstream intent node.", required = true)
            Map<String, Object> semantic_frame,
            @McpToolParam(description = "Optional original natural language question for compatibility and display.", required = false)
            String question,
            @McpToolParam(description = "Optional intent override. Prefer semantic_frame.intent.", required = false)
            String intent,
            @McpToolParam(description = "OAG domain. Defaults to finance_market.", required = false)
            String domain,
            @McpToolParam(description = "Caller context such as permission scopes or pre-resolved params.", required = false)
            Map<String, Object> user_context,
            @McpToolParam(description = "Output view. Defaults to agent; use editor for full debug plan.", required = false)
            String output_view,
            @McpToolParam(description = "Output options such as output_view=agent or editor.", required = false)
            Map<String, Object> options) {
        OAGVO.RetrieveRequest request = new OAGVO.RetrieveRequest();
        request.question = question;
        request.semanticFrame = semantic_frame == null ? new LinkedHashMap<>() : semantic_frame;
        request.intent = StringUtils.hasText(intent) ? intent : "structured_query";
        request.domain = domain;
        request.userContext = user_context == null ? new LinkedHashMap<>() : user_context;
        request.options = options == null ? new LinkedHashMap<>() : options;
        if (StringUtils.hasText(output_view)) {
            request.options.put("output_view", output_view);
        }
        return logic.retrieveContextView(request);
    }

    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.METHOD)
    public @interface ToolMapping {
        String name();
        String description() default "";
    }
}
