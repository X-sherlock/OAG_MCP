CREATE DATABASE IF NOT EXISTS oag_meta CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE oag_meta;

CREATE TABLE IF NOT EXISTS oag_domains (
    domain VARCHAR(128) PRIMARY KEY,
    enabled TINYINT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS oag_objects (
    domain VARCHAR(128) NOT NULL,
    object_type VARCHAR(128) NOT NULL,
    object_id VARCHAR(128) NOT NULL,
    object_name VARCHAR(255) NOT NULL DEFAULT '',
    aliases_json JSON NOT NULL,
    params_json JSON NOT NULL,
    PRIMARY KEY (domain, object_type, object_id),
    INDEX idx_oag_objects_id (domain, object_id)
);

CREATE TABLE IF NOT EXISTS oag_attributes (
    domain VARCHAR(128) NOT NULL,
    object_type VARCHAR(128) NOT NULL,
    attribute_name VARCHAR(128) NOT NULL,
    attribute_name_zh VARCHAR(255) NOT NULL DEFAULT '',
    aliases_json JSON NOT NULL,
    PRIMARY KEY (domain, object_type, attribute_name),
    INDEX idx_oag_attributes_name (domain, attribute_name)
);

CREATE TABLE IF NOT EXISTS oag_query_capabilities (
    domain VARCHAR(128) NOT NULL,
    query_id VARCHAR(128) NOT NULL,
    description VARCHAR(512) NOT NULL DEFAULT '',
    target_object_type VARCHAR(128) NOT NULL,
    required_params_json JSON NOT NULL,
    optional_params_json JSON NOT NULL,
    output_attributes_json JSON NOT NULL,
    tool_type VARCHAR(64) NOT NULL,
    tool_name VARCHAR(128) NOT NULL,
    permission_scope VARCHAR(255) NOT NULL DEFAULT '',
    enabled TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (domain, query_id)
);

CREATE TABLE IF NOT EXISTS oag_skill_capabilities (
    domain VARCHAR(128) NOT NULL,
    skill_id VARCHAR(128) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    description VARCHAR(512) NOT NULL DEFAULT '',
    target_object_type VARCHAR(128) NOT NULL,
    input_params_json JSON NOT NULL,
    output_attributes_json JSON NOT NULL,
    related_queries_json JSON NOT NULL,
    permission_scope VARCHAR(255) NOT NULL DEFAULT '',
    provides_fact_types_json JSON NOT NULL,
    supported_subject_types_json JSON NOT NULL,
    supported_attributes_json JSON NOT NULL,
    output_fact_schema_json JSON NOT NULL,
    supported_constraints_json JSON NOT NULL,
    enabled TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (domain, skill_id)
);

CREATE TABLE IF NOT EXISTS oag_intent_profiles (
    domain VARCHAR(128) NOT NULL,
    intent_name VARCHAR(128) NOT NULL,
    intent_name_zh VARCHAR(255) NOT NULL DEFAULT '',
    trigger_aliases_json JSON NOT NULL,
    default_attributes_json JSON NOT NULL,
    primary_skills_json JSON NOT NULL,
    secondary_skills_json JSON NOT NULL,
    optional_skills_json JSON NOT NULL,
    required_params_json JSON NOT NULL,
    fact_requirements_template_json JSON NOT NULL,
    enabled TINYINT NOT NULL DEFAULT 1,
    PRIMARY KEY (domain, intent_name)
);

CREATE TABLE IF NOT EXISTS oag_object_aliases (
    id BIGINT NOT NULL AUTO_INCREMENT,
    domain VARCHAR(128) NOT NULL,
    object_id VARCHAR(128) NOT NULL,
    object_type VARCHAR(128) NOT NULL,
    alias VARCHAR(255) NOT NULL,
    normalized_alias VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_oag_object_alias (
        domain, object_type, object_id, normalized_alias
    ),
    INDEX idx_oag_object_alias_lookup (domain, normalized_alias),
    INDEX idx_oag_object_alias_object (domain, object_type, object_id)
);

CREATE TABLE IF NOT EXISTS oag_attribute_aliases (
    id BIGINT NOT NULL AUTO_INCREMENT,
    domain VARCHAR(128) NOT NULL,
    attribute_name VARCHAR(128) NOT NULL,
    alias VARCHAR(255) NOT NULL,
    normalized_alias VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_oag_attribute_alias (
        domain, attribute_name, normalized_alias
    ),
    INDEX idx_oag_attribute_alias_lookup (domain, normalized_alias),
    INDEX idx_oag_attribute_alias_name (domain, attribute_name)
);

CREATE TABLE IF NOT EXISTS oag_graph_nodes (
    domain VARCHAR(128) NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    object_type VARCHAR(128) NOT NULL,
    object_id VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL DEFAULT '',
    properties_json JSON NOT NULL,
    enabled TINYINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (domain, node_id),
    UNIQUE KEY uk_oag_graph_node_object (
        domain, object_type, object_id
    ),
    INDEX idx_oag_graph_nodes_enabled (domain, enabled),
    INDEX idx_oag_graph_nodes_object (domain, object_type, object_id)
);

CREATE TABLE IF NOT EXISTS oag_graph_edges (
    domain VARCHAR(128) NOT NULL,
    edge_id VARCHAR(512) NOT NULL,
    from_node_id VARCHAR(255) NOT NULL,
    to_node_id VARCHAR(255) NOT NULL,
    relation_type VARCHAR(128) NOT NULL,
    score DOUBLE NOT NULL DEFAULT 0,
    properties_json JSON NOT NULL,
    enabled TINYINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (domain, edge_id),
    UNIQUE KEY uk_oag_graph_edge_nodes (
        domain, from_node_id, to_node_id, relation_type
    ),
    INDEX idx_oag_graph_edges_from (domain, from_node_id, enabled),
    INDEX idx_oag_graph_edges_to (domain, to_node_id, enabled),
    INDEX idx_oag_graph_edges_relation (domain, relation_type, enabled)
);
