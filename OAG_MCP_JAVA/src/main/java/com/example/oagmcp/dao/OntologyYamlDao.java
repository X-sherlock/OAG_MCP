package com.example.oagmcp.dao;

import static com.example.oagmcp.util.Java8Collections.*;

import com.example.oagmcp.dao.entity.OAGEntity;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.yaml.snakeyaml.Yaml;
import org.springframework.stereotype.Repository;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Repository
public class OntologyYamlDao implements OAGDAO {

    private static final String ONTOLOGY_RESOURCE_ROOT = "/com/example/oagmcp/ontology/";

    private final ObjectMapper jsonMapper = new ObjectMapper();
    private final Yaml yaml = new Yaml();
    private final List<Map<String, Object>> objectTypes;
    private final List<Map<String, Object>> attributes;
    private final List<Map<String, Object>> intentProfiles;
    private final List<Map<String, Object>> skills;
    private final List<Map<String, Object>> graphEdges;

    public OntologyYamlDao() {
        this.objectTypes = loadRows("object_types.yaml");
        this.attributes = loadRows("attributes.yaml");
        this.intentProfiles = loadRows("intent_profiles.yaml");
        this.skills = loadRows("skills.yaml");
        this.graphEdges = loadRows("schema_graph_edges.yaml");
    }

    @Override
    public int countEnabledDomain(String domain) {
        return "finance_market".equals(domain) ? 1 : 0;
    }

    @Override
    public List<OAGEntity.OAGObject> searchObjects(String domain, String question, String normalized, int topK) {
        String text = normalizeSearchText(question, normalized);
        return objectTypes.stream()
                .filter(this::enabled)
                .filter(row -> contains(row, text, "object_type", "object_type_zh", "description"))
                .limit(topK)
                .map(this::objectType)
                .collect(Collectors.toList());
    }

    @Override
    public List<OAGEntity.OAGAttribute> searchAttributes(String domain, String question, String normalized, int topK) {
        String text = normalizeSearchText(question, normalized);
        return attributes.stream()
                .filter(row -> contains(row, text, "attribute_name", "attribute_name_zh", "description"))
                .limit(topK)
                .map(this::attribute)
                .collect(Collectors.toList());
    }

    @Override
    public List<OAGEntity.OAGAttribute> listAttributesByNames(String domain, List<String> names) {
        Set<String> wanted = new LinkedHashSet<String>(names == null ? listOf() : names);
        return attributes.stream()
                .filter(row -> wanted.contains(text(row.get("attribute_name"))))
                .map(this::attribute)
                .collect(Collectors.toList());
    }

    @Override
    public List<OAGEntity.OAGObject> listObjectsByIds(String domain, List<String> objectIds) {
        Set<String> wanted = new LinkedHashSet<String>(objectIds == null ? listOf() : objectIds);
        return objectTypes.stream()
                .filter(this::enabled)
                .filter(row -> wanted.contains(text(row.get("object_type"))))
                .map(this::objectType)
                .collect(Collectors.toList());
    }

    @Override
    public List<OAGEntity.IntentProfile> listIntentProfiles(String domain) {
        return intentProfiles.stream()
                .map(this::intentProfile)
                .collect(Collectors.toList());
    }

    @Override
    public List<OAGEntity.SkillCapability> listSkillCapabilities(String domain) {
        return skills.stream()
                .filter(this::enabled)
                .map(this::skill)
                .collect(Collectors.toList());
    }

    @Override
    public List<OAGEntity.GraphEdge> listGraphEdgesByNodeIds(String domain, List<String> nodeIds, int topK) {
        Set<String> wanted = new LinkedHashSet<String>(nodeIds == null ? listOf() : nodeIds);
        return graphEdges.stream()
                .filter(row -> wanted.contains(text(row.get("from"))) || wanted.contains(text(row.get("to"))))
                .sorted((left, right) -> Double.compare(number(right.get("score")), number(left.get("score"))))
                .limit(topK)
                .map(this::graphEdge)
                .collect(Collectors.toList());
    }

    private List<Map<String, Object>> loadRows(String fileName) {
        String resourcePath = ONTOLOGY_RESOURCE_ROOT + fileName;
        try (InputStream input = OntologyYamlDao.class.getResourceAsStream(resourcePath)) {
            if (input == null) {
                throw new IllegalStateException("Cannot locate ontology YAML resource: " + resourcePath);
            }
            Object loaded = yaml.load(input);
            if (loaded == null) {
                return listOf();
            }
            if (!(loaded instanceof List<?>)) {
                throw new IllegalStateException("Ontology YAML resource must contain a list: " + resourcePath);
            }
            List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
            for (Object item : (List<?>) loaded) {
                if (!(item instanceof Map<?, ?>)) {
                    throw new IllegalStateException("Ontology YAML row must be a map in resource: " + resourcePath);
                }
                rows.add(copyStringKeyMap((Map<?, ?>) item, resourcePath));
            }
            return rows;
        } catch (IOException ex) {
            throw new UncheckedIOException("Cannot read ontology YAML resource: " + resourcePath, ex);
        }
    }

    private Map<String, Object> copyStringKeyMap(Map<?, ?> source, String resourcePath) {
        Map<String, Object> copy = new LinkedHashMap<String, Object>();
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            Object key = entry.getKey();
            if (!(key instanceof String)) {
                throw new IllegalStateException("Ontology YAML row key must be a string in resource: " + resourcePath);
            }
            copy.put((String) key, entry.getValue());
        }
        return copy;
    }

    private OAGEntity.OAGObject objectType(Map<String, Object> row) {
        OAGEntity.OAGObject object = new OAGEntity.OAGObject();
        object.objectType = text(row.get("object_type"));
        object.objectId = object.objectType;
        object.objectName = firstText(row.get("object_type_zh"), row.get("object_type"));
        object.aliasesJson = json(row.get("aliases"));
        object.paramsJson = json(row);
        object.score = 1.0;
        return object;
    }

    private OAGEntity.OAGAttribute attribute(Map<String, Object> row) {
        OAGEntity.OAGAttribute attribute = new OAGEntity.OAGAttribute();
        attribute.attributeName = text(row.get("attribute_name"));
        attribute.attributeNameZh = firstText(row.get("attribute_name_zh"), row.get("attribute_name"));
        attribute.objectType = firstFromList(row.get("object_types"));
        attribute.aliasesJson = json(row.get("aliases"));
        attribute.paramsJson = json(row);
        attribute.score = 1.0;
        return attribute;
    }

    private OAGEntity.IntentProfile intentProfile(Map<String, Object> row) {
        OAGEntity.IntentProfile profile = new OAGEntity.IntentProfile();
        profile.intentName = text(row.get("intent_name"));
        profile.intentNameZh = firstText(row.get("intent_name_zh"), row.get("intent_name"));
        profile.triggerAliasesJson = json(row.get("trigger_aliases"));
        profile.defaultAttributesJson = json(row.get("default_attributes"));
        profile.primarySkillsJson = json(row.get("primary_skills"));
        profile.secondarySkillsJson = json(row.get("secondary_skills"));
        profile.optionalSkillsJson = json(row.get("optional_skills"));
        profile.requiredParamsJson = json(row.get("required_params"));
        profile.factRequirementsTemplateJson = json(row.get("fact_requirements_template"));
        return profile;
    }

    private OAGEntity.SkillCapability skill(Map<String, Object> row) {
        OAGEntity.SkillCapability skill = new OAGEntity.SkillCapability();
        skill.skillId = text(row.get("skill_id"));
        skill.skillName = text(row.get("skill_name"));
        skill.description = text(row.get("description"));
        skill.targetObjectType = text(row.get("target_object_type"));
        skill.inputParamsJson = json(row.get("input_params"));
        skill.defaultParamsJson = json(row.get("default_params"));
        skill.outputAttributesJson = json(row.get("output_attributes"));
        skill.relatedQueriesJson = json(row.get("related_queries"));
        skill.permissionScope = text(row.get("permission_scope"));
        skill.providesFactTypesJson = json(row.get("provides_fact_types"));
        skill.supportedSubjectTypesJson = json(row.get("supported_subject_types"));
        skill.supportedAttributesJson = json(row.get("supported_attributes"));
        skill.supportedRelationsJson = json(row.get("supported_relations"));
        skill.outputFactSchemaJson = json(row.get("output_fact_schema"));
        skill.supportedConstraintsJson = json(row.get("supported_constraints"));
        skill.capabilityStatus = text(row.get("capability_status"));
        skill.unsupportedReasonCode = text(row.get("unsupported_reason_code"));
        skill.unsupportedAttributesJson = json(row.get("unsupported_attributes"));
        skill.supportedPeriodsByAttributeJson = json(row.get("supported_periods_by_attribute"));
        skill.capabilityNoteZh = text(row.get("capability_note_zh"));
        return skill;
    }

    private OAGEntity.GraphEdge graphEdge(Map<String, Object> row) {
        OAGEntity.GraphEdge edge = new OAGEntity.GraphEdge();
        edge.edgeId = text(row.get("edge_id"));
        edge.fromNodeId = text(row.get("from"));
        edge.toNodeId = text(row.get("to"));
        edge.relationType = text(row.get("relation_type"));
        edge.score = number(row.get("score"));
        edge.propertiesJson = json(edgeProperties(row));
        return edge;
    }

    private Map<String, Object> edgeProperties(Map<String, Object> row) {
        Map<String, Object> copy = new LinkedHashMap<>(row);
        copy.remove("edge_id");
        copy.remove("from");
        copy.remove("to");
        copy.remove("relation_type");
        copy.remove("score");
        return copy;
    }

    private boolean enabled(Map<String, Object> row) {
        Object enabled = row.get("enabled");
        return enabled == null || Boolean.TRUE.equals(enabled);
    }

    private boolean contains(Map<String, Object> row, String needle, String... keys) {
        if (!StringUtils.hasText(needle)) {
            return true;
        }
        for (String key : keys) {
            if (text(row.get(key)).toLowerCase(Locale.ROOT).contains(needle)) {
                return true;
            }
        }
        return false;
    }

    private String normalizeSearchText(String question, String normalized) {
        return firstText(question, normalized).toLowerCase(Locale.ROOT);
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

    private String firstFromList(Object value) {
        if (value instanceof List<?> && !((List<?>) value).isEmpty()) {
            List<?> list = (List<?>) value;
            return text(list.get(0));
        }
        return text(value);
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private Double number(Object value) {
        if (value instanceof Number) {
            return ((Number) value).doubleValue();
        }
        return 0.0;
    }

    private String json(Object value) {
        try {
            return jsonMapper.writeValueAsString(value == null ? listOf() : value);
        } catch (IOException ex) {
            throw new UncheckedIOException(ex);
        }
    }
}
