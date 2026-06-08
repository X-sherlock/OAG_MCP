package com.example.oagmcp.logic;

import com.example.oagmcp.dao.OAGDAO;
import com.example.oagmcp.dao.entity.OAGEntity;
import com.example.oagmcp.vo.OAGVO;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class OAGLogic {

    private static final Pattern FUND_CODE_PATTERN = Pattern.compile("(?<!\\d)(\\d{6})(?!\\d)");
    private static final List<String> PERFORMANCE_ATTRIBUTES = List.of(
            "return_rate",
            "benchmark_return",
            "excess_return",
            "max_drawdown",
            "volatility",
            "sharpe_ratio",
            "rank"
    );
    private static final Map<String, String> FACT_TYPE_BY_ATTRIBUTE = Map.ofEntries(
            Map.entry("benchmark_return", "benchmark_metric_value"),
            Map.entry("tracking_error", "benchmark_metric_value"),
            Map.entry("information_ratio", "benchmark_metric_value"),
            Map.entry("excess_return", "excess_metric_value"),
            Map.entry("rank", "peer_rank"),
            Map.entry("peer_return_rank", "peer_rank"),
            Map.entry("peer_risk_rank", "peer_rank"),
            Map.entry("peer_sharpe_rank", "peer_rank"),
            Map.entry("peer_drawdown_rank", "peer_rank"),
            Map.entry("peer_average", "peer_average")
    );
    private static final Map<String, String> PREDICATE_BY_FACT_TYPE = Map.of(
            "benchmark_metric_value", "has_benchmark_metric_value",
            "excess_metric_value", "has_excess_metric_value",
            "peer_rank", "has_peer_rank",
            "peer_average", "has_peer_average",
            "object_profile", "has_profile_fact"
    );

    private final OAGDAO dao;
    private final ObjectMapper objectMapper;
    private final String defaultDomain;

    public OAGLogic(OAGDAO dao,
                    ObjectMapper objectMapper,
                    @Value("${oag.domain:finance_market}") String defaultDomain) {
        this.dao = dao;
        this.objectMapper = objectMapper;
        this.defaultDomain = defaultDomain;
    }

    public OAGVO.RetrieveResponse retrieveContext(OAGVO.RetrieveRequest request) {
        String question = request == null ? "" : safe(request.question);
        String domain = request != null && StringUtils.hasText(request.domain)
                ? request.domain.trim()
                : defaultDomain;
        String intent = request != null && StringUtils.hasText(request.intent)
                ? request.intent.trim()
                : "structured_query";
        OAGVO.RetrieveResponse response = new OAGVO.RetrieveResponse();
        response.domain = domain;
        response.question = question;
        response.intent = intent;

        try {
            if (!StringUtils.hasText(question)) {
                throw new IllegalArgumentException("question must not be empty");
            }
            if (dao.countEnabledDomain(domain) <= 0) {
                throw new IllegalArgumentException("Domain is not enabled: " + domain);
            }

            Map<String, Object> resolvedParams = extractParams(question, request == null ? null : request.userContext);
            List<OAGEntity.IntentProfile> profiles = dao.listIntentProfiles(domain);
            List<OAGEntity.IntentProfile> matchedProfiles = matchIntent(question, resolvedParams, profiles);
            List<String> attributes = inferAttributes(matchedProfiles);
            Map<String, OAGEntity.OAGAttribute> attributeMeta = loadAttributeMeta(domain, attributes);
            List<OAGVO.TargetInstance> targetInstances = buildTargetInstances(resolvedParams);
            List<OAGVO.FactRequirement> factRequirements = buildFactRequirements(
                    matchedProfiles, attributes, attributeMeta, resolvedParams, targetInstances);
            List<OAGVO.FactGroup> factGroups = buildFactGroups(factRequirements);
            List<OAGEntity.SkillCapability> skills = dao.listSkillCapabilities(domain);
            List<OAGVO.CandidateInvocation> invocations = buildCandidateInvocations(skills, factRequirements, resolvedParams);
            List<OAGVO.MissingParam> missingParams = buildMissingParams(factRequirements, resolvedParams);

            response.matchedIntents = intentOutput(matchedProfiles);
            response.matchedAttributes = attributeOutput(attributes, attributeMeta);
            response.resolvedParams = resolvedParams;
            response.targetInstances = targetInstances;
            response.factRequirements = factRequirements;
            response.factGroups = factGroups;
            response.candidateInvocations = invocations;
            response.missingParams = missingParams;
            response.retrievalSummary = buildSummary(resolvedParams, attributes, invocations, factRequirements);
            response.confidence = buildConfidence(resolvedParams, attributes, invocations);
            response.truncation = buildTruncation(factRequirements, invocations);
            response.warnings = buildWarnings(matchedProfiles, attributes, factRequirements, invocations);
            return response;
        } catch (Exception ex) {
            response.status = "error";
            response.warnings.add(ex.getMessage());
            response.confidence.overall = 0.0;
            return response;
        }
    }

    private Map<String, Object> extractParams(String question, Map<String, Object> userContext) {
        Map<String, Object> params = new LinkedHashMap<>();
        if (userContext != null) {
            copyStringParam(userContext, params, "fund_code");
            copyStringParam(userContext, params, "period");
            copyStringParam(userContext, params, "benchmark_code");
        }
        if (!params.containsKey("fund_code")) {
            Matcher matcher = FUND_CODE_PATTERN.matcher(question);
            if (matcher.find()) {
                params.put("fund_code", matcher.group(1));
            }
        }
        if (!params.containsKey("period")) {
            params.put("period", extractPeriod(question));
        }
        return params;
    }

    private List<OAGEntity.IntentProfile> matchIntent(String question,
                                                      Map<String, Object> resolvedParams,
                                                      List<OAGEntity.IntentProfile> profiles) {
        List<OAGEntity.IntentProfile> enabledProfiles = profiles == null ? List.of() : profiles;
        List<OAGEntity.IntentProfile> matched = new ArrayList<>();
        String normalized = normalize(question);
        for (OAGEntity.IntentProfile profile : enabledProfiles) {
            List<String> triggers = jsonStringList(profile.triggerAliasesJson);
            boolean hit = triggers.stream()
                    .filter(StringUtils::hasText)
                    .map(this::normalize)
                    .anyMatch(normalized::contains);
            if (hit) {
                matched.add(profile);
            }
        }
        if (!matched.isEmpty()) {
            matched.sort(Comparator.comparingInt(item -> priorityRank(item.intentName)));
            return List.of(matched.get(0));
        }
        OAGEntity.IntentProfile performance = enabledProfiles.stream()
                .filter(item -> "performance_overview".equals(item.intentName))
                .findFirst()
                .orElseGet(this::fallbackPerformanceProfile);
        if (resolvedParams.containsKey("fund_code")) {
            return List.of(performance);
        }
        return List.of(performance);
    }

    private List<String> inferAttributes(List<OAGEntity.IntentProfile> profiles) {
        LinkedHashSet<String> names = new LinkedHashSet<>();
        for (OAGEntity.IntentProfile profile : profiles) {
            List<String> defaults = jsonStringList(profile.defaultAttributesJson);
            if (defaults.isEmpty() && "performance_overview".equals(profile.intentName)) {
                defaults = PERFORMANCE_ATTRIBUTES;
            }
            names.addAll(defaults);
        }
        if (names.isEmpty()) {
            names.addAll(PERFORMANCE_ATTRIBUTES);
        }
        return new ArrayList<>(names);
    }

    private List<OAGVO.FactRequirement> buildFactRequirements(List<OAGEntity.IntentProfile> matchedProfiles,
                                                              List<String> attributes,
                                                              Map<String, OAGEntity.OAGAttribute> attributeMeta,
                                                              Map<String, Object> resolvedParams,
                                                              List<OAGVO.TargetInstance> targetInstances) {
        LinkedHashSet<String> seen = new LinkedHashSet<>();
        List<OAGVO.FactRequirement> rows = new ArrayList<>();
        String period = stringValue(resolvedParams.get("period"));
        Map<String, Object> instanceRef = targetInstances.isEmpty()
                ? new LinkedHashMap<>()
                : new LinkedHashMap<>(targetInstances.get(0).instanceRef);

        List<Map<String, Object>> templates = factTemplates(matchedProfiles, attributes);
        for (Map<String, Object> template : templates) {
            String attributeName = stringValue(template.get("attribute_name"));
            if (!StringUtils.hasText(attributeName)) {
                continue;
            }
            String requirementId = "fr_" + attributeName + "_" + (StringUtils.hasText(period) ? period : "unspecified_period");
            if (!seen.add(requirementId)) {
                continue;
            }
            String factType = stringValue(template.get("fact_type"));
            if (!StringUtils.hasText(factType)) {
                factType = factTypeForAttribute(attributeName);
            }
            OAGVO.FactRequirement requirement = new OAGVO.FactRequirement();
            requirement.factRequirementId = requirementId;
            requirement.factType = factType;
            requirement.subject = new OAGVO.Subject();
            requirement.subject.objectType = "Fund";
            requirement.subject.instanceRef = instanceRef;
            requirement.predicate = firstText(template.get("predicate"), predicateForFactType(factType));
            requirement.attribute = new OAGVO.Attribute();
            requirement.attribute.attributeName = attributeName;
            OAGEntity.OAGAttribute meta = attributeMeta.get(attributeName);
            requirement.attribute.attributeNameZh = meta == null ? attributeName : firstText(meta.attributeNameZh, attributeName);
            requirement.attribute.objectType = meta == null ? fallbackAttributeObjectType(attributeName) : firstText(meta.objectType, fallbackAttributeObjectType(attributeName));
            if (StringUtils.hasText(period)) {
                requirement.constraints.put("period", period);
            }
            requirement.priority = firstText(template.get("priority"), "optional");
            requirement.reason = firstText(template.get("reason"), "required to answer the current OAG question");
            requirement.source = "inferred_by_intent:" + (matchedProfiles.isEmpty() ? "performance_overview" : matchedProfiles.get(0).intentName);
            requirement.confidence = "required".equals(requirement.priority) ? 0.82 : 0.76;
            rows.add(requirement);
        }
        return rows;
    }

    private List<OAGVO.CandidateInvocation> buildCandidateInvocations(List<OAGEntity.SkillCapability> dbSkills,
                                                                      List<OAGVO.FactRequirement> factRequirements,
                                                                      Map<String, Object> resolvedParams) {
        List<OAGEntity.SkillCapability> skills = dbSkills == null || dbSkills.isEmpty()
                ? fallbackFactSkills()
                : dbSkills;
        List<OAGVO.CandidateInvocation> rows = new ArrayList<>();
        for (OAGEntity.SkillCapability skill : skills) {
            List<OAGVO.FactRequirement> covered = coveredRequirements(skill, factRequirements);
            if (covered.isEmpty()) {
                continue;
            }
            List<String> inputParams = jsonStringList(skill.inputParamsJson);
            List<String> coveredAttributes = unique(covered.stream()
                    .map(item -> item.attribute == null ? "" : item.attribute.attributeName)
                    .filter(StringUtils::hasText)
                    .toList());

            OAGVO.CandidateInvocation invocation = new OAGVO.CandidateInvocation();
            invocation.skillId = skill.skillId;
            invocation.toolName = skill.skillId;
            invocation.priority = covered.stream().anyMatch(item -> "required".equals(item.priority)) ? "primary" : "optional";
            invocation.coversFactRequirements = covered.stream().map(item -> item.factRequirementId).toList();
            for (String inputParam : inputParams) {
                if ("attributes".equals(inputParam)) {
                    invocation.params.put("attributes", coveredAttributes);
                    if (coveredAttributes.isEmpty()) {
                        invocation.missingParams.add("attributes");
                    }
                } else if (StringUtils.hasText(stringValue(resolvedParams.get(inputParam)))) {
                    invocation.params.put(inputParam, resolvedParams.get(inputParam));
                } else {
                    invocation.missingParams.add(inputParam);
                }
            }
            for (OAGVO.FactRequirement item : covered) {
                Map<String, String> expected = new LinkedHashMap<>();
                expected.put("fact_type", item.factType);
                expected.put("attribute_name", item.attribute.attributeName);
                invocation.expectedFacts.add(expected);
            }
            invocation.confidence = invocation.missingParams.isEmpty() ? 0.95 : 0.72;
            invocation.matchReasons = invocationReasons(skill, covered, invocation);
            rows.add(invocation);
        }
        rows.sort(Comparator
                .comparingInt((OAGVO.CandidateInvocation item) -> invocationSortRank(item.skillId, item.priority))
                .thenComparing(item -> item.skillId == null ? "" : item.skillId));
        return rows.stream().limit(6).toList();
    }

    private List<OAGVO.FactGroup> buildFactGroups(List<OAGVO.FactRequirement> factRequirements) {
        List<OAGVO.FactGroup> groups = new ArrayList<>();
        List<String> returnIds = new ArrayList<>();
        List<String> riskIds = new ArrayList<>();
        List<String> peerIds = new ArrayList<>();
        for (OAGVO.FactRequirement item : factRequirements) {
            String attribute = item.attribute == null ? "" : item.attribute.attributeName;
            if (Set.of("return_rate", "benchmark_return", "excess_return").contains(attribute)) {
                returnIds.add(item.factRequirementId);
            }
            if (Set.of("max_drawdown", "volatility", "sharpe_ratio", "sortino_ratio", "calmar_ratio", "downside_risk", "var", "cvar").contains(attribute)) {
                riskIds.add(item.factRequirementId);
            }
            if (Set.of("rank", "peer_return_rank", "peer_risk_rank", "peer_sharpe_rank", "peer_drawdown_rank", "peer_average").contains(attribute)) {
                peerIds.add(item.factRequirementId);
            }
        }
        addGroup(groups, "fg_return_performance", "Return performance facts", "Judge interval return performance", returnIds, "required");
        addGroup(groups, "fg_risk_performance", "Risk performance facts", "Judge interval risk level", riskIds, "required");
        addGroup(groups, "fg_peer_comparison", "Peer comparison facts", "Judge relative peer performance", peerIds, "optional");
        return groups;
    }

    private List<OAGVO.MissingParam> buildMissingParams(List<OAGVO.FactRequirement> factRequirements,
                                                        Map<String, Object> resolvedParams) {
        List<OAGVO.MissingParam> rows = new ArrayList<>();
        for (String paramName : List.of("fund_code", "period")) {
            if (StringUtils.hasText(stringValue(resolvedParams.get(paramName)))) {
                continue;
            }
            List<String> ids = factRequirements.stream()
                    .filter(item -> requirementNeedsParam(item, paramName))
                    .map(item -> item.factRequirementId)
                    .toList();
            if (ids.isEmpty()) {
                continue;
            }
            OAGVO.MissingParam item = new OAGVO.MissingParam();
            item.source = "fact_requirements";
            item.paramName = paramName;
            item.missingParams = List.of(paramName);
            item.factRequirementIds = ids;
            item.suggestedQuestion = "Please provide " + paramName + ".";
            rows.add(item);
        }
        return rows;
    }

    private OAGVO.RetrievalSummary buildSummary(Map<String, Object> resolvedParams,
                                                List<String> attributes,
                                                List<OAGVO.CandidateInvocation> invocations,
                                                List<OAGVO.FactRequirement> factRequirements) {
        OAGVO.RetrievalSummary summary = new OAGVO.RetrievalSummary();
        summary.mainObjectTypes = List.of("Fund");
        summary.mainAttributes = attributes;
        summary.mainSkills = invocations.stream().map(item -> item.skillId).filter(Objects::nonNull).toList();
        summary.period = stringValue(resolvedParams.get("period"));
        summary.fundCode = stringValue(resolvedParams.get("fund_code"));
        summary.factRequirementCount = factRequirements.size();
        summary.candidateInvocationCount = invocations.size();
        return summary;
    }

    private OAGVO.Confidence buildConfidence(Map<String, Object> resolvedParams,
                                             List<String> attributes,
                                             List<OAGVO.CandidateInvocation> invocations) {
        OAGVO.Confidence confidence = new OAGVO.Confidence();
        confidence.entityMatch = StringUtils.hasText(stringValue(resolvedParams.get("fund_code"))) ? 0.98 : 0.3;
        confidence.attributeMatch = attributes.isEmpty() ? 0.0 : 0.82;
        confidence.skillMatch = invocations.isEmpty() ? 0.0 : invocations.stream().mapToDouble(item -> item.confidence).average().orElse(0.0);
        confidence.overall = round3((confidence.entityMatch + confidence.attributeMatch + confidence.skillMatch) / 3.0);
        return confidence;
    }

    private OAGVO.Truncation buildTruncation(List<OAGVO.FactRequirement> factRequirements,
                                             List<OAGVO.CandidateInvocation> invocations) {
        OAGVO.Truncation truncation = new OAGVO.Truncation();
        truncation.limits.put("max_candidate_invocations", 6);
        truncation.originalCounts.put("fact_requirements", factRequirements.size());
        truncation.originalCounts.put("candidate_invocations", invocations.size());
        truncation.returnedCounts.put("fact_requirements", factRequirements.size());
        truncation.returnedCounts.put("candidate_invocations", invocations.size());
        return truncation;
    }

    private List<String> buildWarnings(List<OAGEntity.IntentProfile> matchedProfiles,
                                       List<String> attributes,
                                       List<OAGVO.FactRequirement> requirements,
                                       List<OAGVO.CandidateInvocation> invocations) {
        List<String> warnings = new ArrayList<>();
        if (matchedProfiles.stream().anyMatch(item -> "performance_overview".equals(item.intentName))
                && attributes.containsAll(PERFORMANCE_ATTRIBUTES)) {
            warnings.add("Question did not specify exact metrics; performance_overview defaults were used.");
        }
        Set<String> required = new LinkedHashSet<>();
        for (OAGVO.FactRequirement item : requirements) {
            if ("required".equals(item.priority)) {
                required.add(item.factRequirementId);
            }
        }
        Set<String> covered = new LinkedHashSet<>();
        for (OAGVO.CandidateInvocation invocation : invocations) {
            covered.addAll(invocation.coversFactRequirements);
        }
        required.removeAll(covered);
        if (!required.isEmpty()) {
            warnings.add("Required fact requirements are not covered: " + String.join(",", required));
        }
        return warnings;
    }

    private List<OAGVO.TargetInstance> buildTargetInstances(Map<String, Object> resolvedParams) {
        String fundCode = stringValue(resolvedParams.get("fund_code"));
        if (!StringUtils.hasText(fundCode)) {
            return List.of();
        }
        OAGVO.TargetInstance target = new OAGVO.TargetInstance();
        target.objectType = "Fund";
        target.instanceRef.put("fund_code", fundCode);
        target.role = "analysis_subject";
        target.source = "fund_code_param_inference";
        target.confidence = 0.98;
        return List.of(target);
    }

    private Map<String, OAGEntity.OAGAttribute> loadAttributeMeta(String domain, List<String> names) {
        if (names.isEmpty()) {
            return Map.of();
        }
        Map<String, OAGEntity.OAGAttribute> rows = new LinkedHashMap<>();
        for (OAGEntity.OAGAttribute attribute : dao.listAttributesByNames(domain, names)) {
            rows.put(attribute.attributeName, attribute);
        }
        return rows;
    }

    private List<Map<String, Object>> factTemplates(List<OAGEntity.IntentProfile> profiles, List<String> attributes) {
        List<Map<String, Object>> templates = new ArrayList<>();
        for (OAGEntity.IntentProfile profile : profiles) {
            templates.addAll(jsonObjectList(profile.factRequirementsTemplateJson));
        }
        if (!templates.isEmpty()) {
            return templates;
        }
        for (String attribute : attributes) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("attribute_name", attribute);
            String factType = factTypeForAttribute(attribute);
            item.put("fact_type", factType);
            item.put("predicate", predicateForFactType(factType));
            item.put("priority", Set.of("return_rate", "benchmark_return", "excess_return", "max_drawdown").contains(attribute) ? "required" : "optional");
            item.put("reason", "required to answer the current OAG question");
            templates.add(item);
        }
        return templates;
    }

    private List<OAGVO.FactRequirement> coveredRequirements(OAGEntity.SkillCapability skill,
                                                            List<OAGVO.FactRequirement> factRequirements) {
        Set<String> provides = new LinkedHashSet<>(jsonStringList(skill.providesFactTypesJson));
        Set<String> supportedSubjects = new LinkedHashSet<>(jsonStringList(skill.supportedSubjectTypesJson));
        Set<String> supportedAttributes = new LinkedHashSet<>(jsonStringList(skill.supportedAttributesJson));
        if (provides.isEmpty()) {
            for (String output : jsonStringList(skill.outputAttributesJson)) {
                provides.add(factTypeForAttribute(output));
            }
        }
        if (supportedSubjects.isEmpty() && StringUtils.hasText(skill.targetObjectType)) {
            supportedSubjects.add(skill.targetObjectType);
        }
        if (supportedAttributes.isEmpty()) {
            supportedAttributes.addAll(jsonStringList(skill.outputAttributesJson));
        }

        List<OAGVO.FactRequirement> rows = new ArrayList<>();
        for (OAGVO.FactRequirement requirement : factRequirements) {
            String subjectType = requirement.subject == null ? "" : requirement.subject.objectType;
            String attributeName = requirement.attribute == null ? "" : requirement.attribute.attributeName;
            if (!provides.isEmpty() && !provides.contains(requirement.factType)) {
                continue;
            }
            if (!supportedSubjects.isEmpty() && !supportedSubjects.contains(subjectType)) {
                continue;
            }
            if (!supportedAttributes.isEmpty() && !supportedAttributes.contains(attributeName)) {
                continue;
            }
            rows.add(requirement);
        }
        return rows;
    }

    private List<String> invocationReasons(OAGEntity.SkillCapability skill,
                                           List<OAGVO.FactRequirement> covered,
                                           OAGVO.CandidateInvocation invocation) {
        List<String> reasons = new ArrayList<>();
        reasons.add("target_object_type matched: " + firstText(skill.targetObjectType, "Fund"));
        reasons.add("supported_attributes covered: " + String.join(",", unique(covered.stream()
                .map(item -> item.attribute.attributeName)
                .toList())));
        if (!invocation.params.isEmpty()) {
            reasons.add("required_params resolved: " + String.join(",", invocation.params.keySet()));
        }
        if (!invocation.missingParams.isEmpty()) {
            reasons.add("required_params missing: " + String.join(",", invocation.missingParams));
        }
        return reasons;
    }

    private List<Map<String, Object>> intentOutput(List<OAGEntity.IntentProfile> profiles) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (OAGEntity.IntentProfile profile : profiles) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("intent_name", profile.intentName);
            row.put("intent_name_zh", firstText(profile.intentNameZh, profile.intentName));
            row.put("confidence", 0.85);
            row.put("match_reason", "trigger_or_default_matched");
            rows.add(row);
        }
        return rows;
    }

    private List<Map<String, Object>> attributeOutput(List<String> attributes,
                                                      Map<String, OAGEntity.OAGAttribute> attributeMeta) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (String name : attributes) {
            OAGEntity.OAGAttribute meta = attributeMeta.get(name);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("object_type", meta == null ? fallbackAttributeObjectType(name) : firstText(meta.objectType, fallbackAttributeObjectType(name)));
            row.put("attribute_name", name);
            row.put("attribute_name_zh", meta == null ? name : firstText(meta.attributeNameZh, name));
            row.put("confidence", 0.82);
            row.put("match_reason", "inferred_by_intent");
            rows.add(row);
        }
        return rows;
    }

    private void addGroup(List<OAGVO.FactGroup> groups,
                          String groupId,
                          String groupName,
                          String purpose,
                          List<String> ids,
                          String priority) {
        if (ids.isEmpty()) {
            return;
        }
        OAGVO.FactGroup group = new OAGVO.FactGroup();
        group.groupId = groupId;
        group.groupName = groupName;
        group.purpose = purpose;
        group.factRequirementIds = ids;
        group.priority = priority;
        groups.add(group);
    }

    private boolean requirementNeedsParam(OAGVO.FactRequirement item, String paramName) {
        if ("fund_code".equals(paramName)) {
            return item.subject != null && "Fund".equals(item.subject.objectType);
        }
        if ("period".equals(paramName)) {
            return Set.of("metric_value", "benchmark_metric_value", "excess_metric_value", "peer_rank", "peer_average").contains(item.factType);
        }
        return false;
    }

    private void copyStringParam(Map<String, Object> source, Map<String, Object> target, String key) {
        Object value = source.get(key);
        if (value == null) {
            value = source.get(toCamel(key));
        }
        if (StringUtils.hasText(stringValue(value))) {
            target.put(key, stringValue(value));
        }
    }

    private String extractPeriod(String question) {
        String lower = question.toLowerCase(Locale.ROOT);
        if (lower.contains("1y") || lower.contains("one year")
                || question.contains("\u8fd1\u4e00\u5e74")
                || question.contains("\u4e00\u5e74")
                || question.contains("\u6700\u8fd1\u4e00\u5e74")) {
            return "1y";
        }
        if (lower.contains("ytd") || question.contains("\u4eca\u5e74")) {
            return "ytd";
        }
        if (lower.contains("6m") || question.contains("\u516d\u4e2a\u6708") || question.contains("\u534a\u5e74")) {
            return "6m";
        }
        if (lower.contains("3m") || question.contains("\u4e09\u4e2a\u6708")) {
            return "3m";
        }
        if (lower.contains("1m") || question.contains("\u4e00\u4e2a\u6708")) {
            return "1m";
        }
        return "1y";
    }

    private String factTypeForAttribute(String attributeName) {
        return FACT_TYPE_BY_ATTRIBUTE.getOrDefault(attributeName, "metric_value");
    }

    private String predicateForFactType(String factType) {
        return PREDICATE_BY_FACT_TYPE.getOrDefault(factType, "has_metric_value");
    }

    private String fallbackAttributeObjectType(String attributeName) {
        if (attributeName.contains("rank") || "rank".equals(attributeName)) {
            return "PeerRanking";
        }
        if (Set.of("max_drawdown", "volatility", "sharpe_ratio", "sortino_ratio", "calmar_ratio", "var", "cvar", "downside_risk").contains(attributeName)) {
            return "RiskMetric";
        }
        if (Set.of("fund_name", "fund_category", "fund_company", "fund_manager", "benchmark").contains(attributeName)) {
            return "Fund";
        }
        return "PerformanceMetric";
    }

    private int priorityRank(String intentName) {
        if ("performance_overview".equals(intentName)) {
            return 0;
        }
        if ("benchmark_comparison".equals(intentName)) {
            return 1;
        }
        if ("risk_overview".equals(intentName)) {
            return 2;
        }
        if ("peer_comparison".equals(intentName)) {
            return 3;
        }
        return 9;
    }

    private int invocationSortRank(String skillId, String priority) {
        if ("get_fund_metric_values".equals(skillId)) {
            return 0;
        }
        if ("get_fund_benchmark_facts".equals(skillId)) {
            return 1;
        }
        if ("get_fund_peer_ranking_facts".equals(skillId)) {
            return 2;
        }
        return "primary".equals(priority) ? 3 : 8;
    }

    private OAGEntity.IntentProfile fallbackPerformanceProfile() {
        OAGEntity.IntentProfile profile = new OAGEntity.IntentProfile();
        profile.intentName = "performance_overview";
        profile.intentNameZh = "performance_overview";
        profile.defaultAttributesJson = toJson(PERFORMANCE_ATTRIBUTES);
        profile.primarySkillsJson = toJson(List.of("get_fund_metric_values"));
        profile.secondarySkillsJson = toJson(List.of("get_fund_benchmark_facts"));
        profile.optionalSkillsJson = toJson(List.of("get_fund_peer_ranking_facts"));
        profile.requiredParamsJson = toJson(List.of("fund_code", "period"));
        return profile;
    }

    private List<OAGEntity.SkillCapability> fallbackFactSkills() {
        List<OAGEntity.SkillCapability> rows = new ArrayList<>();
        rows.add(skill("get_fund_metric_values",
                List.of("fund_code", "period", "attributes"),
                List.of("return_rate", "annualized_return", "max_drawdown", "volatility", "standard_deviation", "sharpe_ratio", "sortino_ratio", "calmar_ratio", "var", "cvar", "downside_risk"),
                List.of("metric_value")));
        rows.add(skill("get_fund_benchmark_facts",
                List.of("fund_code", "period", "attributes"),
                List.of("benchmark_return", "excess_return", "tracking_error", "information_ratio"),
                List.of("benchmark_metric_value", "excess_metric_value")));
        rows.add(skill("get_fund_peer_ranking_facts",
                List.of("fund_code", "period", "attributes"),
                List.of("rank", "peer_return_rank", "peer_risk_rank", "peer_sharpe_rank", "peer_drawdown_rank", "peer_average"),
                List.of("peer_rank", "peer_average")));
        return rows;
    }

    private OAGEntity.SkillCapability skill(String skillId,
                                            List<String> inputParams,
                                            List<String> attributes,
                                            List<String> factTypes) {
        OAGEntity.SkillCapability skill = new OAGEntity.SkillCapability();
        skill.skillId = skillId;
        skill.targetObjectType = "Fund";
        skill.inputParamsJson = toJson(inputParams);
        skill.outputAttributesJson = toJson(attributes);
        skill.supportedAttributesJson = toJson(attributes);
        skill.supportedSubjectTypesJson = toJson(List.of("Fund"));
        skill.providesFactTypesJson = toJson(factTypes);
        return skill;
    }

    private List<String> jsonStringList(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> jsonObjectList(String json) {
        if (!StringUtils.hasText(json)) {
            return List.of();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<Map<String, Object>>>() {});
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ignored) {
            return "[]";
        }
    }

    private String normalize(String value) {
        return safe(value).toLowerCase(Locale.ROOT).replaceAll("\\s+", "");
    }

    private String safe(String value) {
        return value == null ? "" : value.trim();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String firstText(Object first, String fallback) {
        String value = stringValue(first);
        return StringUtils.hasText(value) ? value : fallback;
    }

    private String toCamel(String snake) {
        StringBuilder builder = new StringBuilder();
        boolean upper = false;
        for (char ch : snake.toCharArray()) {
            if (ch == '_') {
                upper = true;
            } else if (upper) {
                builder.append(Character.toUpperCase(ch));
                upper = false;
            } else {
                builder.append(ch);
            }
        }
        return builder.toString();
    }

    private List<String> unique(List<String> values) {
        LinkedHashSet<String> set = new LinkedHashSet<>();
        for (String value : values) {
            if (StringUtils.hasText(value)) {
                set.add(value);
            }
        }
        return new ArrayList<>(set);
    }

    private double round3(double value) {
        return Math.round(value * 1000.0) / 1000.0;
    }
}
