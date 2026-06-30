package com.example.oagmcp.vo;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class OAGVO {

    public static class RetrieveRequest {
        public String question;
        public Map<String, Object> semanticFrame = new LinkedHashMap<>();
        public String intent = "structured_query";
        public String domain;
        public Map<String, Object> userContext = new LinkedHashMap<>();
        public Map<String, Object> options = new LinkedHashMap<>();
    }

    public static class RetrieveResponse {
        public String status = "success";
        public String domain;
        public String question;
        public String rawQuestion;
        public String intent;
        public String errorCode;
        public String messageZh;
        public Map<String, Object> semanticFrameSummary = new LinkedHashMap<>();
        public Map<String, Object> normalizedSemanticFrame = new LinkedHashMap<>();
        public List<Map<String, Object>> matchedIntents = new ArrayList<>();
        public List<Map<String, Object>> matchedAttributes = new ArrayList<>();
        public Map<String, Object> resolvedParams = new LinkedHashMap<>();
        public List<TargetInstance> targetInstances = new ArrayList<>();
        public List<FactRequirement> factRequirements = new ArrayList<>();
        public List<FactGroup> factGroups = new ArrayList<>();
        public List<CandidateInvocation> candidateInvocations = new ArrayList<>();
        public Map<String, Object> taskGraph = new LinkedHashMap<>();
        public Map<String, Object> coverageSummary = new LinkedHashMap<>();
        public RetrievalSummary retrievalSummary = new RetrievalSummary();
        public List<MissingParam> missingParams = new ArrayList<>();
        public List<Map<String, Object>> uncoveredFacts = new ArrayList<>();
        public List<Map<String, Object>> diagnostics = new ArrayList<>();
        public Confidence confidence = new Confidence();
        public List<Object> warnings = new ArrayList<>();
        public Truncation truncation = new Truncation();
        public Map<String, Object> editorPlan = new LinkedHashMap<>();
        public Map<String, Object> agentPlan = new LinkedHashMap<>();
        public Map<String, Object> planViews = new LinkedHashMap<>();
    }

    public static class TargetInstance {
        public String targetInstanceId;
        public String objectType;
        public String objectTypeZh;
        public Map<String, Object> instanceRef = new LinkedHashMap<>();
        public String role;
        public String source;
        public double confidence;
        public String displayNameZh;
        public String descriptionZh;
    }

    public static class FactRequirement {
        public String factRequirementId;
        public String factType;
        public String factTypeZh;
        public Subject subject;
        public String predicate;
        public String predicateZh;
        public String targetObjectType;
        public String attributeName;
        public Attribute attribute;
        public Map<String, Object> constraints = new LinkedHashMap<>();
        public String priority;
        public String priorityZh;
        public String reason;
        public String reasonZh;
        public String source;
        public String sourceZh;
        public String answerVisibility;
        public String planningRole;
        public String autoExpandMode;
        public String expansionPriority;
        public String labelZh;
        public String descriptionZh;
        public double confidence;
        public ExpectedOutput expectedOutput = new ExpectedOutput();
        public Map<String, Object> ranking = new LinkedHashMap<>();
        public Map<String, Object> filter = new LinkedHashMap<>();
        public Map<String, Object> expandedFrom = new LinkedHashMap<>();
        public Map<String, Object> objectRelation = new LinkedHashMap<>();
        public Map<String, Object> extra = new LinkedHashMap<>();
        public List<Map<String, Object>> relationExplanations = new ArrayList<>();
    }

    public static class Subject {
        public String objectType;
        public String subjectId;
        public Map<String, Object> instanceRef = new LinkedHashMap<>();
        public String labelZh;
        public Integer targetIndex;
        public String targetRole;
        public String targetInstanceId;
    }

    public static class Attribute {
        public String attributeName;
        public String attributeNameZh;
        public String labelZh;
        public String descriptionZh;
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
        public String invocationId;
        public String skillId;
        public String skillNameZh;
        public String descriptionZh;
        public String toolType = "SkillCapability";
        public String toolName;
        public String priority;
        public List<String> coversFactRequirements = new ArrayList<>();
        public List<String> coveredSubjects = new ArrayList<>();
        public Map<String, Object> params = new LinkedHashMap<>();
        public List<Map<String, String>> expectedFacts = new ArrayList<>();
        public List<String> missingParams = new ArrayList<>();
        public String permissionScope;
        public double coverageScore;
        public int coversRequiredCount;
        public int coversOptionalCount;
        public int coversSupportingCount;
        public int coversDerivedCount;
        public String coverageReasonZh;
        public String uncoveredReasonZh;
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
