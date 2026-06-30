package com.example.oagmcp.logic;

import static com.example.oagmcp.util.Java8Collections.*;

import com.example.oagmcp.dao.OAGDAO;
import com.example.oagmcp.dao.entity.OAGEntity;
import com.example.oagmcp.vo.OAGVO;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.stream.Collectors;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.regex.Pattern;

final class SemanticFramePlanner {

    private static final Set<String> SUPPORTED_TASK_TYPES = setOf(
            "query", "analyze", "compare", "rank", "screen", "recommend", "profile", "explain", "summarize"
    );
    private static final Set<String> SEMANTIC_EXPANSION_TYPES = setOf(
            "compared_with", "derives", "ranked_by_peer", "risk_companion", "return_companion",
            "benchmark_metric_of", "peer_metric_of"
    );
    private static final Set<String> OBJECT_RELATION_TYPES = setOf(
            "managed_by", "issued_by", "managed_by_company", "has_benchmark", "tracks_index",
            "belongs_to_category", "has_dividend", "has_fee", "has_asset_allocation",
            "has_position", "holds_asset"
    );
    private static final Set<String> TASK_GRAPH_RELATION_TYPES = setOf(
            "compared_with", "derives", "ranked_by_peer", "risk_companion", "return_companion",
            "benchmark_metric_of", "peer_metric_of", "managed_by", "issued_by",
            "managed_by_company", "has_benchmark", "tracks_index", "belongs_to_category",
            "has_dividend", "has_fee", "has_asset_allocation", "has_position", "holds_asset"
    );
    private static final int MAX_OPTIONAL_EXPANSIONS_PER_REQUIRED_FACT = 3;
    private static final int MAX_RELATION_EXPANSION_FACTS = 8;
    private static final Set<String> PROFILE_FACT_ATTRIBUTES = setOf(
            "fund_code", "fund_name", "fund_short_name", "fund_type", "fund_status",
            "risk_level", "sale_status", "purchase_status", "redemption_status",
            "pension_fund_flag", "index_fund_flag", "fof_flag", "etf_flag",
            "dividend_mode", "fund_size", "listing_date", "inception_date",
            "company_name", "manager_name", "manager_list"
    );
    private static final Set<String> ASSET_ALLOCATION_ATTRIBUTES = setOf(
            "stock_asset_ratio", "bond_asset_ratio", "cash_asset_ratio", "fund_asset_ratio", "other_asset_ratio"
    );
    private static final Pattern FUND_CODE_PATTERN = Pattern.compile("(?<!\\d)\\d{6}(?!\\d)");
    private static final Map<String, List<String>> SCENARIO_ATTRIBUTES = mapOfEntries(
            entry("fund_profile", listOf("fund_name", "fund_type", "manager_name", "company_name")),
            entry("profile_query", listOf("fund_name", "fund_type", "manager_name", "company_name")),
            entry("fee_analysis", listOf("fee_value")),
            entry("dividend_analysis", listOf("dividend_per_share", "dividend_date")),
            entry("holding_analysis", listOf("stock_name", "stock_nav_ratio", "bond_name", "bond_nav_ratio")),
            entry("asset_allocation_analysis", listOf("asset_total_value", "asset_net_value", "stock_asset_ratio", "bond_asset_ratio", "cash_asset_ratio"))
    );

    private final OAGDAO dao;
    private final ObjectMapper objectMapper;
    private final String defaultDomain;

    SemanticFramePlanner(OAGDAO dao, ObjectMapper objectMapper, String defaultDomain) {
        this.dao = dao;
        this.objectMapper = objectMapper;
        this.defaultDomain = defaultDomain;
    }

    OAGVO.RetrieveResponse retrieveContext(OAGVO.RetrieveRequest request) {
        Map<String, Object> frameInput = request == null ? mapOf() : mapValue(request.semanticFrame);
        String domain = firstText(value(frameInput, "domain"), request == null ? "" : request.domain, defaultDomain);
        OAGVO.RetrieveResponse response = new OAGVO.RetrieveResponse();
        response.domain = domain;
        response.question = request == null ? "" : text(request.question);
        response.rawQuestion = text(value(frameInput, "raw_question"));

        if (frameInput.isEmpty()) {
            return errorResponse(response, "SEMANTIC_FRAME_REQUIRED", "缺少前置意图识别节点输出的结构化 semantic_frame，Java OAG 无法进行事实规划。");
        }

        try {
            if (dao.countEnabledDomain(domain) <= 0) {
                return errorResponse(response, "DOMAIN_DISABLED", "OAG domain 未启用：" + domain);
            }

            Map<String, Object> frame = normalizeSemanticFrame(frameInput, domain);
            response.normalizedSemanticFrame = frame;
            response.semanticFrameSummary = semanticFrameSummary(frame);
            response.rawQuestion = text(value(frame, "raw_question"));
            response.question = firstText(response.question, response.rawQuestion);
            response.intent = text(value(frame, "intent"));

            List<OAGEntity.IntentProfile> profiles = safeList(dao.listIntentProfiles(domain));
            Map<String, OAGEntity.IntentProfile> profileByName = intentProfileMap(profiles);
            Map<String, OAGEntity.OAGObject> objects = loadObjectMeta(domain, semanticObjectTypes(frame));
            List<String> attributeNames = semanticAttributeNames(frame, profiles);
            Map<String, OAGEntity.OAGAttribute> attributes = new LinkedHashMap<>(loadAttributeMeta(domain, attributeNames));
            ValidationResult validation = validateSemanticFrame(frame, objects, attributes, profileByName);
            response.warnings.addAll(validation.warnings);
            if (!validation.errors.isEmpty()) {
                OAGVO.RetrieveResponse invalid = errorResponse(response, "SEMANTIC_FRAME_INVALID", "semantic_frame 中存在本体无法识别的对象或属性，OAG 无法继续规划事实需求。");
                invalid.normalizedSemanticFrame = mapOf();
                invalid.diagnostics = validation.errors;
                invalid.editorPlan = editorPlan(invalid);
                invalid.agentPlan = agentPlan(invalid.editorPlan);
                return invalid;
            }
            Map<String, Object> guardrail = guardrailDecision(frame);
            if (!guardrail.isEmpty()) {
                return blockedResponse(response, frame, guardrail);
            }

            List<OAGVO.TargetInstance> targets = targetInstances(frame);
            List<OAGVO.FactRequirement> facts = factRequirements(frame, profileByName, attributes);
            List<OAGEntity.GraphEdge> relationEdges = recallRelationEdges(domain, frame, facts);
            enrichAttributeMeta(attributes, domain, relationEdges);
            facts = expandByRelations(frame, facts, relationEdges, attributes);
            List<SkillMeta> skills = skillMetas(safeList(dao.listSkillCapabilities(domain)));
            if (facts.isEmpty()) {
                response.status = "need_clarification";
                response.errorCode = "FACT_REQUIREMENTS_INSUFFICIENT";
                response.messageZh = "当前语义信息不足，无法规划事实需求；请补充明确指标、筛选/排序条件，或使用已配置的宽泛意图。";
            }

            CandidateResult candidates = candidateInvocations(frame, facts, skills, request == null ? mapOf() : mapValue(request.userContext));
            Map<String, Object> coverage = coverageSummary(facts, candidates.invocations, candidates.warnings);
            List<OAGVO.FactRequirement> unsupportedFacts = unsupportedRequiredFacts(facts, skills);
            if (!unsupportedFacts.isEmpty() && intValue(coverage.get("covered_required_fact_count"), 0) == 0) {
                return unsupportedResponse(response, frame, facts, unsupportedFacts);
            }
            if ("need_clarification".equals(response.status)) {
                coverage.put("coverage_status", "need_clarification");
                coverage.put("coverage_message_zh", "");
            }
            List<Map<String, Object>> warnings = new ArrayList<>(candidates.warnings);
            warnings.addAll(unsupportedWarnings(unsupportedFacts));
            List<Map<String, Object>> diagnostics = new ArrayList<>();
            diagnostics.addAll(unsupportedDiagnostics(unsupportedFacts));
            diagnostics.addAll(diagnostics(frame, facts, candidates.invocations, coverage, warnings));

            response.targetInstances = "need_clarification".equals(response.status) ? listOf() : targets;
            response.factRequirements = facts;
            response.factGroups = factGroups(facts);
            response.candidateInvocations = candidates.invocations;
            response.coverageSummary = coverage;
            response.missingParams = missingParams(candidates.invocations);
            response.uncoveredFacts = listMapValue(coverage.get("uncovered_required_facts"));
            response.diagnostics = diagnostics;
            response.warnings.addAll(warnings);
            response.taskGraph = taskGraph(frame, targets, facts, candidates.invocations);
            response.resolvedParams = resolvedParams(frame);
            response.retrievalSummary = retrievalSummary(frame, facts, candidates.invocations);
            response.confidence = confidence(facts, candidates.invocations, response.status);
            response.truncation = truncation(facts, candidates.invocations);
            response.matchedIntents = matchedIntents(frame, profileByName);
            response.matchedAttributes = matchedAttributes(attributeNames, attributes);

            Map<String, Object> editorPlan = editorPlan(response);
            response.editorPlan = editorPlan;
            response.agentPlan = agentPlan(editorPlan);
            response.planViews = planViews();
            return response;
        } catch (Exception ex) {
            return errorResponse(
                    response,
                    "OAG_JAVA_PLANNER_ERROR",
                    ex.getClass().getSimpleName() + ": " + firstText(ex.getMessage(), "planner failed")
            );
        }
    }

    private OAGVO.RetrieveResponse errorResponse(OAGVO.RetrieveResponse response, String code, String messageZh) {
        String safeMessage = firstText(messageZh, code);
        response.status = "error";
        response.errorCode = code;
        response.messageZh = safeMessage;
        response.semanticFrameSummary = mapOf();
        response.targetInstances = listOf();
        response.factRequirements = listOf();
        response.candidateInvocations = listOf();
        response.taskGraph = mapOf("nodes", listOf(), "edges", listOf());
        response.coverageSummary = mapOf(
                "required_fact_count", 0,
                "covered_required_fact_count", 0,
                "uncovered_required_facts", listOf(),
                "optional_fact_count", 0,
                "covered_optional_fact_count", 0,
                "uncovered_optional_facts", listOf(),
                "skill_count", 0,
                "has_permission_blocked_facts", false,
                "coverage_status", "no_coverage",
                "coverage_message_zh", ""
        );
        response.warnings.add(row("warning_code", code, "message_zh", safeMessage));
        response.editorPlan = editorPlan(response);
        response.agentPlan = agentPlan(response.editorPlan);
        response.planViews = planViews();
        return response;
    }

    private OAGVO.RetrieveResponse blockedResponse(OAGVO.RetrieveResponse response, Map<String, Object> frame, Map<String, Object> decision) {
        String status = text(value(decision, "status"));
        String reasonCode = text(value(decision, "reason_code"));
        String messageZh = text(value(decision, "message_zh"));
        OAGVO.RetrieveResponse blocked = errorResponse(response, reasonCode, messageZh);
        blocked.status = status;
        blocked.normalizedSemanticFrame = frame;
        blocked.semanticFrameSummary = semanticFrameSummary(frame);
        blocked.coverageSummary = new LinkedHashMap<String, Object>(blocked.coverageSummary);
        blocked.coverageSummary.put("coverage_status", status);
        blocked.coverageSummary.put("coverage_message_zh", messageZh);
        List<String> missing = uniqueStrings(value(decision, "missing_params"));
        if (!missing.isEmpty()) {
            OAGVO.MissingParam row = new OAGVO.MissingParam();
            row.source = "semantic_frame.target_objects";
            row.missingParams = missing;
            row.suggestedQuestion = messageZh;
            blocked.missingParams = listOf(row);
        }
        blocked.editorPlan = editorPlan(blocked);
        blocked.agentPlan = agentPlan(blocked.editorPlan);
        return blocked;
    }

    private OAGVO.RetrieveResponse unsupportedResponse(
            OAGVO.RetrieveResponse response,
            Map<String, Object> frame,
            List<OAGVO.FactRequirement> facts,
            List<OAGVO.FactRequirement> unsupportedFacts) {
        response.status = "unsupported";
        response.errorCode = "UNSUPPORTED_DATA_CAPABILITY";
        response.messageZh = "当前底层数据源不支持部分必需事实，不能生成 ready Skill 调用。";
        response.normalizedSemanticFrame = frame;
        response.semanticFrameSummary = semanticFrameSummary(frame);
        response.targetInstances = listOf();
        response.factRequirements = facts;
        response.candidateInvocations = listOf();
        response.taskGraph = mapOf("nodes", listOf(), "edges", listOf());
        response.coverageSummary = coverageSummary(facts, listOf(), listOf(row(
                "warning_code", "UNSUPPORTED_DATA_CAPABILITY",
                "message_zh", "存在当前 ifund_all_info 不支持的必需事实，已停止规划可执行 Skill。"
        )));
        response.coverageSummary.put("coverage_status", "unsupported");
        response.coverageSummary.put("coverage_message_zh", response.messageZh);
        response.missingParams = listOf();
        response.uncoveredFacts = listMapValue(response.coverageSummary.get("uncovered_required_facts"));
        response.diagnostics = unsupportedFacts.stream().map(item -> {
            Map<String, Object> row = row(
                    "diagnostic_code", "UNSUPPORTED_DATA_CAPABILITY",
                    "severity", "error",
                    "message_zh", firstText(value(item.extra, "unsupported_message_zh"), item.labelZh),
                    "suggestion_zh", "补充对应明细表或将问题改为当前宽表可支持的指标。",
                    "fact_requirement_id", item.factRequirementId,
                    "attribute_name", item.attributeName,
                    "reason_code", value(item.extra, "unsupported_reason_code")
            );
            Object closest = value(item.extra, "closest_supported_periods");
            if (closest != null) {
                row.put("closest_supported_periods", closest);
            }
            return row;
        }).collect(Collectors.toList());
        response.warnings.add(row(
                "warning_code", "UNSUPPORTED_DATA_CAPABILITY",
                "message_zh", "存在当前 ifund_all_info 不支持的必需事实，已停止规划可执行 Skill。",
                "unsupported_fact_requirements", unsupportedFacts.stream().map(item -> item.factRequirementId).collect(Collectors.toList())
        ));
        response.editorPlan = editorPlan(response);
        response.agentPlan = agentPlan(response.editorPlan);
        response.planViews = planViews();
        return response;
    }

    private List<Map<String, Object>> unsupportedWarnings(List<OAGVO.FactRequirement> unsupportedFacts) {
        if (unsupportedFacts == null || unsupportedFacts.isEmpty()) {
            return listOf();
        }
        return listOf(row(
                "warning_code", "UNSUPPORTED_DATA_CAPABILITY",
                "message_zh", "存在当前 ifund_all_info 不支持的事实，已保留为未覆盖事实，不阻断其他可执行 Skill。"
        ));
    }

    private List<Map<String, Object>> unsupportedDiagnostics(List<OAGVO.FactRequirement> unsupportedFacts) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (OAGVO.FactRequirement item : unsupportedFacts) {
            Map<String, Object> row = row(
                    "diagnostic_code", "UNSUPPORTED_DATA_CAPABILITY",
                    "severity", "warning",
                    "message_zh", firstText(value(item.extra, "unsupported_message_zh"), item.labelZh, "当前数据源不支持该事实。"),
                    "suggestion_zh", "补充对应明细表，或将问题改为当前 ifund_all_info 可支持的指标。",
                    "fact_requirement_id", item.factRequirementId,
                    "attribute_name", item.attributeName,
                    "reason_code", value(item.extra, "unsupported_reason_code")
            );
            Object closest = value(item.extra, "closest_supported_periods");
            if (closest != null) {
                row.put("closest_supported_periods", closest);
            }
            rows.add(row);
        }
        return rows;
    }

    private Map<String, Object> normalizeSemanticFrame(Map<String, Object> input, String domain) {
        Map<String, Object> frame = new LinkedHashMap<>(input);
        frame.put("domain", firstText(value(frame, "domain"), domain, defaultDomain));
        frame.put("task_type", firstText(value(frame, "task_type"), "query"));
        frame.put("constraints", mapValue(value(frame, "constraints")));
        Map<String, Object> normalizedConstraints = new LinkedHashMap<>(mapValue(value(frame, "constraints")));
        String period = text(value(normalizedConstraints, "period"));
        if ("12m".equals(period)) {
            normalizedConstraints.put("period", "1y");
        } else if ("YTD".equalsIgnoreCase(period)) {
            normalizedConstraints.put("period", "ytd");
        } else if ("SI".equalsIgnoreCase(period)) {
            normalizedConstraints.put("period", "si");
        }
        frame.put("constraints", normalizedConstraints);
        frame.put("mentioned_attributes", uniqueStrings(value(frame, "mentioned_attributes")));
        frame.put("relation_queries", listMapValue(value(frame, "relation_queries")));
        frame.put("filters", listMapValue(value(frame, "filters")));
        frame.put("ranking", listMapValue(value(frame, "ranking")));
        frame.put("comparison", mapValue(value(frame, "comparison")));
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("allow_relation_expansion", true);
        options.put("allow_peer_expansion", true);
        options.put("include_supporting_context", true);
        options.putAll(mapValue(value(frame, "options")));
        frame.put("options", options);

        List<Map<String, Object>> targets = new ArrayList<>();
        int index = 1;
        for (Map<String, Object> target : listMapValue(value(frame, "target_objects"))) {
            Map<String, Object> row = new LinkedHashMap<>(target);
            row.put("object_type", firstText(value(row, "object_type"), "Fund"));
            row.put("instance_ref", mapValue(value(row, "instance_ref")));
            String objectType = text(value(row, "object_type"));
            row.put("role", firstText(value(row, "role"), objectType.endsWith("Set") ? "candidate_set" : "analysis_subject"));
            row.put("target_index", index++);
            targets.add(row);
        }
        if (targets.isEmpty() && setOf("rank", "screen", "recommend").contains(text(value(frame, "task_type")))) {
            Map<String, Object> synthetic = new LinkedHashMap<>();
            synthetic.put("object_type", "FundSet");
            synthetic.put("instance_ref", mapOf("fund_universe", "all_funds"));
            synthetic.put("role", "candidate_set");
            synthetic.put("target_index", 0);
            targets.add(synthetic);
        }
        frame.put("target_objects", targets);
        if ("profile".equals(frame.get("task_type")) && !StringUtils.hasText(text(value(frame, "intent")))) {
            frame.put("intent", "fund_profile");
        }
        if ("fund_recommendation".equals(frame.get("intent"))) {
            frame.put("task_type", "recommend");
        }
        if ("asset_allocation_analysis".equals(frame.get("intent"))) {
            List<String> mentioned = uniqueStrings(value(frame, "mentioned_attributes"));
            boolean hasAllocationAttribute = mentioned.stream().anyMatch(ASSET_ALLOCATION_ATTRIBUTES::contains);
            if (hasAllocationAttribute) {
                String allocationAttr = mentioned.stream().filter(ASSET_ALLOCATION_ATTRIBUTES::contains).findFirst().orElse("");
                frame.put("mentioned_attributes", mentioned.stream()
                        .filter(item -> !setOf("stock_name", "stock_nav_ratio", "bond_name", "bond_nav_ratio", "holding_industry").contains(item))
                        .collect(Collectors.toList()));
                List<Map<String, Object>> relationQueries = new ArrayList<>();
                for (Map<String, Object> item : listMapValue(value(frame, "relation_queries"))) {
                    if ("has_position".equals(text(value(item, "relation_type")))) {
                        continue;
                    }
                    if ("has_asset_allocation".equals(text(value(item, "relation_type"))) && StringUtils.hasText(allocationAttr)) {
                        item = new LinkedHashMap<>(item);
                        item.put("attribute_name", allocationAttr);
                    }
                    relationQueries.add(item);
                }
                frame.put("relation_queries", relationQueries);
            }
        }
        return frame;
    }

    private Map<String, Object> guardrailDecision(Map<String, Object> frame) {
        Map<String, Object> constraints = mapValue(value(frame, "constraints"));
        String rawQuestion = text(value(frame, "raw_question"));
        Set<String> safetyFlags = new LinkedHashSet<>(uniqueStrings(value(frame, "safety_flags")));
        String testFlag = text(value(constraints, "test_flag"));
        if (!disjoint(safetyFlags, setOf("guaranteed_profit", "no_loss", "must_rise"))
                || containsAny(rawQuestion, "稳赚", "一定会涨", "一定上涨", "稳赚不赔", "保本保收益")
                || (rawQuestion.contains("保证") && rawQuestion.contains("赚"))) {
            return row(
                    "status", "rejected_with_risk_notice",
                    "reason_code", "GUARANTEED_PROFIT_REJECTED",
                    "message_zh", "无法提供稳赚不赔、保证赚钱或一定上涨的结论，可基于历史数据分析风险收益。"
            );
        }
        if (safetyFlags.contains("future_prediction")
                || containsAny(rawQuestion, "预测明天", "明天涨跌", "明天的收益", "未来一年收益", "未来收益")) {
            return row(
                    "status", "rejected",
                    "reason_code", "FUTURE_RETURN_QUERY_REJECTED",
                    "message_zh", "无法查询或预测未来收益和涨跌，可查询历史收益和风险表现。"
            );
        }
        Map<String, Object> dateRange = mapValue(value(constraints, "date_range"));
        if (!dateRange.isEmpty()) {
            LocalDate start = parseDate(value(dateRange, "start_date"));
            LocalDate end = parseDate(value(dateRange, "end_date"));
            LocalDate today = LocalDate.now();
            if (start != null && end != null && start.isAfter(end)) {
                return row(
                        "status", "need_clarification",
                        "reason_code", "INVALID_DATE_RANGE",
                        "message_zh", "日期区间起始日期晚于结束日期，请确认查询区间。"
                );
            }
            if ((start != null && start.isAfter(today)) || (end != null && end.isAfter(today))) {
                return row(
                        "status", "rejected",
                        "reason_code", "FUTURE_DATE_RANGE_REJECTED",
                        "message_zh", "无法查询未来日期区间的收益率，可改查历史区间。"
                );
            }
        }
        if ("invalid_or_future_or_compliance_risk".equals(testFlag)
                && containsAny(rawQuestion, "明天", "未来", "预测", "稳赚", "保证", "一定会涨", "一定上涨")) {
            return row(
                    "status", "rejected",
                    "reason_code", "INVALID_OR_COMPLIANCE_RISK_REJECTED",
                    "message_zh", "该问题涉及未来收益、预测或保证性表述，OAG 不规划可执行 Skill。"
            );
        }
        if (Pattern.compile("近\\s*(?:[1-9]\\d{2,}|[一二三四五六七八九]?百)\\s*年").matcher(rawQuestion).find()) {
            return row(
                    "status", "need_clarification",
                    "reason_code", "UNSUPPORTED_LONG_PERIOD",
                    "message_zh", "当前宽表不支持超长历史周期收益查询，请改用近一周、近一月、近一年、近三年、近五年或成立以来等周期。"
            );
        }
        for (Map<String, Object> target : targetsOfType(frame, "Fund", planningTargets(frame))) {
            Map<String, Object> instanceRef = mapValue(value(target, "instance_ref"));
            String fundCode = text(value(instanceRef, "fund_code"));
            if (!hasFundIdentifier(instanceRef)) {
                if (Pattern.compile("(?<!\\d)\\d{1,5}(?!\\d)|(?<!\\d)\\d{7,}(?!\\d)|[A-Za-z]{6,}|不存在基金").matcher(rawQuestion).find()) {
                    return row(
                            "status", "need_clarification",
                            "reason_code", "INVALID_FUND_CODE_FORMAT",
                            "message_zh", "基金标识无法解析为 6 位基金代码或已知基金名称，请确认基金代码或基金名称。",
                            "missing_params", listOf("fund_code")
                    );
                }
                return row(
                        "status", "blocked_missing_params",
                        "reason_code", "FUND_CODE_REQUIRED",
                        "message_zh", "请先指定 6 位基金代码或可解析的基金名称。",
                        "missing_params", listOf("fund_code")
                );
            }
            if (StringUtils.hasText(fundCode) && !FUND_CODE_PATTERN.matcher(fundCode).matches()) {
                return row(
                        "status", "need_clarification",
                        "reason_code", "INVALID_FUND_CODE_FORMAT",
                        "message_zh", "基金代码应为 6 位数字，请确认基金代码。",
                        "missing_params", listOf("fund_code")
                );
            }
        }
        return mapOf();
    }

    private boolean hasFundIdentifier(Map<String, Object> instanceRef) {
        return StringUtils.hasText(text(value(instanceRef, "fund_code")))
                || StringUtils.hasText(text(value(instanceRef, "fund_name")))
                || StringUtils.hasText(text(value(instanceRef, "fund_short_name")));
    }

    private LocalDate parseDate(Object value) {
        try {
            String dateText = text(value);
            return StringUtils.hasText(dateText) ? LocalDate.parse(dateText) : null;
        } catch (DateTimeParseException ex) {
            return null;
        }
    }

    private boolean containsAny(String text, String... needles) {
        for (String needle : needles) {
            if (text.contains(needle)) {
                return true;
            }
        }
        return false;
    }

    private List<OAGVO.FactRequirement> factRequirements(
            Map<String, Object> frame,
            Map<String, OAGEntity.IntentProfile> profiles,
            Map<String, OAGEntity.OAGAttribute> attributeMeta) {
        List<OAGVO.FactRequirement> rows = new ArrayList<>();
        List<String> mentioned = uniqueStrings(value(frame, "mentioned_attributes"));
        List<Map<String, Object>> targets = planningTargets(frame);

        if (!mentioned.isEmpty()) {
            for (String name : mentioned) {
                RelationHint hint = relationHint(attributeMeta, name);
                if (hint != null) {
                    for (Map<String, Object> target : targetsOfType(frame, "Fund", targets)) {
                        rows.add(relationRequirement(frame, attributeMeta, hint.relationType, hint.targetObjectType, "required", "explicit_relation", hint.attributeName, target));
                    }
                    continue;
                }
                for (Map<String, Object> target : factTargetsForAttribute(frame, name, targets)) {
                    rows.add(attributeRequirement(frame, attributeMeta, name, "required", "explicit_attribute", "用户显式提到该指标，优先作为必需事实。", null, target));
                }
            }
            if ("risk_overview".equals(value(frame, "intent"))) {
                OAGEntity.IntentProfile profile = profiles.get("risk_overview");
                for (Map<String, Object> item : factTemplates(profile)) {
                    String name = text(value(item, "attribute_name"));
                    if (!StringUtils.hasText(name) || mentioned.contains(name)) {
                        continue;
                    }
                    for (Map<String, Object> target : factTargetsForAttribute(frame, name, targets)) {
                        rows.add(attributeRequirement(
                                frame,
                                attributeMeta,
                                name,
                                firstText(value(item, "priority"), "supporting"),
                                "intent_template",
                                firstText(value(item, "reason_zh"), value(item, "reason"), "风险判断需要补充风险指标事实。"),
                                text(value(item, "fact_type")),
                                target
                        ));
                    }
                }
            }
        } else {
            OAGEntity.IntentProfile profile = profiles.get(text(value(frame, "intent")));
            for (Map<String, Object> item : factTemplates(profile)) {
                String name = text(value(item, "attribute_name"));
                if (!StringUtils.hasText(name)) {
                    continue;
                }
                for (Map<String, Object> target : factTargetsForAttribute(frame, name, targets)) {
                    rows.add(attributeRequirement(
                            frame,
                            attributeMeta,
                            name,
                            firstText(value(item, "priority"), "required"),
                            "intent_template",
                            firstText(value(item, "reason_zh"), value(item, "reason"), "由命中的宽泛意图模板补全该事实需求。"),
                            text(value(item, "fact_type")),
                            target
                    ));
                }
            }
        }

        List<String> scenarioAttrs = scenarioAttributesForFrame(frame, mentioned);
        for (String name : scenarioAttrs) {
            for (Map<String, Object> target : factTargetsForAttribute(frame, name, targets)) {
                addIfAbsent(rows, attributeRequirement(frame, attributeMeta, name, "required", "scenario_rule", scenarioReason(text(value(frame, "intent"))), scenarioFactType(text(value(frame, "intent"))), target));
            }
        }
        if ("profile".equals(value(frame, "task_type"))) {
            for (String name : SCENARIO_ATTRIBUTES.getOrDefault("fund_profile", listOf())) {
                for (Map<String, Object> target : factTargetsForAttribute(frame, name, targets)) {
                    addIfAbsent(rows, attributeRequirement(frame, attributeMeta, name, "required", "scenario_rule", "画像任务需要补充对象基础事实。", "object_profile", target));
                }
            }
        }
        boolean explicitProfileAttributeOnly = setOf("fund_profile", "profile_query").contains(text(value(frame, "intent")))
                && !mentioned.isEmpty()
                && !"profile".equals(value(frame, "task_type"));
        if ("profile".equals(value(frame, "task_type"))
                || (setOf("fund_profile", "profile_query").contains(text(value(frame, "intent"))) && !explicitProfileAttributeOnly)) {
            Map<String, String> profileRelations = new LinkedHashMap<>();
            profileRelations.put("managed_by", "FundManager");
            profileRelations.put("issued_by", "FundCompany");
            profileRelations.put("has_benchmark", "Benchmark");
            profileRelations.put("belongs_to_category", "FundCategory");
            for (Map.Entry<String, String> entry : profileRelations.entrySet()) {
                for (Map<String, Object> target : targetsOfType(frame, "Fund", targets)) {
                    String priority = "has_benchmark".equals(entry.getKey()) ? "supporting" : "required";
                    OAGVO.FactRequirement relation = relationRequirement(
                            frame,
                            attributeMeta,
                            entry.getKey(),
                            entry.getValue(),
                            priority,
                            "scenario_rule",
                            explicitRelationReason(entry.getKey(), entry.getValue()),
                            relationAttribute(entry.getKey()),
                            target
                    );
                    if ("supporting".equals(priority)) {
                        relation.answerVisibility = "supporting_context";
                    }
                    relation.planningRole = "profile_relation";
                    addIfAbsent(rows, relation);
                }
            }
        }
        for (OAGVO.FactRequirement item : operationRequirements(frame, attributeMeta, targets)) {
            addIfAbsent(rows, item);
        }
        for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
            String relation = text(value(query, "relation_type"));
            if (!StringUtils.hasText(relation) || !OBJECT_RELATION_TYPES.contains(relation)) {
                continue;
            }
            String targetObjectType = firstText(value(query, "target_object_type"), relationTarget(relation));
            String attributeName = firstText(value(query, "attribute_name"), relationAttribute(relation));
            List<Map<String, Object>> relationTargets = targetsOfType(frame, "Fund", targets);
            if (relationTargets.isEmpty()) {
                relationTargets = targets;
            }
            for (Map<String, Object> target : relationTargets) {
                String priority = "required";
                if (setOf("rank", "screen", "recommend").contains(text(value(frame, "task_type")))
                        && "belongs_to_category".equals(relation)) {
                    priority = "supporting";
                }
                if ("benchmark_comparison".equals(value(frame, "intent")) && "has_benchmark".equals(relation)) {
                    priority = "supporting";
                }
                OAGVO.FactRequirement requirement = relationRequirement(frame, attributeMeta, relation, targetObjectType, priority, "explicit_relation", attributeName, target);
                if ("supporting".equals(priority)) {
                    requirement.answerVisibility = "supporting_context";
                }
                addIfAbsent(rows, requirement);
            }
        }
        if ("benchmark_comparison".equals(value(frame, "intent"))) {
            for (Map<String, Object> target : targetsOfType(frame, "Fund", targets)) {
                OAGVO.FactRequirement relation = relationRequirement(
                        frame,
                        attributeMeta,
                        "has_benchmark",
                        "Benchmark",
                        "supporting",
                        "scenario_rule",
                        "基准比较需要确认基金对应的业绩比较基准作为支撑上下文。",
                        "benchmark_name",
                        target
                );
                relation.answerVisibility = "supporting_context";
                relation.planningRole = "benchmark_context";
                addIfAbsent(rows, relation);
            }
        }
        if ("peer_comparison".equals(value(frame, "intent"))) {
            for (Map<String, Object> target : targetsOfType(frame, "Fund", targets)) {
                OAGVO.FactRequirement relation = relationRequirement(
                        frame,
                        attributeMeta,
                        "belongs_to_category",
                        "FundCategory",
                        "supporting",
                        "scenario_rule",
                        "同类比较需要基金分类作为同类集合支撑上下文。",
                        "fund_type",
                        target
                );
                relation.answerVisibility = "supporting_context";
                relation.planningRole = "peer_context";
                addIfAbsent(rows, relation);
            }
        }
        return rows;
    }

    private List<OAGVO.FactRequirement> operationRequirements(
            Map<String, Object> frame,
            Map<String, OAGEntity.OAGAttribute> attributeMeta,
            List<Map<String, Object>> targets) {
        List<OAGVO.FactRequirement> rows = new ArrayList<>();
        String taskType = text(value(frame, "task_type"));
        if ("compare".equals(taskType) && targetsOfType(frame, "Fund", targets).size() >= 2) {
            for (String name : comparisonAttributes(frame)) {
                for (Map<String, Object> target : targetsOfType(frame, "Fund", targets)) {
                    rows.add(attributeRequirement(frame, attributeMeta, name, "required", "operation_rule", "比较任务需要为每个目标对象查询比较指标。", null, target));
                }
            }
            List<String> attributes = comparisonAttributes(frame).isEmpty() ? listOf("comparison_result") : comparisonAttributes(frame);
            for (String attribute : attributes) {
                rows.add(baseRequirement(frame, attributeMeta, "comparison_result", attribute, "Fund", "derived", "operation_rule", "多基金比较需要基于各主体指标事实形成比较结果。", targetsOfType(frame, "Fund", targets).get(0)));
            }
        }
        if (setOf("rank", "screen", "recommend").contains(taskType)) {
            rows.add(baseRequirement(frame, attributeMeta, "entity_set", null, "FundSet", "required", "operation_rule", "该操作型任务需要先确定候选对象集合。", fundSetTarget(frame)));
        }
        if (setOf("rank", "screen", "recommend").contains(taskType)) {
            Map<String, Object> setTarget = fundSetTarget(frame);
            for (Map<String, Object> ranking : listMapValue(value(frame, "ranking"))) {
                String attribute = text(value(ranking, "attribute"));
                OAGVO.FactRequirement req = baseRequirement(frame, attributeMeta, "metric_ranking", attribute, "FundSet", "required", "operation_rule", "排序或推荐任务需要该指标作为排序依据。", setTarget);
                req.ranking = ranking;
                rows.add(req);
            }
        }
        if ("screen".equals(taskType) || "recommend".equals(taskType)) {
            Map<String, Object> setTarget = fundSetTarget(frame);
            for (Map<String, Object> filter : listMapValue(value(frame, "filters"))) {
                String attribute = text(value(filter, "attribute"));
                OAGVO.FactRequirement req = baseRequirement(frame, attributeMeta, "filter_condition", attribute, "FundSet", "required", "operation_rule", "筛选任务需要该指标作为过滤条件。", setTarget);
                req.filter = filter;
                rows.add(req);
            }
        }
        return rows;
    }

    private OAGVO.FactRequirement attributeRequirement(
            Map<String, Object> frame,
            Map<String, OAGEntity.OAGAttribute> attributeMeta,
            String attributeName,
            String priority,
            String source,
            String reasonZh,
            String factType,
            Map<String, Object> target) {
        return baseRequirement(
                frame,
                attributeMeta,
                defaultFactType(attributeMeta, attributeName, factType),
                attributeName,
                firstText(value(target, "object_type"), "Fund"),
                priority,
                source,
                reasonZh,
                target
        );
    }

    private OAGVO.FactRequirement relationRequirement(
            Map<String, Object> frame,
            Map<String, OAGEntity.OAGAttribute> attributeMeta,
            String relationType,
            String targetObjectType,
            String priority,
            String source,
            String attributeName,
            Map<String, Object> target) {
        return relationRequirement(
                frame,
                attributeMeta,
                relationType,
                targetObjectType,
                priority,
                source,
                explicitRelationReason(relationType, targetObjectType),
                attributeName,
                target
        );
    }

    private OAGVO.FactRequirement relationRequirement(
            Map<String, Object> frame,
            Map<String, OAGEntity.OAGAttribute> attributeMeta,
            String relationType,
            String targetObjectType,
            String priority,
            String source,
            String reasonZh,
            String attributeName,
            Map<String, Object> target) {
        OAGVO.FactRequirement row = baseRequirement(
                frame,
                attributeMeta,
                "relation_instance",
                attributeName,
                firstText(value(target, "object_type"), "Fund"),
                priority,
                source,
                reasonZh,
                target
        );
        row.predicate = relationType;
        row.predicateZh = relationTypeZh(relationType);
        row.targetObjectType = targetObjectType;
        String suffix = StringUtils.hasText(text(value(row.constraints, "period")))
                ? text(value(row.constraints, "period"))
                : firstText(value(frame, "task_type"), "query");
        row.factRequirementId = "FactRequirement:fr_" + relationType + "_" + targetObjectType + "_" + suffix;
        row.objectRelation = row(
                "from_object_type", firstText(value(target, "object_type"), "Fund"),
                "to_object_type", targetObjectType,
                "relation_type", relationType,
                "relation_type_zh", row.predicateZh
        );
        row.labelZh = relationSubjectZh(firstText(value(target, "object_type"), "Fund")) + "与" + relationFactLabelZh(relationType, targetObjectType) + "事实";
        row.descriptionZh = row.reasonZh;
        return row;
    }

    private List<OAGEntity.GraphEdge> recallRelationEdges(String domain, Map<String, Object> frame, List<OAGVO.FactRequirement> facts) {
        List<String> nodeIds = relationSeedNodeIds(frame, facts);
        if (nodeIds.isEmpty()) {
            return listOf();
        }
        return safeList(dao.listGraphEdgesByNodeIds(domain, nodeIds, 1000));
    }

    private void enrichAttributeMeta(Map<String, OAGEntity.OAGAttribute> attributes, String domain, List<OAGEntity.GraphEdge> edges) {
        LinkedHashSet<String> names = new LinkedHashSet<>();
        for (OAGEntity.GraphEdge edge : edges) {
            String[] from = splitNodeId(edge.fromNodeId);
            String[] to = splitNodeId(edge.toNodeId);
            if ("Attribute".equals(from[0]) && !attributes.containsKey(from[1])) {
                names.add(from[1]);
            }
            if ("Attribute".equals(to[0]) && !attributes.containsKey(to[1])) {
                names.add(to[1]);
            }
            String relationAttribute = relationAttribute(edge.relationType);
            if (StringUtils.hasText(relationAttribute) && !attributes.containsKey(relationAttribute)) {
                names.add(relationAttribute);
            }
        }
        if (names.isEmpty()) {
            return;
        }
        attributes.putAll(loadAttributeMeta(domain, new ArrayList<>(names)));
    }

    private List<OAGVO.FactRequirement> expandByRelations(
            Map<String, Object> frame,
            List<OAGVO.FactRequirement> requirements,
            List<OAGEntity.GraphEdge> relationEdges,
            Map<String, OAGEntity.OAGAttribute> attributeMeta) {
        List<OAGVO.FactRequirement> rows = new ArrayList<>(requirements);
        Set<String> existing = requirementKeys(rows);
        Set<String> sourceAttributes = new LinkedHashSet<>();
        for (OAGVO.FactRequirement requirement : requirements) {
            if (StringUtils.hasText(requirement.attributeName) && "required".equals(requirement.priority)) {
                sourceAttributes.add(requirement.attributeName);
            }
        }
        Set<String> targetObjectTypes = new LinkedHashSet<>();
        for (Map<String, Object> target : planningTargets(frame)) {
            addText(targetObjectTypes, value(target, "object_type"));
        }

        Map<String, Integer> expansionsBySource = new LinkedHashMap<>();
        int expansionCount = 0;
        for (OAGEntity.GraphEdge edge : relationEdges.stream().sorted(this::relationExpansionCompare).collect(Collectors.toList())) {
            if (expansionCount >= MAX_RELATION_EXPANSION_FACTS) {
                break;
            }
            if (!TASK_GRAPH_RELATION_TYPES.contains(edge.relationType) || !edgeApplicable(edge, frame, rows)) {
                continue;
            }
            if (!booleanValue(value(mapValue(value(frame, "options")), "allow_peer_expansion"))
                    && setOf("ranked_by_peer", "peer_metric_of").contains(edge.relationType)) {
                continue;
            }
            Map<String, Object> properties = edgeProperties(edge);
            String autoExpandMode = firstText(value(properties, "auto_expand_mode"), "contextual");
            String answerVisibility = firstText(value(properties, "answer_visibility"), "answer_fact");
            if (setOf("disabled", "debug_only").contains(autoExpandMode) || "debug_only".equals(answerVisibility)) {
                continue;
            }
            if ("explicit_only".equals(autoExpandMode) && !explicitRelationTriggered(properties, frame, edge.relationType)) {
                continue;
            }
            String[] from = splitNodeId(edge.fromNodeId);
            String[] to = splitNodeId(edge.toNodeId);
            if (setOf("contextual", "always").contains(autoExpandMode) && !triggerPolicyMatches(properties, frame, from[1], rows)) {
                continue;
            }
            if ("dependency_only".equals(autoExpandMode) && !setOf("supporting_context", "answer_fact").contains(answerVisibility)) {
                continue;
            }

            if ("Attribute".equals(from[0])
                    && sourceAttributes.contains(from[1])
                    && "Attribute".equals(to[0])
                    && SEMANTIC_EXPANSION_TYPES.contains(edge.relationType)) {
                int maxPerSource = intValue(value(mapValue(value(properties, "expansion_limits")), "max_per_source_attribute"), MAX_OPTIONAL_EXPANSIONS_PER_REQUIRED_FACT);
                if (expansionsBySource.getOrDefault(from[1], 0) >= maxPerSource) {
                    continue;
                }
                List<OAGVO.FactRequirement> sourceReqs = requirements.stream()
                        .filter(item -> from[1].equals(item.attributeName) && "required".equals(item.priority))
                        .collect(Collectors.toList());
                for (OAGVO.FactRequirement sourceReq : sourceReqs) {
                    if (expansionCount >= MAX_RELATION_EXPANSION_FACTS) {
                        break;
                    }
                    Map<String, Object> target = targetBySubjectId(frame, sourceReq.subject == null ? "" : sourceReq.subject.subjectId);
                    String priority = firstText(value(properties, "expansion_priority"), value(properties, "default_priority"), "optional");
                    OAGVO.FactRequirement item = attributeRequirement(
                            frame,
                            attributeMeta,
                            to[1],
                            "required".equals(priority) ? "required" : "optional",
                            "relation_expansion",
                            firstText(value(properties, "reason_zh"), relationReason(edge.relationType, from[1], to[1], attributeMeta)),
                            null,
                            target
                    );
                    item.planningRole = text(value(properties, "planning_role"));
                    item.autoExpandMode = autoExpandMode;
                    item.answerVisibility = answerVisibility;
                    item.expansionPriority = priority;
                    item.expandedFrom = row(
                            "source_attribute", from[1],
                            "target_attribute", to[1],
                            "relation_type", edge.relationType,
                            "relation_type_zh", firstText(value(properties, "relation_name_zh"), relationTypeZh(edge.relationType)),
                            "edge_id", firstText(edge.edgeId, edge.fromNodeId + "__" + edge.relationType + "__" + edge.toNodeId),
                            "weight", firstNonNull(value(properties, "weight"), edge.score),
                            "planning_role", value(properties, "planning_role"),
                            "answer_visibility", answerVisibility,
                            "reason_zh", item.reasonZh
                    );
                    String key = requirementKey(item);
                    if (!existing.contains(key)) {
                        rows.add(item);
                        existing.add(key);
                        expansionsBySource.put(from[1], expansionsBySource.getOrDefault(from[1], 0) + 1);
                        expansionCount++;
                    } else {
                        attachRelationExplanation(rows, item);
                    }
                }
            } else if ("ObjectType".equals(from[0])
                    && targetObjectTypes.contains(from[1])
                    && "ObjectType".equals(to[0])
                    && OBJECT_RELATION_TYPES.contains(edge.relationType)) {
                for (Map<String, Object> target : targetsOfType(frame, from[1], planningTargets(frame))) {
                    if (expansionCount >= MAX_RELATION_EXPANSION_FACTS) {
                        break;
                    }
                    String priority = firstText(value(properties, "expansion_priority"), value(properties, "default_priority"), "optional");
                    OAGVO.FactRequirement item = relationRequirement(
                            frame,
                            attributeMeta,
                            edge.relationType,
                            to[1],
                            priority,
                            "relation_expansion",
                            firstText(value(properties, "reason_zh"), "本体关系表明" + from[1] + "需要关联" + to[1] + "事实用于解释。"),
                            relationAttribute(edge.relationType),
                            target
                    );
                    item.planningRole = text(value(properties, "planning_role"));
                    item.autoExpandMode = autoExpandMode;
                    item.answerVisibility = answerVisibility;
                    item.expansionPriority = priority;
                    item.objectRelation.put("edge_id", firstText(edge.edgeId, edge.fromNodeId + "__" + edge.relationType + "__" + edge.toNodeId));
                    item.objectRelation.put("weight", firstNonNull(value(properties, "weight"), edge.score));
                    item.objectRelation.put("planning_role", value(properties, "planning_role"));
                    item.objectRelation.put("answer_visibility", answerVisibility);
                    if (relationFactExists(rows, item)) {
                        continue;
                    }
                    String key = requirementKey(item);
                    if (!existing.contains(key)) {
                        rows.add(item);
                        existing.add(key);
                        expansionCount++;
                    }
                }
            }
        }
        return dedupeRequirements(rows);
    }

    private OAGVO.FactRequirement baseRequirement(
            Map<String, Object> frame,
            Map<String, OAGEntity.OAGAttribute> attributeMeta,
            String factType,
            String attributeName,
            String subjectType,
            String priority,
            String source,
            String reasonZh,
            Map<String, Object> target) {
        Map<String, Object> constraints = mapValue(value(frame, "constraints"));
        Map<String, Object> instanceRef = mapValue(value(target, "instance_ref"));
        Object targetIndex = value(target, "target_index");
        String suffix = firstText(value(constraints, "period"), value(frame, "task_type"), "current");
        String base = StringUtils.hasText(attributeName) ? attributeName : factType;
        String subjectKey = subjectKey(subjectType, instanceRef, targetIndex);
        OAGEntity.OAGAttribute attr = attributeMeta.get(attributeName);
        Map<String, Object> attrParams = attr == null ? mapOf() : jsonObject(attr.paramsJson);
        String capabilityStatus = firstText(value(attrParams, "data_capability_status"));
        String unsupportedReasonCode = firstText(value(attrParams, "unsupported_reason_code"));

        OAGVO.FactRequirement row = new OAGVO.FactRequirement();
        row.factRequirementId = ("FactRequirement:fr_" + base + "_" + subjectKey + "_" + suffix).replace(" ", "_");
        row.factType = factType;
        row.factTypeZh = factTypeZh(factType);
        row.subject = new OAGVO.Subject();
        row.subject.objectType = subjectType;
        row.subject.subjectId = subjectId(subjectType, instanceRef, targetIndex);
        row.subject.instanceRef = instanceRef;
        row.subject.labelZh = subjectType;
        row.subject.targetIndex = numberValue(targetIndex);
        row.subject.targetRole = text(value(target, "role"));
        row.subject.targetInstanceId = targetInstanceId(target);
        row.attributeName = attributeName;
        if (StringUtils.hasText(attributeName)) {
            row.attribute = new OAGVO.Attribute();
            row.attribute.attributeName = attributeName;
            row.attribute.attributeNameZh = attr == null ? attributeName : firstText(attr.attributeNameZh, attributeName);
            row.attribute.labelZh = row.attribute.attributeNameZh;
            row.attribute.objectType = attr == null ? "" : firstText(attr.objectType, "");
            row.attribute.descriptionZh = "";
        }
        row.constraints = constraints;
        row.priority = priority;
        row.priorityZh = priorityZh(priority);
        row.reason = reasonZh;
        row.reasonZh = reasonZh;
        row.source = source;
        row.sourceZh = sourceZh(source);
        row.answerVisibility = "supporting".equals(priority) ? "supporting_context" : "answer_fact";
        row.planningRole = priority;
        String labelAttr = row.attribute == null ? row.factTypeZh : firstText(row.attribute.attributeNameZh, attributeName);
        row.labelZh = labelAttr + "事实需求";
        row.descriptionZh = reasonZh;
        row.confidence = "required".equals(priority) ? 0.86 : 0.76;
        if (StringUtils.hasText(capabilityStatus)) {
            row.extra.put("capability_status", capabilityStatus);
            row.extra.put("data_source_status", "unsupported".equals(capabilityStatus) ? "unsupported_by_ifund_all_info" : capabilityStatus);
        }
        if (StringUtils.hasText(unsupportedReasonCode)) {
            row.extra.put("unsupported_reason_code", unsupportedReasonCode);
        }
        if ("unsupported".equals(capabilityStatus)) {
            row.extra.put("unsupported_message_zh", labelAttr + "当前未在 ifund_all_info 中声明可支持，不能规划为 ready Skill。");
        }
        return row;
    }

    private CandidateResult candidateInvocations(
            Map<String, Object> frame,
            List<OAGVO.FactRequirement> facts,
            List<SkillMeta> skills,
            Map<String, Object> userContext) {
        List<OAGVO.CandidateInvocation> invocations = new ArrayList<>();
        List<Map<String, Object>> warnings = new ArrayList<>();
        Set<String> scopes = new LinkedHashSet<>(uniqueStrings(value(userContext, "permission_scopes")));
        for (SkillMeta skill : skills) {
            List<OAGVO.FactRequirement> coveredIgnoringPermission = facts.stream()
                    .filter(fact -> skillCovers(skill, fact))
                    .collect(Collectors.toList());
            if (coveredIgnoringPermission.isEmpty()) {
                continue;
            }
            if (StringUtils.hasText(skill.permissionScope) && !scopes.contains(skill.permissionScope)) {
                warnings.add(row(
                        "warning_code", "SKILL_PERMISSION_BLOCKED",
                        "skill_id", skill.skillId,
                        "skill_name_zh", firstText(skill.skillName, skill.skillId),
                        "permission_scope", skill.permissionScope,
                        "blocked_fact_requirements", coveredIgnoringPermission.stream().map(item -> item.factRequirementId).collect(Collectors.toList()),
                        "message_zh", "Skill " + firstText(skill.skillName, skill.skillId) + " 需要权限 " + skill.permissionScope + "，当前上下文未授权。"
                ));
                continue;
            }
            int groupIndex = 1;
            for (List<OAGVO.FactRequirement> group : invocationFactGroups(skill, coveredIgnoringPermission)) {
                ParamsResult params = skillParams(skill, frame, group);
                if (!params.missing.isEmpty()) {
                    warnings.add(row(
                            "warning_code", "SKILL_PARAMS_MISSING",
                            "skill_id", skill.skillId,
                            "skill_name_zh", firstText(skill.skillName, skill.skillId),
                            "missing_params", params.missing,
                            "message_zh", "Skill " + firstText(skill.skillName, skill.skillId) + " 缺少必要调用参数：" + String.join(", ", params.missing) + "。"
                    ));
                }
                OAGVO.CandidateInvocation invocation = new OAGVO.CandidateInvocation();
                invocation.invocationId = "SkillInvocation:" + skill.skillId + ":" + groupIndex++;
                invocation.skillId = skill.skillId;
                invocation.skillNameZh = firstText(skill.skillName, skill.skillId);
                invocation.descriptionZh = skill.description;
                invocation.toolName = skill.skillId;
                invocation.priority = group.stream().anyMatch(item -> "required".equals(item.priority)) ? "primary" : "optional";
                invocation.coversFactRequirements = group.stream().map(item -> item.factRequirementId).collect(Collectors.toList());
                invocation.coveredSubjects = uniqueStrings(group.stream().map(item -> item.subject == null ? "" : item.subject.subjectId).collect(Collectors.toList()));
                invocation.params = params.params;
                invocation.missingParams = params.missing;
                invocation.permissionScope = skill.permissionScope;
                invocation.coverageScore = coverageScore(group, facts);
                invocation.coversRequiredCount = (int) group.stream().filter(item -> "required".equals(item.priority)).count();
                invocation.coversOptionalCount = (int) group.stream().filter(item -> !"required".equals(item.priority) && !"supporting".equals(item.priority) && !"derived".equals(item.priority)).count();
                invocation.coversSupportingCount = (int) group.stream().filter(item -> "supporting".equals(item.priority)).count();
                invocation.coversDerivedCount = (int) group.stream().filter(item -> "derived".equals(item.priority)).count();
                invocation.coverageReasonZh = coverageReason(skill, group);
                invocation.confidence = params.missing.isEmpty() ? 0.95 : 0.72;
                invocation.matchReasons = listOf(invocation.coverageReasonZh);
                for (OAGVO.FactRequirement item : group) {
                    Map<String, String> expected = new LinkedHashMap<>();
                    expected.put("fact_type", item.factType);
                    expected.put("attribute_name", firstText(item.attributeName, ""));
                    invocation.expectedFacts.add(expected);
                }
                invocations.add(invocation);
            }
        }
        invocations = selectInvocations(invocations, facts, frame);
        invocations.sort(Comparator
                .comparingInt((OAGVO.CandidateInvocation item) -> skillSortRank(item.skillId))
                .thenComparing(item -> item.skillId == null ? "" : item.skillId));
        return new CandidateResult(invocations, warnings);
    }

    private List<OAGVO.FactRequirement> unsupportedRequiredFacts(List<OAGVO.FactRequirement> facts, List<SkillMeta> skills) {
        List<OAGVO.FactRequirement> rows = new ArrayList<>();
        for (OAGVO.FactRequirement fact : facts) {
            if (!"required".equals(fact.priority)) {
                continue;
            }
            if ("unsupported".equals(value(fact.extra, "capability_status"))) {
                rows.add(fact);
                continue;
            }
            Map<String, Object> periodReason = unsupportedPeriodReason(fact, skills);
            if (!periodReason.isEmpty()) {
                fact.extra.put("unsupported_reason_code", periodReason.get("reason_code"));
                fact.extra.put("unsupported_message_zh", periodReason.get("message_zh"));
                if (periodReason.containsKey("closest_supported_periods")) {
                    fact.extra.put("closest_supported_periods", periodReason.get("closest_supported_periods"));
                }
                fact.extra.put("data_source_status", "unsupported_by_ifund_all_info");
                rows.add(fact);
            }
        }
        return rows;
    }

    private Map<String, Object> unsupportedPeriodReason(OAGVO.FactRequirement fact, List<SkillMeta> skills) {
        if (!StringUtils.hasText(fact.attributeName)) {
            return mapOf();
        }
        String period = text(value(fact.constraints, "period"));
        if (!StringUtils.hasText(period)) {
            return mapOf();
        }
        String periodKey = period.toLowerCase(Locale.ROOT);
        Set<String> supported = supportedPeriodsForAttribute(fact.attributeName, skills);
        if (setOf("custom", "custom_range").contains(periodKey) || fact.constraints.containsKey("date_range")) {
            return mapOf(
                    "reason_code", "CUSTOM_DATE_RANGE_REQUIRES_NAV_SERIES",
                    "message_zh", "当前 ifund_all_info 宽表不支持自定义日期区间收益，需要净值时间序列。",
                    "closest_supported_periods", new ArrayList<>(supported)
            );
        }
        if (!supported.isEmpty() && !supported.contains(periodKey)) {
            return mapOf(
                    "reason_code", "UNSUPPORTED_PERIOD",
                    "message_zh", fact.attributeName + " 当前不支持周期 " + period + "，不能规划为 ready Skill。",
                    "closest_supported_periods", new ArrayList<>(supported)
            );
        }
        return mapOf();
    }

    private Set<String> supportedPeriodsForAttribute(String attributeName, List<SkillMeta> skills) {
        Set<String> periods = new LinkedHashSet<>();
        for (SkillMeta skill : skills) {
            if ("unsupported".equals(skill.capabilityStatus) || !skill.supportedAttributes.contains(attributeName)) {
                continue;
            }
            Object values = skill.supportedPeriodsByAttribute.get(attributeName);
            for (String value : uniqueStrings(values)) {
                periods.add(value.toLowerCase(Locale.ROOT));
            }
        }
        return periods;
    }

    private List<OAGVO.CandidateInvocation> selectInvocations(
            List<OAGVO.CandidateInvocation> invocations,
            List<OAGVO.FactRequirement> facts,
            Map<String, Object> frame) {
        Set<String> requiredIds = facts.stream()
                .filter(item -> "required".equals(item.priority))
                .map(item -> item.factRequirementId)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        Set<String> optionalIds = facts.stream()
                .filter(item -> !"required".equals(item.priority) && !"supporting".equals(item.priority) && !"derived".equals(item.priority))
                .map(item -> item.factRequirementId)
                .collect(Collectors.toCollection(LinkedHashSet::new));
        int fundTargetCount = targetsOfType(frame, "Fund", planningTargets(frame)).size();
        List<OAGVO.CandidateInvocation> selected = new ArrayList<>();
        Set<String> selectedIds = new LinkedHashSet<>();
        for (OAGVO.CandidateInvocation invocation : invocations) {
            if (!skillAllowedForTask(invocation.skillId, frame)) {
                continue;
            }
            boolean coversRequired = invocation.coversFactRequirements.stream().anyMatch(requiredIds::contains);
            boolean coversDerivedComparison = "compare_funds_by_metric".equals(invocation.skillId)
                    && invocation.coversDerivedCount > 0
                    && fundTargetCount >= 2;
            if (!coversRequired && !coversDerivedComparison) {
                continue;
            }
            if ("compare_funds_by_metric".equals(invocation.skillId) && fundTargetCount < 2) {
                continue;
            }
            selected.add(invocation);
            selectedIds.addAll(invocation.coversFactRequirements);
        }
        for (OAGVO.CandidateInvocation invocation : invocations) {
            if (selected.contains(invocation)) {
                continue;
            }
            if (!skillAllowedForTask(invocation.skillId, frame)) {
                continue;
            }
            if ("compare_funds_by_metric".equals(invocation.skillId) && fundTargetCount < 2) {
                continue;
            }
            boolean coversUnselectedOptional = invocation.coversFactRequirements.stream()
                    .anyMatch(item -> optionalIds.contains(item) && !selectedIds.contains(item));
            if (coversUnselectedOptional) {
                selected.add(invocation);
                selectedIds.addAll(invocation.coversFactRequirements);
            }
        }
        return selected;
    }

    private boolean skillAllowedForTask(String skillId, Map<String, Object> frame) {
        String taskType = text(value(frame, "task_type"));
        if ("screen".equals(taskType)) {
            return "screen_funds_by_metric_condition".equals(skillId);
        }
        if ("rank".equals(taskType)) {
            return "rank_funds_by_metric".equals(skillId);
        }
        if ("recommend".equals(taskType)) {
            return "recommend_funds_by_risk_return".equals(skillId);
        }
        if (setOf("screen_funds_by_metric_condition", "rank_funds_by_metric", "recommend_funds_by_risk_return").contains(skillId)) {
            return setOf("screen", "rank", "recommend").contains(taskType);
        }
        return true;
    }

    private boolean skillCovers(SkillMeta skill, OAGVO.FactRequirement fact) {
        if ("unsupported".equals(skill.capabilityStatus)) {
            return false;
        }
        if ("unsupported".equals(value(fact.extra, "capability_status"))) {
            return false;
        }
        if (!skill.providesFactTypes.contains(fact.factType)
                && !("relation_instance".equals(fact.factType) && skill.providesFactTypes.contains("object_profile"))) {
            return false;
        }
        if (!skill.supportedSubjectTypes.isEmpty() && fact.subject != null && !skill.supportedSubjectTypes.contains(fact.subject.objectType)) {
            return false;
        }
        if ("relation_instance".equals(fact.factType)) {
            if (!skill.supportedRelations.isEmpty() && skill.supportedRelations.contains(fact.predicate)) {
                return true;
            }
            if (StringUtils.hasText(fact.attributeName) && !skill.supportedAttributes.isEmpty()) {
                return skill.supportedAttributes.contains(fact.attributeName);
            }
            return skill.supportedRelations.isEmpty() && skill.supportedAttributes.isEmpty();
        }
        if (StringUtils.hasText(fact.attributeName) && skill.unsupportedAttributes.contains(fact.attributeName)) {
            return false;
        }
        if (!unsupportedPeriodReason(fact, listOf(skill)).isEmpty()) {
            return false;
        }
        if (StringUtils.hasText(fact.attributeName) && !skill.supportedAttributes.isEmpty() && !skill.supportedAttributes.contains(fact.attributeName)) {
            return false;
        }
        return true;
    }

    private ParamsResult skillParams(SkillMeta skill, Map<String, Object> frame, List<OAGVO.FactRequirement> covered) {
        Map<String, Object> params = new LinkedHashMap<>();
        Map<String, Object> constraints = mapValue(value(frame, "constraints"));
        Map<String, Object> instanceRef = covered.stream()
                .map(item -> item.subject == null ? SemanticFramePlanner.<String, Object>emptyMap() : item.subject.instanceRef)
                .filter(item -> !item.isEmpty())
                .findFirst()
                .orElse(mapOf());
        for (String name : skill.inputParams) {
            if ("attributes".equals(name)) {
                params.put("attributes", uniqueStrings(covered.stream().map(item -> item.attributeName).collect(Collectors.toList())));
            } else if ("fund_code".equals(name) && !instanceRef.containsKey("fund_code")) {
                if (StringUtils.hasText(text(value(instanceRef, "fund_name")))) {
                    params.put("fund_name", value(instanceRef, "fund_name"));
                } else if (StringUtils.hasText(text(value(instanceRef, "fund_short_name")))) {
                    params.put("fund_short_name", value(instanceRef, "fund_short_name"));
                }
            } else if ("fund_codes".equals(name)) {
                List<String> codes = uniqueStrings(covered.stream()
                        .map(item -> item.subject == null ? "" : text(value(item.subject.instanceRef, "fund_code")))
                        .collect(Collectors.toList()));
                if (!codes.isEmpty()) {
                    params.put("fund_codes", codes);
                }
            } else if ("ranking".equals(name)) {
                List<Map<String, Object>> ranking = listMapValue(value(frame, "ranking"));
                params.put("ranking", ranking);
            } else if ("filters".equals(name)) {
                List<Map<String, Object>> filters = listMapValue(value(frame, "filters"));
                params.put("filters", filters);
            } else if ("limit".equals(name) && value(frame, "limit") != null) {
                params.put("limit", value(frame, "limit"));
            } else if (instanceRef.containsKey(name)) {
                params.put(name, instanceRef.get(name));
            } else if (constraints.containsKey(name)) {
                params.put(name, constraints.get(name));
            } else if (value(frame, name) != null) {
                params.put(name, value(frame, name));
            } else if (skill.defaultParams.containsKey(name)) {
                params.put(name, skill.defaultParams.get(name));
            }
        }
        List<String> missing = skill.inputParams.stream()
                .filter(name -> !params.containsKey(name)
                        && !"attributes".equals(name)
                        && !("fund_code".equals(name) && (params.containsKey("fund_name") || params.containsKey("fund_short_name"))))
                .collect(Collectors.toList());
        return new ParamsResult(params, missing);
    }

    private Map<String, Object> coverageSummary(
            List<OAGVO.FactRequirement> facts,
            List<OAGVO.CandidateInvocation> invocations,
            List<Map<String, Object>> warnings) {
        Set<String> covered = new LinkedHashSet<>();
        for (OAGVO.CandidateInvocation invocation : invocations) {
            covered.addAll(invocation.coversFactRequirements);
        }
        List<OAGVO.FactRequirement> required = facts.stream().filter(item -> "required".equals(item.priority)).collect(Collectors.toList());
        List<OAGVO.FactRequirement> optional = facts.stream().filter(item -> !"required".equals(item.priority) && !"supporting".equals(item.priority) && !"derived".equals(item.priority)).collect(Collectors.toList());
        List<OAGVO.FactRequirement> coveredRequired = required.stream().filter(item -> covered.contains(item.factRequirementId)).collect(Collectors.toList());
        List<OAGVO.FactRequirement> coveredOptional = optional.stream().filter(item -> covered.contains(item.factRequirementId)).collect(Collectors.toList());
        List<OAGVO.FactRequirement> uncoveredRequired = required.stream().filter(item -> !covered.contains(item.factRequirementId)).collect(Collectors.toList());
        List<OAGVO.FactRequirement> uncoveredOptional = optional.stream().filter(item -> !covered.contains(item.factRequirementId)).collect(Collectors.toList());
        boolean permissionBlocked = warnings.stream().anyMatch(item -> "SKILL_PERMISSION_BLOCKED".equals(item.get("warning_code")));
        String status;
        if (!required.isEmpty() && coveredRequired.size() == required.size()) {
            status = "full_coverage";
        } else if (!coveredRequired.isEmpty()) {
            status = "partial_coverage";
        } else if (permissionBlocked && !required.isEmpty()) {
            status = "permission_blocked";
        } else {
            status = "no_coverage";
        }
        Map<String, String> messages = mapOf(
                "full_coverage", "必需事实均有 Skill 覆盖，规划可以继续执行。",
                "partial_coverage", "部分必需事实已有 Skill 覆盖，但仍存在能力缺口。",
                "permission_blocked", "存在 Skill 权限未授权，导致事实无法覆盖。",
                "no_coverage", "当前事实需求没有可用 Skill 覆盖，需要补充 Skill 能力声明。"
        );
        String message = messages.get(status);
        return row(
                "required_fact_count", required.size(),
                "covered_required_fact_count", coveredRequired.size(),
                "uncovered_required_facts", uncoveredRows(uncoveredRequired, "当前没有可用 Skill 覆盖该必需事实。"),
                "optional_fact_count", optional.size(),
                "covered_optional_fact_count", coveredOptional.size(),
                "uncovered_optional_facts", uncoveredRows(uncoveredOptional, "当前没有可用 Skill 覆盖该可选补充事实。"),
                "skill_count", invocations.size(),
                "has_permission_blocked_facts", permissionBlocked,
                "coverage_status", status,
                "coverage_message_zh", message
        );
    }

    private List<Map<String, Object>> diagnostics(
            Map<String, Object> frame,
            List<OAGVO.FactRequirement> facts,
            List<OAGVO.CandidateInvocation> invocations,
            Map<String, Object> coverage,
            List<Map<String, Object>> warnings) {
        List<Map<String, Object>> rows = new ArrayList<>();
        if (!SUPPORTED_TASK_TYPES.contains(text(value(frame, "task_type")))) {
            rows.add(row("diagnostic_code", "UNKNOWN_TASK_TYPE", "severity", "warning", "message_zh", "未知任务类型：" + text(value(frame, "task_type")) + "。", "suggestion_zh", "请确认 semantic_frame.task_type 是否符合 OAG 支持范围。"));
        }
        if (requiresMultipleFundTargets(frame) && targetsOfType(frame, "Fund", planningTargets(frame)).size() < 2) {
            rows.add(row("diagnostic_code", "COMPARE_TARGET_TOO_FEW", "severity", "error", "message_zh", "比较任务的基金目标对象少于 2 个。", "suggestion_zh", "请在 target_objects 中提供至少两只 Fund，或改用 FundSet 排序/筛选任务。"));
        }
        if (setOf("rank", "screen", "recommend").contains(text(value(frame, "task_type"))) && explicitFundSetTargetMissing(frame)) {
            rows.add(row("diagnostic_code", "FUNDSET_TARGET_MISSING", "severity", "warning", "message_zh", "集合任务缺少 FundSet 目标对象。", "suggestion_zh", "请补充 FundSet target_object 或 fund_universe。"));
        }
        if (invocations.isEmpty() && !facts.isEmpty()) {
            rows.add(row("diagnostic_code", "CANDIDATE_INVOCATIONS_EMPTY", "severity", "error", "message_zh", "事实需求已生成，但没有任何 Skill 能覆盖。", "suggestion_zh", "请在 skills.yaml 中为相关 fact_type、subject_type 和 attribute 声明 Skill 能力。"));
        }
        for (Map<String, Object> item : warnings) {
            if ("SKILL_PARAMS_MISSING".equals(item.get("warning_code"))) {
                rows.add(row("diagnostic_code", "SKILL_PARAMS_MISSING", "severity", "warning", "skill_id", item.get("skill_id"), "message_zh", item.get("message_zh"), "suggestion_zh", "请在 semantic_frame 的 target_objects、constraints 或 options 中补充参数。"));
            }
        }
        for (Map<String, Object> item : listMapValue(coverage.get("uncovered_required_facts"))) {
            addDiagnosticOnce(rows, row(
                    "diagnostic_code", "REQUIRED_FACT_UNCOVERED",
                    "severity", "warning",
                    "message_zh", "必需事实未覆盖：" + value(item, "label_zh") + "。",
                    "suggestion_zh", firstText(value(item, "reason_zh"), "请补充对应 Skill。")
            ));
        }
        for (OAGVO.FactRequirement fact : facts) {
            boolean covered = invocations.stream().anyMatch(invocation -> invocation.coversFactRequirements.contains(fact.factRequirementId));
            if ("relation_instance".equals(fact.factType) && "required".equals(fact.priority) && !covered) {
                rows.add(row(
                        "diagnostic_code", "RELATION_INSTANCE_UNCOVERED",
                        "severity", "warning",
                        "message_zh", "关系事实未覆盖：" + explicitRelationTypeZh(fact.predicate) + "。",
                        "suggestion_zh", "请确认 get_fund_profile_facts 的 supported_relations 覆盖该关系。"
                ));
            }
            if (fact.subject != null && "FundSet".equals(fact.subject.objectType) && "metric_ranking".equals(fact.factType) && !covered) {
                addDiagnosticOnce(rows, row(
                        "diagnostic_code", "FUNDSET_RANKING_SKILL_MISSING",
                        "severity", "warning",
                        "message_zh", "FundSet 指标排序事实没有 Skill 覆盖。",
                        "suggestion_zh", "请补充 rank_funds_by_metric 或 recommend_funds_by_risk_return 能力声明。"
                ));
            }
            if (fact.subject != null && "FundSet".equals(fact.subject.objectType) && "filter_condition".equals(fact.factType) && !covered) {
                addDiagnosticOnce(rows, row(
                        "diagnostic_code", "FUNDSET_SCREENING_SKILL_MISSING",
                        "severity", "warning",
                        "message_zh", "FundSet 筛选条件事实没有 Skill 覆盖。",
                        "suggestion_zh", "请补充 screen_funds_by_metric_condition 或 recommend_funds_by_risk_return 能力声明。"
                ));
            }
        }
        if (!listMapValue(coverage.get("uncovered_required_facts")).isEmpty()) {
            rows.add(row("diagnostic_code", "REQUIRED_FACT_UNCOVERED", "severity", "warning", "message_zh", "存在必需事实当前没有可用 Skill 覆盖，需要补充能力或调整语义框架。", "suggestion_zh", ""));
        }
        return rows;
    }

    private void addDiagnosticOnce(List<Map<String, Object>> rows, Map<String, Object> diagnostic) {
        boolean exists = rows.stream().anyMatch(item ->
                Objects.equals(value(item, "diagnostic_code"), value(diagnostic, "diagnostic_code"))
                        && Objects.equals(value(item, "message_zh"), value(diagnostic, "message_zh")));
        if (!exists) {
            rows.add(diagnostic);
        }
    }

    private Map<String, Object> taskGraph(
            Map<String, Object> frame,
            List<OAGVO.TargetInstance> targets,
            List<OAGVO.FactRequirement> facts,
            List<OAGVO.CandidateInvocation> invocations) {
        Map<String, Map<String, Object>> nodes = new LinkedHashMap<>();
        Map<String, Map<String, Object>> edges = new LinkedHashMap<>();
        addNode(nodes, row("node_id", "SemanticFrame:current", "node_type", "SemanticFrame", "label_zh", "当前语义框架", "role", "input_context", "description_zh", "前置意图识别节点输出的结构化语义结果。"));
        if (StringUtils.hasText(text(value(frame, "task_type")))) {
            String id = "TaskType:" + value(frame, "task_type");
            addNode(nodes, row("node_id", id, "node_type", "TaskType", "label_zh", taskTypeZh(text(value(frame, "task_type"))), "role", "task_control"));
            addEdge(edges, "SemanticFrame:current", id, "has_task_type", "具有任务类型", "semantic_frame 显式给出 task_type。");
        }
        if (StringUtils.hasText(text(value(frame, "intent")))) {
            String id = "IntentProfile:" + value(frame, "intent");
            addNode(nodes, row("node_id", id, "node_type", "IntentProfile", "label_zh", "意图：" + value(frame, "intent"), "role", "intent_context"));
            addEdge(edges, "SemanticFrame:current", id, "has_intent", "具有意图", "semantic_frame 显式给出 intent。");
        }
        for (OAGVO.TargetInstance target : targets) {
            String objectNode = "ObjectType:" + target.objectType;
            addNode(nodes, row("node_id", objectNode, "node_type", "ObjectType", "label_zh", firstText(target.objectTypeZh, target.objectType), "role", "ontology_object", "object_type", target.objectType));
            addNode(nodes, row("node_id", target.targetInstanceId, "node_type", "TargetInstance", "label_zh", target.displayNameZh, "role", "subject", "object_type", target.objectType, "instance_ref", target.instanceRef));
            addEdge(edges, "SemanticFrame:current", target.targetInstanceId, "has_target", "包含目标对象", "semantic_frame 的 target_objects 指定该对象。");
            addEdge(edges, target.targetInstanceId, objectNode, "has_subject", "属于对象类型", "目标对象实例对应该本体对象类型。");
        }
        for (OAGVO.FactRequirement fact : facts) {
            addNode(nodes, row("node_id", fact.factRequirementId, "node_type", "FactRequirement", "label_zh", fact.labelZh, "role", "fact_requirement", "fact_type", fact.factType, "attribute_name", fact.attributeName, "priority", fact.priority));
            addEdge(edges, "SemanticFrame:current", fact.factRequirementId, "requires_fact", "需要事实", fact.reasonZh);
            if (fact.subject != null && StringUtils.hasText(fact.subject.targetInstanceId)) {
                addEdge(edges, fact.subject.targetInstanceId, fact.factRequirementId, "requires_subject_fact", "主体需要事实", "该事实需求归属于这个目标对象。");
            }
            if (StringUtils.hasText(fact.attributeName)) {
                String attrNode = "Attribute:" + fact.attributeName;
                String attrLabel = fact.attribute == null ? fact.attributeName : firstText(fact.attribute.attributeNameZh, fact.attributeName);
                addNode(nodes, row("node_id", attrNode, "node_type", "Attribute", "label_zh", attrLabel, "role", "fact_attribute", "attribute_name", fact.attributeName));
                addEdge(edges, fact.factRequirementId, attrNode, "has_attribute", "对应属性", "该事实需求需要查询这个属性。");
            }
            if ("relation_instance".equals(fact.factType) && fact.subject != null && StringUtils.hasText(fact.targetObjectType)) {
                String sourceNode = "ObjectType:" + fact.subject.objectType;
                String targetNode = "ObjectType:" + fact.targetObjectType;
                addNode(nodes, row("node_id", sourceNode, "node_type", "ObjectType", "label_zh", fact.subject.objectType, "role", "ontology_object", "object_type", fact.subject.objectType));
                addNode(nodes, row("node_id", targetNode, "node_type", "ObjectType", "label_zh", fact.targetObjectType, "role", "ontology_object", "object_type", fact.targetObjectType));
                addEdge(edges, sourceNode, targetNode, fact.predicate, firstText(fact.predicateZh, relationTypeZh(fact.predicate)), fact.reasonZh);
            }
            List<Map<String, Object>> explanations = new ArrayList<>();
            if (!fact.expandedFrom.isEmpty()) {
                explanations.add(fact.expandedFrom);
            }
            explanations.addAll(fact.relationExplanations);
            for (Map<String, Object> explanation : explanations) {
                String sourceAttr = text(value(explanation, "source_attribute"));
                String targetAttr = firstText(value(explanation, "target_attribute"), fact.attributeName);
                if (StringUtils.hasText(sourceAttr) && StringUtils.hasText(targetAttr)) {
                    String sourceNode = "Attribute:" + sourceAttr;
                    String targetNode = "Attribute:" + targetAttr;
                    addNode(nodes, row("node_id", sourceNode, "node_type", "Attribute", "label_zh", sourceAttr, "role", "fact_attribute", "attribute_name", sourceAttr));
                    addNode(nodes, row("node_id", targetNode, "node_type", "Attribute", "label_zh", targetAttr, "role", "fact_attribute", "attribute_name", targetAttr));
                    addEdge(edges, sourceNode, targetNode, text(value(explanation, "relation_type")), firstText(value(explanation, "relation_type_zh"), "本体关系扩展"), firstText(value(explanation, "reason_zh"), fact.reasonZh));
                }
            }
        }
        for (OAGVO.CandidateInvocation invocation : invocations) {
            addNode(nodes, row("node_id", invocation.invocationId, "node_type", "SkillCapability", "label_zh", invocation.skillNameZh, "role", "skill_candidate", "skill_id", invocation.skillId));
            for (String factId : invocation.coversFactRequirements) {
                addEdge(edges, invocation.invocationId, factId, "covers_fact", "覆盖事实", invocation.coverageReasonZh);
            }
        }
        return row("nodes", new ArrayList<>(nodes.values()), "edges", new ArrayList<>(edges.values()));
    }

    private Map<String, Object> editorPlan(OAGVO.RetrieveResponse response) {
        return row(
                "status", response.status,
                "domain", response.domain,
                "raw_question", response.rawQuestion,
                "error_code", response.errorCode,
                "message_zh", response.messageZh,
                "semantic_frame_summary", response.semanticFrameSummary,
                "normalized_semantic_frame", response.normalizedSemanticFrame,
                "target_instances", response.targetInstances,
                "fact_requirements", response.factRequirements,
                "candidate_invocations", response.candidateInvocations,
                "task_graph", response.taskGraph,
                "coverage_summary", response.coverageSummary,
                "missing_params", response.missingParams,
                "uncovered_facts", response.uncoveredFacts,
                "diagnostics", response.diagnostics,
                "warnings", response.warnings
        );
    }

    private Map<String, Object> agentPlan(Map<String, Object> editorPlan) {
        List<Map<String, Object>> targets = convertList(editorPlan.get("target_instances"));
        List<Map<String, Object>> facts = convertList(editorPlan.get("fact_requirements"));
        List<Map<String, Object>> invocations = convertList(editorPlan.get("candidate_invocations"));
        Map<String, Object> coverage = mapValue(editorPlan.get("coverage_summary"));
        List<Map<String, Object>> skillCalls = invocations.stream().map(item -> skillCall(item, coverage)).collect(Collectors.toList());
        Map<String, Object> projected = row(
                "status", editorPlan.get("status"),
                "task", row(
                        "raw_question", editorPlan.get("raw_question"),
                        "domain", editorPlan.get("domain"),
                        "task_type", firstText(value(mapValue(editorPlan.get("normalized_semantic_frame")), "task_type"), ""),
                        "intent", value(mapValue(editorPlan.get("normalized_semantic_frame")), "intent"),
                        "constraints", firstNonNull(value(mapValue(editorPlan.get("normalized_semantic_frame")), "constraints"), mapOf())
                ),
                "targets", targets.stream().map(this::agentTarget).collect(Collectors.toList()),
                "facts", facts.stream().map(this::agentFact).collect(Collectors.toList()),
                "skill_calls", skillCalls,
                "coverage", row(
                        "coverage_status", coverage.get("coverage_status"),
                        "required_fact_count", coverage.get("required_fact_count"),
                        "covered_required_fact_count", coverage.get("covered_required_fact_count"),
                        "uncovered_required_facts", coverage.get("uncovered_required_facts"),
                        "optional_fact_count", coverage.get("optional_fact_count"),
                        "covered_optional_fact_count", coverage.get("covered_optional_fact_count"),
                        "message_zh", coverage.get("coverage_message_zh")
                ),
                "execution", execution(skillCalls),
                "uncovered_facts", editorPlan.get("uncovered_facts"),
                "issues", issues(editorPlan)
        );
        if (StringUtils.hasText(text(editorPlan.get("error_code")))) {
            projected.put("error_code", editorPlan.get("error_code"));
        }
        if (StringUtils.hasText(text(editorPlan.get("message_zh")))) {
            projected.put("message_zh", editorPlan.get("message_zh"));
        }
        return projected;
    }

    private Map<String, Object> agentTarget(Map<String, Object> item) {
        return row(
                "target_id", value(item, "target_instance_id"),
                "object_type", value(item, "object_type"),
                "label_zh", value(item, "display_name_zh"),
                "instance_ref", value(item, "instance_ref"),
                "role", value(item, "role")
        );
    }

    private Map<String, Object> agentFact(Map<String, Object> item) {
        Map<String, Object> attribute = mapValue(value(item, "attribute"));
        Map<String, Object> subject = mapValue(value(item, "subject"));
        return row(
                "fact_id", value(item, "fact_requirement_id"),
                "fact_type", value(item, "fact_type"),
                "fact_type_zh", value(item, "fact_type_zh"),
                "target_id", value(subject, "target_instance_id"),
                "attribute", value(item, "attribute_name"),
                "attribute_zh", nullableFirstText(value(attribute, "attribute_name_zh"), value(attribute, "label_zh")),
                "predicate", value(item, "predicate"),
                "target_object_type", value(item, "target_object_type"),
                "constraints", value(item, "constraints"),
                "priority", value(item, "priority"),
                "source", value(item, "source"),
                "reason_zh", value(item, "reason_zh")
        );
    }

    private Map<String, Object> skillCall(Map<String, Object> item, Map<String, Object> coverage) {
        List<String> missing = uniqueStrings(value(item, "missing_params"));
        String status;
        if (!missing.isEmpty()) {
            status = "blocked_missing_params";
        } else if ("permission_blocked".equals(coverage.get("coverage_status"))) {
            status = "blocked_permission";
        } else {
            status = "ready";
        }
        return row(
                "skill_id", value(item, "skill_id"),
                "skill_name_zh", value(item, "skill_name_zh"),
                "description_zh", value(item, "description_zh"),
                "params", value(item, "params"),
                "missing_params", missing,
                "covers", uniqueStrings(value(item, "covers_fact_requirements")),
                "covers_required_count", value(item, "covers_required_count"),
                "covers_optional_count", value(item, "covers_optional_count"),
                "coverage_score", value(item, "coverage_score"),
                "coverage_reason_zh", value(item, "coverage_reason_zh"),
                "call_status", status
        );
    }

    private Map<String, Object> execution(List<Map<String, Object>> skillCalls) {
        List<Map<String, Object>> blocking = new ArrayList<>();
        Set<String> blockingKeys = new LinkedHashSet<>();
        for (Map<String, Object> call : skillCalls) {
            if ("blocked_missing_params".equals(call.get("call_status"))) {
                String key = firstText(value(call, "skill_id"), "") + "|" + String.join(",", uniqueStrings(call.get("missing_params")));
                if (!blockingKeys.add(key)) {
                    continue;
                }
                blocking.add(row(
                        "code", "SKILL_PARAMS_MISSING",
                        "skill_id", call.get("skill_id"),
                        "skill_name_zh", call.get("skill_name_zh"),
                        "missing_params", call.get("missing_params"),
                        "message_zh", "调用该 Skill 前需要补充参数：" + String.join("、", uniqueStrings(call.get("missing_params")))
                ));
            }
        }
        String status;
        if (skillCalls.isEmpty()) {
            status = "no_skill_calls";
        } else if (!blocking.isEmpty()) {
            status = "blocked_missing_params";
        } else {
            status = "ready";
        }
        return row(
                "execution_status", status,
                "ready_skill_count", (int) skillCalls.stream().filter(item -> "ready".equals(item.get("call_status"))).count(),
                "blocked_skill_count", (int) skillCalls.stream().filter(item -> "blocked_missing_params".equals(item.get("call_status"))).count(),
                "message_zh", executionMessage(status),
                "blocking_issues", blocking
        );
    }

    private List<Map<String, Object>> issues(Map<String, Object> editorPlan) {
        if ("error".equals(value(editorPlan, "status"))) {
            return listOf();
        }
        List<Map<String, Object>> rows = new ArrayList<>();
        List<Map<String, Object>> delayed = new ArrayList<>();
        for (Map<String, Object> diagnostic : convertList(editorPlan.get("diagnostics"))) {
            if ("SKILL_PARAMS_MISSING".equals(value(diagnostic, "diagnostic_code"))) {
                continue;
            }
            Map<String, Object> issue = row(
                    "code", value(diagnostic, "diagnostic_code"),
                    "severity", firstText(value(diagnostic, "severity"), "warning"),
                    "skill_id", value(diagnostic, "skill_id"),
                    "fact_id", value(diagnostic, "fact_requirement_id"),
                    "message_zh", firstText(value(diagnostic, "message_zh"), ""),
                    "suggestion_zh", firstText(value(diagnostic, "suggestion_zh"), "")
            );
            if ("REQUIRED_FACT_UNCOVERED".equals(value(diagnostic, "diagnostic_code"))
                    && "存在必需事实当前没有可用 Skill 覆盖，需要补充能力或调整语义框架。".equals(value(diagnostic, "message_zh"))) {
                delayed.add(issue);
            } else {
                rows.add(issue);
            }
        }
        for (Map<String, Object> warning : convertList(editorPlan.get("warnings"))) {
            String code = text(firstNonNull(value(warning, "warning_code"), value(warning, "code")));
            if ("SKILL_PARAMS_MISSING".equals(code)) {
                continue;
            }
            rows.add(row(
                    "code", code,
                    "severity", firstText(value(warning, "severity"), "warning"),
                    "skill_id", value(warning, "skill_id"),
                    "fact_id", value(warning, "fact_requirement_id"),
                    "message_zh", firstText(value(warning, "message_zh"), ""),
                    "suggestion_zh", firstText(value(warning, "suggestion_zh"), "")
            ));
        }
        rows.addAll(delayed);
        for (Map<String, Object> item : convertList(editorPlan.get("uncovered_facts"))) {
            rows.add(row(
                    "code", "REQUIRED_FACT_UNCOVERED",
                    "severity", "warning",
                    "skill_id", null,
                    "fact_id", value(item, "fact_requirement_id"),
                    "message_zh", "必需事实未覆盖：" + firstText(value(item, "label_zh"), value(item, "fact_requirement_id"), "") + "。",
                    "suggestion_zh", value(item, "reason_zh")
            ));
        }
        return dedupeIssueRows(rows);
    }

    private List<Map<String, Object>> dedupeIssueRows(List<Map<String, Object>> rows) {
        Map<String, Map<String, Object>> deduped = new LinkedHashMap<>();
        for (Map<String, Object> row : rows) {
            String key = text(value(row, "code"))
                    + "|" + text(value(row, "severity"))
                    + "|" + text(value(row, "skill_id"))
                    + "|" + text(value(row, "fact_id"))
                    + "|" + text(value(row, "message_zh"))
                    + "|" + text(value(row, "suggestion_zh"));
            if (!deduped.containsKey(key)) {
                deduped.put(key, row);
            }
        }
        return new ArrayList<>(deduped.values());
    }

    private Map<String, Object> planViews() {
        return row(
                "editor", row("label_zh", "Editor 调试计划", "description_zh", "保留完整事实需求、任务图、诊断和调试证据。"),
                "agent", row("label_zh", "Agent 执行计划", "description_zh", "面向 MCP/智能体消费的精简 Skill 调用计划。")
        );
    }

    private List<SkillMeta> skillMetas(List<OAGEntity.SkillCapability> dbSkills) {
        List<SkillMeta> rows = new ArrayList<>();
        for (OAGEntity.SkillCapability item : dbSkills) {
            rows.add(new SkillMeta(
                    item.skillId,
                    firstText(item.skillName, item.skillId),
                    text(item.description),
                    text(item.permissionScope),
                    jsonStringList(item.inputParamsJson),
                    jsonObject(item.defaultParamsJson),
                    jsonStringList(item.outputAttributesJson),
                    jsonStringList(item.providesFactTypesJson),
                    jsonStringList(item.supportedSubjectTypesJson),
                    jsonStringList(item.supportedAttributesJson),
                    jsonStringList(item.supportedRelationsJson),
                    firstText(item.capabilityStatus, "full"),
                    jsonStringList(item.unsupportedAttributesJson),
                    jsonObject(item.supportedPeriodsByAttributeJson)
            ));
        }
        return rows;
    }

    private List<OAGVO.TargetInstance> targetInstances(Map<String, Object> frame) {
        List<OAGVO.TargetInstance> rows = new ArrayList<>();
        int index = 1;
        for (Map<String, Object> target : planningTargets(frame)) {
            OAGVO.TargetInstance row = new OAGVO.TargetInstance();
            row.objectType = text(value(target, "object_type"));
            row.objectTypeZh = row.objectType;
            row.instanceRef = mapValue(value(target, "instance_ref"));
            row.role = text(value(target, "role"));
            row.targetInstanceId = "TargetInstance:" + row.objectType + ":" + index++;
            row.displayNameZh = displayTarget(row.objectType, row.instanceRef, row.role);
            row.descriptionZh = "本次问题中的目标对象实例或对象集合。";
            row.source = "semantic_frame.target_objects";
            row.confidence = 1.0;
            rows.add(row);
        }
        return rows;
    }

    private Map<String, Object> semanticFrameSummary(Map<String, Object> frame) {
        return row(
                "task_type", value(frame, "task_type"),
                "intent", value(frame, "intent"),
                "target_objects", value(frame, "target_objects"),
                "constraints", value(frame, "constraints"),
                "mentioned_attributes", value(frame, "mentioned_attributes"),
                "relation_queries", value(frame, "relation_queries"),
                "filters", value(frame, "filters"),
                "ranking", value(frame, "ranking"),
                "comparison", value(frame, "comparison"),
                "limit", value(frame, "limit")
        );
    }

    private List<String> semanticAttributeNames(Map<String, Object> frame, List<OAGEntity.IntentProfile> profiles) {
        LinkedHashSet<String> names = new LinkedHashSet<>();
        for (String name : uniqueStrings(value(frame, "mentioned_attributes"))) {
            names.add(name);
        }
        for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
            if (StringUtils.hasText(text(value(query, "attribute_name")))) {
                addText(names, value(query, "attribute_name"));
            } else {
                addText(names, relationAttribute(text(value(query, "relation_type"))));
            }
        }
        for (Map<String, Object> ranking : listMapValue(value(frame, "ranking"))) {
            addText(names, value(ranking, "attribute"));
        }
        for (Map<String, Object> filter : listMapValue(value(frame, "filters"))) {
            addText(names, value(filter, "attribute"));
        }
        names.addAll(uniqueStrings(value(mapValue(value(frame, "comparison")), "attributes")));
        names.addAll(SCENARIO_ATTRIBUTES.getOrDefault(text(value(frame, "intent")), listOf()));
        if ("profile".equals(value(frame, "task_type"))) {
            names.addAll(SCENARIO_ATTRIBUTES.getOrDefault("fund_profile", listOf()));
        }
        String intent = text(value(frame, "intent"));
        for (OAGEntity.IntentProfile profile : profiles) {
            if (intent.equals(profile.intentName)) {
                for (Map<String, Object> item : factTemplates(profile)) {
                    addText(names, value(item, "attribute_name"));
                }
                names.addAll(jsonStringList(profile.defaultAttributesJson));
            }
        }
        return new ArrayList<>(names);
    }

    private List<String> semanticObjectTypes(Map<String, Object> frame) {
        LinkedHashSet<String> names = new LinkedHashSet<>();
        for (Map<String, Object> target : planningTargets(frame)) {
            addText(names, value(target, "object_type"));
        }
        for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
            addText(names, value(query, "target_object_type"));
        }
        String intent = text(value(frame, "intent"));
        if ("profile".equals(value(frame, "task_type")) || setOf("fund_profile", "profile_query").contains(intent)) {
            names.addAll(listOf("FundManager", "FundCompany", "Benchmark", "FundCategory"));
        }
        if ("benchmark_comparison".equals(intent)) {
            names.add("Benchmark");
        }
        if ("peer_comparison".equals(intent)) {
            names.add("FundCategory");
        }
        if ("fee_analysis".equals(intent)) {
            names.add("FundFee");
        }
        if ("dividend_analysis".equals(intent)) {
            names.add("Dividend");
        }
        if ("holding_analysis".equals(intent)) {
            names.add("FundPosition");
        }
        if ("asset_allocation_analysis".equals(intent)) {
            names.add("AssetAllocation");
        }
        return new ArrayList<>(names);
    }

    private ValidationResult validateSemanticFrame(
            Map<String, Object> frame,
            Map<String, OAGEntity.OAGObject> objects,
            Map<String, OAGEntity.OAGAttribute> attributes,
            Map<String, OAGEntity.IntentProfile> profiles) {
        List<Map<String, Object>> errors = new ArrayList<>();
        List<Map<String, Object>> warnings = new ArrayList<>();
        if (planningTargets(frame).isEmpty()) {
            errors.add(row("diagnostic_code", "TARGET_OBJECTS_REQUIRED", "severity", "error", "message_zh", "semantic_frame 缺少 target_objects。", "suggestion_zh", "请传入至少一个目标对象。"));
        }
        for (Map<String, Object> target : planningTargets(frame)) {
            String objectType = text(value(target, "object_type"));
            if (StringUtils.hasText(objectType) && !objects.containsKey(objectType)) {
                errors.add(row("diagnostic_code", "UNKNOWN_OBJECT_TYPE", "severity", "error", "object_type", objectType, "message_zh", "本体中不存在对象类型：" + objectType + "。", "suggestion_zh", "请确认 semantic_frame.target_objects 中的 object_type。"));
            }
        }
        for (String attr : semanticAttributeNames(frame, new ArrayList<>(profiles.values()))) {
            if (StringUtils.hasText(attr) && !attributes.containsKey(attr)) {
                errors.add(row("diagnostic_code", "UNKNOWN_ATTRIBUTE", "severity", "error", "attribute_name", attr, "message_zh", "本体中不存在属性：" + attr + "。", "suggestion_zh", "请确认 mentioned_attributes、filters、ranking 或 comparison 中的属性名。"));
            }
        }
        for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
            String relationType = text(value(query, "relation_type"));
            String targetObjectType = text(value(query, "target_object_type"));
            if (StringUtils.hasText(targetObjectType) && !objects.containsKey(targetObjectType)) {
                errors.add(row("diagnostic_code", "UNKNOWN_OBJECT_TYPE", "severity", "error", "object_type", targetObjectType, "message_zh", "relation_queries 中不存在目标对象类型：" + targetObjectType + "。", "suggestion_zh", "请确认 relation_queries.target_object_type。"));
            }
        }
        String intent = text(value(frame, "intent"));
        if (StringUtils.hasText(intent) && !profiles.containsKey(intent)) {
            warnings.add(row("warning_code", "UNKNOWN_INTENT", "intent", intent, "message_zh", "未找到意图画像 " + intent + "，将仅基于显式属性和操作规则规划事实需求。"));
        }
        String taskType = text(value(frame, "task_type"));
        if (StringUtils.hasText(taskType) && !SUPPORTED_TASK_TYPES.contains(taskType)) {
            warnings.add(row("warning_code", "UNKNOWN_TASK_TYPE", "task_type", taskType, "message_zh", "未知任务类型 " + taskType + "，Java OAG 会尽量使用已有语义字段规划。"));
        }
        return new ValidationResult(errors, warnings);
    }

    private Map<String, OAGEntity.OAGObject> loadObjectMeta(String domain, List<String> objectIds) {
        if (objectIds.isEmpty()) {
            return mapOf();
        }
        Map<String, OAGEntity.OAGObject> rows = new LinkedHashMap<>();
        for (OAGEntity.OAGObject object : safeList(dao.listObjectsByIds(domain, objectIds))) {
            rows.put(firstText(object.objectId, object.objectType), object);
        }
        return rows;
    }

    private Map<String, OAGEntity.OAGAttribute> loadAttributeMeta(String domain, List<String> names) {
        if (names.isEmpty()) {
            return mapOf();
        }
        Map<String, OAGEntity.OAGAttribute> rows = new LinkedHashMap<>();
        for (OAGEntity.OAGAttribute attribute : safeList(dao.listAttributesByNames(domain, names))) {
            rows.put(attribute.attributeName, attribute);
        }
        return rows;
    }

    private Map<String, OAGEntity.IntentProfile> intentProfileMap(List<OAGEntity.IntentProfile> profiles) {
        Map<String, OAGEntity.IntentProfile> rows = new LinkedHashMap<>();
        for (OAGEntity.IntentProfile profile : profiles) {
            rows.put(profile.intentName, profile);
        }
        return rows;
    }

    private List<Map<String, Object>> factTemplates(OAGEntity.IntentProfile profile) {
        if (profile == null) {
            return listOf();
        }
        return jsonObjectList(profile.factRequirementsTemplateJson);
    }

    private List<Map<String, Object>> planningTargets(Map<String, Object> frame) {
        return listMapValue(value(frame, "target_objects"));
    }

    private List<Map<String, Object>> targetsOfType(Map<String, Object> frame, String objectType, List<Map<String, Object>> fallback) {
        return planningTargets(frame).stream()
                .filter(item -> objectType.equals(value(item, "object_type")))
                .collect(Collectors.toList());
    }

    private List<Map<String, Object>> factTargetsForAttribute(Map<String, Object> frame, String attributeName, List<Map<String, Object>> targets) {
        if (setOf("rank", "screen", "recommend").contains(text(value(frame, "task_type")))) {
            return listOf(fundSetTarget(frame));
        }
        List<Map<String, Object>> funds = targetsOfType(frame, "Fund", targets);
        return funds.isEmpty() ? targets : funds;
    }

    private Map<String, Object> fundSetTarget(Map<String, Object> frame) {
        for (Map<String, Object> target : planningTargets(frame)) {
            if (text(value(target, "object_type")).endsWith("Set")) {
                return target;
            }
        }
        return syntheticFundSetTarget();
    }

    private boolean explicitFundSetTargetMissing(Map<String, Object> frame) {
        return planningTargets(frame).stream()
                .noneMatch(target -> text(value(target, "object_type")).endsWith("Set"));
    }

    private boolean requiresMultipleFundTargets(Map<String, Object> frame) {
        if (!"compare".equals(value(frame, "task_type"))) {
            return false;
        }
        if (setOf("benchmark_comparison", "peer_comparison").contains(text(value(frame, "intent")))) {
            return false;
        }
        Map<String, Object> comparison = mapValue(value(frame, "comparison"));
        if (!uniqueStrings(value(comparison, "benchmark_refs")).isEmpty()
                || !uniqueStrings(value(comparison, "peer_group")).isEmpty()
                || !uniqueStrings(value(comparison, "index_refs")).isEmpty()) {
            return false;
        }
        Set<String> relations = new LinkedHashSet<>();
        for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
            addText(relations, value(query, "relation_type"));
        }
        return disjoint(relations, setOf("has_benchmark", "belongs_to_category", "tracks_index"));
    }

    private Map<String, Object> syntheticFundSetTarget() {
        return row("object_type", "FundSet", "instance_ref", mapOf("fund_universe", "all_funds"), "role", "candidate_set", "target_index", 0);
    }

    private List<String> comparisonAttributes(Map<String, Object> frame) {
        LinkedHashSet<String> names = new LinkedHashSet<>(uniqueStrings(value(mapValue(value(frame, "comparison")), "attributes")));
        names.addAll(uniqueStrings(value(frame, "mentioned_attributes")));
        for (Map<String, Object> ranking : listMapValue(value(frame, "ranking"))) {
            addText(names, value(ranking, "attribute"));
        }
        if (names.isEmpty()) {
            names.add("return_rate");
        }
        return new ArrayList<>(names);
    }

    private void addIfAbsent(List<OAGVO.FactRequirement> rows, OAGVO.FactRequirement item) {
        if (relationFactExists(rows, item)) {
            return;
        }
        boolean exists = rows.stream().anyMatch(row ->
                Objects.equals(row.factType, item.factType)
                        && Objects.equals(row.attributeName, item.attributeName)
                        && Objects.equals(row.predicate, item.predicate)
                        && Objects.equals(row.targetObjectType, item.targetObjectType)
                        && row.subject != null
                        && item.subject != null
                        && Objects.equals(row.subject.subjectId, item.subject.subjectId));
        if (!exists) {
            rows.add(item);
        }
    }

    private boolean relationFactExists(List<OAGVO.FactRequirement> rows, OAGVO.FactRequirement item) {
        if (!"relation_instance".equals(item.factType)) {
            return false;
        }
        String subjectId = item.subject == null ? "" : firstText(item.subject.subjectId, "");
        return rows.stream().anyMatch(row ->
                "relation_instance".equals(row.factType)
                        && Objects.equals(row.predicate, item.predicate)
                        && Objects.equals(row.targetObjectType, item.targetObjectType)
                        && row.subject != null
                        && Objects.equals(firstText(row.subject.subjectId, ""), subjectId));
    }

    private List<String> relationSeedNodeIds(Map<String, Object> frame, List<OAGVO.FactRequirement> facts) {
        LinkedHashSet<String> rows = new LinkedHashSet<>();
        for (Map<String, Object> target : planningTargets(frame)) {
            String objectType = text(value(target, "object_type"));
            if (StringUtils.hasText(objectType)) {
                rows.add("ObjectType:" + objectType);
            }
        }
        for (OAGVO.FactRequirement fact : facts) {
            if (StringUtils.hasText(fact.attributeName)) {
                rows.add("Attribute:" + fact.attributeName);
            }
        }
        return new ArrayList<>(rows);
    }

    private Set<String> requirementKeys(List<OAGVO.FactRequirement> rows) {
        LinkedHashSet<String> keys = new LinkedHashSet<>();
        for (OAGVO.FactRequirement row : rows) {
            keys.add(requirementKey(row));
        }
        return keys;
    }

    private String requirementKey(OAGVO.FactRequirement item) {
        String subjectId = item.subject == null ? "" : firstText(item.subject.subjectId, "");
        return String.join("|",
                firstText(item.factType, ""),
                firstText(item.attributeName, ""),
                subjectId,
                firstText(item.predicate, ""),
                firstText(item.targetObjectType, ""));
    }

    private List<OAGVO.FactRequirement> dedupeRequirements(List<OAGVO.FactRequirement> rows) {
        Map<String, OAGVO.FactRequirement> deduped = new LinkedHashMap<>();
        for (OAGVO.FactRequirement item : rows) {
            String key = requirementKey(item);
            OAGVO.FactRequirement existing = deduped.get(key);
            if (existing != null && "required".equals(existing.priority)) {
                if (!item.expandedFrom.isEmpty()) {
                    existing.relationExplanations.add(item.expandedFrom);
                }
                continue;
            }
            deduped.put(key, item);
        }
        return new ArrayList<>(deduped.values());
    }

    private void attachRelationExplanation(List<OAGVO.FactRequirement> rows, OAGVO.FactRequirement explanation) {
        for (OAGVO.FactRequirement existing : rows) {
            if (Objects.equals(existing.factType, explanation.factType)
                    && Objects.equals(existing.attributeName, explanation.attributeName)
                    && existing.subject != null
                    && explanation.subject != null
                    && Objects.equals(existing.subject.subjectId, explanation.subject.subjectId)) {
                if (!explanation.expandedFrom.isEmpty()) {
                    existing.relationExplanations.add(explanation.expandedFrom);
                }
                return;
            }
        }
    }

    private Map<String, Object> edgeProperties(OAGEntity.GraphEdge edge) {
        Map<String, Object> properties = jsonObject(edge.propertiesJson);
        properties.putIfAbsent("relation_type", edge.relationType);
        properties.putIfAbsent("edge_id", edge.edgeId);
        return properties;
    }

    private int relationExpansionCompare(OAGEntity.GraphEdge left, OAGEntity.GraphEdge right) {
        int leftPhase = semanticExpansionPhase(left);
        int rightPhase = semanticExpansionPhase(right);
        if (leftPhase != rightPhase) {
            return Integer.compare(leftPhase, rightPhase);
        }
        int score = Double.compare(right.score == null ? 0.0 : right.score, left.score == null ? 0.0 : left.score);
        if (score != 0) {
            return score;
        }
        return firstText(left.edgeId, "").compareTo(firstText(right.edgeId, ""));
    }

    private int semanticExpansionPhase(OAGEntity.GraphEdge edge) {
        String[] from = splitNodeId(edge.fromNodeId);
        return "Attribute".equals(from[0]) && SEMANTIC_EXPANSION_TYPES.contains(edge.relationType) ? 0 : 1;
    }

    private boolean edgeApplicable(OAGEntity.GraphEdge edge, Map<String, Object> frame, List<OAGVO.FactRequirement> requirements) {
        Map<String, Object> properties = edgeProperties(edge);
        List<String> tasks = uniqueStrings(value(properties, "applicable_tasks"));
        List<String> intents = uniqueStrings(value(properties, "applicable_intents"));
        Map<String, Object> triggerPolicy = mapValue(value(properties, "trigger_policy"));
        if (!triggerPolicy.isEmpty()) {
            List<String> policyTasks = uniqueStrings(value(triggerPolicy, "tasks"));
            List<String> policyIntents = uniqueStrings(value(triggerPolicy, "intents"));
            if (!policyTasks.isEmpty()) {
                tasks = policyTasks;
            }
            if (!policyIntents.isEmpty()) {
                intents = policyIntents;
            }
        }
        if (!tasks.isEmpty() && !tasks.contains(text(value(frame, "task_type")))) {
            return false;
        }
        String intent = text(value(frame, "intent"));
        if (!intents.isEmpty() && StringUtils.hasText(intent) && !intents.contains(intent)) {
            return false;
        }
        return triggerPolicy.isEmpty() || triggerPolicyMatches(properties, frame, splitNodeId(edge.fromNodeId)[1], requirements);
    }

    private boolean triggerPolicyMatches(
            Map<String, Object> properties,
            Map<String, Object> frame,
            String sourceId,
            List<OAGVO.FactRequirement> requirements) {
        Map<String, Object> policy = mapValue(value(properties, "trigger_policy"));
        if (policy.isEmpty()) {
            return true;
        }
        Set<String> mentioned = new LinkedHashSet<>(uniqueStrings(value(frame, "mentioned_attributes")));
        Set<String> requirementAttrs = new LinkedHashSet<>();
        Set<String> requirementFactTypes = new LinkedHashSet<>();
        for (OAGVO.FactRequirement requirement : requirements) {
            if (StringUtils.hasText(requirement.attributeName)) {
                requirementAttrs.add(requirement.attributeName);
            }
            if (StringUtils.hasText(requirement.factType)) {
                requirementFactTypes.add(requirement.factType);
            }
        }
        Set<String> sourceAttributes = new LinkedHashSet<>(uniqueStrings(value(policy, "source_attributes")));
        if (!sourceAttributes.isEmpty()
                && !sourceAttributes.contains(sourceId)
                && disjoint(sourceAttributes, mentioned)
                && disjoint(sourceAttributes, requirementAttrs)) {
            return false;
        }
        Set<String> sourceFactTypes = new LinkedHashSet<>(uniqueStrings(value(policy, "source_fact_types")));
        if (!sourceFactTypes.isEmpty() && sourceAttributes.contains(sourceId)) {
            OAGVO.FactRequirement sourceReq = requirements.stream()
                    .filter(item -> sourceId.equals(item.attributeName))
                    .findFirst()
                    .orElse(null);
            if (sourceReq != null && !sourceFactTypes.contains(sourceReq.factType)) {
                return false;
            }
        }
        Set<String> requiredFactTypes = new LinkedHashSet<>(uniqueStrings(value(policy, "requires_existing_fact_types")));
        if (!requiredFactTypes.isEmpty() && disjoint(requiredFactTypes, requirementFactTypes)) {
            return false;
        }
        if (booleanValue(value(policy, "requires_explicit_attribute"))) {
            Set<String> explicitAttrs = new LinkedHashSet<>(uniqueStrings(value(policy, "explicit_attributes")));
            if (explicitAttrs.isEmpty()) {
                explicitAttrs.addAll(sourceAttributes);
            }
            if (disjoint(explicitAttrs, mentioned)) {
                return false;
            }
        }
        if (booleanValue(value(policy, "requires_relation_query"))) {
            Set<String> relations = new LinkedHashSet<>();
            for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
                addText(relations, value(query, "relation_type"));
            }
            Set<String> explicitAttrs = new LinkedHashSet<>(uniqueStrings(value(policy, "explicit_attributes")));
            if (explicitAttrs.isEmpty()) {
                explicitAttrs.addAll(sourceAttributes);
            }
            String relationType = text(value(properties, "relation_type"));
            if (!relations.contains(relationType) && disjoint(explicitAttrs, mentioned)) {
                return false;
            }
        }
        return true;
    }

    private boolean explicitRelationTriggered(Map<String, Object> properties, Map<String, Object> frame, String relationType) {
        Map<String, Object> policy = mapValue(value(properties, "trigger_policy"));
        Set<String> mentioned = new LinkedHashSet<>(uniqueStrings(value(frame, "mentioned_attributes")));
        Set<String> explicitAttrs = new LinkedHashSet<>(uniqueStrings(value(policy, "explicit_attributes")));
        if (explicitAttrs.isEmpty()) {
            explicitAttrs.addAll(uniqueStrings(value(policy, "source_attributes")));
        }
        Set<String> relationQueries = new LinkedHashSet<>();
        for (Map<String, Object> query : listMapValue(value(frame, "relation_queries"))) {
            addText(relationQueries, value(query, "relation_type"));
        }
        if (relationQueries.contains(relationType) || !disjoint(explicitAttrs, mentioned)) {
            return true;
        }
        Set<String> intents = new LinkedHashSet<>(uniqueStrings(value(policy, "intents")));
        return StringUtils.hasText(text(value(frame, "intent")))
                && intents.contains(text(value(frame, "intent")))
                && setOf("query", "explain").contains(text(value(frame, "task_type")));
    }

    private Map<String, Object> targetBySubjectId(Map<String, Object> frame, String subjectId) {
        for (Map<String, Object> target : planningTargets(frame)) {
            String objectType = firstText(value(target, "object_type"), "Fund");
            String id = subjectId(objectType, mapValue(value(target, "instance_ref")), value(target, "target_index"));
            if (Objects.equals(id, subjectId)) {
                return target;
            }
        }
        List<Map<String, Object>> targets = planningTargets(frame);
        return targets.isEmpty() ? mapOf() : targets.get(0);
    }

    private List<List<OAGVO.FactRequirement>> invocationFactGroups(SkillMeta skill, List<OAGVO.FactRequirement> covered) {
        if (skill.supportedSubjectTypes.contains("FundSet") || skill.inputParams.contains("fund_codes")) {
            return listOf(covered);
        }
        Map<String, List<OAGVO.FactRequirement>> groups = new LinkedHashMap<>();
        for (OAGVO.FactRequirement fact : covered) {
            String subjectId = fact.subject == null ? "global" : firstText(fact.subject.subjectId, "global");
            groups.computeIfAbsent(subjectId, ignored -> new ArrayList<>()).add(fact);
        }
        return new ArrayList<>(groups.values());
    }

    private List<OAGVO.FactGroup> factGroups(List<OAGVO.FactRequirement> facts) {
        List<OAGVO.FactGroup> rows = new ArrayList<>();
        addGroup(rows, "fg_required", "必需事实", "回答问题前必须获取的事实。", facts.stream().filter(item -> "required".equals(item.priority)).map(item -> item.factRequirementId).collect(Collectors.toList()), "required");
        addGroup(rows, "fg_optional", "可选事实", "可增强回答质量的补充事实。", facts.stream().filter(item -> !"required".equals(item.priority)).map(item -> item.factRequirementId).collect(Collectors.toList()), "optional");
        return rows;
    }

    private void addGroup(List<OAGVO.FactGroup> rows, String id, String name, String purpose, List<String> factIds, String priority) {
        if (factIds.isEmpty()) {
            return;
        }
        OAGVO.FactGroup group = new OAGVO.FactGroup();
        group.groupId = id;
        group.groupName = name;
        group.purpose = purpose;
        group.factRequirementIds = factIds;
        group.priority = priority;
        rows.add(group);
    }

    private List<OAGVO.MissingParam> missingParams(List<OAGVO.CandidateInvocation> invocations) {
        List<OAGVO.MissingParam> rows = new ArrayList<>();
        for (OAGVO.CandidateInvocation invocation : invocations) {
            for (String param : invocation.missingParams) {
                OAGVO.MissingParam row = new OAGVO.MissingParam();
                row.source = "candidate_invocations";
                row.paramName = param;
                row.missingParams = listOf(param);
                row.factRequirementIds = invocation.coversFactRequirements;
                row.suggestedQuestion = "请补充参数：" + param;
                rows.add(row);
            }
        }
        return rows;
    }

    private OAGVO.RetrievalSummary retrievalSummary(Map<String, Object> frame, List<OAGVO.FactRequirement> facts, List<OAGVO.CandidateInvocation> invocations) {
        OAGVO.RetrievalSummary summary = new OAGVO.RetrievalSummary();
        summary.mainObjectTypes = uniqueStrings(planningTargets(frame).stream().map(item -> text(value(item, "object_type"))).collect(Collectors.toList()));
        summary.mainAttributes = uniqueStrings(facts.stream().map(item -> item.attributeName).collect(Collectors.toList()));
        summary.mainSkills = uniqueStrings(invocations.stream().map(item -> item.skillId).collect(Collectors.toList()));
        summary.period = text(value(mapValue(value(frame, "constraints")), "period"));
        summary.fundCode = planningTargets(frame).stream()
                .map(item -> text(value(mapValue(value(item, "instance_ref")), "fund_code")))
                .filter(StringUtils::hasText)
                .findFirst()
                .orElse("");
        summary.factRequirementCount = facts.size();
        summary.candidateInvocationCount = invocations.size();
        return summary;
    }

    private OAGVO.Confidence confidence(List<OAGVO.FactRequirement> facts, List<OAGVO.CandidateInvocation> invocations, String status) {
        OAGVO.Confidence confidence = new OAGVO.Confidence();
        confidence.entityMatch = facts.isEmpty() ? 0.0 : 0.9;
        confidence.attributeMatch = facts.isEmpty() ? 0.0 : 0.86;
        confidence.skillMatch = invocations.isEmpty() ? 0.0 : invocations.stream().mapToDouble(item -> item.confidence).average().orElse(0.0);
        confidence.overall = "success".equals(status) ? round3((confidence.entityMatch + confidence.attributeMatch + confidence.skillMatch) / 3.0) : 0.0;
        return confidence;
    }

    private OAGVO.Truncation truncation(List<OAGVO.FactRequirement> facts, List<OAGVO.CandidateInvocation> invocations) {
        OAGVO.Truncation truncation = new OAGVO.Truncation();
        truncation.detailLevel = "semantic_frame";
        truncation.originalCounts.put("fact_requirements", facts.size());
        truncation.originalCounts.put("candidate_invocations", invocations.size());
        truncation.returnedCounts.put("fact_requirements", facts.size());
        truncation.returnedCounts.put("candidate_invocations", invocations.size());
        return truncation;
    }

    private Map<String, Object> resolvedParams(Map<String, Object> frame) {
        Map<String, Object> params = new LinkedHashMap<>(mapValue(value(frame, "constraints")));
        for (Map<String, Object> target : planningTargets(frame)) {
            params.putAll(mapValue(value(target, "instance_ref")));
        }
        if (value(frame, "limit") != null) {
            params.put("limit", value(frame, "limit"));
        }
        return params;
    }

    private List<Map<String, Object>> matchedIntents(Map<String, Object> frame, Map<String, OAGEntity.IntentProfile> profiles) {
        String intent = text(value(frame, "intent"));
        if (!StringUtils.hasText(intent)) {
            return listOf();
        }
        OAGEntity.IntentProfile profile = profiles.get(intent);
        return listOf(row(
                "intent_name", intent,
                "intent_name_zh", profile == null ? intent : firstText(profile.intentNameZh, intent),
                "confidence", profile == null ? 0.55 : 0.9,
                "match_reason", "semantic_frame.intent"
        ));
    }

    private List<Map<String, Object>> matchedAttributes(List<String> names, Map<String, OAGEntity.OAGAttribute> meta) {
        List<Map<String, Object>> rows = new ArrayList<>();
        for (String name : names) {
            OAGEntity.OAGAttribute attr = meta.get(name);
            rows.add(row(
                    "attribute_name", name,
                    "attribute_name_zh", attr == null ? name : firstText(attr.attributeNameZh, name),
                    "object_type", attr == null ? "" : firstText(attr.objectType, ""),
                    "confidence", attr == null ? 0.72 : 0.9,
                    "match_reason", "semantic_frame"
            ));
        }
        return rows;
    }

    private void addNode(Map<String, Map<String, Object>> nodes, Map<String, Object> node) {
        nodes.putIfAbsent(text(node.get("node_id")), node);
    }

    private void addEdge(Map<String, Map<String, Object>> edges, String source, String target, String relationType, String labelZh, String reasonZh) {
        String edgeId = source + "__" + relationType + "__" + target;
        edges.putIfAbsent(edgeId, row("edge_id", edgeId, "source", source, "target", target, "relation_type", relationType, "label_zh", labelZh, "reason_zh", reasonZh));
    }

    private List<Map<String, Object>> uncoveredRows(List<OAGVO.FactRequirement> facts, String reason) {
        return facts.stream()
                .map(item -> row("fact_requirement_id", item.factRequirementId, "label_zh", item.labelZh, "reason_zh", reason))
                .collect(Collectors.toList());
    }

    private double coverageScore(List<OAGVO.FactRequirement> covered, List<OAGVO.FactRequirement> all) {
        if (all.isEmpty()) {
            return 0.0;
        }
        Set<String> ids = new LinkedHashSet<>(covered.stream().map(item -> item.factRequirementId).collect(Collectors.toList()));
        double score = 0;
        double total = 0;
        for (OAGVO.FactRequirement fact : all) {
            double weight = "required".equals(fact.priority) ? 2.0 : 1.0;
            total += weight;
            if (ids.contains(fact.factRequirementId)) {
                score += weight;
            }
        }
        return total == 0 ? 0.0 : round3(score / total);
    }

    private String coverageReason(SkillMeta skill, List<OAGVO.FactRequirement> covered) {
        List<String> attrs = covered.stream()
                .filter(item -> StringUtils.hasText(item.attributeName))
                .map(item -> firstText(item.attribute == null ? "" : item.attribute.attributeNameZh, item.attributeName))
                .collect(Collectors.toList());
        List<String> relations = covered.stream()
                .filter(item -> "relation_instance".equals(item.factType))
                .map(item -> item.predicateZh)
                .filter(StringUtils::hasText)
                .collect(Collectors.toList());
        List<String> subjects = uniqueStrings(covered.stream().map(item -> item.subject == null ? "" : item.subject.objectType).collect(Collectors.toList())).stream().sorted().collect(Collectors.toList());
        String attrText = firstText(String.join("、", concat(attrs, relations)), "相关事实");
        return "该 Skill 声明支持 " + String.join(", ", subjects) + " 的 " + attrText + " 查询，并且 fact_type 与事实需求匹配。";
    }

    private int skillSortRank(String skillId) {
        List<String> order = listOf(
                "get_fund_metric_values",
                "get_fund_benchmark_facts",
                "get_fund_peer_ranking_facts",
                "get_fund_profile_facts",
                "get_fund_risk_facts",
                "rank_funds_by_metric",
                "screen_funds_by_metric_condition",
                "recommend_funds_by_risk_return",
                "compare_funds_by_metric",
                "get_fund_fee_facts",
                "get_fund_dividend_facts",
                "get_fund_allocation_facts",
                "get_fund_holding_facts"
        );
        int index = order.indexOf(skillId);
        return index < 0 ? 99 : index;
    }

    private String defaultFactType(Map<String, OAGEntity.OAGAttribute> attributes, String attributeName, String explicitFactType) {
        if (StringUtils.hasText(explicitFactType)) {
            return explicitFactType;
        }
        OAGEntity.OAGAttribute attr = attributes.get(attributeName);
        Map<String, Object> params = attr == null ? mapOf() : jsonObject(attr.paramsJson);
        String yamlFactType = firstText(value(params, "default_fact_type"));
        if (StringUtils.hasText(yamlFactType)) {
            return yamlFactType;
        }
        return "metric_value";
    }

    private RelationHint relationHint(Map<String, OAGEntity.OAGAttribute> attributes, String attributeName) {
        OAGEntity.OAGAttribute attr = attributes.get(attributeName);
        if (attr != null) {
            Map<String, Object> params = jsonObject(attr.paramsJson);
            Map<String, Object> relationQuery = mapValue(value(params, "relation_query"));
            String relationType = text(value(relationQuery, "relation_type"));
            String targetObjectType = text(value(relationQuery, "target_object_type"));
            if (StringUtils.hasText(relationType) && StringUtils.hasText(targetObjectType)) {
                return new RelationHint(
                        relationType,
                        targetObjectType,
                        firstText(value(relationQuery, "attribute_name"), attributeName)
                );
            }
        }
        return null;
    }

    private String relationTarget(String relation) {
        if ("managed_by".equals(relation)) return "FundManager";
        if ("issued_by".equals(relation) || "managed_by_company".equals(relation)) return "FundCompany";
        if ("has_benchmark".equals(relation)) return "Benchmark";
        if ("belongs_to_category".equals(relation)) return "FundCategory";
        if ("has_fee".equals(relation)) return "FundFee";
        if ("has_dividend".equals(relation)) return "Dividend";
        if ("has_position".equals(relation)) return "FundPosition";
        if ("has_asset_allocation".equals(relation)) return "AssetAllocation";
        return "";
    }

    private String relationAttribute(String relation) {
        if ("managed_by".equals(relation)) return "manager_name";
        if ("issued_by".equals(relation) || "managed_by_company".equals(relation)) return "company_name";
        if ("has_benchmark".equals(relation)) return "benchmark_name";
        if ("belongs_to_category".equals(relation)) return "fund_type";
        if ("has_fee".equals(relation)) return "fee_value";
        if ("has_dividend".equals(relation)) return "dividend_per_share";
        if ("has_position".equals(relation)) return "stock_name";
        if ("has_asset_allocation".equals(relation)) return "asset_total_value";
        return "";
    }

    private String relationTypeZh(String relationType) {
        if ("managed_by".equals(relationType)) return "管理关系";
        if ("issued_by".equals(relationType)) return "基金公司发行或管理";
        if ("managed_by_company".equals(relationType)) return "基金公司管理";
        if ("has_benchmark".equals(relationType)) return "基准关系";
        if ("tracks_index".equals(relationType)) return "跟踪指数";
        if ("belongs_to_category".equals(relationType)) return "分类关系";
        if ("has_dividend".equals(relationType)) return "分红关系";
        if ("has_fee".equals(relationType)) return "费率关系";
        if ("has_asset_allocation".equals(relationType)) return "资产配置关系";
        if ("has_position".equals(relationType)) return "持仓关系";
        return relationType;
    }

    private String explicitRelationReason(String relationType, String targetObjectType) {
        return "用户需要查询基金与" + relationTargetZh(targetObjectType) + "之间的" + explicitRelationTypeZh(relationType) + "。";
    }

    private String explicitRelationTypeZh(String relationType) {
        if ("has_dividend".equals(relationType)) return "分红关系";
        if ("has_fee".equals(relationType)) return "费率关系";
        if ("has_position".equals(relationType)) return "持仓关系";
        return relationTypeZh(relationType);
    }

    private String relationTargetZh(String targetObjectType) {
        if ("FundManager".equals(targetObjectType)) return "基金经理";
        if ("FundCompany".equals(targetObjectType)) return "基金公司";
        if ("Benchmark".equals(targetObjectType)) return "业绩比较基准";
        if ("FundCategory".equals(targetObjectType)) return "基金分类";
        if ("Index".equals(targetObjectType)) return "指数";
        if ("AssetAllocation".equals(targetObjectType)) return "资产配置";
        if ("FundFee".equals(targetObjectType)) return "基金费率";
        if ("Dividend".equals(targetObjectType)) return "基金分红";
        if ("FundPosition".equals(targetObjectType)) return "基金持仓";
        return targetObjectType;
    }

    private String relationSubjectZh(String subjectObjectType) {
        if ("FundSet".equals(subjectObjectType)) return "基金集合";
        return "基金产品";
    }

    private String relationFactLabelZh(String relationType, String targetObjectType) {
        return relationTargetZh(targetObjectType) + "关系";
    }

    private String scenarioFactType(String intent) {
        if ("fee_analysis".equals(intent)) return "fee_fact";
        if ("dividend_analysis".equals(intent)) return "dividend_fact";
        if ("holding_analysis".equals(intent)) return "holding_fact";
        if ("asset_allocation_analysis".equals(intent)) return "allocation_fact";
        return null;
    }

    private List<String> scenarioAttributesForFrame(Map<String, Object> frame, List<String> mentioned) {
        String intent = text(value(frame, "intent"));
        if (setOf("fund_profile", "profile_query").contains(intent)
                && !mentioned.isEmpty()
                && !"profile".equals(value(frame, "task_type"))) {
            return mentioned.stream().filter(PROFILE_FACT_ATTRIBUTES::contains).collect(Collectors.toList());
        }
        if ("asset_allocation_analysis".equals(intent)
                && mentioned.stream().anyMatch(ASSET_ALLOCATION_ATTRIBUTES::contains)) {
            return mentioned.stream().filter(ASSET_ALLOCATION_ATTRIBUTES::contains).collect(Collectors.toList());
        }
        if (setOf("fee_analysis", "dividend_analysis", "holding_analysis").contains(intent)) {
            List<String> scenarioAttrs = SCENARIO_ATTRIBUTES.getOrDefault(intent, listOf());
            List<String> explicit = mentioned.stream().filter(scenarioAttrs::contains).collect(Collectors.toList());
            if (!explicit.isEmpty()) {
                return explicit;
            }
        }
        return SCENARIO_ATTRIBUTES.getOrDefault(intent, listOf());
    }

    private String scenarioReason(String intent) {
        if ("fund_profile".equals(intent) || "profile_query".equals(intent)) return "画像类查询需要基金基础信息及核心对象关系。";
        if ("fee_analysis".equals(intent)) return "费率查询需要基金费率事实。";
        if ("dividend_analysis".equals(intent)) return "分红查询需要基金分红事实。";
        if ("holding_analysis".equals(intent)) return "持仓查询需要基金持仓事实。";
        if ("asset_allocation_analysis".equals(intent)) return "配置查询需要基金资产配置事实。";
        return "业务场景规则要求补充该事实。";
    }

    private String factTypeZh(String factType) {
        if ("metric_value".equals(factType)) return "指标值";
        if ("benchmark_metric_value".equals(factType)) return "基准指标值";
        if ("excess_metric_value".equals(factType)) return "超额指标值";
        if ("peer_rank".equals(factType)) return "同类排名";
        if ("peer_average".equals(factType)) return "同类平均";
        if ("entity_set".equals(factType)) return "候选对象集合";
        if ("metric_ranking".equals(factType)) return "指标排序";
        if ("filter_condition".equals(factType)) return "筛选条件";
        if ("relation_instance".equals(factType)) return "关系事实";
        if ("object_profile".equals(factType)) return "对象基础事实";
        if ("comparison_result".equals(factType)) return "比较结果";
        if ("holding_fact".equals(factType)) return "持仓事实";
        if ("allocation_fact".equals(factType)) return "配置事实";
        if ("fee_fact".equals(factType)) return "费率事实";
        if ("dividend_fact".equals(factType)) return "分红事实";
        if ("document_fact".equals(factType)) return "文档事实";
        return factType;
    }

    private String sourceZh(String source) {
        if ("explicit_attribute".equals(source)) return "显式属性";
        if ("intent_template".equals(source)) return "意图模板";
        if ("operation_rule".equals(source)) return "操作规则";
        if ("relation_expansion".equals(source)) return "本体关系扩展";
        if ("explicit_relation".equals(source)) return "显式关系查询";
        if ("scenario_rule".equals(source)) return "场景规划规则";
        return source;
    }

    private String priorityZh(String priority) {
        if ("required".equals(priority)) return "必需";
        if ("supporting".equals(priority)) return "支撑上下文";
        if ("derived".equals(priority)) return "派生事实";
        if ("debug".equals(priority)) return "调试证据";
        return "可选";
    }

    private String taskTypeZh(String taskType) {
        if ("query".equals(taskType)) return "查询任务";
        if ("analyze".equals(taskType)) return "分析任务";
        if ("compare".equals(taskType)) return "比较任务";
        if ("rank".equals(taskType)) return "排序任务";
        if ("screen".equals(taskType)) return "筛选任务";
        if ("recommend".equals(taskType)) return "推荐任务";
        if ("explain".equals(taskType)) return "解释任务";
        if ("profile".equals(taskType)) return "画像任务";
        if ("summarize".equals(taskType)) return "总结任务";
        return "业务任务";
    }

    private String executionMessage(String status) {
        if ("ready".equals(status)) return "Skill 调用参数齐全，可以执行。";
        if ("blocked_missing_params".equals(status)) return "存在 Skill 调用缺失参数，需要补充后再执行。";
        if ("no_skill_calls".equals(status)) return "当前没有可执行的 Skill 调用建议。";
        return "当前 Skill 调用状态需要人工确认。";
    }

    private String displayTarget(String objectType, Map<String, Object> instanceRef, String role) {
        if (StringUtils.hasText(text(value(instanceRef, "fund_code")))) {
            return "基金 " + value(instanceRef, "fund_code");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_name")))) {
            return "基金 " + value(instanceRef, "fund_name");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_short_name")))) {
            return "基金 " + value(instanceRef, "fund_short_name");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_universe")))) {
            return "基金集合 " + value(instanceRef, "fund_universe");
        }
        return objectType + " 目标对象" + (StringUtils.hasText(role) ? "（" + role + "）" : "");
    }

    private String subjectKey(String subjectType, Map<String, Object> instanceRef, Object targetIndex) {
        if (StringUtils.hasText(text(value(instanceRef, "fund_code")))) {
            return text(value(instanceRef, "fund_code"));
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_name")))) {
            return "name_" + value(instanceRef, "fund_name");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_short_name")))) {
            return "short_name_" + value(instanceRef, "fund_short_name");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_universe")))) {
            return text(value(instanceRef, "fund_universe"));
        }
        if (targetIndex != null) {
            return subjectType + "_" + targetIndex;
        }
        return subjectType;
    }

    private String subjectId(String subjectType, Map<String, Object> instanceRef, Object targetIndex) {
        if (StringUtils.hasText(text(value(instanceRef, "fund_code")))) {
            return subjectType + ":" + value(instanceRef, "fund_code");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_name")))) {
            return subjectType + ":name:" + value(instanceRef, "fund_name");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_short_name")))) {
            return subjectType + ":short_name:" + value(instanceRef, "fund_short_name");
        }
        if (StringUtils.hasText(text(value(instanceRef, "fund_universe")))) {
            return subjectType + ":" + value(instanceRef, "fund_universe");
        }
        if (targetIndex != null) {
            return subjectType + ":" + targetIndex;
        }
        return subjectType;
    }

    private String targetInstanceId(Map<String, Object> target) {
        Object index = value(target, "target_index");
        if (index == null || Objects.equals(index, 0)) {
            return "";
        }
        return "TargetInstance:" + firstText(value(target, "object_type"), "Fund") + ":" + index;
    }

    private Integer numberValue(Object value) {
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        if (!StringUtils.hasText(text(value))) {
            return null;
        }
        try {
            return Integer.parseInt(text(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        if (!StringUtils.hasText(text(value))) {
            return fallback;
        }
        try {
            return Integer.parseInt(text(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private boolean booleanValue(Object value) {
        if (value instanceof Boolean) {
            return ((Boolean) value).booleanValue();
        }
        return "true".equalsIgnoreCase(text(value)) || "1".equals(text(value));
    }

    private Object firstNonNull(Object first, Object second) {
        return first == null ? second : first;
    }

    private boolean disjoint(Set<String> left, Set<String> right) {
        for (String item : left) {
            if (right.contains(item)) {
                return false;
            }
        }
        return true;
    }

    private String[] splitNodeId(String nodeId) {
        String text = firstText(nodeId, "");
        int index = text.indexOf(':');
        if (index < 0) {
            return new String[]{"", text};
        }
        return new String[]{text.substring(0, index), text.substring(index + 1)};
    }

    private Object value(Object source, String snakeKey) {
        if (!(source instanceof Map<?, ?>)) {
            return null;
        }
        Map<?, ?> raw = (Map<?, ?>) source;
        if (raw.containsKey(snakeKey)) {
            return raw.get(snakeKey);
        }
        String camel = toCamel(snakeKey);
        return raw.get(camel);
    }

    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?>) {
            Map<?, ?> raw = (Map<?, ?>) value;
            Map<String, Object> result = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : raw.entrySet()) {
                result.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return result;
        }
        return new LinkedHashMap<>();
    }

    private List<Map<String, Object>> listMapValue(Object value) {
        if (!(value instanceof List<?>)) {
            return listOf();
        }
        List<?> list = (List<?>) value;
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Object item : list) {
            Map<String, Object> row = mapValue(item);
            if (!row.isEmpty()) {
                rows.add(row);
            }
        }
        return rows;
    }

    private List<Map<String, Object>> convertList(Object value) {
        if (!(value instanceof List<?>)) {
            return listOf();
        }
        List<?> list = (List<?>) value;
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?>) {
                rows.add(mapValue(item));
            } else {
                rows.add(objectMapper.convertValue(item, new TypeReference<Map<String, Object>>() {}));
            }
        }
        return rows;
    }

    private List<String> uniqueStrings(Object value) {
        if (!(value instanceof Iterable<?>)) {
            return listOf();
        }
        Iterable<?> items = (Iterable<?>) value;
        LinkedHashSet<String> rows = new LinkedHashSet<>();
        for (Object item : items) {
            String text = text(item);
            if (StringUtils.hasText(text)) {
                rows.add(text);
            }
        }
        return new ArrayList<>(rows);
    }

    private void addText(Set<String> rows, Object value) {
        String text = text(value);
        if (StringUtils.hasText(text)) {
            rows.add(text);
        }
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String firstText(Object... values) {
        for (Object value : values) {
            String text = text(value);
            if (StringUtils.hasText(text)) {
                return text;
            }
        }
        return "";
    }

    private String nullableFirstText(Object... values) {
        String value = firstText(values);
        return StringUtils.hasText(value) ? value : null;
    }

    private List<String> concat(List<String> left, List<String> right) {
        List<String> rows = new ArrayList<>(left);
        rows.addAll(right);
        return rows;
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

    private List<String> jsonStringList(String json) {
        if (!StringUtils.hasText(json)) {
            return listOf();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception ignored) {
            return listOf();
        }
    }

    private List<Map<String, Object>> jsonObjectList(String json) {
        if (!StringUtils.hasText(json)) {
            return listOf();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<Map<String, Object>>>() {});
        } catch (Exception ignored) {
            return listOf();
        }
    }

    private Map<String, Object> jsonObject(String json) {
        if (!StringUtils.hasText(json)) {
            return new LinkedHashMap<>();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception ignored) {
            return new LinkedHashMap<>();
        }
    }

    private String relationReason(String relationType, String sourceAttr, String targetAttr, Map<String, OAGEntity.OAGAttribute> attributes) {
        OAGEntity.OAGAttribute source = attributes.get(sourceAttr);
        OAGEntity.OAGAttribute target = attributes.get(targetAttr);
        String sourceLabel = source == null ? sourceAttr : firstText(source.attributeNameZh, sourceAttr);
        String targetLabel = target == null ? targetAttr : firstText(target.attributeNameZh, targetAttr);
        return "本体关系 " + relationTypeZh(relationType) + " 表明分析" + sourceLabel + "时通常需要补充" + targetLabel + "。";
    }

    private <T> List<T> safeList(List<T> rows) {
        return rows == null ? listOf() : rows;
    }

    private double round3(double value) {
        return Math.round(value * 1000.0) / 1000.0;
    }

    private Map<String, Object> row(Object... pairs) {
        Map<String, Object> row = new LinkedHashMap<>();
        for (int index = 0; index + 1 < pairs.length; index += 2) {
            row.put(String.valueOf(pairs[index]), pairs[index + 1]);
        }
        return row;
    }

    private static <K, V> Map<K, V> emptyMap() {
        return mapOf();
    }

    private static final class RelationHint {
        private final String relationType;
        private final String targetObjectType;
        private final String attributeName;

        private RelationHint(String relationType, String targetObjectType, String attributeName) {
            this.relationType = relationType;
            this.targetObjectType = targetObjectType;
            this.attributeName = attributeName;
        }
    }

    private static final class SkillMeta {
        private final String skillId;
        private final String skillName;
        private final String description;
        private final String permissionScope;
        private final List<String> inputParams;
        private final Map<String, Object> defaultParams;
        private final List<String> outputAttributes;
        private final List<String> providesFactTypes;
        private final List<String> supportedSubjectTypes;
        private final List<String> supportedAttributes;
        private final List<String> supportedRelations;
        private final String capabilityStatus;
        private final List<String> unsupportedAttributes;
        private final Map<String, Object> supportedPeriodsByAttribute;

        private SkillMeta(String skillId,
                          String skillName,
                          String description,
                          String permissionScope,
                          List<String> inputParams,
                          Map<String, Object> defaultParams,
                          List<String> outputAttributes,
                          List<String> providesFactTypes,
                          List<String> supportedSubjectTypes,
                          List<String> supportedAttributes,
                          List<String> supportedRelations,
                          String capabilityStatus,
                          List<String> unsupportedAttributes,
                          Map<String, Object> supportedPeriodsByAttribute) {
            this.skillId = skillId;
            this.skillName = skillName;
            this.description = description;
            this.permissionScope = permissionScope;
            this.inputParams = inputParams;
            this.defaultParams = defaultParams;
            this.outputAttributes = outputAttributes;
            this.providesFactTypes = providesFactTypes;
            this.supportedSubjectTypes = supportedSubjectTypes;
            this.supportedAttributes = supportedAttributes;
            this.supportedRelations = supportedRelations;
            this.capabilityStatus = capabilityStatus;
            this.unsupportedAttributes = unsupportedAttributes;
            this.supportedPeriodsByAttribute = supportedPeriodsByAttribute;
        }
    }

    private static final class ParamsResult {
        private final Map<String, Object> params;
        private final List<String> missing;

        private ParamsResult(Map<String, Object> params, List<String> missing) {
            this.params = params;
            this.missing = missing;
        }
    }

    private static final class CandidateResult {
        private final List<OAGVO.CandidateInvocation> invocations;
        private final List<Map<String, Object>> warnings;

        private CandidateResult(List<OAGVO.CandidateInvocation> invocations, List<Map<String, Object>> warnings) {
            this.invocations = invocations;
            this.warnings = warnings;
        }
    }

    private static final class ValidationResult {
        private final List<Map<String, Object>> errors;
        private final List<Map<String, Object>> warnings;

        private ValidationResult(List<Map<String, Object>> errors, List<Map<String, Object>> warnings) {
            this.errors = errors;
            this.warnings = warnings;
        }
    }
}
