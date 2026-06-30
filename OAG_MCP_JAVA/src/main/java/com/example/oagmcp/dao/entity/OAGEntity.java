package com.example.oagmcp.dao.entity;

public class OAGEntity {

    public static class OAGObject {
        public String objectType;
        public String objectId;
        public String objectName;
        public String aliasesJson;
        public String paramsJson;
        public Double score;
    }

    public static class OAGAttribute {
        public String objectType;
        public String attributeName;
        public String attributeNameZh;
        public String aliasesJson;
        public String paramsJson;
        public Double score;
    }

    public static class IntentProfile {
        public String intentName;
        public String intentNameZh;
        public String triggerAliasesJson;
        public String defaultAttributesJson;
        public String primarySkillsJson;
        public String secondarySkillsJson;
        public String optionalSkillsJson;
        public String requiredParamsJson;
        public String factRequirementsTemplateJson;
    }

    public static class SkillCapability {
        public String skillId;
        public String skillName;
        public String description;
        public String targetObjectType;
        public String inputParamsJson;
        public String defaultParamsJson;
        public String outputAttributesJson;
        public String relatedQueriesJson;
        public String permissionScope;
        public String providesFactTypesJson;
        public String supportedSubjectTypesJson;
        public String supportedAttributesJson;
        public String supportedRelationsJson;
        public String outputFactSchemaJson;
        public String supportedConstraintsJson;
        public String capabilityStatus;
        public String unsupportedReasonCode;
        public String unsupportedAttributesJson;
        public String supportedPeriodsByAttributeJson;
        public String capabilityNoteZh;
    }

    public static class GraphEdge {
        public String edgeId;
        public String fromNodeId;
        public String toNodeId;
        public String relationType;
        public Double score;
        public String propertiesJson;
    }
}
