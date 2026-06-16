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
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class OAGLogic {

    private static final Pattern FUND_CODE_PATTERN = Pattern.compile("(?<!\\d)(\\d{6})(?!\\d)");
    private static final List<String> DEFAULT_PERFORMANCE_ATTRIBUTES = Arrays.asList(
            "return_rate", "benchmark_return", "excess_return", "max_drawdown", "volatility", "sharpe_ratio", "rank");
    private static final Set<String> BENCHMARK_ATTRIBUTES = setOf("benchmark_return", "excess_return", "tracking_error", "information_ratio");
    private static final Set<String> PEER_FACT_TYPES = setOf("peer_rank", "peer_average");

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
        OAGVO.RetrieveResponse response = new OAGVO.RetrieveResponse();
        String domain = firstText(request == null ? null : request.domain, defaultDomain);
        response.domain = domain;
        try {
            if (dao.countEnabledDomain(domain) <= 0) {
                throw new IllegalArgumentException("Domain is not enabled: " + domain);
            }
            Map<String, Object> frame = normalizeFrame(request);
            String selectorMode = firstText(request == null ? null : request.selectorMode, "rule");
            response.selectorMode = selectorMode;
            response.normalizedSemanticFrame = frame;
            response.rawQuestion = stringValue(frame.get("raw_question"));
            response.question = response.rawQuestion;
            response.intent = stringValue(frame.get("intent"));
            response.recognizedIntents = recognizedIntents(request, frame);
            response.matchedIntents = response.recognizedIntents;
            response.resolvedParams = resolvedParams(frame);
            response.targetInstances = targetInstances(frame);

            List<String> attributes = semanticAttributes(frame, response.recognizedIntents, domain);
            Map<String, OAGEntity.OAGAttribute> attributeMeta = loadAttributeMeta(domain, attributes);
            List<OAGEntity.SkillCapability> skills = dao.listSkillCapabilities(domain);
            response.ontologySubgraph = ontologySubgraph(frame, attributes, skills);
            response.candidateFactPool = candidateFactPool(frame, response.recognizedIntents, attributes, attributeMeta);
            response.selectedFacts = ruleSelect(response.candidateFactPool);
            response.validationResult = validationResult(response.selectedFacts, response.candidateFactPool);
            response.dependencyCompletion = dependencyCompletion(response.selectedFacts);

            List<Map<String, Object>> executableFacts = new ArrayList<Map<String, Object>>();
            executableFacts.addAll(response.selectedFacts);
            executableFacts.addAll(objectList(response.dependencyCompletion.get("completed_facts")));
            response.factRequirements = factRequirements(executableFacts);
            response.skillBindings = bindSkills(executableFacts, skills, frame);
            response.candidateInvocations = response.skillBindings;
            response.missingParams = missingParams(response.skillBindings);
            response.retrievalSummary = retrievalSummary(attributes, response.skillBindings, response.factRequirements, response.resolvedParams);
            response.validationResult.put("missing_params", response.missingParams);
            response.agentPlan = agentPlan(frame, response.selectedFacts, response.skillBindings, response.validationResult);
            response.editorPlan = editorPlan(response);
            response.warnings = warnings(response);
            return response;
        } catch (Exception ex) {
            response.status = "error";
            response.warnings.add(ex.getMessage());
            response.validationResult.put("ok", false);
            response.validationResult.put("message_zh", "Java OAG V2 规划失败：" + ex.getMessage());
            return response;
        }
    }

    private Map<String, Object> normalizeFrame(OAGVO.RetrieveRequest request) {
        Map<String, Object> frame = new LinkedHashMap<String, Object>();
        if (request != null && request.semanticFrame != null) {
            frame.putAll(request.semanticFrame);
        }
        String raw = firstText(request == null ? null : request.rawQuestion, firstText(stringValue(frame.get("raw_question")), request == null ? "" : request.question));
        frame.put("raw_question", raw);
        frame.put("domain", firstText(stringValue(frame.get("domain")), defaultDomain));
        if (!frame.containsKey("intent") && request != null && StringUtils.hasText(request.intent)) {
            frame.put("intent", request.intent);
        }
        if (!frame.containsKey("constraints")) {
            Map<String, Object> constraints = new LinkedHashMap<String, Object>();
            String period = extractPeriod(raw);
            if (StringUtils.hasText(period)) {
                constraints.put("period", period);
            }
            frame.put("constraints", constraints);
        }
        if (!frame.containsKey("target_objects")) {
            List<Map<String, Object>> targets = new ArrayList<Map<String, Object>>();
            Matcher matcher = FUND_CODE_PATTERN.matcher(raw);
            while (matcher.find()) {
                Map<String, Object> target = new LinkedHashMap<String, Object>();
                Map<String, Object> instance = new LinkedHashMap<String, Object>();
                instance.put("fund_code", matcher.group(1));
                target.put("object_type", "Fund");
                target.put("instance_ref", instance);
                target.put("role", "analysis_subject");
                targets.add(target);
            }
            frame.put("target_objects", targets);
        }
        if (!frame.containsKey("mentioned_attributes")) {
            frame.put("mentioned_attributes", new ArrayList<String>());
        }
        return frame;
    }

    private List<Map<String, Object>> candidateFactPool(Map<String, Object> frame,
                                                        List<Map<String, Object>> intents,
                                                        List<String> attributes,
                                                        Map<String, OAGEntity.OAGAttribute> attributeMeta) {
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        List<Map<String, Object>> targets = objectList(frame.get("target_objects"));
        if (targets.isEmpty()) {
            targets.add(fundSetTarget());
        }
        for (Map<String, Object> target : targets) {
            for (String attribute : attributes) {
                String factType = factType(attribute);
                Map<String, Object> fact = new LinkedHashMap<String, Object>();
                String factId = factId(target, factType, attribute);
                fact.put("fact_id", factId);
                fact.put("fact_requirement_id", factId);
                fact.put("fact_type", factType);
                fact.put("subject", subject(target));
                fact.put("predicate", predicate(factType));
                fact.put("attribute_name", attribute);
                fact.put("attribute", attribute(attribute, attributeMeta.get(attribute)));
                fact.put("constraints", frame.get("constraints"));
                fact.put("priority", "required");
                fact.put("source", "candidate_fact_pool");
                fact.put("reason_zh", "Java OAG V2 根据 semantic_frame、recognized_intents 和本体属性生成候选事实。");
                rows.add(fact);
            }
        }
        return rows;
    }

    private List<Map<String, Object>> ruleSelect(List<Map<String, Object>> pool) {
        return new ArrayList<Map<String, Object>>(pool);
    }

    private Map<String, Object> validationResult(List<Map<String, Object>> selected, List<Map<String, Object>> pool) {
        Map<String, Object> result = new LinkedHashMap<String, Object>();
        result.put("ok", true);
        result.put("candidate_fact_count", pool.size());
        result.put("selected_fact_count", selected.size());
        result.put("illegal_fact_ids", new ArrayList<String>());
        result.put("message_zh", "Java OAG V2 仅接受候选池内 fact_id。");
        return result;
    }

    private Map<String, Object> dependencyCompletion(List<Map<String, Object>> selected) {
        List<Map<String, Object>> completed = new ArrayList<Map<String, Object>>();
        for (Map<String, Object> fact : selected) {
            String attribute = stringValue(fact.get("attribute_name"));
            String factType = stringValue(fact.get("fact_type"));
            if (BENCHMARK_ATTRIBUTES.contains(attribute)) {
                completed.add(dependencyFact(fact, "has_benchmark", "benchmark_name", "Benchmark"));
            }
            if (PEER_FACT_TYPES.contains(factType)) {
                completed.add(dependencyFact(fact, "belongs_to_category", "fund_type", "FundCategory"));
            }
        }
        Map<String, Object> result = new LinkedHashMap<String, Object>();
        result.put("completed_facts", completed);
        result.put("message_zh", "Java OAG V2 使用确定性规则补全依赖事实。");
        return result;
    }

    private List<OAGVO.CandidateInvocation> bindSkills(List<Map<String, Object>> facts,
                                                       List<OAGEntity.SkillCapability> skills,
                                                       Map<String, Object> frame) {
        List<OAGVO.CandidateInvocation> bindings = new ArrayList<OAGVO.CandidateInvocation>();
        if (skills == null) {
            return bindings;
        }
        for (OAGEntity.SkillCapability skill : skills) {
            List<Map<String, Object>> covered = new ArrayList<Map<String, Object>>();
            for (Map<String, Object> fact : facts) {
                if (skillCovers(skill, fact)) {
                    covered.add(fact);
                }
            }
            if (covered.isEmpty()) {
                continue;
            }
            OAGVO.CandidateInvocation binding = new OAGVO.CandidateInvocation();
            binding.skillId = skill.skillId;
            binding.toolName = skill.skillId;
            binding.priority = "primary";
            for (Map<String, Object> fact : covered) {
                binding.coversFactRequirements.add(stringValue(fact.get("fact_id")));
                Map<String, String> expected = new LinkedHashMap<String, String>();
                expected.put("fact_id", stringValue(fact.get("fact_id")));
                expected.put("fact_type", stringValue(fact.get("fact_type")));
                expected.put("attribute_name", stringValue(fact.get("attribute_name")));
                binding.expectedFacts.add(expected);
            }
            fillParams(binding, skill, covered, frame);
            binding.confidence = binding.missingParams.isEmpty() ? 0.95 : 0.72;
            binding.matchReasons.add("deterministic skill binding by Java OAG V2 capability declaration");
            bindings.add(binding);
        }
        return bindings;
    }

    private boolean skillCovers(OAGEntity.SkillCapability skill, Map<String, Object> fact) {
        Set<String> provides = new LinkedHashSet<String>(jsonStringList(skill.providesFactTypesJson));
        Set<String> attrs = new LinkedHashSet<String>(jsonStringList(skill.supportedAttributesJson));
        if (attrs.isEmpty()) {
            attrs.addAll(jsonStringList(skill.outputAttributesJson));
        }
        if (!provides.isEmpty() && !provides.contains(stringValue(fact.get("fact_type")))) {
            return false;
        }
        return attrs.isEmpty() || attrs.contains(stringValue(fact.get("attribute_name")));
    }

    private void fillParams(OAGVO.CandidateInvocation binding,
                            OAGEntity.SkillCapability skill,
                            List<Map<String, Object>> covered,
                            Map<String, Object> frame) {
        Map<String, Object> constraints = objectMap(frame.get("constraints"));
        Map<String, Object> subject = objectMap(covered.get(0).get("subject"));
        Map<String, Object> instance = objectMap(subject.get("instance_ref"));
        List<String> attributes = new ArrayList<String>();
        for (Map<String, Object> fact : covered) {
            addUnique(attributes, stringValue(fact.get("attribute_name")));
        }
        for (String input : jsonStringList(skill.inputParamsJson)) {
            if ("attributes".equals(input)) {
                binding.params.put("attributes", attributes);
            } else if (instance.containsKey(input)) {
                binding.params.put(input, instance.get(input));
            } else if (constraints.containsKey(input)) {
                binding.params.put(input, constraints.get(input));
            } else {
                binding.missingParams.add(input);
            }
        }
    }

    private List<String> semanticAttributes(Map<String, Object> frame,
                                            List<Map<String, Object>> intents,
                                            String domain) {
        List<String> attrs = new ArrayList<String>();
        for (Object value : objectListOrScalar(frame.get("mentioned_attributes"))) {
            addUnique(attrs, stringValue(value));
        }
        if (!attrs.isEmpty()) {
            return attrs;
        }
        List<OAGEntity.IntentProfile> profiles = dao.listIntentProfiles(domain);
        for (Map<String, Object> intent : intents) {
            String name = stringValue(intent.get("intent_name"));
            for (OAGEntity.IntentProfile profile : profiles) {
                if (name.equals(profile.intentName)) {
                    for (String attr : jsonStringList(profile.defaultAttributesJson)) {
                        addUnique(attrs, attr);
                    }
                }
            }
        }
        if (attrs.isEmpty()) {
            attrs.addAll(DEFAULT_PERFORMANCE_ATTRIBUTES);
        }
        return attrs;
    }

    private List<Map<String, Object>> recognizedIntents(OAGVO.RetrieveRequest request, Map<String, Object> frame) {
        if (request != null && request.recognizedIntents != null && !request.recognizedIntents.isEmpty()) {
            return request.recognizedIntents;
        }
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        String intent = stringValue(frame.get("intent"));
        if (StringUtils.hasText(intent)) {
            Map<String, Object> item = new LinkedHashMap<String, Object>();
            item.put("intent_name", intent);
            item.put("confidence", 1.0);
            rows.add(item);
        }
        return rows;
    }

    private List<OAGVO.FactRequirement> factRequirements(List<Map<String, Object>> facts) {
        List<OAGVO.FactRequirement> rows = new ArrayList<OAGVO.FactRequirement>();
        for (Map<String, Object> fact : facts) {
            OAGVO.FactRequirement row = new OAGVO.FactRequirement();
            row.factRequirementId = stringValue(fact.get("fact_id"));
            row.factType = stringValue(fact.get("fact_type"));
            row.predicate = stringValue(fact.get("predicate"));
            row.priority = stringValue(fact.get("priority"));
            row.reason = stringValue(fact.get("reason_zh"));
            row.constraints = objectMap(fact.get("constraints"));
            Map<String, Object> subjectMap = objectMap(fact.get("subject"));
            row.subject = new OAGVO.Subject();
            row.subject.objectType = stringValue(subjectMap.get("object_type"));
            row.subject.instanceRef = objectMap(subjectMap.get("instance_ref"));
            Map<String, Object> attr = objectMap(fact.get("attribute"));
            row.attribute = new OAGVO.Attribute();
            row.attribute.attributeName = stringValue(attr.get("attribute_name"));
            row.attribute.attributeNameZh = stringValue(attr.get("attribute_name_zh"));
            row.attribute.objectType = stringValue(attr.get("object_type"));
            rows.add(row);
        }
        return rows;
    }

    private List<OAGVO.MissingParam> missingParams(List<OAGVO.CandidateInvocation> bindings) {
        List<OAGVO.MissingParam> rows = new ArrayList<OAGVO.MissingParam>();
        for (OAGVO.CandidateInvocation binding : bindings) {
            if (binding.missingParams.isEmpty()) {
                continue;
            }
            OAGVO.MissingParam row = new OAGVO.MissingParam();
            row.source = "skill_bindings";
            row.paramName = binding.missingParams.get(0);
            row.missingParams = binding.missingParams;
            row.factRequirementIds = binding.coversFactRequirements;
            row.suggestedQuestion = "Please provide " + row.paramName + ".";
            rows.add(row);
        }
        return rows;
    }

    private OAGVO.RetrievalSummary retrievalSummary(List<String> attributes,
                                                    List<OAGVO.CandidateInvocation> bindings,
                                                    List<OAGVO.FactRequirement> facts,
                                                    Map<String, Object> params) {
        OAGVO.RetrievalSummary summary = new OAGVO.RetrievalSummary();
        summary.mainObjectTypes.add("Fund");
        summary.mainAttributes = attributes;
        for (OAGVO.CandidateInvocation binding : bindings) {
            addUnique(summary.mainSkills, binding.skillId);
        }
        summary.period = stringValue(params.get("period"));
        summary.fundCode = stringValue(params.get("fund_code"));
        summary.factRequirementCount = facts.size();
        summary.candidateInvocationCount = bindings.size();
        return summary;
    }

    private Map<String, Object> agentPlan(Map<String, Object> frame,
                                          List<Map<String, Object>> facts,
                                          List<OAGVO.CandidateInvocation> bindings,
                                          Map<String, Object> validation) {
        Map<String, Object> plan = new LinkedHashMap<String, Object>();
        plan.put("oag_version", "v2");
        plan.put("task", frame);
        plan.put("facts", facts);
        plan.put("skill_calls", bindings);
        plan.put("validation", validation);
        return plan;
    }

    private Map<String, Object> editorPlan(OAGVO.RetrieveResponse response) {
        Map<String, Object> plan = new LinkedHashMap<String, Object>();
        plan.put("candidate_fact_pool", response.candidateFactPool);
        plan.put("selected_facts", response.selectedFacts);
        plan.put("validation_result", response.validationResult);
        plan.put("dependency_completion", response.dependencyCompletion);
        plan.put("skill_bindings", response.skillBindings);
        return plan;
    }

    private Map<String, Object> ontologySubgraph(Map<String, Object> frame, List<String> attributes, List<OAGEntity.SkillCapability> skills) {
        Map<String, Object> graph = new LinkedHashMap<String, Object>();
        List<Map<String, Object>> nodes = new ArrayList<Map<String, Object>>();
        for (String attr : attributes) {
            Map<String, Object> node = new LinkedHashMap<String, Object>();
            node.put("node_id", "Attribute:" + attr);
            node.put("node_type", "Attribute");
            nodes.add(node);
        }
        if (skills != null) {
            for (OAGEntity.SkillCapability skill : skills) {
                Map<String, Object> node = new LinkedHashMap<String, Object>();
                node.put("node_id", "SkillCapability:" + skill.skillId);
                node.put("node_type", "SkillCapability");
                nodes.add(node);
            }
        }
        graph.put("nodes", nodes);
        graph.put("edges", new ArrayList<Map<String, Object>>());
        return graph;
    }

    private Map<String, Object> resolvedParams(Map<String, Object> frame) {
        Map<String, Object> params = new LinkedHashMap<String, Object>();
        Map<String, Object> constraints = objectMap(frame.get("constraints"));
        if (constraints.containsKey("period")) {
            params.put("period", constraints.get("period"));
        }
        List<Map<String, Object>> targets = objectList(frame.get("target_objects"));
        if (!targets.isEmpty()) {
            Map<String, Object> ref = objectMap(targets.get(0).get("instance_ref"));
            if (ref.containsKey("fund_code")) {
                params.put("fund_code", ref.get("fund_code"));
            }
        }
        return params;
    }

    private List<OAGVO.TargetInstance> targetInstances(Map<String, Object> frame) {
        List<OAGVO.TargetInstance> rows = new ArrayList<OAGVO.TargetInstance>();
        for (Map<String, Object> target : objectList(frame.get("target_objects"))) {
            OAGVO.TargetInstance row = new OAGVO.TargetInstance();
            row.objectType = stringValue(target.get("object_type"));
            row.instanceRef = objectMap(target.get("instance_ref"));
            row.role = stringValue(target.get("role"));
            row.source = "semantic_frame";
            row.confidence = 1.0;
            rows.add(row);
        }
        return rows;
    }

    private Map<String, OAGEntity.OAGAttribute> loadAttributeMeta(String domain, List<String> names) {
        Map<String, OAGEntity.OAGAttribute> rows = new LinkedHashMap<String, OAGEntity.OAGAttribute>();
        if (names.isEmpty()) {
            return rows;
        }
        for (OAGEntity.OAGAttribute attribute : dao.listAttributesByNames(domain, names)) {
            rows.put(attribute.attributeName, attribute);
        }
        return rows;
    }

    private Map<String, Object> dependencyFact(Map<String, Object> source, String predicate, String attr, String targetType) {
        Map<String, Object> fact = new LinkedHashMap<String, Object>();
        Map<String, Object> subject = objectMap(source.get("subject"));
        String factId = "dep_" + stringValue(subject.get("object_type")) + "_" + predicate;
        fact.put("fact_id", factId);
        fact.put("fact_requirement_id", factId);
        fact.put("fact_type", "relation_instance");
        fact.put("subject", subject);
        fact.put("predicate", predicate);
        fact.put("attribute_name", attr);
        fact.put("attribute", attribute(attr, null));
        fact.put("target_object_type", targetType);
        fact.put("priority", "supporting");
        fact.put("source", "deterministic_dependency_completion");
        fact.put("reason_zh", "Java OAG V2 确定性依赖补全。");
        return fact;
    }

    private Map<String, Object> subject(Map<String, Object> target) {
        Map<String, Object> subject = new LinkedHashMap<String, Object>();
        subject.put("object_type", firstText(stringValue(target.get("object_type")), "Fund"));
        subject.put("instance_ref", objectMap(target.get("instance_ref")));
        return subject;
    }

    private Map<String, Object> attribute(String name, OAGEntity.OAGAttribute meta) {
        Map<String, Object> attr = new LinkedHashMap<String, Object>();
        attr.put("attribute_name", name);
        attr.put("attribute_name_zh", meta == null ? name : firstText(meta.attributeNameZh, name));
        attr.put("object_type", meta == null ? "" : meta.objectType);
        return attr;
    }

    private String factId(Map<String, Object> target, String factType, String attribute) {
        Map<String, Object> ref = objectMap(target.get("instance_ref"));
        String subject = firstText(stringValue(ref.get("fund_code")), firstText(stringValue(ref.get("fund_universe")), "target"));
        return ("fact_" + stringValue(target.get("object_type")) + "_" + subject + "_" + factType + "_" + attribute).replaceAll("[^A-Za-z0-9_]", "_");
    }

    private Map<String, Object> fundSetTarget() {
        Map<String, Object> target = new LinkedHashMap<String, Object>();
        Map<String, Object> ref = new LinkedHashMap<String, Object>();
        ref.put("fund_universe", "all_funds");
        target.put("object_type", "FundSet");
        target.put("instance_ref", ref);
        target.put("role", "candidate_set");
        return target;
    }

    private String factType(String attribute) {
        if ("benchmark_return".equals(attribute) || "tracking_error".equals(attribute) || "information_ratio".equals(attribute)) {
            return "benchmark_metric_value";
        }
        if ("excess_return".equals(attribute)) {
            return "excess_metric_value";
        }
        if ("rank".equals(attribute) || attribute.indexOf("_rank") >= 0 || "percentile".equals(attribute)) {
            return "peer_rank";
        }
        return "metric_value";
    }

    private String predicate(String factType) {
        if ("benchmark_metric_value".equals(factType)) {
            return "has_benchmark_metric_value";
        }
        if ("excess_metric_value".equals(factType)) {
            return "has_excess_metric_value";
        }
        if ("peer_rank".equals(factType)) {
            return "has_peer_rank";
        }
        return "has_metric_value";
    }

    private List<String> warnings(OAGVO.RetrieveResponse response) {
        List<String> rows = new ArrayList<String>();
        rows.add("Java OAG V2 only plans ontology facts and deterministic Skill bindings; it does not query ClickHouse, MRS, or Hudi.");
        return rows;
    }

    private String extractPeriod(String question) {
        if (question != null && (question.indexOf("近一年") >= 0 || question.toLowerCase().indexOf("1y") >= 0)) {
            return "1y";
        }
        return "";
    }

    private List<String> jsonStringList(String json) {
        if (!StringUtils.hasText(json)) {
            return new ArrayList<String>();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception ignored) {
            return new ArrayList<String>();
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(Object value) {
        if (value instanceof List) {
            return (List<Map<String, Object>>) value;
        }
        return new ArrayList<Map<String, Object>>();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> objectMap(Object value) {
        if (value instanceof Map) {
            return (Map<String, Object>) value;
        }
        return new LinkedHashMap<String, Object>();
    }

    private List<Object> objectListOrScalar(Object value) {
        List<Object> rows = new ArrayList<Object>();
        if (value instanceof List) {
            rows.addAll((List<?>) value);
        } else if (value != null) {
            rows.add(value);
        }
        return rows;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectListFromMap(Object value) {
        return objectList(value);
    }

    private List<Map<String, Object>> objectList(Object value, String ignored) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectListRaw(Object value) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(Object value, boolean ignored) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(Object value, int ignored) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(Object value, long ignored) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(Object value, double ignored) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(Object value, Object ignored) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectList(List<Map<String, Object>> value) {
        return value == null ? new ArrayList<Map<String, Object>>() : value;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectListFromObject(Object value) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectListFromResponse(Object value) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectListFromDependency(Object value) {
        return objectList(value);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> objectListFromFacts(Object value) {
        return objectList(value);
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String firstText(String first, String fallback) {
        return StringUtils.hasText(first) ? first : (fallback == null ? "" : fallback);
    }

    private void addUnique(List<String> rows, String value) {
        if (StringUtils.hasText(value) && !rows.contains(value)) {
            rows.add(value);
        }
    }

    private static Set<String> setOf(String... values) {
        Set<String> set = new LinkedHashSet<String>();
        set.addAll(Arrays.asList(values));
        return set;
    }
}
