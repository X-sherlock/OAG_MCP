package com.example.oagmcp.vo;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class OAGVO {

    public static class RetrieveRequest {
        @JsonProperty("raw_question")
        public String rawQuestion;
        public String question;
        public String intent = "structured_query";
        public String domain;
        @JsonProperty("semantic_frame")
        public Map<String, Object> semanticFrame = new LinkedHashMap<>();
        @JsonProperty("recognized_intents")
        public List<Map<String, Object>> recognizedIntents = new ArrayList<>();
        @JsonProperty("selector_mode")
        public String selectorMode = "rule";
        @JsonProperty("planning_options")
        public Map<String, Object> planningOptions = new LinkedHashMap<>();
        @JsonProperty("user_context")
        public Map<String, Object> userContext = new LinkedHashMap<>();
        public Map<String, Object> options = new LinkedHashMap<>();
    }

    public static class RetrieveResponse {
        public String status = "success";
        public String oagVersion = "v2";
        public String domain;
        public String rawQuestion;
        public String question;
        public String intent;
        public String selectorMode = "rule";
        public Map<String, Object> normalizedSemanticFrame = new LinkedHashMap<>();
        public List<Map<String, Object>> recognizedIntents = new ArrayList<>();
        public Map<String, Object> ontologySubgraph = new LinkedHashMap<>();
        public List<Map<String, Object>> candidateFactPool = new ArrayList<>();
        public List<Map<String, Object>> selectedFacts = new ArrayList<>();
        public Map<String, Object> validationResult = new LinkedHashMap<>();
        public Map<String, Object> dependencyCompletion = new LinkedHashMap<>();
        public List<CandidateInvocation> skillBindings = new ArrayList<>();
        public Map<String, Object> agentPlan = new LinkedHashMap<>();
        public Map<String, Object> editorPlan = new LinkedHashMap<>();
        public List<Map<String, Object>> matchedIntents = new ArrayList<>();
        public List<Map<String, Object>> matchedAttributes = new ArrayList<>();
        public Map<String, Object> resolvedParams = new LinkedHashMap<>();
        public List<TargetInstance> targetInstances = new ArrayList<>();
        public List<FactRequirement> factRequirements = new ArrayList<>();
        public List<FactGroup> factGroups = new ArrayList<>();
        public List<CandidateInvocation> candidateInvocations = new ArrayList<>();
        public RetrievalSummary retrievalSummary = new RetrievalSummary();
        public List<MissingParam> missingParams = new ArrayList<>();
        public Confidence confidence = new Confidence();
        public List<String> warnings = new ArrayList<>();
        public Truncation truncation = new Truncation();
    }

    public static class TargetInstance {
        public String objectType;
        public Map<String, Object> instanceRef = new LinkedHashMap<>();
        public String role;
        public String source;
        public double confidence;
    }

    public static class FactRequirement {
        public String factRequirementId;
        public String factType;
        public Subject subject;
        public String predicate;
        public Attribute attribute;
        public Map<String, Object> constraints = new LinkedHashMap<>();
        public String priority;
        public String reason;
        public String source;
        public double confidence;
        public ExpectedOutput expectedOutput = new ExpectedOutput();
    }

    public static class Subject {
        public String objectType;
        public Map<String, Object> instanceRef = new LinkedHashMap<>();
    }

    public static class Attribute {
        public String attributeName;
        public String attributeNameZh;
        public String objectType;
    }

    public static class ExpectedOutput {
        public boolean valueRequired = true;
        public boolean unitRequired = true;
        public boolean asOfDateRequired = false;
    }

    public static class FactGroup {
        public String groupId;
        public String groupName;
        public String purpose;
        public List<String> factRequirementIds = new ArrayList<>();
        public String priority;
    }

    public static class CandidateInvocation {
        public String capabilityType = "skill";
        public String skillId;
        public String toolType = "SkillCapability";
        public String toolName;
        public String priority;
        public List<String> coversFactRequirements = new ArrayList<>();
        public Map<String, Object> params = new LinkedHashMap<>();
        public List<Map<String, String>> expectedFacts = new ArrayList<>();
        public List<String> missingParams = new ArrayList<>();
        public double confidence;
        public List<String> matchReasons = new ArrayList<>();
    }

    public static class RetrievalSummary {
        public List<String> mainObjectTypes = new ArrayList<>();
        public List<String> mainAttributes = new ArrayList<>();
        public List<String> mainSkills = new ArrayList<>();
        public String period;
        public String fundCode;
        public int factRequirementCount;
        public int candidateInvocationCount;
    }

    public static class MissingParam {
        public String source;
        public String paramName;
        public List<String> missingParams = new ArrayList<>();
        public List<String> factRequirementIds = new ArrayList<>();
        public String suggestedQuestion;
    }

    public static class Confidence {
        public double overall;
        public double entityMatch;
        public double attributeMatch;
        public double skillMatch;
    }

    public static class Truncation {
        public boolean truncated = false;
        public String detailLevel = "compact";
        public Map<String, Integer> limits = new LinkedHashMap<>();
        public Map<String, Integer> originalCounts = new LinkedHashMap<>();
        public Map<String, Integer> returnedCounts = new LinkedHashMap<>();
        public List<String> reasons = new ArrayList<>();
    }
}
