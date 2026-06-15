const NODE_TYPES = [
  "ObjectType",
  "Attribute",
  "SkillCapability",
  "QueryCapability",
  "IntentProfile",
  "RelationType",
  "FactType",
  "DataTable",
  "DataField",
  "DataSource",
  "PeriodVariant",
  "InstanceRule",
  "Parameter",
];

const QUICK_FIELDS = {
  SkillCapability: [
    "skill_id",
    "skill_name",
    "description",
    "enabled",
    "target_object_type",
    "supported_subject_types",
    "input_params",
    "supported_attributes",
    "output_attributes",
    "provides_fact_types",
    "supported_relations",
    "related_queries",
    "permission_scope",
  ],
  ObjectType: ["object_type", "object_type_zh", "description", "enabled"],
  Attribute: [
    "attribute_name",
    "attribute_name_zh",
    "description",
    "object_types",
    "value_type",
    "data_type",
    "aliases",
    "enabled",
  ],
  IntentProfile: ["intent_name", "intent_name_zh", "trigger_aliases", "default_attributes", "skill_priorities", "fact_requirements_template"],
  QueryCapability: [
    "query_id",
    "query_name",
    "description",
    "target_object_type",
    "input_params",
    "required_params",
    "optional_params",
    "output_attributes",
    "source_tables",
  ],
  RelationType: ["relation_type", "relation_name_zh", "from_object_type", "to_object_type", "description", "direction", "enabled"],
  FactType: ["fact_type", "fact_type_name_zh", "description_zh", "applicable_subject_types", "typical_attributes", "default_priority"],
  DataTable: ["table_name", "table_name_zh", "description"],
  DataField: ["field_name", "field_name_zh", "semantic_type", "data_type", "maps_to_attribute", "description"],
  DataSource: ["source_id", "source_type", "enabled", "description", "tables"],
  Edge: ["edge_id", "source", "target", "relation_type", "properties"],
};

const TASKS = [
  {
    id: "oag_plan",
    title: "OAG 规划调试",
    description: "输入语义框架，生成事实需求、候选 Skill、覆盖情况和本次任务子图。",
    viewMode: "requirement",
    recommendedTypes: [],
    dashboard: "oag_plan",
    includeInferred: true,
  },
  {
    id: "core_graph",
    title: "本体核心图",
    description: "查看对象、属性、事实类型、Intent、Skill 和本体关系。",
    viewMode: "requirement",
    recommendedTypes: ["ObjectType", "Attribute", "SkillCapability", "IntentProfile"],
    dashboard: "core_graph",
    includeInferred: true,
  },
  {
    id: "intent_templates",
    title: "意图模板",
    description: "维护宽泛意图默认需要哪些事实，编辑属性、事实类型、优先级和中文原因。",
    viewMode: "requirement",
    recommendedTypes: ["IntentProfile"],
    dashboard: "intent_templates",
    includeInferred: true,
  },
  {
    id: "semantic_relations",
    title: "关系治理",
    description: "维护属性语义扩展边和对象关系边，检查适用任务、权重和中文原因。",
    viewMode: "object_attribute",
    recommendedTypes: ["Attribute", "ObjectType"],
    dashboard: "semantic_relations",
    includeInferred: true,
  },
  {
    id: "skill_coverage",
    title: "Skill 覆盖",
    description: "维护 Skill 能提供的事实类型、支持对象、指标属性、关系和权限要求。",
    viewMode: "skill",
    recommendedTypes: ["SkillCapability"],
    dashboard: "skill_coverage",
    includeInferred: true,
  },
  {
    id: "diagnostic",
    title: "诊断中心",
    description: "查看意图模板、Skill 能力、关系边、属性覆盖和必需事实覆盖问题。",
    viewMode: "overview",
    recommendedTypes: [],
    dashboard: "diagnostic",
    includeInferred: true,
  },
  {
    id: "yaml_files",
    title: "YAML 文件",
    description: "查看本体 YAML 文件状态，进入高级原始文件编辑和导出。",
    viewMode: "overview",
    recommendedTypes: [],
    dashboard: "yaml_files",
    includeInferred: true,
  },
];

const DEFAULT_SKILL_INPUT_PARAMS = ["fund_code", "period", "attributes"];

const FALLBACK_SKILL_INPUT_PARAM_OPTIONS = [
  { value: "fund_code", label_zh: "基金代码", group_zh: "常用参数" },
  { value: "fund_codes", label_zh: "多只基金代码", group_zh: "常用参数" },
  { value: "fund_universe", label_zh: "基金池", group_zh: "常用参数" },
  { value: "period", label_zh: "统计周期", group_zh: "常用参数" },
  { value: "attributes", label_zh: "事实名称/指标列表", group_zh: "常用参数" },
  { value: "report_date", label_zh: "报告日期", group_zh: "常用参数" },
  { value: "date_or_date_range", label_zh: "日期或日期范围", group_zh: "常用参数" },
  { value: "report_date_or_date_range", label_zh: "报告日期或日期范围", group_zh: "常用参数" },
  { value: "benchmark_code", label_zh: "基准代码", group_zh: "常用参数" },
  { value: "limit", label_zh: "返回数量", group_zh: "常用参数" },
  { value: "ranking", label_zh: "排序规则", group_zh: "常用参数" },
  { value: "filters", label_zh: "筛选条件", group_zh: "常用参数" },
  { value: "policy_topic", label_zh: "政策主题", group_zh: "常用参数" },
];

const VIEW_LABELS = {
  overview: "概览",
  requirement: "需求定位",
  skill: "Skill 设计",
  object_attribute: "对象属性",
  table_mapping: "表字段映射",
  full: "全图，高级模式",
};

const DEFAULT_LAYOUT_BY_VIEW = {
  overview: "semantic",
  requirement: "semantic",
  skill: "cose",
  object_attribute: "semantic",
  table_mapping: "semantic",
  full: "cose",
};

const SEMANTIC_RANKS = {
  requirement: ["IntentProfile", "ObjectType", "FactType", "Attribute", "SkillCapability"],
  skill: ["ObjectType", "SkillCapability", "Attribute", "QueryCapability", "DataTable"],
  object_attribute: ["ObjectType", "Attribute", "SkillCapability"],
  table_mapping: ["ObjectType", "Attribute", "DataField", "DataTable"],
  overview: ["IntentProfile", "ObjectType", "FactType", "SkillCapability", "Attribute"],
  full: ["IntentProfile", "ObjectType", "FactType", "Attribute", "SkillCapability", "QueryCapability", "DataTable", "DataField", "RelationType"],
};

const TYPE_BADGES = {
  SkillCapability: "Skill",
  QueryCapability: "Query",
  IntentProfile: "Intent",
  ObjectType: "ObjectType",
  Attribute: "Attribute",
  DataTable: "DataTable",
  DataField: "DataField",
  RelationType: "RelationType",
  FactType: "FactType",
};

const NODE_TYPE_LABELS = {
  ObjectType: "对象类型",
  Attribute: "对象属性",
  SkillCapability: "Skill 能力",
  QueryCapability: "查询能力",
  IntentProfile: "Intent 编排",
  RelationType: "关系类型",
  FactType: "事实类型",
  DataTable: "数据表",
  DataField: "表字段",
  Edge: "关系边",
  BundleEdge: "聚合关系边",
  SemanticFrame: "语义输入",
  TaskType: "任务类型",
  TargetInstance: "目标对象",
  Constraint: "约束条件",
  FactRequirement: "事实需求",
  Parameter: "参数",
};

const RELATION_TYPE_LABELS = {
  managed_by_company: "由基金公司管理",
  managed_by: "由基金经理管理",
  compares_to_benchmark: "比较业绩基准",
  tracks_index: "跟踪指数",
  belongs_to_category: "归属基金分类",
  has_nav: "具有净值记录",
  has_performance_metric: "具有业绩指标",
  has_risk_metric: "具有风险指标",
  has_peer_ranking: "具有同类排名",
  has_single_period_performance: "具有单周期表现",
  holds_industry: "持有行业配置",
  maps_to_industry: "映射到行业",
  holds_stock: "持有股票",
  holds_bond: "持有债券",
  holds_fund: "持有其他基金",
  has_asset_allocation: "具有资产配置",
  has_holder_structure: "具有持有人结构",
  has_fee: "具有费率信息",
  has_dividend: "具有分红信息",
  has_issue_info: "具有发行信息",
  related_to_report: "关联研报",
  related_to_news: "相关新闻",
  affects_fund: "政策影响基金",
  sourced_from_table: "来源于数据表",
  stored_in_table: "存储在数据表",
  has_field: "包含字段",
  mapped_to_field: "映射到表字段",
  joins_on: "表连接字段",
  targets_object_type: "面向对象类型",
  uses_query: "使用查询能力",
  uses_table: "使用数据表",
  outputs_attribute: "输出属性",
  supports_attribute: "支持属性",
  provides_attribute: "提供属性",
  related_query: "关联查询能力",
  has_query: "拥有查询能力",
  has_skill: "拥有 Skill",
  recommends_skill: "推荐 Skill",
  has_attribute: "包含属性",
  requires_attribute: "需要属性",
  returns_attribute: "返回属性",
  maps_to_attribute: "映射到属性",
  requires_fact: "需要事实",
  requires_fact_type: "需要事实类型",
  provides_fact_type: "提供事实类型",
  has_task_type: "任务类型",
  uses_intent: "使用意图模板",
  has_target: "目标对象",
  uses_constraint: "使用约束",
  has_attribute: "包含属性",
  expanded_from_relation: "关系扩展",
  covered_by_skill: "由 Skill 覆盖",
  requires_param: "需要参数",
  provides_relation_target: "关系事实目标对象",
};

const MODELING_RELATION_TYPES = [
  { value: "supports_attribute", label: "Skill 支持属性" },
  { value: "outputs_attribute", label: "Skill 输出属性" },
  { value: "provides_attribute", label: "Skill 提供属性" },
  { value: "provides_fact_type", label: "Skill 提供事实类型" },
  { value: "related_query", label: "Skill 关联查询能力" },
  { value: "uses_query", label: "Intent 使用查询能力" },
  { value: "has_skill", label: "Intent 关联 Skill" },
  { value: "recommends_skill", label: "Intent 推荐 Skill" },
  { value: "has_attribute", label: "对象或 Intent 包含属性" },
  { value: "maps_to_field", label: "属性映射到表字段" },
  { value: "mapped_to_field", label: "表字段映射到属性" },
  { value: "targets_object_type", label: "能力面向对象类型" },
  { value: "uses_table", label: "能力使用数据表" },
];

const FIELD_LABELS = {
  object_type: "对象类型标识",
  object_type_zh: "对象类型中文名",
  attribute_name: "属性标识",
  attribute_name_zh: "属性中文名",
  skill_id: "Skill 标识",
  skill_name: "Skill 名称",
  query_id: "查询能力标识",
  query_name: "查询能力名称",
  intent_name: "Intent 标识",
  intent_name_zh: "Intent 中文名",
  relation_type: "关系类型标识",
  relation_name_zh: "关系中文名",
  table_name: "数据表名",
  table_name_zh: "数据表中文名",
  field_name: "字段名",
  field_name_zh: "字段中文名",
  description: "说明",
  enabled: "是否启用",
  target_object_type: "目标对象类型",
  object_types: "适用对象类型",
  input_params: "输入参数",
  required_params: "必填参数",
  optional_params: "可选参数",
  supported_attributes: "支持的属性",
  output_attributes: "输出属性",
  default_attributes: "默认属性",
  skill_priorities: "候选 Skill 优先级",
  related_queries: "关联查询能力",
  provides_fact_types: "提供的事实类型",
  supported_subject_types: "支持对象类型",
  supported_relations: "支持关系类型",
  permission_scope: "权限范围",
  fact_type: "事实类型",
  fact_type_name_zh: "事实类型中文名",
  description_zh: "中文说明",
  applicable_subject_types: "适用主体对象",
  typical_attributes: "典型属性",
  default_priority: "默认优先级",
  value_type: "值类型",
  data_type: "数据类型",
  aliases: "别名",
  trigger_aliases: "触发表达",
  fact_requirements_template: "事实需求模板",
  source_tables: "来源数据表",
  applicable_tasks: "适用任务",
  applicable_intents: "适用意图",
  reason_zh: "中文原因",
  from_object_type: "起点对象类型",
  to_object_type: "终点对象类型",
  direction: "方向",
  semantic_type: "语义类型",
  maps_to_attribute: "映射属性",
  properties: "关系附加属性 JSON",
  source: "起点节点",
  target: "终点节点",
};

const FIELD_HELP = {
  object_type: "用于 YAML 引用的英文/拼音标识，例如 Fund。",
  attribute_name: "用于 YAML 引用的属性标识，例如 return_rate。",
  skill_id: "用于 YAML 引用的 Skill 标识，例如 get_fund_metric_values。",
  query_id: "用于 YAML 引用的查询能力标识。",
  intent_name: "用于 YAML 引用的 Intent 标识。",
  relation_type: "关系类型必须与现有关系定义保持一致。",
  input_params: "调用该能力时需要传入的参数，例如基金代码、起止日期、统计区间。多个值用逗号分隔。",
  trigger_aliases: "用户可能说出的触发表达，多个值用逗号分隔。",
  default_attributes: "该 Intent 默认需要展示或计算的属性。可多选；不选表示暂不配置默认属性。",
  skill_priorities: "处理该 Intent 时优先尝试的 Skill。可多选；顺序暂按选择结果保存。",
  supported_attributes: "该 Skill 理解、支持或可参与分析的属性，用于能力覆盖检查。",
  output_attributes: "该 Skill 实际会返回给上层流程的属性，通常是结果字段。",
  provides_fact_types: "该 Skill 产出的事实类别，例如指标值事实、排名事实、对象基础事实。多个值用逗号分隔。",
  related_queries: "该 Skill 需要调用或依赖的查询能力，例如先查净值、再计算收益。",
  permission_scope: "该 Skill 所需的数据或功能权限范围；不确定时可先留空。",
  supported_subject_types: "该 Skill 支持的主体对象类型，例如 Fund 或 FundSet。可多选。",
  supported_relations: "该 Skill 可覆盖的对象关系，例如 managed_by 或 has_benchmark。可多选。",
  fact_requirements_template: "Intent 对事实的结构化需求模板；建议在“意图模板”视图中维护。",
  source_tables: "该查询能力可能读取的数据表。",
  maps_to_attribute: "该字段语义上对应的对象属性。",
};

const WIZARD_REQUIRED_FIELDS = {
  ObjectType: new Set(["object_type", "object_type_zh"]),
  Attribute: new Set(["attribute_name", "attribute_name_zh", "object_types"]),
  SkillCapability: new Set(["skill_id", "skill_name", "description", "target_object_type", "permission_scope"]),
  QueryCapability: new Set(["query_id", "query_name", "target_object_type"]),
  IntentProfile: new Set(["intent_name", "intent_name_zh"]),
  RelationType: new Set(["relation_type", "relation_name_zh"]),
  FactType: new Set(["fact_type", "fact_type_name_zh"]),
  DataTable: new Set(["table_name"]),
  DataField: new Set(["table_name", "field_name"]),
};

const NODE_TYPE_COLORS = {
  ObjectType: "#78aee8",
  Attribute: "#76c89b",
  SkillCapability: "#b79add",
  QueryCapability: "#e3ad62",
  IntentProfile: "#df8181",
  DataTable: "#8fa3b8",
  DataField: "#e5e7eb",
  DataSource: "#82b5ad",
  RelationType: "#475569",
  FactType: "#14b8a6",
  SemanticFrame: "#60a5fa",
  TaskType: "#f59e0b",
  TargetInstance: "#22c55e",
  Constraint: "#a78bfa",
  FactRequirement: "#fb7185",
  Group: "#334155",
  Parameter: "#cbd5e1",
};

const state = {
  viewMode: "requirement",
  query: "",
  focusId: "",
  depth: 2,
  includeFields: false,
  includeInferred: true,
  aggregateEdges: true,
  enableGroups: true,
  showEdgeLabels: false,
  relationFilter: "",
  selectedNodeId: "",
  activeTaskId: "",
  editMode: false,
  dirty: false,
  dirtyObjectId: "",
  dirtySourceFile: "",
  originalRaw: null,
  expandedGroups: new Set(),
  hiddenNodeTypes: new Set(),
  edgeDrawMode: false,
  edgeDraftSource: "",
  loadingGraph: false,
};

let cy;
let currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
let currentOptions = {};
let currentOagOptions = {};
let currentPlan = null;
let currentDiagnostics = { items: [], summary: {} };
let currentMappingMatrix = { rows: [], summary: {} };
let selected = null;
let edgeCreationSource = null;

const el = (id) => document.getElementById(id);
const on = (id, eventName, handler) => {
  const node = el(id);
  if (node) node.addEventListener(eventName, handler);
};

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  bindEvents();
  initResizablePanels();
  renderTaskCards();
  renderWorkbenchHome();
  syncControls();
  updateEditModeUi();
  refreshAll({ loadGraph: false });
});

function initCytoscape() {
  cy = cytoscape({
    container: el("cy"),
    elements: [],
    minZoom: 0.08,
    maxZoom: 3,
    wheelSensitivity: 0.16,
    boxSelectionEnabled: true,
    style: [
      {
        selector: "node",
        style: {
          label: "data(card_label)",
          "font-size": 12,
          "min-zoomed-font-size": 0,
          "text-wrap": "wrap",
          "text-max-width": 96,
          "text-valign": "center",
          "text-halign": "center",
          "text-margin-y": 0,
          "text-opacity": 0.62,
          "text-background-color": "#ffffff",
          "text-background-opacity": 0,
          "text-background-padding": 1,
          width: "mapData(degree, 0, 80, 82, 126)",
          height: "mapData(degree, 0, 80, 42, 70)",
          "border-width": 1.5,
          "border-color": "#ffffff",
          color: "#111827",
          "background-color": "#a3aab8",
          "overlay-padding": 4,
        },
      },
      { selector: 'node[type = "ObjectType"]', style: { "background-color": "#bdd4ea", shape: "ellipse" } },
      { selector: 'node[type = "Attribute"]', style: { "background-color": "#bde0cc", shape: "round-rectangle" } },
      { selector: 'node[type = "SkillCapability"]', style: { "background-color": "#d7c8ea", shape: "round-rectangle" } },
      { selector: 'node[type = "QueryCapability"]', style: { "background-color": "#ead1a6", shape: "hexagon" } },
      { selector: 'node[type = "IntentProfile"]', style: { "background-color": "#ebc0c0", shape: "diamond" } },
      { selector: 'node[type = "DataTable"]', style: { "background-color": "#c8d2dc", shape: "rectangle" } },
      { selector: 'node[type = "DataField"]', style: { "background-color": "#e5e7eb", shape: "round-rectangle" } },
      { selector: 'node[type = "RelationType"]', style: { "background-color": "#475569", color: "#ffffff" } },
      { selector: 'node[type = "Group"]', style: { "background-color": "#334155", color: "#ffffff", shape: "round-rectangle" } },
      {
        selector: 'node[origin = "task_graph"]',
        style: {
          width: 104,
          height: 52,
          "font-size": 10,
          "text-max-width": 88,
          "text-opacity": 0.92,
          "border-width": 1.2,
          "border-color": "#ffffff",
        },
      },
      { selector: 'node[origin = "task_graph"][type = "SemanticFrame"]', style: { "background-color": "#94a3b8", color: "#111827" } },
      { selector: 'node[origin = "task_graph"][type = "FactRequirement"]', style: { "background-color": "#f0a5b5", shape: "round-rectangle" } },
      { selector: 'node[origin = "task_graph"][type = "TargetInstance"]', style: { "background-color": "#93c5fd", shape: "ellipse" } },
      { selector: 'node[origin = "task_graph"][type = "Constraint"]', style: { "background-color": "#d9e3f0", shape: "round-rectangle" } },
      { selector: 'node[origin = "task_graph"][type = "Parameter"]', style: { "background-color": "#fde68a", shape: "round-rectangle" } },
      { selector: 'node[enabled = "false"]', style: { opacity: 0.42 } },
      { selector: 'node[inferred_only = "true"]', style: { opacity: 0.55 } },
      {
        selector: "edge",
        style: {
          width: "mapData(bundle_count, 1, 40, 1.2, 4)",
          "line-color": "#94a3b8",
          "target-arrow-color": "#94a3b8",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "",
          "font-size": 8,
          color: "#334155",
          "text-background-color": "#ffffff",
          "text-background-opacity": 0.92,
          opacity: 0.45,
        },
      },
      { selector: 'edge[origin = "inferred"]', style: { "line-style": "dashed" } },
      { selector: 'edge[origin = "explicit"]', style: { "line-style": "solid" } },
      { selector: 'edge[is_bundle = "true"]', style: { "line-style": "dotted", opacity: 0.8 } },
      { selector: ".hidden-by-type", style: { display: "none" } },
      { selector: "edge.hover, edge:selected, edge.show-label", style: { label: "data(label)", opacity: 1 } },
      { selector: "edge:selected", style: { "line-color": "#2563eb", "target-arrow-color": "#2563eb", width: 2.2 } },
      { selector: ".faded", style: { opacity: 0.16, "text-opacity": 0.18 } },
      { selector: ".path-highlight", style: { opacity: 1, "line-color": "#16a34a", "target-arrow-color": "#16a34a", "border-color": "#16a34a", "border-width": 4, width: 3 } },
      {
        selector: ".selected-node",
        style: {
          opacity: 1,
          "border-width": 4,
          "border-color": "#2563eb",
          color: "#0f172a",
          "font-size": 12,
          "font-weight": 700,
          "text-opacity": 1,
          "text-background-opacity": 0,
          "text-background-padding": 0,
        },
      },
      {
        selector: ".neighbor-node",
        style: {
          opacity: 1,
          "border-width": 2,
          "border-color": "#0f172a",
          color: "#111827",
          "font-size": 11,
          "text-opacity": 0.95,
          "text-background-opacity": 0,
          "text-background-padding": 0,
        },
      },
      { selector: 'node.selected-node[type = "ObjectType"], node.neighbor-node[type = "ObjectType"]', style: { "background-color": "#78aee8" } },
      { selector: 'node.selected-node[type = "Attribute"], node.neighbor-node[type = "Attribute"]', style: { "background-color": "#76c89b" } },
      { selector: 'node.selected-node[type = "SkillCapability"], node.neighbor-node[type = "SkillCapability"]', style: { "background-color": "#b79add" } },
      { selector: 'node.selected-node[type = "QueryCapability"], node.neighbor-node[type = "QueryCapability"]', style: { "background-color": "#e3ad62" } },
      { selector: 'node.selected-node[type = "IntentProfile"], node.neighbor-node[type = "IntentProfile"]', style: { "background-color": "#df8181" } },
      { selector: 'node.selected-node[type = "DataTable"], node.neighbor-node[type = "DataTable"]', style: { "background-color": "#8fa3b8" } },
      { selector: ".edge-draft-source", style: { "border-color": "#f59e0b", "border-width": 5, "text-opacity": 1, opacity: 1 } },
      { selector: ".neighbor-edge", style: { opacity: 0.9, width: 2, "line-color": "#2563eb", "target-arrow-color": "#2563eb" } },
      { selector: ".faded-relation", style: { opacity: 0.08 } },
    ],
  });
  window.__ontologyCy = cy;

  cy.on("tap", "node", (event) => {
    const node = event.target;
    if (node.data("type") === "Group") {
      toggleGroup(node.id());
      return;
    }
    if (state.edgeDrawMode) {
      handleEdgeDrawNodeTap(node);
      return;
    }
    if (edgeCreationSource && edgeCreationSource !== node.id()) {
      openEdgeDialog({ source: edgeCreationSource, target: node.id() });
      edgeCreationSource = null;
      return;
    }
    selectElement(node);
  });
  cy.on("tap", "edge", (event) => selectElement(event.target));
  cy.on("mouseover", "edge", (event) => event.target.addClass("hover"));
  cy.on("mouseout", "edge", (event) => event.target.removeClass("hover"));
  cy.on("dbltap", "node", (event) => focusOnNode(event.target.id(), 2));
  cy.on("tap", (event) => {
    if (event.target === cy) clearSelection();
  });
}

function bindEvents() {
  on("moreBtn", "click", toggleMorePanel);
  on("refreshBtn", "click", () => guarded(() => refreshAll({ loadGraph: Boolean(state.activeTaskId || state.focusId) })));
  on("layoutSelect", "change", runLayout);
  on("semanticLayoutBtn", "click", () => {
    el("layoutSelect").value = "semantic";
    runLayout();
  });
  on("autoLayoutBtn", "click", () => {
    el("layoutSelect").value = "cose";
    runLayout();
  });
  on("editModeBtn", "click", toggleEditMode);
  on("saveBtn", "click", saveSelected);
  on("saveSelectedBtn", "click", saveSelected);
  on("deleteSelectedBtn", "click", deleteSelected);
  on("validateBtn", "click", validateOntology);
  on("seedBtn", "click", seedOntology);
  on("searchBtn", "click", () => guarded(search));
  el("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") guarded(search);
  });
  el("taskSearchInput").addEventListener("input", renderTaskCandidates);
  on("addNodeBtn", "click", () => openAddNodeDialog());
  on("addEdgeBtn", "click", () => startEdgeCreation());
  on("modeSelect", "change", () => guarded(() => setViewMode(el("modeSelect").value)));
  el("depthSelect").addEventListener("change", () => guarded(async () => {
    state.depth = Number(el("depthSelect").value);
    if (state.focusId) await loadGraphView();
  }));
  el("includeInferred").addEventListener("change", () => guarded(async () => {
    state.includeInferred = el("includeInferred").checked;
    if (state.focusId) await loadGraphView();
  }));
  el("includeFields").addEventListener("change", () => guarded(async () => {
    state.includeFields = el("includeFields").checked;
    if (state.focusId) await loadGraphView();
  }));
  el("aggregateEdges").addEventListener("change", () => guarded(async () => {
    state.aggregateEdges = el("aggregateEdges").checked;
    if (state.focusId) await loadGraphView();
  }));
  el("enableGroups").addEventListener("change", () => {
    state.enableGroups = el("enableGroups").checked;
    renderGraph();
  });
  el("showEdgeLabels").addEventListener("change", () => {
    state.showEdgeLabels = el("showEdgeLabels").checked;
    applyEdgeLabelMode();
  });
  on("overviewBtn", "click", () => guarded(() => setViewMode("overview")));
  on("requirementBtn", "click", () => guarded(() => setViewMode("requirement")));
  on("skillBtn", "click", () => guarded(() => setViewMode("skill")));
  on("objectAttributeBtn", "click", () => guarded(() => setViewMode("object_attribute")));
  on("tableMappingBtn", "click", () => guarded(() => setViewMode("table_mapping")));
  on("fullBtn", "click", () => guarded(() => setViewMode("full")));
  on("toggleLeftBtn", "click", () => toggleShellClass("left-collapsed"));
  on("toggleRightBtn", "click", () => toggleShellClass("right-collapsed"));
  on("focusModeBtn", "click", enterFocusMode);
  on("exitFocusBtn", "click", exitFocusMode);
  on("diagnosticFilter", "change", renderDiagnostics);
  document.querySelectorAll(".inspector-tabs button").forEach((button) => {
    button.addEventListener("click", () => setInspectorTab(button.dataset.tab));
  });
  el("rawEditor").addEventListener("input", markDirtyFromInspector);
  window.addEventListener("beforeunload", (event) => {
    if (state.dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  document.addEventListener("keydown", handleShortcuts);
  document.addEventListener("click", closeMorePanelOnOutsideClick);
}

function initResizablePanels() {
  const shell = document.querySelector(".app-shell");
  const leftHandle = el("leftResizeHandle");
  const rightHandle = el("rightResizeHandle");
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const startDrag = (side, event) => {
    event.preventDefault();
    const handle = side === "left" ? leftHandle : rightHandle;
    handle.classList.add("dragging");
    const onMove = (moveEvent) => {
      const rect = shell.getBoundingClientRect();
      const maxPanel = Math.max(220, Math.floor(rect.width * 0.45));
      if (side === "left") {
        const width = clamp(moveEvent.clientX - rect.left, 200, maxPanel);
        shell.style.setProperty("--left-panel-width", `${width}px`);
      } else {
        const width = clamp(rect.right - moveEvent.clientX, 280, maxPanel);
        shell.style.setProperty("--right-panel-width", `${width}px`);
      }
      cy?.resize();
    };
    const onUp = () => {
      handle.classList.remove("dragging");
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      cy?.resize().fit(undefined, 48);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };
  leftHandle?.addEventListener("mousedown", (event) => startDrag("left", event));
  rightHandle?.addEventListener("mousedown", (event) => startDrag("right", event));
}

function toggleMorePanel(event) {
  event?.stopPropagation();
  const panel = el("morePanel");
  const button = el("moreBtn");
  const nextHidden = !panel.hidden;
  panel.hidden = nextHidden;
  button.setAttribute("aria-expanded", String(!nextHidden));
}

function closeMorePanelOnOutsideClick(event) {
  const panel = el("morePanel");
  if (panel.hidden) return;
  if (panel.contains(event.target) || el("moreBtn").contains(event.target)) return;
  panel.hidden = true;
  el("moreBtn").setAttribute("aria-expanded", "false");
}

async function guarded(action) {
  const decision = await confirmDirtyIfNeeded();
  if (decision === "cancel") return;
  await action();
}

async function refreshAll({ loadGraph = false } = {}) {
  await Promise.all([loadFiles(), loadOptions(), loadDiagnostics(), loadMappingMatrix()]);
  if (loadGraph) await loadGraphView();
  renderTaskCandidates();
  renderTaskActionPanel();
  updateEditModeUi();
}

async function loadFiles() {
  const res = await api("/api/files");
  el("ontologyRoot").textContent = `本体目录：${res.ontology_root}`;
  renderFiles(res.files || []);
}

function renderFiles(files) {
  el("fileList").innerHTML = files
    .map((file) => {
      const cls = file.exists && !file.error ? "" : "file-missing";
      const dirtyMark = state.dirty && file.name === state.dirtySourceFile ? " *" : "";
      const suffix = file.error ? ` - ${file.error}` : file.modified_at || "missing";
      return `<div class="${cls}">${escapeHtml(file.name)}${dirtyMark}<br>${escapeHtml(suffix)}</div>`;
    })
    .join("");
}

async function loadOptions() {
  const [editorOptions, oagOptions] = await Promise.all([api("/api/options"), api("/api/oag/options")]);
  currentOptions = editorOptions;
  currentOagOptions = oagOptions;
}

async function loadOagOptions() {
  currentOagOptions = await api("/api/oag/options");
}

async function ensureOagOptions(requiredFields = []) {
  const missingBaseOptions = !currentOagOptions.task_types?.length;
  const missingRequiredFields = requiredFields.some((field) => !Array.isArray(currentOagOptions[field]));
  if (missingBaseOptions || missingRequiredFields) await loadOagOptions();
}

async function loadDiagnostics() {
  currentDiagnostics = await api("/api/diagnostics");
  renderDiagnostics();
}

async function loadMappingMatrix() {
  currentMappingMatrix = await api("/api/mapping-matrix");
}

function renderTaskCards() {
  const html = TASKS.map(
    (task) => `
      <button class="task-card ${state.activeTaskId === task.id ? "active" : ""}" data-task-id="${task.id}">
        <strong>${escapeHtml(task.title)}</strong>
        <span>${escapeHtml(task.description)}</span>
      </button>
    `,
  ).join("");
  el("taskCards").innerHTML = html;
  document.querySelectorAll("#taskCards [data-task-id]").forEach((button) => {
    button.addEventListener("click", () => guarded(() => selectTask(button.dataset.taskId)));
  });
}

function setTaskChromeMode() {
  const shell = document.querySelector(".app-shell");
  const isOag = state.activeTaskId === "oag_plan";
  shell?.classList.toggle("oag-mode", isOag);
  el("searchInput").placeholder = isOag ? "搜索任务图节点 / 事实 / Skill" : "搜索 Fund / return_rate / skill";
  el("searchBtn").textContent = isOag ? "搜索图" : "定位";
  if (isOag && el("layoutSelect")) el("layoutSelect").value = "semantic";
  const relationsTab = document.querySelector('.inspector-tabs button[data-tab="relations"]');
  const impactTab = document.querySelector('.inspector-tabs button[data-tab="impact"]');
  if (relationsTab) relationsTab.textContent = isOag ? "任务图" : "关联关系";
  if (impactTab) impactTab.textContent = isOag ? "提醒" : "上下游影响";
}

function renderWorkbenchHome() {
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.remove("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel">
      <h1>OAG 事实规划与本体关系治理工作台</h1>
      <p>从语义框架生成事实规划，查看任务子图，并维护意图模板、语义关系和 Skill 覆盖能力。</p>
      <div class="workbench-grid">
        ${TASKS.map(
          (task) => `
            <button data-home-task="${task.id}">
              <strong>${escapeHtml(task.title)}</strong>
              <span>${escapeHtml(task.description)}</span>
            </button>
          `,
        ).join("")}
      </div>
    </div>
  `;
  document.querySelectorAll("[data-home-task]").forEach((button) => {
    button.addEventListener("click", () => guarded(() => selectTask(button.dataset.homeTask)));
  });
}

function renderDashboardLoading(title, message) {
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel dashboard-loading">
      <div class="loading-card inline-loading-card">
        <div class="loading-spinner"></div>
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(message)}</span>
      </div>
    </div>
  `;
}

function renderTaskActionPanel() {
  const task = TASKS.find((item) => item.id === state.activeTaskId);
  setTaskChromeMode();
  el("currentTaskTitle").textContent = task ? task.title : "工作台";
  const box = el("taskActions");
  if (!box) return;
  if (!task) {
    box.innerHTML = `<div class="muted">选择建模任务后显示快捷操作。</div>`;
    return;
  }
  const common = [
    `<button id="taskEditModeBtn">${state.editMode ? "退出编辑模式" : "进入编辑模式"}</button>`,
    `<button id="taskValidateBtn">校验 ontology</button>`,
  ];
  const actionsByTask = {
    core_graph: [
      `<button id="taskNewObjectBtn" data-edit-only>新增对象类型</button>`,
      `<button id="taskNewAttributeBtn" data-edit-only>新增属性</button>`,
      `<button id="taskNewSkillBtn" data-edit-only>新增 Skill</button>`,
      `<button id="taskNewEdgeBtn" data-edit-only>创建关系边</button>`,
    ],
    skill_coverage: [
      `<button id="taskNewSkillBtn" data-edit-only>新增 Skill</button>`,
      `<button id="taskNewQueryBtn" data-edit-only>新增查询能力</button>`,
      `<button id="taskNewObjectBtn" data-edit-only>新增对象类型</button>`,
      `<button id="taskNewEdgeBtn" data-edit-only>创建关系边</button>`,
      `<button id="taskSkillCoverageBtn">查看 Skill 覆盖问题</button>`,
    ],
    semantic_relations: [
      `<button id="taskNewSemanticRelationBtn" data-edit-only>新增语义关系</button>`,
      `<button id="taskNewRelationTypeBtn" data-edit-only>新增关系类型</button>`,
      `<button id="taskNewEdgeBtn" data-edit-only>通用关系边</button>`,
    ],
    object_attribute: [
      `<button id="taskNewObjectBtn" data-edit-only>新增对象类型</button>`,
      `<button id="taskNewAttributeBtn" data-edit-only>新增属性</button>`,
      `<button id="taskNewSkillForObjectBtn" data-edit-only>新增 Skill</button>`,
      `<button id="taskNewQueryBtn" data-edit-only>新增查询能力</button>`,
      `<button id="taskAttributeIssuesBtn">查看属性问题</button>`,
    ],
    intent_templates: [
      `<button id="taskNewIntentBtn" data-edit-only>新增 Intent</button>`,
      `<button id="taskIntentIssuesBtn">查看 Intent 问题</button>`,
      `<button id="taskNewEdgeBtn" data-edit-only>关联 Skill / 属性</button>`,
    ],
    table_mapping: [
      `<button id="taskMappingMissingBtn">只看未映射</button>`,
      `<button id="taskNewTableBtn" data-edit-only>新增数据表</button>`,
      `<button id="taskNewDataFieldBtn" data-edit-only>新增字段</button>`,
      `<button id="taskNewEdgeBtn" data-edit-only>创建映射边</button>`,
    ],
    diagnostic: [
      `<button id="taskRunValidationBtn">运行校验</button>`,
      `<button id="taskShowAllDiagnosticsBtn">显示全部问题</button>`,
      `<button id="taskNewObjectBtn" data-edit-only>新增对象类型</button>`,
      `<button id="taskNewAttributeBtn" data-edit-only>新增属性</button>`,
      `<button id="taskNewSkillBtn" data-edit-only>新增 Skill</button>`,
      `<button id="taskNewQueryBtn" data-edit-only>新增查询能力</button>`,
    ],
  };
  box.innerHTML = [...common, ...(actionsByTask[task.id] || [])].join("");
  on("taskEditModeBtn", "click", toggleEditMode);
  on("taskValidateBtn", "click", validateOntology);
  on("taskRunValidationBtn", "click", validateOntology);
  on("taskNewObjectBtn", "click", () => openAddNodeDialog("ObjectType", {}, { lockedType: true }));
  on("taskNewSkillBtn", "click", () => openSkillCoverageEditor({}));
  on("taskNewQueryBtn", "click", () => openAddNodeDialog("QueryCapability", {}, { lockedType: true }));
  on("taskNewAttributeBtn", "click", () => openAddNodeDialog("Attribute", {}, { lockedType: true }));
  on("taskNewSkillForObjectBtn", "click", () => openSkillCoverageEditor({}));
  on("taskNewIntentBtn", "click", () => openIntentTemplateEditor({}));
  on("taskNewRelationTypeBtn", "click", () => openAddNodeDialog("RelationType", {}, { lockedType: true }));
  on("taskNewTableBtn", "click", () => openAddNodeDialog("DataTable", {}, { lockedType: true }));
  on("taskNewDataFieldBtn", "click", () => openAddNodeDialog("DataField", {}, { lockedType: true }));
  on("taskNewSemanticRelationBtn", "click", () => openSemanticRelationEditor({}));
  on("taskNewEdgeBtn", "click", () => openEdgeDialog({}));
  on("taskSkillCoverageBtn", "click", () => filterDiagnostics("skills_without_attributes"));
  on("taskAttributeIssuesBtn", "click", () => filterDiagnostics("attributes_without_skill"));
  on("taskIntentIssuesBtn", "click", () => filterDiagnostics("intents_without_skill"));
  on("taskMappingMissingBtn", "click", () => renderMappingDashboard("missing"));
  on("taskShowAllDiagnosticsBtn", "click", () => filterDiagnostics(""));
  updateEditModeUi();
}

function renderDiagnosticDashboard() {
  const summary = currentDiagnostics.summary || {};
  const byType = countBy(currentDiagnostics.items || [], "type");
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel">
      <h1>全局检查</h1>
      <p>点击左侧问题项可以定位节点；右侧任务操作提供校验和修复入口。</p>
      <div class="dashboard-metrics">
        <div><strong>${summary.error_count || 0}</strong><span>错误</span></div>
        <div><strong>${summary.warning_count || 0}</strong><span>警告</span></div>
        <div><strong>${summary.item_count || 0}</strong><span>问题项</span></div>
      </div>
      <div class="dashboard-list">
        ${Object.entries(byType).map(([type, count]) => `<button data-diagnostic-type="${escapeHtml(type)}"><strong>${escapeHtml(diagnosticTypeLabel(type))}</strong><span>${count}</span></button>`).join("")}
      </div>
    </div>
  `;
  document.querySelectorAll("[data-diagnostic-type]").forEach((button) => {
    button.addEventListener("click", () => filterDiagnostics(button.dataset.diagnosticType));
  });
}

function renderMappingDashboard(statusFilter = "") {
  const rows = currentMappingMatrix.rows || [];
  const summary = currentMappingMatrix.summary || {};
  const filtered = rows.filter((row) => !statusFilter || row.status === statusFilter).slice(0, 180);
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel mapping-dashboard">
      <h1>属性映射矩阵</h1>
      <p>默认只展示属性到表字段的聚合状态；点击一行后才展开该属性的表字段链路图。</p>
      <div class="dashboard-metrics">
        <div><strong>${summary.attribute_count || 0}</strong><span>属性</span></div>
        <div><strong>${summary.mapped || 0}</strong><span>已映射</span></div>
        <div><strong>${summary.missing || 0}</strong><span>未映射</span></div>
        <div><strong>${summary.multi_mapped || 0}</strong><span>多重映射</span></div>
      </div>
      <div class="mapping-table">
        <div class="mapping-row mapping-head"><span>属性</span><span>对象类型</span><span>字段数</span><span>数据表</span><span>状态</span></div>
        ${filtered.map(renderMappingRow).join("")}
      </div>
    </div>
  `;
  document.querySelectorAll("[data-map-attribute]").forEach((button) => {
    button.addEventListener("click", () => guarded(() => focusMappingAttribute(button.dataset.mapAttribute)));
  });
}

function renderMappingRow(row) {
  return `
    <button class="mapping-row ${escapeHtml(row.status)}" data-map-attribute="${escapeHtml(row.attribute_id)}">
      <span>${escapeHtml(row.attribute_label || row.attribute_name)}<em>${escapeHtml(row.attribute_name)}</em></span>
      <span>${escapeHtml((row.object_types || []).join(", ") || "-")}</span>
      <span>${row.field_count || 0}</span>
      <span>${escapeHtml((row.tables || []).join(", ") || "-")}</span>
      <span>${escapeHtml(mappingStatusLabel(row.status))}</span>
    </button>
  `;
}

function renderOagPlanningDashboard() {
  const example = exampleSemanticFrame("分析某基金近一年表现");
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel oag-plan-panel">
      <div class="oag-page-head">
        <div>
          <h1>OAG 规划调试</h1>
          <p>输入原始问题后自动生成 semantic_frame 草稿，再由 OAG 事实规划器生成执行计划。</p>
        </div>
        <div class="oag-tabs" role="tablist" aria-label="OAG 输入模式">
          <button data-oag-tab="form" class="active">问题输入</button>
          <button data-oag-tab="json">JSON 输入</button>
        </div>
      </div>
      <section id="oagFormPanel" class="oag-form-shell">
        <div class="oag-card oag-primary-card">
          <h2>原始问题</h2>
          <div class="oag-question-input">
            <textarea id="oagRawQuestion" rows="3" placeholder="例如：分析000001近一年的表现">${escapeHtml(example.raw_question)}</textarea>
            <div class="task-actions">
              <button id="refreshOagDraftBtn">刷新语义草稿</button>
              <button id="runOagPlanBtn" class="primary-action">生成事实规划</button>
            </div>
          </div>
          <div class="example-buttons oag-example-strip">
            ${oagExampleNames().slice(0, 8).map((name) => `<button data-example-frame="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join("")}
          </div>
          <div id="oagAutoSummary" class="oag-auto-summary"></div>
        </div>
        <details id="oagStructuredDraft" class="oag-card">
          <summary>结构化草稿（可选校正）</summary>
          <label class="oag-debug-toggle"><input id="oagUseStructuredDraft" type="checkbox"> 使用下方结构化草稿覆盖自动识别结果</label>
          <div class="oag-form-grid oag-core-grid">
            <label>任务类型<select id="oagTaskType">${optionHtml(currentOagOptions.task_types, example.task_type)}</select></label>
            <label>业务意图<select id="oagIntent">${optionHtml(currentOagOptions.intents, example.intent)}</select></label>
            <label>目标对象类型<select id="oagObjectType">${optionHtml(currentOagOptions.object_types, "Fund")}</select></label>
            <label>基金代码<input id="oagFundCode" value="000001" placeholder="000001"></label>
            <label>对象集合<input id="oagFundUniverse" placeholder="all_funds / equity_funds"></label>
            <label>周期<select id="oagPeriod">${optionHtml(currentOagOptions.periods, "1y")}</select></label>
            <label>报告日期<input id="oagReportDate" placeholder="例如 2026-03-31 或 latest"></label>
            <label>返回数量<input id="oagLimit" type="number" min="1" value="" placeholder="可选"></label>
            <label class="wide">显式属性${checkboxList("oagAttributes", currentOagOptions.attributes, example.mentioned_attributes)}</label>
            <label class="wide">目标对象列表<textarea id="oagTargets" rows="4" placeholder='例如 [{"object_type":"Fund","instance_ref":{"fund_code":"000001"},"role":"analysis_subject"}]'></textarea></label>
            <label class="wide">关系查询<textarea id="oagRelationQueries" rows="3" placeholder='例如 [{"relation_type":"managed_by","target_object_type":"FundManager"}]'></textarea></label>
            <label class="wide">筛选条件<textarea id="oagFilters" rows="3" placeholder='例如 [{"attribute":"max_drawdown","operator":"<","value":0.2}]'></textarea></label>
            <label class="wide">排序条件<textarea id="oagRanking" rows="3" placeholder='例如 [{"attribute":"return_rate","direction":"desc"}]'></textarea></label>
            <label class="wide">比较设置<textarea id="oagComparison" rows="3" placeholder='例如 {"mode":"side_by_side","attributes":["return_rate"],"target_object_policy":"all_targets"}'></textarea></label>
            <label class="wide">规划选项<textarea id="oagOptions" rows="3" placeholder='例如 {"allow_relation_expansion":true,"include_supporting_context":true}'></textarea></label>
          </div>
        </details>
        <div class="oag-runbar">
          <label class="oag-debug-toggle"><input id="oagDebug" type="checkbox" checked> 保留高级调试信息</label>
          <div class="task-actions">
            <button id="syncOagJsonBtn">同步到 JSON</button>
          </div>
        </div>
      </section>
      <section id="oagJsonPanel" class="oag-json-panel" hidden>
        <textarea id="oagJsonInput" rows="18">${escapeHtml(JSON.stringify(example, null, 2))}</textarea>
      </section>
      <div id="oagPlanSummary" class="oag-result-panel">
        <div class="oag-empty-state">
          <strong>尚未生成规划</strong>
          <span>输入问题或选择场景后点击“生成事实规划”。生成后中间画布显示 task_graph，右侧显示执行摘要。</span>
        </div>
      </div>
    </div>
  `;
  fillOagExample("分析某基金近一年表现");
  document.querySelectorAll("[data-oag-tab]").forEach((button) => {
    button.addEventListener("click", () => switchOagInputTab(button.dataset.oagTab));
  });
  document.querySelectorAll("[data-example-frame]").forEach((button) => {
    button.addEventListener("click", () => fillOagExample(button.dataset.exampleFrame));
  });
  on("syncOagJsonBtn", "click", () => {
    el("oagJsonInput").value = JSON.stringify(readSemanticFrameFromForm(), null, 2);
    switchOagInputTab("json");
  });
  on("refreshOagDraftBtn", "click", () => refreshAutoSemanticPreview({ forceDraftControls: true }));
  on("oagRawQuestion", "input", () => refreshAutoSemanticPreview());
  on("runOagPlanBtn", "click", () => guarded(runOagPlan));
  renderTaskCandidates();
  renderOagPlanPlaceholder();
}

function switchOagInputTab(tab) {
  document.querySelectorAll("[data-oag-tab]").forEach((button) => button.classList.toggle("active", button.dataset.oagTab === tab));
  el("oagFormPanel").hidden = tab !== "form";
  el("oagJsonPanel").hidden = tab !== "json";
}

function fillOagExample(name) {
  const frame = exampleSemanticFrame(name);
  fillOagFrame(frame);
  if (el("oagUseStructuredDraft")) el("oagUseStructuredDraft").checked = false;
  refreshAutoSemanticPreview({ frame, forceDraftControls: true });
}

function exampleSemanticFrame(name) {
  const base = {
    raw_question: "分析000001近一年的表现",
    domain: "finance_market",
    task_type: "analyze",
    intent: "performance_overview",
    target_objects: [{ object_type: "Fund", instance_ref: { fund_code: "000001" }, role: "analysis_subject" }],
    constraints: { period: "1y" },
    mentioned_attributes: [],
  };
  const examples = {
    "查询某基金最大回撤和夏普": { raw_question: "查询000001近一年最大回撤和夏普", mentioned_attributes: ["max_drawdown", "sharpe_ratio"] },
    "查询某基金经理": {
      raw_question: "查询000001的基金经理",
      task_type: "query",
      intent: "",
      mentioned_attributes: [],
      relation_queries: [{ relation_type: "managed_by", target_object_type: "FundManager" }],
      constraints: {},
    },
    "查询某基金公司": {
      raw_question: "查询000001的基金公司",
      task_type: "query",
      intent: "",
      mentioned_attributes: [],
      relation_queries: [{ relation_type: "issued_by", target_object_type: "FundCompany" }],
      constraints: {},
    },
    "查询某基金业绩基准": {
      raw_question: "查询000001的业绩比较基准",
      task_type: "query",
      intent: "",
      mentioned_attributes: [],
      relation_queries: [{ relation_type: "has_benchmark", target_object_type: "Benchmark" }],
      constraints: {},
    },
    "推荐收益高、回撤低的基金": {
      raw_question: "推荐近一年收益高、回撤低的基金",
      task_type: "recommend",
      intent: "fund_recommendation",
      target_objects: [{ object_type: "FundSet", instance_ref: { fund_universe: "all_funds" }, role: "candidate_set" }],
      ranking: [{ attribute: "return_rate", direction: "desc" }],
      filters: [{ attribute: "max_drawdown", operator: "<=", value: 0.1 }],
      limit: 10,
    },
    "筛选最大回撤低于10%的基金": {
      raw_question: "筛选近一年最大回撤低于10%的基金",
      task_type: "screen",
      intent: "fund_screening",
      target_objects: [{ object_type: "FundSet", instance_ref: { fund_universe: "all_funds" }, role: "candidate_set" }],
      ranking: [],
      filters: [{ attribute: "max_drawdown", operator: "<=", value: 0.1 }],
      limit: 20,
    },
    "比较两只基金收益": {
      raw_question: "比较000001和000002近一年收益",
      task_type: "compare",
      intent: "fund_comparison",
      target_objects: [
        { object_type: "Fund", instance_ref: { fund_code: "000001" }, role: "comparison_subject" },
        { object_type: "Fund", instance_ref: { fund_code: "000002" }, role: "comparison_subject" },
      ],
      mentioned_attributes: ["return_rate"],
      comparison: { mode: "side_by_side", attributes: ["return_rate"], target_object_policy: "all_targets" },
    },
    "查询是否跑赢基准": { raw_question: "000001近一年是否跑赢基准", task_type: "compare", intent: "benchmark_comparison", mentioned_attributes: ["return_rate"] },
    "查询同类排名": { raw_question: "000001近一年同类排名怎么样", task_type: "compare", intent: "peer_comparison", mentioned_attributes: [] },
    "查询费率": { raw_question: "000001费率是多少", task_type: "query", intent: "fee_analysis", mentioned_attributes: [] },
    "查询分红": { raw_question: "000001近几年分红情况", task_type: "query", intent: "dividend_analysis", mentioned_attributes: [], constraints: {} },
    "查询持仓配置": {
      raw_question: "000001当前持仓和资产配置如何",
      task_type: "query",
      intent: "holding_analysis",
      mentioned_attributes: [],
      constraints: { report_date: "latest" },
    },
  };
  return { ...base, ...(examples[name] || {}) };
}

function readSemanticFrameFromForm() {
  const inferred = inferSemanticFrameFromQuestion(el("oagRawQuestion").value.trim());
  if (!el("oagUseStructuredDraft")?.checked) {
    if (el("oagDebug")?.checked) inferred.debug = true;
    return inferred;
  }
  const objectType = el("oagObjectType").value || "Fund";
  const instanceRef = {};
  if (el("oagFundCode").value.trim()) instanceRef.fund_code = el("oagFundCode").value.trim();
  if (el("oagFundUniverse").value.trim()) instanceRef.fund_universe = el("oagFundUniverse").value.trim();
  const defaultTarget = { object_type: objectType, instance_ref: instanceRef, role: objectType === "FundSet" ? "candidate_set" : "analysis_subject" };
  const targetObjects = parseJsonField("oagTargets", [defaultTarget]);
  const frame = {
    raw_question: el("oagRawQuestion").value.trim(),
    domain: "finance_market",
    task_type: el("oagTaskType").value,
    target_objects: targetObjects.length ? targetObjects : [defaultTarget],
    constraints: {},
    mentioned_attributes: checkedValues("oagAttributes"),
  };
  if (el("oagIntent").value) frame.intent = el("oagIntent").value;
  if (el("oagPeriod").value) frame.constraints.period = el("oagPeriod").value;
  if (el("oagReportDate").value.trim()) frame.constraints.report_date = el("oagReportDate").value.trim();
  if (el("oagLimit").value) frame.limit = Number(el("oagLimit").value);
  const filters = parseJsonField("oagFilters", []);
  const ranking = parseJsonField("oagRanking", []);
  const relationQueries = parseJsonField("oagRelationQueries", []);
  const comparison = parseJsonField("oagComparison", {});
  const options = parseJsonField("oagOptions", {});
  if (filters.length) frame.filters = filters;
  if (ranking.length) frame.ranking = ranking;
  if (relationQueries.length) frame.relation_queries = relationQueries;
  if (Object.keys(comparison).length) frame.comparison = comparison;
  if (Object.keys(options).length) frame.options = options;
  if (el("oagDebug").checked) frame.debug = true;
  return frame;
}

function refreshAutoSemanticPreview({ frame = null, forceDraftControls = false } = {}) {
  if (!el("oagRawQuestion")) return;
  const inferred = frame || inferSemanticFrameFromQuestion(el("oagRawQuestion").value.trim());
  const shouldSyncDraft = forceDraftControls || !el("oagUseStructuredDraft")?.checked;
  if (shouldSyncDraft) fillOagFrame(inferred);
  if (el("oagJsonPanel")?.hidden) el("oagJsonInput").value = JSON.stringify(inferred, null, 2);
  const summary = [
    ["任务", taskTypeLabel(inferred.task_type)],
    ["意图", intentLabel(inferred.intent)],
    ["目标", semanticTargetSummary(inferred.target_objects)],
    ["指标", semanticAttributeSummary(inferred)],
    ["约束", semanticConstraintSummary(inferred)],
  ];
  el("oagAutoSummary").innerHTML = `
    <div class="oag-auto-title"><strong>自动语义草稿</strong><span>来自原始问题，可展开下方草稿校正。</span></div>
    <div class="oag-auto-grid">
      ${summary.map(([key, value]) => `<div><span>${escapeHtml(key)}</span><strong>${escapeHtml(value || "-")}</strong></div>`).join("")}
    </div>
  `;
}

function inferSemanticFrameFromQuestion(rawQuestion) {
  const text = (rawQuestion || "").trim();
  const taskType = inferTaskType(text);
  const intent = inferIntent(text, taskType);
  const codes = [...new Set((text.match(/\b\d{6}\b/g) || []))];
  const isCollectionTask = ["rank", "screen", "recommend"].includes(taskType);
  const targetObjects = isCollectionTask
    ? [{ object_type: "FundSet", instance_ref: { fund_universe: "all_funds" }, role: "candidate_set" }]
    : (codes.length ? codes : ["000001"]).map((code) => ({
        object_type: "Fund",
        instance_ref: { fund_code: code },
        role: taskType === "compare" && codes.length > 1 ? "comparison_subject" : "analysis_subject",
      }));
  const frame = {
    raw_question: text || "分析000001近一年的表现",
    domain: "finance_market",
    task_type: taskType,
    target_objects: targetObjects,
    constraints: inferConstraints(text, intent),
    mentioned_attributes: inferMentionedAttributes(text, intent, taskType),
  };
  if (intent) frame.intent = intent;
  const relations = inferRelationQueries(text, intent);
  if (relations.length) frame.relation_queries = relations;
  const ranking = inferRanking(text, taskType);
  if (ranking.length) frame.ranking = ranking;
  const filters = inferFilters(text, taskType);
  if (filters.length) frame.filters = filters;
  if (taskType === "compare" && codes.length > 1) {
    const attrs = frame.mentioned_attributes.length ? frame.mentioned_attributes : ["return_rate"];
    frame.comparison = { mode: "side_by_side", attributes: attrs, target_object_policy: "all_targets" };
  }
  const limit = inferLimit(text, taskType);
  if (limit) frame.limit = limit;
  if (!Object.keys(frame.constraints).length) delete frame.constraints;
  return frame;
}

function inferTaskType(text) {
  if (/推荐/.test(text)) return "recommend";
  if (/筛选|选出|过滤/.test(text)) return "screen";
  if (/排名|排行|前\s*\d+|前[一二三四五六七八九十]+/.test(text) && !/同类排名|排名怎么样|排第几/.test(text)) return "rank";
  if (/比较|对比|跑赢|战胜|相对|基准|同类|和\d{6}|与\d{6}/.test(text)) return "compare";
  if (/画像|概况|基本信息/.test(text)) return "profile";
  if (/分析|表现|怎么样|如何/.test(text)) return "analyze";
  return "query";
}

function inferIntent(text, taskType) {
  if (/推荐/.test(text)) return "fund_recommendation";
  if (/筛选|选出|过滤/.test(text)) return "fund_screening";
  if (taskType === "rank") return "fund_ranking";
  if (/比较|对比/.test(text) && (text.match(/\b\d{6}\b/g) || []).length > 1) return "fund_comparison";
  if (/跑赢|基准|业绩比较基准|比较基准/.test(text)) return "benchmark_comparison";
  if (/同类|排名|分位/.test(text)) return "peer_comparison";
  if (/费率|费用|申购费|赎回费|管理费|托管费/.test(text)) return "fee_analysis";
  if (/分红|派息/.test(text)) return "dividend_analysis";
  if (/持仓|重仓|股票|债券|行业配置/.test(text)) return "holding_analysis";
  if (/资产配置|仓位|股票资产|债券资产|现金资产/.test(text)) return "asset_allocation_analysis";
  if (/画像|概况|基本信息/.test(text) || taskType === "profile") return "fund_profile";
  if (/表现|收益|回撤|夏普|风险|波动|分析|怎么样|如何/.test(text)) return "performance_overview";
  return "";
}

function inferConstraints(text, intent) {
  const constraints = {};
  const periodRules = [
    [/近一周|一周|近1周/, "1w"],
    [/近一月|一个月|近1月/, "1m"],
    [/近三个月|三个月|近3月/, "3m"],
    [/近六月|六个月|近6月/, "6m"],
    [/近一年|最近一年|一年|近1年/, "1y"],
    [/近两年|两年|近2年/, "2y"],
    [/近三年|三年|近3年/, "3y"],
    [/近五年|五年|近5年/, "5y"],
    [/近十年|十年|近10年/, "10y"],
    [/今年以来|本年以来|YTD/i, "ytd"],
    [/成立以来|设立以来|SI/i, "si"],
  ];
  const match = periodRules.find(([pattern]) => pattern.test(text));
  if (match) constraints.period = match[1];
  const dateMatch = text.match(/\b(20\d{2}-\d{1,2}-\d{1,2}|20\d{2}\/\d{1,2}\/\d{1,2})\b/);
  if (dateMatch) constraints.report_date = dateMatch[1].replace(/\//g, "-");
  if (!constraints.report_date && (/最新|当前/.test(text) || ["holding_analysis", "asset_allocation_analysis"].includes(intent))) {
    constraints.report_date = "latest";
  }
  return constraints;
}

function inferMentionedAttributes(text, intent, taskType) {
  const attrs = [];
  const add = (name) => {
    if (!attrs.includes(name)) attrs.push(name);
  };
  [
    ["max_drawdown", /最大回撤|回撤|最大跌幅/],
    ["sharpe_ratio", /夏普|Sharpe/i],
    ["return_rate", /收益率|收益|回报率|回报|涨幅/],
    ["annualized_return", /年化收益|年化回报/],
    ["benchmark_return", /基准收益|业绩基准收益/],
    ["excess_return", /超额收益|跑赢|战胜/],
    ["volatility", /波动率|波动/],
    ["tracking_error", /跟踪误差|跟踪偏离/],
    ["information_ratio", /信息比率|信息比|\bIR\b/i],
    ["peer_return_rank", /同类收益排名|收益排名/],
    ["rank", /同类排名|排名|排第几/],
    ["percentile", /分位|百分位/],
    ["fund_type", /基金类型|品种|分类/],
    ["manager_name", /基金经理|经理/],
    ["company_name", /基金公司|管理人/],
    ["benchmark_name", /业绩比较基准|比较基准|基准名称/],
    ["fee_value", /费率|费用比例/],
    ["dividend_per_share", /分红金额|每份分红|派息/],
    ["stock_name", /持仓|重仓股票|股票名称/],
    ["stock_nav_ratio", /股票占比|持仓占比/],
    ["asset_total_value", /总资产|资产总值/],
    ["stock_asset_ratio", /股票仓位|股票资产占比/],
    ["bond_asset_ratio", /债券仓位|债券资产占比/],
    ["cash_asset_ratio", /现金仓位|现金资产占比/],
  ].forEach(([name, pattern]) => {
    if (pattern.test(text)) add(name);
  });
  if (!attrs.length && taskType === "compare" && intent === "fund_comparison") add("return_rate");
  if (["fund_recommendation", "fund_screening"].includes(intent)) {
    if (/收益高|高收益|收益/.test(text)) add("return_rate");
    if (/回撤低|低回撤|回撤/.test(text)) add("max_drawdown");
  }
  return attrs;
}

function inferRelationQueries(text, intent) {
  const rows = [];
  const add = (relation_type, target_object_type) => {
    if (!rows.some((item) => item.relation_type === relation_type && item.target_object_type === target_object_type)) {
      rows.push({ relation_type, target_object_type });
    }
  };
  if (/基金经理|经理/.test(text)) add("managed_by", "FundManager");
  if (/基金公司|管理人/.test(text)) add("issued_by", "FundCompany");
  if (/业绩比较基准|比较基准|基准名称/.test(text)) add("has_benchmark", "Benchmark");
  if (/基金类型|品种|分类|同类/.test(text) && intent !== "peer_comparison") add("belongs_to_category", "FundCategory");
  return rows;
}

function inferRanking(text, taskType) {
  if (!["rank", "recommend"].includes(taskType)) return [];
  const rows = [];
  if (/收益高|高收益|收益|收益率/.test(text)) rows.push({ attribute: "return_rate", direction: "desc" });
  if (/回撤低|低回撤/.test(text)) rows.push({ attribute: "max_drawdown", direction: "asc" });
  if (/夏普高|高夏普|夏普/.test(text)) rows.push({ attribute: "sharpe_ratio", direction: "desc" });
  return rows.length ? rows : [{ attribute: "return_rate", direction: "desc" }];
}

function inferFilters(text, taskType) {
  if (!["screen", "recommend"].includes(taskType)) return [];
  const rows = [];
  const drawdown = text.match(/回撤(?:低于|小于|不超过|<=?|≤)\s*(\d+(?:\.\d+)?)\s*%?/);
  if (drawdown) rows.push({ attribute: "max_drawdown", operator: "<=", value: percentOrNumber(drawdown[1], text) });
  if (!rows.length && /回撤低|低回撤/.test(text)) rows.push({ attribute: "max_drawdown", operator: "<=", value: 0.1 });
  return rows;
}

function inferLimit(text, taskType) {
  if (!["rank", "screen", "recommend"].includes(taskType)) return null;
  const arabic = text.match(/(?:前|top\s*)(\d+)/i);
  if (arabic) return Number(arabic[1]);
  const chinese = text.match(/前([一二三四五六七八九十]+)(?:只|个|名)?/);
  if (chinese) return chineseNumber(chinese[1]);
  return taskType === "recommend" ? 10 : taskType === "screen" ? 20 : null;
}

function percentOrNumber(value, text) {
  const number = Number(value);
  return text.includes("%") || number > 1 ? number / 100 : number;
}

function chineseNumber(text) {
  const map = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 };
  if (text === "十") return 10;
  if (text.startsWith("十")) return 10 + (map[text.slice(1)] || 0);
  if (text.includes("十")) {
    const [tens, ones] = text.split("十");
    return (map[tens] || 1) * 10 + (map[ones] || 0);
  }
  return map[text] || null;
}

function semanticTargetSummary(targets = []) {
  return (targets || []).map((target) => {
    const ref = target.instance_ref || {};
    if (target.object_type === "FundSet") return `基金集合 ${ref.fund_universe || "all_funds"}`;
    return `${target.object_type || "Fund"} ${ref.fund_code || "-"}`;
  }).join("、");
}

function semanticAttributeSummary(frame) {
  const parts = [];
  if ((frame.mentioned_attributes || []).length) parts.push((frame.mentioned_attributes || []).join("、"));
  if ((frame.ranking || []).length) parts.push(`排序 ${frame.ranking.map((item) => `${item.attribute} ${item.direction || ""}`).join("、")}`);
  if ((frame.filters || []).length) parts.push(`筛选 ${frame.filters.map((item) => `${item.attribute}${item.operator}${item.value}`).join("、")}`);
  if ((frame.relation_queries || []).length) parts.push(`关系 ${(frame.relation_queries || []).map((item) => item.relation_type).join("、")}`);
  return parts.join("；") || "由意图模板补全";
}

function semanticConstraintSummary(frame) {
  const constraints = frame.constraints || {};
  const parts = [];
  if (constraints.period) parts.push(`周期 ${constraints.period}`);
  if (constraints.report_date) parts.push(`报告日 ${constraints.report_date}`);
  if (frame.limit) parts.push(`返回 ${frame.limit}`);
  return parts.join("、");
}

function taskTypeLabel(value) {
  const row = (currentOagOptions.task_types || []).find((item) => item.value === value);
  return row?.label_zh || value || "-";
}

function intentLabel(value) {
  if (!value) return "未指定，按显式指标/操作规则规划";
  const row = (currentOagOptions.intents || []).find((item) => item.value === value);
  return row?.label_zh || value;
}

async function runOagPlan() {
  const frame = el("oagJsonPanel").hidden ? readSemanticFrameFromForm() : JSON.parse(el("oagJsonInput").value || "{}");
  const runButton = el("runOagPlanBtn");
  const originalText = runButton?.textContent || "";
  if (runButton) {
    runButton.disabled = true;
    runButton.textContent = "生成中...";
  }
  el("oagPlanSummary").innerHTML = `<div class="oag-empty-state"><strong>正在生成事实规划...</strong><span>读取本体配置并计算事实需求、Skill 覆盖和任务子图。</span></div>`;
  setGraphLoading(true, "正在生成事实规划", "正在计算事实需求、候选 Skill、覆盖情况和任务子图...");
  try {
    const result = await api("/api/oag/plan", {
      method: "POST",
      body: JSON.stringify({
        semantic_frame: frame,
        user_context: { permission_scopes: ["fund_public_data:read"], debug: Boolean(frame.debug) },
        output_view: "editor",
      }),
    });
    currentPlan = result.editor_plan || result.task_plan || result;
    currentPlan.agent_plan = result.agent_plan || null;
    currentPlan.plan_views = result.plan_views || {};
    currentPlan.sent_semantic_frame = frame;
    currentGraph = taskGraphToCytoscape(currentPlan.task_graph || { nodes: [], edges: [] });
    el("workbenchHome").classList.add("hidden");
    renderGraph();
    updateCounts();
    showOagPlanInspector(currentPlan);
    writeOutput({ editor_plan: currentPlan, agent_plan: currentPlan.agent_plan });
  } finally {
    setGraphLoading(false);
    if (runButton) {
      runButton.disabled = false;
      runButton.textContent = originalText || "生成事实规划";
    }
  }
}

function renderOagPlanPlaceholder() {
  el("inspectorTitle").textContent = "OAG 执行摘要";
  el("inspectorMeta").textContent = "等待生成规划";
  el("basicInfo").innerHTML = [
    ["当前阶段", "填写语义框架"],
    ["下一步", "生成事实规划"],
    ["输出视图", "Editor 完整计划"],
    ["执行状态", "尚未计算"],
  ].map(([key, value]) => `<div>${escapeHtml(key)}</div><strong>${escapeHtml(value)}</strong>`).join("");
  el("quickForm").innerHTML = `
    <div class="oag-result-panel">
      <div class="oag-empty-state">
        <strong>右侧会显示执行摘要</strong>
        <span>生成规划后，这里展示事实覆盖、事实需求、诊断提醒和未覆盖事实。</span>
      </div>
    </div>
  `;
  el("relatedEdges").innerHTML = `<div class="muted">生成规划后可查看 task_graph 中的关系边说明。</div>`;
  el("impactPanel").innerHTML = `<div class="muted">生成规划后显示诊断和提醒。</div>`;
  el("pathPanel").innerHTML = "";
  setRaw({});
  setInspectorTab("overview");
}

function taskGraphToCytoscape(taskGraph) {
  const nodes = (taskGraph.nodes || [])
    .filter((node) => !["DataTable", "DataField", "QueryCapability"].includes(node.node_type))
    .map((node) => ({
      data: {
        id: node.node_id,
        type: node.node_type,
        origin: "task_graph",
        label: node.label_zh || node.node_id,
        short_label: node.label_zh || node.node_id,
        degree: 1,
        raw: node,
      },
    }));
  const ids = new Set(nodes.map((node) => node.data.id));
  const edges = (taskGraph.edges || [])
    .filter((edge) => ids.has(edge.source) && ids.has(edge.target))
    .map((edge) => ({
      data: {
        id: edge.edge_id || `${edge.source}__${edge.relation_type}__${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: edge.relation_type,
        label: edge.label_zh || relationTypeLabel(edge.relation_type),
        origin: "task_graph",
        raw: edge,
      },
    }));
  return {
    kind: "task_graph",
    nodes,
    edges,
    summary: { node_count: nodes.length, edge_count: edges.length, total_node_count: nodes.length, total_edge_count: edges.length },
    relation_groups: countBy(edges.map((edge) => edge.data), "type"),
    hidden_counts: { data_fields: 0, inferred_edges: 0 },
    search_results: [],
  };
}

function showOagPlanInspector(plan) {
  const summary = plan.coverage_summary || {};
  const warnings = (plan.warnings || []).map((item) => item.message_zh || item).filter(Boolean);
  const execution = oagExecutionState(plan);
  el("inspectorTitle").textContent = "事实规划结果";
  el("inspectorMeta").textContent = `${statusLabel(plan.status)} / ${execution.label}`;
  el("basicInfo").innerHTML = [
    ["规划状态", statusLabel(plan.status)],
    ["执行状态", execution.label],
    ["目标对象", (plan.target_instances || []).map((item) => item.display_name_zh).join("、") || "-"],
    ["事实需求数量", (plan.fact_requirements || []).length],
    ["必须事实覆盖", `${summary.covered_required_fact_count || 0}/${summary.required_fact_count || 0}`],
    ["可选事实覆盖", `${summary.covered_optional_fact_count || 0}/${summary.optional_fact_count || 0}`],
    ["候选 Skill 数量", summary.skill_count || 0],
    ["缺失参数", execution.missingParams.length ? execution.missingParams.join("、") : "无"],
    ["未覆盖事实", (summary.uncovered_required_facts || []).length ? "存在" : "无"],
  ].map(([key, value]) => `<div>${escapeHtml(key)}</div><strong>${escapeHtml(value)}</strong>`).join("");
  el("quickForm").innerHTML = `
    <div class="oag-result-panel oag-inspector-plan">
      <div class="oag-status-card ${escapeHtml(execution.status)}">
        <strong>${escapeHtml(execution.label)}</strong>
        <span>${escapeHtml(execution.message)}</span>
      </div>
      <div class="task-actions"><button id="editOagFrameBtn">返回修改输入</button></div>
      ${renderPlanViewSplit(plan)}
      ${renderCoverageOverview(summary, execution)}
      ${renderFactRequirementOverview(plan.fact_requirements || [])}
      ${renderInvocationOverview(plan.candidate_invocations || [])}
      ${renderRelationExpansionPaths(plan)}
      ${renderPlanningIssues(plan, warnings)}
      ${renderYamlGovernanceEntry(plan)}
      ${renderTaskGraphHint(plan)}
      ${renderMissingParams(plan.missing_params || [])}
      <details class="oag-debug-details"><summary>高级调试</summary><pre>${escapeHtml(JSON.stringify({ warnings, diagnostics: plan.diagnostics || [], debug_evidence: plan.debug_evidence || {} }, null, 2))}</pre></details>
    </div>
  `;
  el("relatedEdges").innerHTML = renderTaskGraphEdgeList(plan.task_graph?.edges || []);
  el("impactPanel").innerHTML = warnings.length ? warnings.map((warning) => `<div class="impact-card"><strong>规划提醒</strong><span>${escapeHtml(warning)}</span></div>`).join("") : `<div class="muted">没有规划提醒</div>`;
  el("pathPanel").innerHTML = renderRelationExpansionPathList(plan, { compact: true });
  setRaw(plan);
  setInspectorTab("overview");
  on("editOagFrameBtn", "click", () => {
    const sentFrame = currentPlan?.sent_semantic_frame;
    renderOagPlanningDashboard();
    if (sentFrame) {
      el("oagJsonInput").value = JSON.stringify(sentFrame, null, 2);
      fillOagFrame(sentFrame);
    }
    writeOutput(currentPlan || {});
  });
  bindPlanListHighlights();
  bindPlanGovernanceActions();
}

function fillOagFrame(frame) {
  el("oagRawQuestion").value = frame.raw_question || "";
  el("oagTaskType").value = frame.task_type || "analyze";
  el("oagIntent").value = frame.intent || "";
  el("oagObjectType").value = frame.target_objects?.[0]?.object_type || "Fund";
  el("oagFundCode").value = frame.target_objects?.[0]?.instance_ref?.fund_code || "";
  el("oagFundUniverse").value = frame.target_objects?.[0]?.instance_ref?.fund_universe || "";
  el("oagPeriod").value = frame.constraints?.period || "1y";
  el("oagReportDate").value = frame.constraints?.report_date || "";
  el("oagLimit").value = frame.limit || "";
  setCheckedValues("oagAttributes", frame.mentioned_attributes || []);
  el("oagTargets").value = JSON.stringify(frame.target_objects || [], null, 2);
  el("oagRelationQueries").value = JSON.stringify(frame.relation_queries || [], null, 2);
  el("oagFilters").value = JSON.stringify(frame.filters || [], null, 2);
  el("oagRanking").value = JSON.stringify(frame.ranking || [], null, 2);
  el("oagComparison").value = JSON.stringify(frame.comparison || {}, null, 2);
  el("oagOptions").value = JSON.stringify(frame.options || {}, null, 2);
  el("oagJsonInput").value = JSON.stringify(frame, null, 2);
}

function oagExecutionState(plan) {
  const missingRows = plan.missing_params || [];
  const missingParams = [...new Set(missingRows.flatMap((item) => item.missing_params || []))];
  const uncovered = plan.coverage_summary?.uncovered_required_facts || [];
  if (uncovered.length) {
    return {
      status: "blocked",
      label: "能力未覆盖",
      message: "存在必需事实没有 Skill 覆盖，需要先补充能力声明。",
      missingParams,
    };
  }
  if (missingParams.length) {
    return {
      status: "blocked",
      label: "缺少参数",
      message: `补充 ${missingParams.join("、")} 后即可调用相关 Skill。`,
      missingParams,
    };
  }
  if ((plan.candidate_invocations || []).length) {
    return { status: "ready", label: "可执行", message: "候选 Skill 参数齐全，可以进入后续调用。", missingParams };
  }
  return { status: "empty", label: "无候选调用", message: "当前规划没有生成可调用 Skill。", missingParams };
}

function renderMissingParams(rows) {
  if (!rows.length) return "";
  return `
    <h3>缺失参数</h3>
    <div class="mini-table">
      ${rows.map((item) => `
        <button data-highlight-node="SkillCapability:${escapeHtml(item.skill_id || "")}">
          <strong>${escapeHtml(item.skill_name_zh || item.skill_id || "Skill")}</strong>
          <span>${escapeHtml((item.missing_params || []).join("、"))}</span>
          <em>${escapeHtml(item.message_zh || "")}</em>
        </button>
      `).join("")}
    </div>
  `;
}

function renderCoverageOverview(summary, execution) {
  const requiredTotal = Number(summary.required_fact_count || 0);
  const requiredCovered = Number(summary.covered_required_fact_count || 0);
  const optionalTotal = Number(summary.optional_fact_count || 0);
  const optionalCovered = Number(summary.covered_optional_fact_count || 0);
  const requiredRate = requiredTotal ? Math.round((requiredCovered / requiredTotal) * 100) : 0;
  const optionalRate = optionalTotal ? Math.round((optionalCovered / optionalTotal) * 100) : 0;
  const chips = [
    ["必须事实", `${requiredCovered}/${requiredTotal}`],
    ["辅助事实", `${optionalCovered}/${optionalTotal}`],
    ["Skill 覆盖", summary.skill_count || 0],
    ["缺失参数", execution.missingParams.length || 0],
  ];
  return `
    <section class="oag-summary-section">
      <h3>覆盖摘要</h3>
      <div class="oag-summary-chips">
        ${chips.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
      </div>
      <div class="oag-coverage-bars">
        ${renderCoverageBar("必须事实覆盖", requiredRate)}
        ${renderCoverageBar("辅助事实覆盖", optionalRate)}
      </div>
    </section>
  `;
}

function renderCoverageBar(label, rate) {
  const boundedRate = Math.max(0, Math.min(100, Number(rate) || 0));
  return `
    <div class="oag-coverage-row">
      <span>${escapeHtml(label)}</span>
      <strong>${boundedRate}%</strong>
      <div class="oag-coverage-track"><i style="width:${boundedRate}%"></i></div>
    </div>
  `;
}

function renderFactRequirementOverview(rows) {
  if (!rows.length) {
    return `
      <section class="oag-summary-section">
        <h3>事实需求</h3>
        <div class="muted">暂无事实需求</div>
      </section>
    `;
  }
  const required = rows.filter((item) => item.priority === "required");
  const optional = rows.filter((item) => item.priority !== "required");
  const visible = [...required, ...optional].slice(0, 10);
  const hiddenCount = Math.max(0, rows.length - visible.length);
  return `
    <section class="oag-summary-section">
      <h3>事实需求</h3>
      <div class="oag-fact-summary">
        <span>必须 ${required.length}</span>
        <span>辅助 ${optional.length}</span>
        <span>合计 ${rows.length}</span>
      </div>
      ${renderFactRequirementList(visible)}
      ${hiddenCount ? `<div class="muted">还有 ${hiddenCount} 条事实需求，可在高级调试中查看完整结构。</div>` : ""}
    </section>
  `;
}

function renderPlanningIssues(plan, warnings) {
  const diagnostics = plan.diagnostics || [];
  const uncovered = plan.coverage_summary?.uncovered_required_facts || [];
  const rows = [];
  uncovered.forEach((item) => {
    rows.push({
      title: item.label_zh || item.fact_requirement_id || "未覆盖事实",
      text: item.reason_zh || item.message_zh || "必须事实当前没有 Skill 覆盖。",
      nodeId: item.fact_requirement_id || "",
      severity: "warning",
    });
  });
  diagnostics.slice(0, 6).forEach((item) => {
    rows.push({
      title: diagnosticTypeLabel(item.type),
      text: item.diagnostic_message_zh || item.message_zh || item.message || "",
      nodeId: item.node_id || "",
      severity: item.severity || "info",
    });
  });
  warnings.slice(0, 4).forEach((warning) => {
    rows.push({ title: "规划提醒", text: warning, nodeId: "", severity: "info" });
  });
  if (!rows.length) {
    return `
      <section class="oag-summary-section">
        <h3>缺口与诊断</h3>
        <div class="muted">没有规划提醒或覆盖缺口</div>
      </section>
    `;
  }
  return `
    <section class="oag-summary-section">
      <h3>缺口与诊断</h3>
      <div class="oag-issue-list">
        ${rows.slice(0, 8).map((item) => `
          <button class="${escapeHtml(item.severity)}" ${item.nodeId ? `data-highlight-node="${escapeHtml(item.nodeId)}"` : "disabled"}>
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.text)}</span>
          </button>
        `).join("")}
      </div>
    </section>
  `;
}

function renderTaskGraphHint(plan) {
  const graph = plan.task_graph || {};
  const nodeCount = (graph.nodes || []).length;
  const edgeCount = (graph.edges || []).length;
  return `
    <section class="oag-summary-section">
      <h3>任务图</h3>
      <div class="oag-task-graph-hint">
        <strong>${escapeHtml(nodeCount)} 个节点 / ${escapeHtml(edgeCount)} 条边</strong>
        <span>点击图中的事实、关系或 Skill 节点查看细节；空白处会回到本摘要。</span>
      </div>
    </section>
  `;
}

function renderPlanViewSplit(plan) {
  const agentPlan = plan.agent_plan || {};
  const agentExecution = agentPlan.execution || {};
  const agentCoverage = agentPlan.coverage || {};
  const editorView = plan.plan_views?.editor || {};
  const agentView = plan.plan_views?.agent || {};
  return `
    <section class="oag-summary-section">
      <h3>Plan 分流</h3>
      <div class="oag-view-split">
        <div>
          <strong>${escapeHtml(editorView.label_zh || "Editor 调试计划")}</strong>
          <span>${escapeHtml(editorView.description_zh || "展示完整任务子图、诊断和调试证据。")}</span>
          <em>事实 ${escapeHtml((plan.fact_requirements || []).length)} · Skill ${escapeHtml((plan.candidate_invocations || []).length)} · 图边 ${escapeHtml((plan.task_graph?.edges || []).length)}</em>
        </div>
        <div>
          <strong>${escapeHtml(agentView.label_zh || "Agent 执行计划")}</strong>
          <span>${escapeHtml(agentView.description_zh || "只保留后续智能体执行 Skill 所需结构。")}</span>
          <em>${escapeHtml(executionStatusLabel(agentExecution.execution_status))} · 可执行 ${escapeHtml(agentExecution.ready_skill_count || 0)} · 覆盖 ${escapeHtml(coverageStatusLabel(agentCoverage.coverage_status))}</em>
        </div>
      </div>
    </section>
  `;
}

function renderInvocationOverview(rows) {
  const readyCount = rows.filter((item) => !(item.missing_params || []).length).length;
  const blockedCount = rows.length - readyCount;
  return `
    <section class="oag-summary-section">
      <h3>候选 Skill</h3>
      <div class="oag-fact-summary">
        <span>可执行 ${readyCount}</span>
        <span>待补参 ${blockedCount}</span>
        <span>合计 ${rows.length}</span>
      </div>
      ${renderInvocationList(rows.slice(0, 10))}
    </section>
  `;
}

function renderRelationExpansionPaths(plan) {
  const html = renderRelationExpansionPathList(plan);
  return `
    <section class="oag-summary-section">
      <h3>关系扩展路径</h3>
      ${html}
    </section>
  `;
}

function renderRelationExpansionPathList(plan, { compact = false } = {}) {
  const evidence = plan.debug_evidence?.relation_expansion_edges || [];
  const relationEdges = (plan.task_graph?.edges || []).filter((edge) => {
    const type = edge.relation_type || "";
    return type.includes("relation") || type.includes("context") || type === "expanded_by_relation" || edge.reason_zh;
  });
  const rows = evidence.length
    ? evidence.map((item) => ({
        source: item.source_attribute || item.from_object_type || item.edge_id || "",
        relation: item.relation_type_zh || relationTypeLabel(item.relation_type) || item.relation_type || "关系扩展",
        target: item.target_attribute || item.to_object_type || item.target_object_type || "",
        reason: item.reason_zh || "",
        role: item.planning_role || item.answer_visibility || "",
      }))
    : relationEdges.map((edge) => ({
        source: edge.source,
        relation: edge.label_zh || relationTypeLabel(edge.relation_type),
        target: edge.target,
        reason: edge.reason_zh || "",
        role: edge.relation_type || "",
      }));
  if (!rows.length) return `<div class="muted">本次规划没有触发本体关系扩展；显式指标或意图模板已能构造事实需求。</div>`;
  return `
    <div class="oag-path-list ${compact ? "compact" : ""}">
      ${rows.slice(0, compact ? 6 : 10).map((item) => `
        <div>
          <strong>${escapeHtml(item.source || "-")} → ${escapeHtml(item.relation || "关系")} → ${escapeHtml(item.target || "-")}</strong>
          <span>${escapeHtml(item.reason || "由本体关系治理配置触发。")}</span>
          ${item.role ? `<em>${escapeHtml(item.role)}</em>` : ""}
        </div>
      `).join("")}
    </div>
  `;
}

function renderYamlGovernanceEntry(plan) {
  const uncovered = plan.coverage_summary?.uncovered_required_facts || [];
  const diagnostics = plan.diagnostics || [];
  const hasRelationEvidence = Boolean(plan.debug_evidence?.relation_expansion_edges?.length);
  const hasMissingSkill = uncovered.length || diagnostics.some((item) => String(item.type || "").includes("skill") || String(item.diagnostic_type || "").includes("skill"));
  const hasIntentIssue = diagnostics.some((item) => String(item.type || "").includes("intent") || String(item.diagnostic_type || "").includes("intent"));
  const actions = [
    { id: "skill_coverage", label: "维护 Skill 覆盖", active: hasMissingSkill },
    { id: "semantic_relations", label: "维护关系治理", active: hasRelationEvidence || diagnostics.some((item) => String(item.type || "").includes("edge") || String(item.type || "").includes("relation")) },
    { id: "intent_templates", label: "维护意图模板", active: hasIntentIssue || plan.semantic_frame_summary?.intent },
    { id: "diagnostic", label: "查看诊断中心", active: diagnostics.length || uncovered.length },
    { id: "yaml_files", label: "查看 YAML 文件", active: true },
  ];
  return `
    <section class="oag-summary-section">
      <h3>YAML 治理入口</h3>
      <div class="oag-governance-actions">
        ${actions.map((item) => `<button class="${item.active ? "active" : ""}" data-oag-governance="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`).join("")}
      </div>
    </section>
  `;
}

function renderTaskGraphEdgeList(edges) {
  if (!edges.length) return `<div class="muted">任务子图暂无关系边。</div>`;
  return `<div class="mini-table oag-plan-list">${edges.slice(0, 40).map((edge) => `
    <button data-highlight-node="${escapeHtml(edge.target || "")}">
      <strong>${escapeHtml(edge.label_zh || relationTypeLabel(edge.relation_type))}</strong>
      <span>${escapeHtml(edge.source || "-")} → ${escapeHtml(edge.target || "-")}</span>
      <em>${escapeHtml(edge.reason_zh || sourceLabel(edge.source) || "")}</em>
    </button>
  `).join("")}</div>`;
}

function bindPlanGovernanceActions() {
  document.querySelectorAll("[data-oag-governance]").forEach((button) => {
    button.addEventListener("click", () => guarded(() => selectTask(button.dataset.oagGovernance)));
  });
}

function renderFactRequirementList(rows) {
  if (!rows.length) return `<div class="muted">暂无事实需求</div>`;
  return `<div class="mini-table oag-plan-list">${rows.map((item) => `
    <button data-highlight-node="${escapeHtml(item.fact_requirement_id)}" title="${escapeHtml(item.reason_zh || "")}">
      <strong>${escapeHtml(item.label_zh || item.fact_requirement_id)}</strong>
      <span>${escapeHtml(item.fact_type_zh || item.fact_type)} · ${escapeHtml(item.subject?.label_zh || item.subject?.object_type || "-")} · ${escapeHtml(item.attribute?.label_zh || item.predicate_zh || "-")}</span>
      <em>${escapeHtml(item.priority_zh || priorityLabel(item.priority))} · ${escapeHtml(item.source_zh || sourceLabel(item.source))}</em>
    </button>`).join("")}</div>`;
}

function renderInvocationList(rows) {
  if (!rows.length) return `<div class="muted">暂无候选 Skill</div>`;
  return `<div class="mini-table oag-plan-list">${rows.map((item) => `
    <button data-highlight-node="SkillCapability:${escapeHtml(item.skill_id)}" title="${escapeHtml(item.coverage_reason_zh || "")}">
      <strong>${escapeHtml(item.skill_name_zh || item.skill_name || item.skill_id)}</strong>
      <span>覆盖事实：${escapeHtml((item.covers_fact_requirements || []).length)} · 覆盖评分：${escapeHtml(item.coverage_score ?? "-")}</span>
      <em>缺失参数：${escapeHtml((item.missing_params || []).join("、") || "无")} · 权限：${escapeHtml(item.permission_scope || "未声明")}</em>
    </button>`).join("")}</div>`;
}

function bindPlanListHighlights() {
  document.querySelectorAll("[data-highlight-node]").forEach((button) => {
    button.addEventListener("click", () => centerNode(button.dataset.highlightNode));
  });
}

async function renderIntentTemplatesDashboard() {
  const data = await api("/api/intent-profiles");
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel">
      <h1>意图模板</h1>
      <p>维护宽泛意图默认事实模板；保存后可直接用该意图生成示例规划。</p>
      <div class="task-actions"><button id="newIntentTemplateBtn" data-edit-only>新增意图模板</button></div>
      <div class="governance-list">
        ${(data.items || []).map((item) => `
          <button data-edit-intent="${escapeHtml(item.intent_name)}">
            <strong>${escapeHtml(item.display_name_zh)}</strong>
            <span>默认事实：${item.fact_template_count || 0} · ${escapeHtml(item.enabled_zh)}</span>
            <em>${escapeHtml(item.description || "")}</em>
          </button>
        `).join("")}
      </div>
    </div>
  `;
  on("newIntentTemplateBtn", "click", () => openIntentTemplateEditor({}));
  document.querySelectorAll("[data-edit-intent]").forEach((button) => {
    const item = (data.items || []).find((row) => row.intent_name === button.dataset.editIntent);
    button.addEventListener("click", () => openIntentTemplateEditor(item));
  });
  updateEditModeUi();
}

async function renderSemanticRelationsDashboard() {
  const data = await api("/api/semantic-relations");
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel">
      <h1>关系治理</h1>
      <p>重点维护属性语义扩展关系和对象关系，并补齐适用任务、适用意图、权重和中文原因。</p>
      <div class="task-actions"><button id="newSemanticRelationBtn" data-edit-only>新增关系边</button></div>
      <div class="dashboard-metrics">
        <div><strong>${data.summary?.edge_count || 0}</strong><span>治理关系</span></div>
        <div><strong>${data.summary?.attribute_expansion_count || 0}</strong><span>属性扩展</span></div>
        <div><strong>${data.summary?.object_relation_count || 0}</strong><span>对象关系</span></div>
      </div>
      <div class="governance-list">
        ${(data.items || []).slice(0, 240).map((item) => `
          <button data-edit-relation="${escapeHtml(item.edge_id)}">
            <strong>${escapeHtml(item.display_name_zh)} · ${escapeHtml(item.group_zh)}</strong>
            <span>${escapeHtml(item.source)} → ${escapeHtml(item.target)}</span>
            <em>${escapeHtml(item.reason_zh || item.reason_status_zh)}</em>
          </button>
        `).join("")}
      </div>
    </div>
  `;
  on("newSemanticRelationBtn", "click", () => openSemanticRelationEditor({}));
  document.querySelectorAll("[data-edit-relation]").forEach((button) => {
    const item = (data.items || []).find((row) => row.edge_id === button.dataset.editRelation);
    button.addEventListener("click", () => openSemanticRelationEditor(item));
  });
  updateEditModeUi();
}

async function renderSkillCoverageDashboard() {
  const data = await api("/api/skills");
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel">
      <h1>Skill 覆盖</h1>
      <p>维护 Skill 的事实覆盖能力；诊断会据此判断必须事实是否可覆盖。</p>
      <div class="task-actions"><button id="newSkillCoverageBtn" data-edit-only>新增 Skill</button></div>
      <div class="governance-list">
        ${(data.items || []).map((item) => `
          <button data-edit-skill="${escapeHtml(item.skill_id)}">
            <strong>${escapeHtml(item.display_name_zh)}</strong>
            <span>事实类型：${item.fact_type_count || 0} · 支持属性：${item.supported_attribute_count || 0} · ${escapeHtml(item.enabled_zh)}</span>
            <em>${escapeHtml(item.description || "")}</em>
          </button>
        `).join("")}
      </div>
    </div>
  `;
  on("newSkillCoverageBtn", "click", () => openSkillCoverageEditor({}));
  document.querySelectorAll("[data-edit-skill]").forEach((button) => {
    const item = (data.items || []).find((row) => row.skill_id === button.dataset.editSkill);
    button.addEventListener("click", () => openSkillCoverageEditor(item));
  });
  updateEditModeUi();
}

function renderYamlFilesDashboard() {
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.add("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel dashboard-panel">
      <h1>YAML 文件</h1>
      <p>左侧展示本体 YAML 文件状态；需要直接编辑原始文件时，请使用右侧原始数据页或 YAML 接口。</p>
      <div class="task-actions"><a href="/api/export">导出当前 YAML</a><button id="validateYamlBtn">校验本体配置</button></div>
      <div class="governance-list">${el("fileList").innerHTML || `<div class="muted">文件列表加载中</div>`}</div>
    </div>
  `;
  on("validateYamlBtn", "click", validateOntology);
}

function mappingStatusLabel(status) {
  const labels = { mapped: "已映射", missing: "未映射", multi_mapped: "多重映射" };
  return labels[status] || status || "-";
}

async function focusMappingAttribute(attributeId) {
  const task = TASKS.find((item) => item.id === "table_mapping");
  await enterTaskFocus(task, attributeId);
}

function countBy(items, key) {
  return items.reduce((acc, item) => {
    const value = item[key] || "unknown";
    acc[value] = (acc[value] || 0) + 1;
    return acc;
  }, {});
}

function optionHtml(options = [], selected = "") {
  return [`<option value="">请选择</option>`, ...(options || []).map((item) => {
    const value = item.value || item.id || "";
    const label = item.label_zh || item.label || value;
    return `<option value="${escapeHtml(value)}" ${String(value) === String(selected || "") ? "selected" : ""}>${escapeHtml(label)}</option>`;
  })].join("");
}

function checkboxList(name, options = [], selected = []) {
  const selectedSet = new Set(selected || []);
  return `<div class="multi-choice-list compact-choice-list" data-choice-list="${escapeHtml(name)}">
    ${(options || []).slice(0, 80).map((item) => {
      const value = item.value || item.id || "";
      const label = item.label_zh || item.label || value;
      return `<label class="multi-choice-item"><input type="checkbox" value="${escapeHtml(value)}" ${selectedSet.has(value) ? "checked" : ""}><span>${escapeHtml(label)}<br><em>${escapeHtml(value)}</em></span></label>`;
    }).join("")}
  </div>`;
}

function checkedValues(name) {
  return [...document.querySelectorAll(`[data-choice-list="${CSS.escape(name)}"] input:checked`)].map((input) => input.value);
}

function setCheckedValues(name, values) {
  const selected = new Set(values || []);
  document.querySelectorAll(`[data-choice-list="${CSS.escape(name)}"] input`).forEach((input) => {
    input.checked = selected.has(input.value);
  });
}

function parseJsonField(id, fallback) {
  const text = el(id).value.trim();
  if (!text) return fallback;
  try {
    return JSON.parse(text);
  } catch (error) {
    throw new Error(`${el(id).closest("label")?.firstChild?.textContent || "JSON 字段"}格式不正确：${error.message}`);
  }
}

function statusLabel(status) {
  const labels = { success: "规划成功", need_clarification: "需要补充信息", error: "规划失败" };
  return labels[status] || status || "-";
}

function executionStatusLabel(status) {
  const labels = {
    ready: "可执行",
    blocked_missing_params: "缺少参数",
    blocked_permission: "权限不足",
    partial: "部分可执行",
    no_skill_calls: "无 Skill 调用",
    disabled: "Skill 不可用",
  };
  return labels[status] || status || "-";
}

function coverageStatusLabel(status) {
  const labels = {
    full_coverage: "完全覆盖",
    partial_coverage: "部分覆盖",
    no_coverage: "没有覆盖",
    need_clarification: "需要补充信息",
    permission_blocked: "权限受阻",
  };
  return labels[status] || status || "-";
}

function diagnosticTypeLabel(type) {
  const labels = {
    intent_missing_fact_requirements_template: "意图缺少事实模板",
    skill_missing_provides_fact_types: "Skill 缺少事实类型",
    skill_missing_supported_attributes: "Skill 缺少支持属性",
    skill_missing_supported_subject_types: "Skill 缺少支持对象",
    attribute_without_skill_coverage: "属性缺少 Skill 覆盖",
    semantic_edge_missing_reason_zh: "关系边缺少中文原因",
    semantic_edge_missing_applicability: "关系边缺少适用范围",
    relation_edge_unknown_node: "关系边引用不存在节点",
    required_fact_without_skill_coverage: "必须事实缺少 Skill 覆盖",
    orphan_nodes: "孤立节点",
    skills_without_attributes: "Skill 缺少属性声明",
    attributes_without_skill: "属性没有 Skill 覆盖",
    attributes_without_table_mapping: "属性缺少表字段映射",
    intents_without_skill: "意图缺少候选 Skill",
    relation_types_unused: "关系类型未使用",
    disabled_skills_referenced: "停用 Skill 仍被引用",
  };
  return labels[type] || type || "诊断问题";
}

function priorityLabel(value) {
  return value === "required" ? "必须查询" : "辅助参考";
}

function sourceLabel(value) {
  const labels = {
    explicit_attribute: "显式属性",
    intent_template: "意图模板",
    relation_expansion: "关系扩展",
    operation_rule: "操作规则",
    explicit_relation: "显式关系查询",
  };
  return labels[value] || value || "-";
}

async function openIntentTemplateEditor(item = {}) {
  const isNew = !item.intent_name;
  if (!(await requestEditModeForAction(isNew ? "新增意图模板" : "编辑意图模板"))) return;
  await ensureOagOptions();
  const draft = isNew ? newIntentTemplateDraft() : item;
  el("modalTitle").textContent = isNew ? "新增意图模板" : "编辑意图事实模板";
  const rows = draft.fact_requirements_template?.length ? draft.fact_requirements_template : [{ priority: "required" }];
  el("modalBody").innerHTML = `
    <div class="wizard-panel intent-template-editor">
      <section class="intent-template-section">
        <h3>1. 定义这个意图</h3>
        <div class="oag-form-grid">
          <label>意图标识<input id="intentName" value="${escapeHtml(draft.intent_name || "")}" ${isNew ? "" : "disabled"} placeholder="例如 performance_overview"></label>
          <label>意图名称<input id="intentNameZh" value="${escapeHtml(draft.intent_name_zh || "")}" placeholder="例如 基金综合表现分析"></label>
          <label class="wide">用户会怎么说<input id="intentTriggers" value="${escapeHtml((draft.trigger_aliases || []).join(", "))}" placeholder="多个表达用逗号分隔，例如 分析表现, 看一下收益风险"></label>
          <label>适用对象<input id="intentObjects" value="${escapeHtml((draft.target_object_types || ["Fund"]).join(", "))}" placeholder="例如 Fund, FundSet"></label>
          <label class="wide">说明<input id="intentDescription" value="${escapeHtml(draft.description || "")}" placeholder="这个意图解决什么问题，可选"></label>
        </div>
      </section>
      <section class="intent-template-section">
        <h3>2. 这个意图默认需要哪些事实</h3>
        <p class="wizard-help">每一行就是一个事实需求：选择事实类型、事实名称，标记是否必须查询，并写清楚原因。</p>
        <div class="template-editor-row template-editor-head">
          <span>事实类型</span>
          <span>事实名称</span>
          <span>是否必须查询</span>
          <span>原因</span>
          <span></span>
        </div>
        <div id="intentFactRows" class="template-editor-list">
          ${rows.map((row) => renderIntentFactEditorRow(row)).join("")}
        </div>
        <div class="task-actions">
          <button id="addIntentFactBtn" type="button">添加事实需求</button>
        </div>
      </section>
      <details><summary>高级：原始 YAML 数据</summary><textarea id="intentRawJson" rows="10">${escapeHtml(JSON.stringify(draft, null, 2))}</textarea></details>
    </div>
  `;
  el("addIntentFactBtn").addEventListener("click", () => {
    el("intentFactRows").insertAdjacentHTML("beforeend", renderIntentFactEditorRow({ priority: "required" }));
  });
  openModal(async () => {
    const raw = JSON.parse(el("intentRawJson").value || "{}");
    const intentName = isNew ? el("intentName").value.trim() : item.intent_name;
    if (!intentName) throw new Error("请先填写意图标识");
    const factRows = readIntentFactRows();
    if (!factRows.length) throw new Error("请至少添加一个事实需求");
    const next = { ...draft, ...raw };
    next.intent_name = intentName;
    next.intent_name_zh = el("intentNameZh").value.trim() || intentName;
    next.description = el("intentDescription").value.trim();
    next.trigger_aliases = splitCsv(el("intentTriggers").value);
    next.target_object_types = splitCsv(el("intentObjects").value);
    next.fact_requirements_template = factRows;
    next.default_attributes = Array.from(new Set(factRows.map((row) => row.attribute_name).filter(Boolean)));
    next.skill_priorities = Array.isArray(next.skill_priorities) ? next.skill_priorities : [];
    await confirmPreviewAndSave(isNew ? "新增意图模板" : "保存意图模板", item, next, async () => {
      const result = await api(`/api/intent-profiles/${encodeURIComponent(intentName)}`, {
        method: "PUT",
        body: JSON.stringify({ data: next }),
      });
      writeOutput(result);
      await refreshAll({ loadGraph: false });
      await renderIntentTemplatesDashboard();
    });
  });
}

function newIntentTemplateDraft() {
  return {
    intent_name: "",
    intent_name_zh: "",
    enabled: true,
    trigger_aliases: [],
    target_object_types: ["Fund"],
    fact_requirements_template: [{ priority: "required", reason_zh: "" }],
  };
}

function renderIntentFactEditorRow(row = {}) {
  return `
    <div class="template-editor-row">
      <select data-template-field="fact_type">${optionHtml(currentOagOptions.fact_types, row.fact_type)}</select>
      <select data-template-field="attribute_name">${optionHtml(currentOagOptions.attributes, row.attribute_name)}</select>
      <select data-template-field="priority">
        <option value="required" ${row.priority !== "optional" ? "selected" : ""}>必须查询</option>
        <option value="optional" ${row.priority === "optional" ? "selected" : ""}>辅助参考</option>
      </select>
      <input data-template-field="reason_zh" value="${escapeHtml(row.reason_zh || "")}" placeholder="该事实用于说明什么？">
      <button type="button" onclick="this.closest('.template-editor-row').remove()">删除</button>
    </div>
  `;
}

function readIntentFactRows() {
  return [...document.querySelectorAll("#intentFactRows .template-editor-row")].map((row) => {
    const get = (field) => row.querySelector(`[data-template-field="${field}"]`)?.value.trim();
    return {
      fact_type: get("fact_type"),
      attribute_name: get("attribute_name"),
      priority: get("priority") || "required",
      reason_zh: get("reason_zh") || "该事实用于支撑当前意图回答。",
    };
  }).filter((row) => row.fact_type && row.attribute_name);
}

async function openSkillCoverageEditor(item = {}) {
  const isNew = !item.skill_id;
  if (!(await requestEditModeForAction(isNew ? "新增 Skill" : "编辑 Skill 覆盖"))) return;
  await ensureOagOptions(["fact_requirements", "input_params"]);
  const draft = isNew ? newSkillDraft(item) : item;
  const selectedFactIds = selectedFactRequirementIdsForSkill(draft);
  const selectedInputParams = draft.input_params?.length ? draft.input_params : DEFAULT_SKILL_INPUT_PARAMS;
  el("modalTitle").textContent = isNew ? "新增 Skill" : "编辑 Skill 覆盖能力";
  el("modalBody").innerHTML = `
    <div class="wizard-panel skill-coverage-editor">
      <section class="intent-template-section">
        <h3>1. 定义这个 Skill</h3>
        <div class="oag-form-grid">
          <label>Skill 标识<input id="skillId" value="${escapeHtml(draft.skill_id || "")}" ${isNew ? "" : "disabled"} placeholder="例如 get_fund_metric_values"></label>
          <label>Skill 名称<input id="skillName" value="${escapeHtml(draft.skill_name || "")}" placeholder="例如 获取基金指标值"></label>
          <label>面向对象<select id="skillTargetObject">${optionHtml(currentOagOptions.object_types, draft.target_object_type || "Fund")}</select></label>
          <label>权限要求<input id="skillPermission" value="${escapeHtml(draft.permission_scope || "fund_public_data:read")}"></label>
          <div class="wide choice-field">
            <span class="choice-field-title">输入参数</span>
            <span class="wizard-help">选择调用这个 Skill 时需要用户或上游流程提供的信息。</span>
            ${skillInputParamCheckboxList("skillInputParams", selectedInputParams)}
          </div>
          <label class="wide">说明<input id="skillDescription" value="${escapeHtml(draft.description || "")}" placeholder="这个 Skill 如何产出事实，可选"></label>
        </div>
      </section>
      <section class="intent-template-section">
        <h3>2. 这个 Skill 能满足哪些事实需求</h3>
        <p class="wizard-help">勾选事实需求后，系统会自动生成事实类型、事实名称、对象类型和关系覆盖声明。</p>
        ${factRequirementCheckboxList("skillFactRequirements", currentOagOptions.fact_requirements || [], selectedFactIds)}
      </section>
      <details><summary>高级：原始 YAML 数据</summary><textarea id="skillRawJson" rows="10">${escapeHtml(JSON.stringify(draft, null, 2))}</textarea></details>
    </div>
  `;
  openModal(async () => {
    const raw = JSON.parse(el("skillRawJson").value || "{}");
    const skillId = isNew ? el("skillId").value.trim() : item.skill_id;
    if (!skillId) throw new Error("请先填写 Skill 标识");
    const inputParams = checkedValues("skillInputParams");
    if (!inputParams.length) throw new Error("请至少选择一个输入参数");
    const selectedFacts = selectedFactRequirements("skillFactRequirements");
    if (!selectedFacts.length) throw new Error("请至少关联一个事实需求");
    const coverage = deriveSkillCoverageFromFacts(selectedFacts, el("skillTargetObject").value || "Fund");
    const next = { ...draft, ...raw };
    next.skill_id = skillId;
    next.skill_name = el("skillName").value.trim() || skillId;
    next.description = el("skillDescription").value.trim();
    next.target_object_type = el("skillTargetObject").value || coverage.supported_subject_types[0] || "Fund";
    next.permission_scope = el("skillPermission").value.trim();
    next.input_params = inputParams;
    next.supported_fact_requirements = selectedFacts.map((fact) => fact.value);
    next.provides_fact_types = coverage.provides_fact_types;
    next.supported_subject_types = coverage.supported_subject_types;
    next.supported_attributes = coverage.supported_attributes;
    next.output_attributes = Array.from(new Set([...(next.output_attributes || []), ...next.supported_attributes]));
    next.supported_relations = coverage.supported_relations;
    await confirmPreviewAndSave(isNew ? "新增 Skill" : "保存 Skill 覆盖能力", item, next, async () => {
      const result = await api(`/api/skills/${encodeURIComponent(skillId)}`, {
        method: "PUT",
        body: JSON.stringify({ data: next }),
      });
      writeOutput(result);
      await refreshAll({ loadGraph: false });
      await renderSkillCoverageDashboard();
    });
  });
}

function newSkillDraft(defaults = {}) {
  return {
    skill_id: "",
    skill_name: "",
    description: "",
    target_object_type: defaults.target_object_type || "Fund",
    input_params: DEFAULT_SKILL_INPUT_PARAMS,
    permission_scope: "fund_public_data:read",
    enabled: true,
    supported_fact_requirements: [],
    ...defaults,
  };
}

function skillInputParamOptions(selected = []) {
  const byValue = new Map();
  [...FALLBACK_SKILL_INPUT_PARAM_OPTIONS, ...(currentOagOptions.input_params || [])].forEach((item) => {
    const value = item.value || item.id || "";
    if (!value) return;
    byValue.set(value, {
      value,
      label_zh: item.label_zh || item.label || value,
      group_zh: item.group_zh || "输入参数",
    });
  });
  (selected || []).forEach((value) => {
    if (value && !byValue.has(value)) {
      byValue.set(value, { value, label_zh: String(value).replaceAll("_", " "), group_zh: "已保存参数" });
    }
  });
  return [...byValue.values()];
}

function skillInputParamCheckboxList(name, selected = []) {
  const selectedSet = new Set(selected || []);
  return `<div class="multi-choice-list input-param-choice-list" data-choice-list="${escapeHtml(name)}">
    ${skillInputParamOptions(selected).map((item) => `
      <label class="multi-choice-item">
        <input type="checkbox" value="${escapeHtml(item.value)}" ${selectedSet.has(item.value) ? "checked" : ""}>
        <span>${escapeHtml(item.label_zh || item.label || item.value)}<br><em>${escapeHtml(item.group_zh || "输入参数")}</em></span>
      </label>
    `).join("")}
  </div>`;
}

function factRequirementCheckboxList(name, options = [], selected = []) {
  const selectedSet = new Set(selected || []);
  if (!options.length) {
    return `<div class="oag-empty-state"><strong>没有读取到事实需求模板</strong><span>请确认意图模板中已经配置事实需求；如果刚刚修改过模板，请刷新后再试。</span></div>`;
  }
  return `<div class="multi-choice-list fact-requirement-choice-list" data-choice-list="${escapeHtml(name)}">
    ${options.map((item) => `
      <label class="multi-choice-item fact-requirement-choice">
        <input type="checkbox" value="${escapeHtml(item.value)}" ${selectedSet.has(item.value) ? "checked" : ""}>
        <span>
          <strong>${escapeHtml(item.label_zh || item.label || item.value)}</strong>
          <em>${escapeHtml(item.fact_type_zh || item.fact_type || "事实")} · ${escapeHtml(item.priority_zh || priorityLabel(item.priority))}</em>
          <small>${escapeHtml(item.reason_zh || "")}</small>
        </span>
      </label>
    `).join("")}
  </div>`;
}

function selectedFactRequirements(name) {
  const selected = new Set(checkedValues(name));
  return (currentOagOptions.fact_requirements || []).filter((item) => selected.has(item.value));
}

function selectedFactRequirementIdsForSkill(skill) {
  const explicit = Array.isArray(skill.supported_fact_requirements) ? skill.supported_fact_requirements : [];
  if (explicit.length) return explicit;
  const factTypes = new Set(skill.provides_fact_types || []);
  const attributes = new Set([...(skill.supported_attributes || []), ...(skill.output_attributes || [])]);
  const relations = new Set(skill.supported_relations || []);
  return (currentOagOptions.fact_requirements || [])
    .filter((fact) => {
      if (!factTypes.has(fact.fact_type)) return false;
      if (fact.attribute_name) return attributes.has(fact.attribute_name);
      if (fact.relation_type) return relations.has(fact.relation_type);
      return true;
    })
    .map((fact) => fact.value);
}

function deriveSkillCoverageFromFacts(facts, fallbackSubjectType = "Fund") {
  const factTypes = new Set();
  const subjectTypes = new Set([fallbackSubjectType].filter(Boolean));
  const attributes = new Set();
  const relations = new Set();
  facts.forEach((fact) => {
    if (fact.fact_type) factTypes.add(fact.fact_type);
    (fact.subject_types || []).forEach((type) => type && subjectTypes.add(type));
    if (fact.attribute_name) attributes.add(fact.attribute_name);
    if (fact.relation_type) relations.add(fact.relation_type);
  });
  return {
    provides_fact_types: [...factTypes],
    supported_subject_types: [...subjectTypes],
    supported_attributes: [...attributes],
    supported_relations: [...relations],
  };
}

async function openSemanticRelationEditor(item = {}) {
  if (!(await requestEditModeForAction("维护语义关系"))) return;
  await ensureOptions();
  const isNew = !item.edge_id;
  el("modalTitle").textContent = isNew ? "新增语义关系边" : "编辑语义关系边";
  el("modalBody").innerHTML = `
    <div class="wizard-panel">
      <label>起点节点<input id="relationSource" list="semanticNodeOptions" value="${escapeHtml(item.source || item.from || "")}"></label>
      <label>终点节点<input id="relationTarget" list="semanticNodeOptions" value="${escapeHtml(item.target || item.to || "")}"></label>
      <datalist id="semanticNodeOptions">${semanticNodeOptionsHtml()}</datalist>
      <label>关系类型<select id="relationType">${optionHtml(currentOagOptions.relation_types, item.relation_type)}</select></label>
      <label>适用任务<input id="relationTasks" value="${escapeHtml((item.applicable_tasks || []).join(", "))}" placeholder="analyze, compare"></label>
      <label>适用意图<input id="relationIntents" value="${escapeHtml((item.applicable_intents || []).join(", "))}" placeholder="performance_overview"></label>
      <label>默认优先级<select id="relationPriority"><option value="optional" ${item.default_priority !== "required" ? "selected" : ""}>辅助参考</option><option value="required" ${item.default_priority === "required" ? "selected" : ""}>必须查询</option></select></label>
      <label>规划角色<input id="relationPlanningRole" value="${escapeHtml(item.planning_role || item.expansion_role || "")}" placeholder="risk_context / peer_context"></label>
      <label>自动扩展模式<select id="relationAutoExpandMode">
        ${["contextual", "explicit_only", "dependency_only", "debug_only", "disabled", "always"].map((mode) => `<option value="${mode}" ${item.auto_expand_mode === mode ? "selected" : ""}>${mode}</option>`).join("")}
      </select></label>
      <label>答案可见性<select id="relationAnswerVisibility">
        ${["answer_fact", "supporting_context", "hidden_dependency", "debug_only"].map((visibility) => `<option value="${visibility}" ${(item.answer_visibility || "answer_fact") === visibility ? "selected" : ""}>${visibility}</option>`).join("")}
      </select></label>
      <label>扩展优先级<select id="relationExpansionPriority">
        ${["optional", "required", "supporting", "debug"].map((priority) => `<option value="${priority}" ${(item.expansion_priority || item.default_priority || "optional") === priority ? "selected" : ""}>${priority}</option>`).join("")}
      </select></label>
      <label>触发策略 JSON<textarea id="relationTriggerPolicy" rows="5">${escapeHtml(JSON.stringify(item.trigger_policy || {}, null, 2))}</textarea></label>
      <label>扩展限制 JSON<textarea id="relationExpansionLimits" rows="3">${escapeHtml(JSON.stringify(item.expansion_limits || {}, null, 2))}</textarea></label>
      <label>权重<input id="relationWeight" type="number" step="0.01" min="0" max="1" value="${escapeHtml(item.weight ?? item.score ?? "")}"></label>
      <label>中文原因<textarea id="relationReason" rows="3">${escapeHtml(item.reason_zh || "")}</textarea></label>
      <details><summary>原始数据</summary><textarea id="relationRawJson" rows="8">${escapeHtml(JSON.stringify(item, null, 2))}</textarea></details>
    </div>
  `;
  openModal(async () => {
    const raw = JSON.parse(el("relationRawJson").value || "{}");
    const source = el("relationSource").value.trim();
    const target = el("relationTarget").value.trim();
    const relationType = el("relationType").value.trim();
    const next = {
      ...raw,
      edge_id: item.edge_id || `${source}__${relationType}__${target}`,
      from: source,
      to: target,
      relation_type: relationType,
      applicable_tasks: splitCsv(el("relationTasks").value),
      applicable_intents: splitCsv(el("relationIntents").value),
      default_priority: el("relationPriority").value,
      planning_role: el("relationPlanningRole").value.trim(),
      expansion_role: el("relationPlanningRole").value.trim(),
      auto_expand_mode: el("relationAutoExpandMode").value,
      answer_visibility: el("relationAnswerVisibility").value,
      expansion_priority: el("relationExpansionPriority").value,
      trigger_policy: JSON.parse(el("relationTriggerPolicy").value || "{}"),
      expansion_limits: JSON.parse(el("relationExpansionLimits").value || "{}"),
      reason_zh: el("relationReason").value.trim(),
      weight: Number(el("relationWeight").value || raw.weight || raw.score || 0),
    };
    next.score = next.weight || raw.score || 0;
    await confirmPreviewAndSave(isNew ? "新增关系边" : "保存关系边", item, next, async () => {
      const url = isNew ? "/api/semantic-relations" : `/api/semantic-relations/${encodeURIComponent(item.edge_id)}`;
      const result = await api(url, {
        method: isNew ? "POST" : "PUT",
        body: JSON.stringify({ source, target, relation_type: relationType, properties: next }),
      });
      writeOutput(result);
      await refreshAll({ loadGraph: false });
      await renderSemanticRelationsDashboard();
    });
  });
}

async function confirmPreviewAndSave(title, oldValue, newValue, saveFn) {
  const diff = diffJson(oldValue || {}, newValue || {});
  const preview = {
    changed: diff.changed.map((row) => FIELD_LABELS[row.key] || row.key),
    added: diff.added.map((row) => FIELD_LABELS[row.key] || row.key),
    removed: diff.removed.map((row) => FIELD_LABELS[row.key] || row.key),
  };
  writeOutput({ title, preview, next: newValue });
  const message = `${title}\n\n变更字段：${preview.changed.join("、") || "无"}\n新增字段：${preview.added.join("、") || "无"}\n删除字段：${preview.removed.join("、") || "无"}\n\n是否确认写回 YAML？`;
  if (!confirm(message)) return;
  await saveFn();
}

function splitCsv(value) {
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function semanticNodeOptionsHtml() {
  return [
    ...(currentOptions.attributes || []),
    ...(currentOptions.object_types || []),
    ...(currentOptions.fact_types || []),
  ].map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label || item.id)}</option>`).join("");
}

function filterDiagnostics(type) {
  el("diagnosticFilter").value = type || "";
  renderDiagnostics();
}

async function selectTask(taskId) {
  const task = TASKS.find((item) => item.id === taskId);
  if (!task) return;
  state.activeTaskId = task.id;
  setTaskChromeMode();
  state.viewMode = task.viewMode;
  state.focusId = "";
  state.query = "";
  state.depth = 2;
  state.includeFields = Boolean(task.includeFields);
  state.includeInferred = task.includeInferred !== false;
  state.relationFilter = "";
  state.expandedGroups.clear();
  setDefaultLayoutForView();
  clearSelection();
  renderTaskCards();
  renderTaskActionPanel();
  syncControls();
  renderEmptyInspector();
  if (task.dashboard === "oag_plan") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    renderTaskCandidates();
    renderDashboardLoading("正在进入 OAG 规划调试", "正在准备语义输入选项，稍后即可填写或选择示例。");
    updateCounts();
    setGraphLoading(true, "正在进入 OAG 规划调试", "正在加载任务类型、意图、属性和事实类型选项...");
    try {
      await ensureOagOptions();
    } finally {
      setGraphLoading(false);
    }
    renderOagPlanningDashboard();
    updateCounts();
    return;
  }
  if (!currentOptions.object_types?.length || !currentOagOptions.task_types?.length) {
    renderDashboardLoading(`正在进入${task.title}`, "正在读取本体选项和诊断信息...");
    setGraphLoading(true, `正在进入${task.title}`, "正在读取 ontology YAML 和工作台选项...");
    try {
      await loadOptions();
    } finally {
      setGraphLoading(false);
    }
  }
  renderTaskCandidates();
  if (task.dashboard === "intent_templates") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    await renderIntentTemplatesDashboard();
    updateCounts();
    return;
  }
  if (task.dashboard === "semantic_relations") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    await renderSemanticRelationsDashboard();
    updateCounts();
    return;
  }
  if (task.dashboard === "skill_coverage") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    await renderSkillCoverageDashboard();
    updateCounts();
    return;
  }
  if (task.dashboard === "yaml_files") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    renderYamlFilesDashboard();
    updateCounts();
    return;
  }
  if (task.dashboard === "diagnostic") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    renderDiagnosticDashboard();
    renderDiagnostics();
    updateCounts();
    return;
  }
  if (task.dashboard === "table_mapping") {
    cy.elements().remove();
    currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
    renderMappingDashboard();
    updateCounts();
    return;
  }
  await loadGraphView({ keepDashboard: false });
}

function renderTaskCandidates() {
  const task = TASKS.find((item) => item.id === state.activeTaskId);
  const box = el("taskCandidates");
  const title = el("taskSearchTitle");
  if (!task) {
    title.textContent = "任务候选节点";
    box.innerHTML = `<div class="muted">先选择一个建模任务</div>`;
    return;
  }
  title.textContent = `${task.title}候选节点`;
  if (task.id === "oag_plan") {
    title.textContent = "OAG 调试流程";
    box.innerHTML = `
      <div class="oag-sidebar-flow">
        <div class="oag-flow-step active"><strong>1 输入任务</strong><span>选择场景或填写语义框架</span></div>
        <div class="oag-flow-step"><strong>2 生成规划</strong><span>计算事实需求和 Skill 覆盖</span></div>
        <div class="oag-flow-step"><strong>3 查看执行</strong><span>确认参数缺口和可调用 Skill</span></div>
      </div>
      <div class="oag-sidebar-examples">
        <h3>常用场景</h3>
        ${oagExampleNames().map((name) => `<button data-oag-side-example="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join("")}
      </div>
    `;
    bindOagSidebarActions();
    return;
  }
  if (task.id === "diagnostic") {
    const items = (currentDiagnostics.items || []).slice(0, 80);
    box.innerHTML = items.length
      ? items.map((item) => `
          <button data-diagnostic-node="${escapeHtml(item.node_id || "")}">
            <strong>${escapeHtml(item.type)} / ${escapeHtml(item.severity)}</strong>
            <span>${escapeHtml(item.node_id || "-")}</span>
            <em>${escapeHtml(item.suggested_action || "")}</em>
          </button>
        `).join("")
      : `<div class="muted">当前没有诊断检查项</div>`;
    document.querySelectorAll("#taskCandidates [data-diagnostic-node]").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.diagnosticNode) jumpToNode(button.dataset.diagnosticNode);
      });
    });
    return;
  }
  if (task.id === "table_mapping") {
    const query = el("taskSearchInput").value.trim().toLowerCase();
    const rows = (currentMappingMatrix.rows || [])
      .filter((row) => !query || `${row.attribute_name} ${row.attribute_label} ${(row.object_types || []).join(" ")}`.toLowerCase().includes(query))
      .slice(0, 120);
    box.innerHTML = rows.length
      ? rows.map((row) => `
          <button data-map-candidate="${escapeHtml(row.attribute_id)}">
            <strong>${escapeHtml(row.attribute_label || row.attribute_name)}</strong>
            <span>${escapeHtml((row.object_types || []).join(", ") || "-")} · ${row.field_count} 个字段</span>
            <em>${escapeHtml(row.status)}</em>
          </button>
        `).join("")
      : `<div class="muted">没有匹配的属性映射</div>`;
    document.querySelectorAll("#taskCandidates [data-map-candidate]").forEach((button) => {
      button.addEventListener("click", () => guarded(() => focusMappingAttribute(button.dataset.mapCandidate)));
    });
    return;
  }
  const query = el("taskSearchInput").value.trim().toLowerCase();
  const options = task.recommendedTypes.flatMap((type) => optionsForType(type));
  const filtered = options
    .filter((item) => !query || `${item.id} ${item.label} ${item.value}`.toLowerCase().includes(query))
    .slice(0, 120);
  if (!filtered.length) {
    box.innerHTML = `<div class="muted">没有候选节点</div>`;
    return;
  }
  box.innerHTML = "";
  filtered.forEach((item) => {
    const button = document.createElement("button");
    button.innerHTML = `
      <strong>${escapeHtml(item.label || item.value)}</strong>
      <span>${escapeHtml(item.type)} · ${escapeHtml(item.id)}</span>
      <em>${escapeHtml(task.viewMode)} / focus 2 跳</em>
    `;
    button.addEventListener("click", () => guarded(() => enterTaskFocus(task, item.id)));
    box.appendChild(button);
  });
}

function oagExampleNames() {
  return [
    "分析某基金近一年表现",
    "查询某基金最大回撤和夏普",
    "查询某基金经理",
    "查询某基金公司",
    "查询某基金业绩基准",
    "比较两只基金收益",
    "推荐收益高、回撤低的基金",
    "筛选最大回撤低于10%的基金",
    "查询同类排名",
    "查询费率",
    "查询分红",
    "查询持仓配置",
  ];
}

function bindOagSidebarActions() {
  document.querySelectorAll("[data-oag-side-example]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!el("oagRawQuestion")) return;
      fillOagExample(button.dataset.oagSideExample);
      document.querySelectorAll("[data-oag-side-example]").forEach((item) => item.classList.toggle("active", item === button));
    });
  });
}

async function enterTaskFocus(task, nodeId) {
  state.viewMode = task.viewMode;
  state.focusId = nodeId;
  state.depth = 2;
  state.includeFields = task.dashboard === "table_mapping";
  state.includeInferred = task.includeInferred !== false;
  state.query = "";
  if (task.dashboard === "table_mapping") state.viewMode = "table_mapping";
  setDefaultLayoutForView();
  syncControls();
  await loadGraphView();
}

function optionsForType(type) {
  const map = {
    ObjectType: currentOptions.object_types || [],
    Attribute: currentOptions.attributes || [],
    SkillCapability: currentOptions.skills || [],
    QueryCapability: currentOptions.queries || [],
    RelationType: currentOptions.relation_types || [],
    FactType: currentOptions.fact_types || [],
    DataTable: currentOptions.data_tables || [],
  };
  return map[type] || [];
}

async function loadGraphView({ keepDashboard = false } = {}) {
  const params = new URLSearchParams({
    view_mode: state.viewMode,
    depth: String(state.depth),
    include_fields: String(state.includeFields),
    include_inferred: String(state.includeInferred),
    aggregate_edges: String(state.aggregateEdges),
  });
  if (state.query) params.set("q", state.query);
  if (state.focusId) params.set("focus_id", state.focusId);
  setGraphLoading(true, "正在加载图谱", "正在读取 ontology YAML 并计算节点关系...");
  try {
    currentGraph = await api(`/api/graph?${params.toString()}`);
    if (!keepDashboard) el("workbenchHome").classList.add("hidden");
    renderGraph();
    renderSearchResults(currentGraph.search_results || []);
    updateCounts();
    updateRelationSummary();
    writeOutput({ summary: currentGraph.summary, search_results: currentGraph.search_results, hidden_counts: currentGraph.hidden_counts });
    if (state.focusId) centerNode(state.focusId);
  } finally {
    setGraphLoading(false);
  }
}

function setGraphLoading(loading, title = "正在加载图谱", text = "请稍候...") {
  state.loadingGraph = loading;
  const panel = el("graphLoading");
  if (panel) panel.hidden = !loading;
  if (el("graphLoadingTitle")) el("graphLoadingTitle").textContent = title;
  if (el("graphLoadingText")) el("graphLoadingText").textContent = text;
  if (loading) el("canvasStatus").textContent = text;
}

function renderGraph() {
  selected = null;
  clearDirty({ keepEditor: false });
  cy.elements().remove();
  const elements = prepareGraphElements(currentGraph);
  cy.add([...elements.nodes, ...elements.edges]);
  renderNodeTypeLegend();
  applyNodeTypeFilter();
  applyEdgeLabelMode();
  applyLargeGraphLabelMode();
  applyRelationFilter();
  runLayout();
  renderEmptyInspector();
}

function prepareGraphElements(graph) {
  let nodes = (graph.nodes || []).map((node) => ({ data: decorateNodeData(node.data) }));
  let edges = (graph.edges || []).map((edge) => ({ data: normalizeEdgeData(edge.data) }));
  if (graph.kind !== "task_graph" && state.enableGroups && !state.focusId && ["overview", "requirement"].includes(state.viewMode)) {
    const grouped = applyVirtualGroups(nodes, edges);
    nodes = grouped.nodes;
    edges = grouped.edges;
  }
  const nodeIds = new Set(nodes.map((node) => node.data.id));
  edges = edges.filter((edge) => nodeIds.has(edge.data.source) && nodeIds.has(edge.data.target));
  return { nodes, edges };
}

function decorateNodeData(data) {
  const short = data.short_label || shortLabel(data.label || data.identity || data.id);
  const badge = nodeBadge(data);
  return { ...data, card_label: `${short}\n${badge}`, bundle_count: data.bundle_count || 1 };
}

function normalizeEdgeData(data) {
  return { ...data, bundle_count: data.bundle_count || 1, label: data.label || relationTypeLabel(data.type) || "" };
}

function nodeBadge(data) {
  if (data.type === "Group") return data.group_badge || "分组";
  const parts = [NODE_TYPE_LABELS[data.type] || TYPE_BADGES[data.type] || data.type || "节点"];
  if (data.enabled === false) parts.push("停用");
  if (data.type === "DataTable" && data.field_count) parts.push(`${data.field_count} 个字段`);
  return parts.join(" / ");
}

function applyVirtualGroups(nodes, edges) {
  const expanded = state.expandedGroups;
  const replacements = new Map();
  const groupNodes = new Map();
  nodes.forEach((node) => {
    const type = node.data.type;
    if (!["Attribute", "SkillCapability"].includes(type)) return;
    const groupId = groupIdForNode(node.data);
    if (!groupId || expanded.has(groupId)) return;
    replacements.set(node.data.id, groupId);
    if (!groupNodes.has(groupId)) {
      const label = groupId.split(":").slice(-1)[0];
      groupNodes.set(groupId, {
        data: decorateNodeData({
          id: groupId,
          label,
          short_label: shortLabel(label, 22),
          type: "Group",
          degree: 1,
          group_badge: type === "Attribute" ? "属性分组" : "Skill 分组",
        }),
      });
    }
  });
  if (!replacements.size) return { nodes, edges };

  const keptNodes = nodes.filter((node) => !replacements.has(node.data.id));
  const groupedEdges = new Map();
  edges.forEach((edge) => {
    const source = replacements.get(edge.data.source) || edge.data.source;
    const target = replacements.get(edge.data.target) || edge.data.target;
    if (source === target) return;
    const key = `${source}|${target}|${edge.data.type}`;
    const existing = groupedEdges.get(key);
    if (existing) {
      existing.data.bundle_count += edge.data.bundle_count || 1;
      existing.data.label = `${relationTypeLabel(edge.data.type)} × ${existing.data.bundle_count}`;
      existing.data.is_bundle = true;
      existing.data.bundled_edges = [...(existing.data.bundled_edges || []), edge.data];
    } else {
      groupedEdges.set(key, {
        data: {
          ...edge.data,
          id: `group-edge:${hashString(key)}`,
          source,
          target,
          bundle_count: edge.data.bundle_count || 1,
          bundled_edges: [edge.data],
        },
      });
    }
  });
  return { nodes: [...keptNodes, ...groupNodes.values()], edges: [...groupedEdges.values()] };
}

function groupIdForNode(data) {
  if (data.type === "Attribute") {
    const raw = data.raw || {};
    const group = raw.attribute_group || raw.metric_group || raw.category || (Array.isArray(raw.object_types) ? raw.object_types[0] : "general");
    return `Group:Attribute:${group || "general"}`;
  }
  if (data.type === "SkillCapability") {
    const raw = data.raw || {};
    const group = data.enabled === false ? "disabled_skills" : raw.skill_group || raw.skill_type || (raw.provides_fact_types ? "fact_provider_skills" : "analysis_skills");
    return `Group:Skill:${group || "analysis_skills"}`;
  }
  return "";
}

function toggleGroup(groupId) {
  if (state.expandedGroups.has(groupId)) state.expandedGroups.delete(groupId);
  else state.expandedGroups.add(groupId);
  renderGraph();
}

function runLayout() {
  if (currentGraph.kind === "task_graph") {
    runTaskGraphLayout();
    return;
  }
  const name = el("layoutSelect").value;
  if (name === "semantic") {
    runSemanticLayout();
    return;
  }
  const options = {
    name,
    animate: false,
    fit: true,
    padding: 48,
    eles: cy.elements().not(".hidden-by-type"),
    nodeDimensionsIncludeLabels: true,
  };
  if (!options.eles.length) return;
  if (name === "breadthfirst") Object.assign(options, { directed: true, spacingFactor: 1.45, avoidOverlap: true });
  if (name === "concentric") Object.assign(options, { minNodeSpacing: 72, concentric: (node) => node.degree(), avoidOverlap: true });
  if (name === "cose") {
    Object.assign(options, {
      idealEdgeLength: state.viewMode === "skill" ? 190 : 170,
      nodeOverlap: state.viewMode === "skill" ? 34 : 40,
      nodeRepulsion: () => (state.viewMode === "skill" ? 760000 : 520000),
      refresh: 20,
      componentSpacing: state.viewMode === "skill" ? 120 : 160,
      gravity: state.viewMode === "skill" ? 0.2 : 0.18,
      randomize: true,
    });
    if (state.viewMode === "skill") {
      Object.assign(options, { idealEdgeLength: 200, numIter: 2200, initialTemp: 320 });
    }
  }
  options.stop = () => {
    separateOverlappingNodes(options.eles.nodes());
    cy.fit(options.eles, 56);
  };
  cy.layout(options).run();
}

function runTaskGraphLayout() {
  const eles = cy.elements().not(".hidden-by-type");
  if (!eles.length) return;
  const columns = new Map();
  const columnOf = (node) => {
    const type = node.data("type");
    if (["SemanticFrame"].includes(type)) return 0;
    if (["TaskType", "IntentProfile"].includes(type)) return 1;
    if (["TargetInstance", "ObjectType", "Constraint"].includes(type)) return 2;
    if (["FactRequirement"].includes(type)) return 3;
    if (["Attribute"].includes(type)) return 4;
    if (["SkillCapability", "Parameter"].includes(type)) return 5;
    return 3;
  };
  eles.nodes().forEach((node) => {
    const column = columnOf(node);
    if (!columns.has(column)) columns.set(column, []);
    columns.get(column).push(node);
  });
  const positions = {};
  [...columns.entries()].forEach(([column, nodes]) => {
    nodes.sort((a, b) => {
      const typeRank = String(a.data("type")).localeCompare(String(b.data("type")));
      return typeRank || String(a.data("label")).localeCompare(String(b.data("label")));
    });
    const spacing = nodes.length > 8 ? 58 : 72;
    const total = (nodes.length - 1) * spacing;
    nodes.forEach((node, index) => {
      positions[node.id()] = { x: column * 132, y: index * spacing - total / 2 };
    });
  });
  cy.layout({ name: "preset", positions, animate: false, fit: false }).run();
  cy.fit(eles, 72);
  const readableZoom = Math.min(0.78, Math.max(cy.zoom(), 0.56));
  cy.zoom({
    level: readableZoom,
    renderedPosition: { x: Math.max(220, (cy.width() - 160) / 2), y: cy.height() / 2 },
  });
  cy.panBy({ x: 16, y: 8 });
}

function separateOverlappingNodes(nodes) {
  const visibleNodes = nodes.filter((node) => node.visible());
  const count = visibleNodes.length;
  if (count < 2 || count > 420) return;
  const padding = state.viewMode === "skill" ? 18 : 14;
  const iterations = count > 260 ? 36 : 68;
  for (let pass = 0; pass < iterations; pass += 1) {
    let moved = false;
    for (let i = 0; i < count; i += 1) {
      const a = visibleNodes[i];
      const ap = a.position();
      const aw = a.width() + padding;
      const ah = a.height() + padding;
      for (let j = i + 1; j < count; j += 1) {
        const b = visibleNodes[j];
        const bp = b.position();
        const bw = b.width() + padding;
        const bh = b.height() + padding;
        const dx = bp.x - ap.x || 0.01;
        const dy = bp.y - ap.y || 0.01;
        const overlapX = (aw + bw) / 2 - Math.abs(dx);
        const overlapY = (ah + bh) / 2 - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        const pushX = Math.sign(dx) * Math.min(overlapX / 2 + 1, 18);
        const pushY = Math.sign(dy) * Math.min(overlapY / 2 + 1, 18);
        if (overlapX < overlapY) {
          a.position("x", ap.x - pushX);
          b.position("x", bp.x + pushX);
        } else {
          a.position("y", ap.y - pushY);
          b.position("y", bp.y + pushY);
        }
        moved = true;
      }
    }
    if (!moved) break;
  }
}

function runSemanticLayout() {
  const ranks = SEMANTIC_RANKS[state.viewMode] || SEMANTIC_RANKS.requirement;
  const rankOf = (node) => {
    if (node.data("type") === "Group") return ranks.indexOf(node.id().includes(":Skill:") ? "SkillCapability" : "Attribute");
    const rank = ranks.indexOf(node.data("type"));
    return rank >= 0 ? rank : ranks.length;
  };
  const layers = new Map();
  cy.nodes().forEach((node) => {
    const rank = rankOf(node);
    if (!layers.has(rank)) layers.set(rank, []);
    layers.get(rank).push(node);
  });
  const positions = {};
  [...layers.entries()].forEach(([rank, layer]) => {
    layer.sort((a, b) => b.degree() - a.degree() || String(a.data("label")).localeCompare(String(b.data("label"))));
    const spacing = layer.length > 24 ? 72 : 92;
    const total = (layer.length - 1) * spacing;
    layer.forEach((node, index) => {
      positions[node.id()] = { x: rank * 260, y: index * spacing - total / 2 };
    });
  });
  cy.layout({ name: "preset", positions, animate: false, fit: true, padding: 64 }).run();
}

async function selectElement(ele) {
  const decision = await confirmDirtyIfNeeded();
  if (decision === "cancel") return;
  selected = ele;
  clearHighlight();
  if (ele.isNode()) {
    state.selectedNodeId = ele.id();
    ele.addClass("selected-node");
    const oneHop = ele.closedNeighborhood();
    ele.neighborhood().nodes().addClass("neighbor-node");
    ele.connectedEdges().addClass("neighbor-edge");
    cy.elements().difference(oneHop).addClass("faded");
    showNodeInspector(ele);
    updateSelectedRelationSummary(ele.id());
  } else {
    ele.addClass("neighbor-edge show-label");
    ele.connectedNodes().addClass("neighbor-node");
    cy.elements().difference(ele.union(ele.connectedNodes())).addClass("faded");
    showEdgeInspector(ele);
    updateSelectedRelationSummary(null);
  }
}

function clearSelection() {
  clearHighlight();
  selected = null;
  state.selectedNodeId = "";
  clearDirty({ keepEditor: false });
  updateSelectedRelationSummary(null);
  if (currentGraph.kind === "task_graph" && currentPlan) {
    showOagPlanInspector(currentPlan);
  } else {
    renderEmptyInspector();
  }
}

function clearHighlight() {
  cy.elements().removeClass("selected-node neighbor-node neighbor-edge faded show-label path-highlight");
  applyRelationFilter();
}

function centerNode(nodeId) {
  const node = cy.getElementById(nodeId);
  if (node.length) {
    selectElement(node);
    cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 0.85) }, { duration: 220 });
  }
}

async function focusOnNode(nodeId, depth = 2) {
  const decision = await confirmDirtyIfNeeded();
  if (decision === "cancel") return;
  state.focusId = nodeId;
  state.depth = depth;
  syncControls();
  await loadGraphView();
}

async function expandFields(nodeId) {
  state.focusId = nodeId;
  state.includeFields = true;
  syncControls();
  await loadGraphView();
}

async function viewTableMapping(nodeId) {
  state.viewMode = "table_mapping";
  state.focusId = nodeId;
  state.includeFields = true;
  state.includeInferred = true;
  setDefaultLayoutForView();
  syncControls();
  await loadGraphView();
}

function showNodeInspector(node) {
  const data = node.data();
  el("inspectorTitle").textContent = data.id;
  el("inspectorMeta").textContent = `${NODE_TYPE_LABELS[data.type] || data.type} / 关联数 ${data.degree || 0}${data.field_count ? ` / ${data.field_count} 个字段` : ""}`;
  renderBasicInfo(data);
  setRaw(data.raw || {});
  setOriginalRaw(data.id, data.raw || {}, data.source_file || "");
  buildQuickForm(data.type, data.raw || {});
  renderInspectorActions(data);
  showRelatedEdges(data.id);
  showFieldList(data);
  loadNodeImpact(data.id);
  setInspectorTab("overview");
  updateEditModeUi();
}

function showEdgeInspector(edge) {
  const data = edge.data();
  const raw = {
    edge_id: data.raw?.edge_id || data.id,
    source: data.source,
    target: data.target,
    relation_type: data.type,
    ...(data.raw || {}),
    properties: edgeProperties(data.raw || {}),
  };
  el("inspectorTitle").textContent = data.id;
  el("inspectorMeta").textContent = `${data.origin === "explicit" ? "显式关系" : "推断关系"} / ${data.source} -> ${data.target}`;
  renderBasicInfo({
    id: data.id,
    type: data.is_bundle ? "BundleEdge" : "Edge",
    label: data.label,
    enabled: true,
    source_file: data.origin === "explicit" ? "schema_graph_edges.yaml" : data.raw?.from_file || data.origin || "inferred",
  });
  setRaw(raw);
  setOriginalRaw(data.id, raw, data.origin === "explicit" ? "schema_graph_edges.yaml" : "");
  buildQuickForm("Edge", raw);
  renderInspectorActions(null);
  showRelatedEdges(null);
  renderEdgeImpact(data);
  el("fieldList").innerHTML = "";
  setInspectorTab("relations");
  updateEditModeUi();
}

function renderEmptyInspector() {
  el("inspectorTitle").textContent = "未选择";
  el("inspectorMeta").textContent = "";
  el("contextActions").innerHTML = "";
  el("basicInfo").innerHTML = `<div class="muted">点击节点或边查看详情</div>`;
  el("quickForm").innerHTML = "";
  el("relatedEdges").innerHTML = "";
  el("impactPanel").innerHTML = `<div class="muted">未选择节点</div>`;
  el("pathPanel").innerHTML = "";
  el("fieldList").innerHTML = "";
  setRaw({});
  updateEditModeUi();
}

function renderBasicInfo(data) {
  const raw = data.raw || {};
  const name = data.label || raw.skill_name || raw.object_type_zh || raw.attribute_name_zh || raw.query_name || raw.intent_name || data.id;
  const rows = [
    ["节点 ID", data.id],
    ["节点类型", NODE_TYPE_LABELS[data.type] || data.type],
    ["名称", name],
    ["启用状态", data.enabled === false ? "停用" : "启用"],
    ["来源 YAML", data.source_file || raw.from_file || "-"],
  ];
  el("basicInfo").innerHTML = rows.map(([key, value]) => `<div>${escapeHtml(key)}</div><strong>${escapeHtml(value)}</strong>`).join("");
}

function renderInspectorActions(data) {
  const box = el("contextActions");
  if (!data) {
    box.innerHTML = "";
    return;
  }
  const buttons = [
    `<button id="focusOneHopBtn">聚焦 1 跳</button>`,
    `<button id="focusTwoHopBtn">聚焦 2 跳</button>`,
    `<button id="pathSkillBtn">到 Skill 路径</button>`,
    `<button id="pathTableBtn">到数据表路径</button>`,
    `<button id="pathIntentBtn">到 Intent 路径</button>`,
    `<button id="drawEdgeBtn" data-edit-only>创建关系</button>`,
  ];
  if (data.type === "ObjectType") {
    buttons.push(`<button id="newAttrBtn" data-edit-only>新增属性</button>`);
    buttons.push(`<button id="newSkillBtn" data-edit-only>新增 Skill</button>`);
  }
  if (data.type === "Attribute") {
    buttons.push(`<button id="linkSkillBtn" data-edit-only>关联 Skill</button>`);
    buttons.push(`<button id="linkFieldBtn" data-edit-only>关联表字段</button>`);
  }
  if (data.type === "SkillCapability") {
    buttons.push(`<button id="toggleSkillBtn" data-edit-only>${data.enabled === false ? "启用" : "禁用"}</button>`);
    buttons.push(`<button id="copySkillBtn" data-edit-only>复制 Skill 模板</button>`);
  }
  if (data.type === "DataTable") buttons.push(`<button id="expandFieldsBtn">展开字段</button>`);
  buttons.push(`<button id="tableMappingBtnLocal">表字段映射</button>`);
  box.innerHTML = buttons.join("");
  el("focusOneHopBtn").addEventListener("click", () => focusOnNode(data.id, 1));
  el("focusTwoHopBtn").addEventListener("click", () => focusOnNode(data.id, 2));
  el("pathSkillBtn").addEventListener("click", () => showPathsToType(data.id, "SkillCapability"));
  el("pathTableBtn").addEventListener("click", () => showPathsToType(data.id, "DataTable"));
  el("pathIntentBtn").addEventListener("click", () => showPathsToType(data.id, "IntentProfile"));
  el("drawEdgeBtn")?.addEventListener("click", () => startEdgeCreation(data.id));
  el("tableMappingBtnLocal").addEventListener("click", () => viewTableMapping(data.id));
  el("newAttrBtn")?.addEventListener("click", () => openAddNodeDialog("Attribute", { object_types: [data.identity] }));
  el("newSkillBtn")?.addEventListener("click", () => openSkillCoverageEditor({ target_object_type: data.identity }));
  el("linkSkillBtn")?.addEventListener("click", () => openEdgeDialog({ target: data.id, relation_type: "supports_attribute" }));
  el("linkFieldBtn")?.addEventListener("click", () => openEdgeDialog({ source: data.id, relation_type: "maps_to_field" }));
  el("toggleSkillBtn")?.addEventListener("click", () => toggleSelectedSkillEnabled());
  el("copySkillBtn")?.addEventListener("click", () => openSkillCoverageEditor({ ...(data.raw || {}), skill_id: `${data.identity}_copy`, skill_name: `${data.label || data.identity} copy` }));
  el("expandFieldsBtn")?.addEventListener("click", () => expandFields(data.id));
  updateEditModeUi();
}

function buildQuickForm(type, raw) {
  const fields = QUICK_FIELDS[type] || Object.keys(raw);
  const box = el("quickForm");
  box.innerHTML = "";
  fields.forEach((field) => {
    const label = document.createElement("label");
    label.textContent = fieldLabel(field);
    let input;
    if (typeof raw[field] === "boolean") {
      input = document.createElement("select");
      input.innerHTML = `<option value="true">启用</option><option value="false">停用</option>`;
      input.value = String(raw[field]);
    } else {
      input = document.createElement(field === "description" || typeof raw[field] === "object" ? "textarea" : "input");
      input.value = formatFormValue(raw[field]);
    }
    input.dataset.field = field;
    input.addEventListener("input", markDirtyFromInspector);
    input.addEventListener("change", markDirtyFromInspector);
    box.append(label, input);
  });
}

function showRelatedEdges(nodeId) {
  const box = el("relatedEdges");
  if (!nodeId) {
    const data = selected?.data?.() || {};
    if (data.is_bundle && Array.isArray(data.bundled_edges)) {
      box.innerHTML = data.bundled_edges
        .map((edge) => `<div class="related-edge"><div><strong>${escapeHtml(edge.label || edge.type)}</strong><span>${escapeHtml(edge.source)} -> ${escapeHtml(edge.target)}</span><em>${escapeHtml(edge.origin || "")}</em></div></div>`)
        .join("");
    } else {
      box.innerHTML = "";
    }
    return;
  }
  const edges = cy
    .edges()
    .filter((edge) => edge.data("source") === nodeId || edge.data("target") === nodeId)
    .sort((a, b) => String(a.data("type")).localeCompare(String(b.data("type"))))
    .slice(0, 120);
  box.innerHTML = "";
  if (!edges.length) {
    box.innerHTML = `<div class="muted">当前子图没有关联边</div>`;
    return;
  }
  edges.forEach((edge) => {
    const data = edge.data();
    const otherId = data.source === nodeId ? data.target : data.source;
    const item = document.createElement("div");
    item.className = "related-edge";
    item.innerHTML = `
      <div>
        <strong>${escapeHtml(data.label || data.type)}</strong>
        <span>${escapeHtml(data.source)} -> ${escapeHtml(data.target)}</span>
        <em>${escapeHtml(data.type)} / ${escapeHtml(data.origin || "explicit")}</em>
      </div>
      <button data-action="edit">查看</button>
      <button data-action="same" data-edit-only>同类</button>
      <button data-action="delete" ${data.origin === "explicit" ? "" : "disabled"} data-edit-only>删除</button>
      <button data-action="jump">跳转</button>
    `;
    item.querySelector('[data-action="edit"]').addEventListener("click", () => selectElement(edge));
    item.querySelector('[data-action="same"]').addEventListener("click", () => openEdgeDialog({ source: data.source, relation_type: data.type }));
    item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteEdge(edge));
    item.querySelector('[data-action="jump"]').addEventListener("click", () => jumpToNode(otherId));
    box.appendChild(item);
  });
  updateEditModeUi();
}

function showFieldList(data) {
  const box = el("fieldList");
  box.innerHTML = "";
  if (data.type !== "DataTable") return;
  const fields = Array.isArray(data.raw?.fields) ? data.raw.fields : [];
  if (!fields.length) return;
  const title = document.createElement("h3");
  title.textContent = `字段列表 (${fields.length})`;
  box.appendChild(title);
  fields.slice(0, 120).forEach((field) => {
    const item = document.createElement("button");
    const fieldName = field.field_name || "";
    item.textContent = `${fieldName}${field.field_name_zh ? ` / ${field.field_name_zh}` : ""}`;
    item.addEventListener("click", () => jumpToNode(`DataField:${data.identity}.${fieldName}`));
    box.appendChild(item);
  });
}

async function loadNodeImpact(nodeId) {
  el("impactPanel").innerHTML = `<div class="muted">加载中...</div>`;
  try {
    const context = await api(`/api/node-context/${encodeURIComponent(nodeId)}?include_inferred=true`);
    renderNodeImpact(context);
  } catch (error) {
    el("impactPanel").innerHTML = `<div class="muted">${escapeHtml(error.message)}</div>`;
  }
}

function renderNodeImpact(context) {
  const cards = [
    ["上游节点数量", context.incoming?.length || 0],
    ["下游节点数量", context.outgoing?.length || 0],
    ["被 Intent 使用", listLabels(context.used_by_intents)],
    ["被 Skill 使用", listLabels(context.used_by_skills)],
    ["关联属性", listLabels(context.related_attributes)],
    ["关联查询能力", listLabels(context.related_queries)],
    ["关联数据表", listLabels(context.related_tables)],
    ["删除影响显式边", context.explicit_edge_count || 0],
    ["修改主键影响引用", (context.primary_key_reference_hint || []).join("; ") || "-"],
  ];
  el("impactPanel").innerHTML = cards.map(([title, value]) => `<div class="impact-card"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(value)}</span></div>`).join("");
}

function renderEdgeImpact(data) {
  const bundle = data.is_bundle ? `<div class="impact-card"><strong>聚合关系数量</strong><span>${data.bundle_count || 0}</span></div>` : "";
  el("impactPanel").innerHTML = `
    <div class="impact-card"><strong>起点节点</strong><span>${escapeHtml(data.source)}</span></div>
    <div class="impact-card"><strong>终点节点</strong><span>${escapeHtml(data.target)}</span></div>
    <div class="impact-card"><strong>关系类型</strong><span>${escapeHtml(data.type)}</span></div>
    ${bundle}
  `;
}

function listLabels(items) {
  return (items || []).map((item) => item.label || item.id).join(", ") || "-";
}

async function jumpToNode(nodeId) {
  const decision = await confirmDirtyIfNeeded();
  if (decision === "cancel") return;
  const resolvedNodeId = resolveNodeId(nodeId);
  if (!resolvedNodeId) {
    writeOutput({ error: "无法定位节点", node_id: nodeId });
    return;
  }
  const node = cy.getElementById(resolvedNodeId);
  if (node.length) {
    centerNode(resolvedNodeId);
    return;
  }
  const nodeType = resolvedNodeId.split(":", 1)[0];
  if (["RelationType", "DataSource", "PeriodVariant", "InstanceRule", "Parameter"].includes(nodeType)) {
    state.viewMode = "full";
  } else if (nodeType === "DataField") {
    state.viewMode = "table_mapping";
    state.includeFields = true;
  } else if (nodeType === "Attribute") {
    state.viewMode = "object_attribute";
  } else if (nodeType === "SkillCapability") {
    state.viewMode = "skill";
  } else if (nodeType === "IntentProfile") {
    state.viewMode = "requirement";
  } else if (nodeType === "DataTable") {
    state.viewMode = "table_mapping";
  }
  state.focusId = resolvedNodeId;
  state.depth = 2;
  state.includeInferred = true;
  setDefaultLayoutForView();
  syncControls();
  await loadGraphView();
  if (!cy.getElementById(resolvedNodeId).length) {
    writeOutput({ warning: "已请求定位，但当前图谱范围没有返回该节点", node_id: resolvedNodeId, view_mode: state.viewMode });
  }
}

function resolveNodeId(value) {
  const nodeId = String(value || "").trim();
  if (!nodeId) return "";
  if (nodeId.includes(":")) return nodeId;
  const pools = [
    currentOptions.object_types,
    currentOptions.attributes,
    currentOptions.skills,
    currentOptions.queries,
    currentOptions.relation_types,
    currentOptions.data_tables,
  ];
  for (const pool of pools) {
    const item = (pool || []).find((option) => option.value === nodeId || option.id === nodeId);
    if (item?.id) return item.id;
  }
  return nodeId;
}

async function saveSelected() {
  if (!selected) return;
  if (!state.editMode) {
    writeOutput({ error: "当前是浏览模式。请先进入编辑模式。" });
    return;
  }
  let raw;
  try {
    raw = readInspectorPayload();
  } catch (error) {
    writeOutput({ error: error.message });
    return;
  }
  const diff = diffJson(state.originalRaw || {}, raw);
  const decision = await openDiffModal(diff);
  if (decision === "cancel") return;
  if (decision === "discard") {
    clearDirty({ keepEditor: false });
    if (selected?.isNode()) showNodeInspector(selected);
    else if (selected?.isEdge()) showEdgeInspector(selected);
    return;
  }
  await performSave(raw);
}

async function performSave(raw) {
  try {
    let result;
    if (selected.isEdge()) {
      result = await api("/api/graph/edge", {
        method: "POST",
        body: JSON.stringify({
          edge_id: raw.edge_id,
          source: raw.source || raw.from,
          target: raw.target || raw.to,
          relation_type: raw.relation_type,
          properties: edgeProperties(raw),
        }),
      });
    } else {
      result = await api("/api/graph/node", {
        method: "POST",
        body: JSON.stringify({
          node_type: selected.data("type"),
          node_id: selected.id(),
          data: raw,
        }),
      });
      state.focusId = selected.id();
    }
    el("lastSaved").textContent = `最近保存：${new Date().toLocaleString()}`;
    clearDirty({ keepEditor: true });
    writeOutput(result);
    await Promise.all([loadFiles(), loadOptions(), loadDiagnostics()]);
    await loadGraphView();
  } catch (error) {
    markDirty();
    writeOutput({ error: error.message, detail: error.detail });
  }
}

async function deleteSelected() {
  if (!selected) return;
  if (!state.editMode) {
    writeOutput({ error: "当前是浏览模式。请先进入编辑模式。" });
    return;
  }
  if (selected.isEdge()) {
    await deleteEdge(selected);
    return;
  }
  const id = selected.id();
  if (!confirm(`确认删除 ${id} ?`)) return;
  try {
    const result = await api(`/api/graph/node/${encodeURIComponent(id)}`, { method: "DELETE" });
    writeOutput(result);
    selected = null;
    state.focusId = "";
    state.selectedNodeId = "";
    clearDirty({ keepEditor: false });
    await loadGraphView();
  } catch (error) {
    const force = error.status === 409 && confirm("节点仍有关联边。是否 force=true 删除节点并同步删除 schema_graph_edges.yaml 中相关显式边？");
    if (force) {
      const result = await api(`/api/graph/node/${encodeURIComponent(id)}?force=true`, { method: "DELETE" });
      writeOutput(result);
      selected = null;
      state.focusId = "";
      state.selectedNodeId = "";
      clearDirty({ keepEditor: false });
      await loadGraphView();
    } else {
      writeOutput({ error: error.message, detail: error.detail });
    }
  }
}

async function deleteEdge(edge) {
  if (!state.editMode) {
    writeOutput({ error: "当前是浏览模式。请先进入编辑模式。" });
    return;
  }
  const id = edge.id();
  if (edge.data("origin") !== "explicit") {
    writeOutput({ error: "inferred/bundle edge 不能直接删除，请修改对应 YAML 来源。" });
    return;
  }
  if (!confirm(`确认删除显式边 ${id} ?`)) return;
  try {
    const result = await api(`/api/graph/edge/${encodeURIComponent(id)}`, { method: "DELETE" });
    writeOutput(result);
    selected = null;
    clearDirty({ keepEditor: false });
    await loadGraphView();
  } catch (error) {
    writeOutput({ error: error.message, detail: error.detail });
  }
}

async function validateOntology() {
  const result = await api("/api/validate", { method: "POST" });
  el("validationStatus").textContent = result.ok ? `校验：通过（${result.warnings.length} 条警告）` : `校验：${result.errors.length} 个错误`;
  renderValidationPanel(result);
  writeOutput(result);
}

function renderValidationPanel(result) {
  const checkedAt = new Date().toLocaleString();
  const rows = [
    ...(result.errors || []).map((message) => ({ severity: "error", message })),
    ...(result.warnings || []).map((message) => ({ severity: "warning", message })),
  ];
  if (!rows.length) {
    el("validationPanel").innerHTML = `<div class="validation-item"><strong>0 个错误 / 0 条警告</strong><span>检查时间：${escapeHtml(checkedAt)}</span></div>`;
    return;
  }
  el("validationPanel").innerHTML = `
    <div class="validation-item"><strong>${result.errors?.length || 0} 个错误 / ${result.warnings?.length || 0} 条警告</strong><span>检查时间：${escapeHtml(checkedAt)}</span></div>
    ${rows.map((row) => renderValidationItem(row)).join("")}
  `;
  document.querySelectorAll("[data-validation-node]").forEach((button) => button.addEventListener("click", () => jumpToNode(button.dataset.validationNode)));
}

function renderValidationItem(row) {
  const nodeId = inferNodeIdFromMessage(row.message);
  const action = nodeId ? `<button data-validation-node="${escapeHtml(nodeId)}">定位节点</button>` : "";
  return `
    <div class="validation-item ${escapeHtml(row.severity)}">
      <strong>${escapeHtml(row.severity === "error" ? "错误" : "警告")}</strong>
      <span>${escapeHtml(row.message)}</span>
      <div class="diagnostic-actions">${action}</div>
    </div>
  `;
}

async function seedOntology() {
  if (!confirm("确认执行 scripts/seed_ontology.py 写入数据库？")) return;
  if (!confirm("再次确认：seed 会使用当前环境变量连接数据库，不会自动回滚数据库写入。继续？")) return;
  const result = await api("/api/seed", { method: "POST" });
  writeOutput(result);
}

async function search() {
  state.query = el("searchInput").value.trim();
  state.viewMode = state.viewMode === "full" ? "requirement" : state.viewMode;
  state.focusId = "";
  state.depth = 2;
  state.includeFields = false;
  state.relationFilter = "";
  setDefaultLayoutForView();
  syncControls();
  await loadGraphView();
}

function renderSearchResults(results) {
  const box = el("searchResults");
  if (!state.query) {
    box.innerHTML = `<div class="muted">输入关键词后点击定位</div>`;
    return;
  }
  if (!results.length) {
    box.innerHTML = `<div class="muted">没有搜索结果</div>`;
    return;
  }
  box.innerHTML = "";
  results.forEach((item) => {
    const btn = document.createElement("button");
    btn.innerHTML = `
      <strong>${escapeHtml(item.short_label || item.label || item.id)}</strong>
      <span>${escapeHtml(NODE_TYPE_LABELS[item.type] || item.type)} · ${escapeHtml(item.id)}</span>
      <em>匹配字段：${escapeHtml(fieldLabel(item.matched_field || "-"))}</em>
    `;
    btn.addEventListener("click", () => guarded(async () => {
      state.focusId = item.id;
      state.depth = 2;
      syncControls();
      await loadGraphView();
    }));
    box.appendChild(btn);
  });
}

async function setViewMode(viewMode) {
  state.viewMode = viewMode;
  state.focusId = "";
  state.query = "";
  state.relationFilter = "";
  state.includeFields = false;
  state.includeInferred = true;
  state.expandedGroups.clear();
  setDefaultLayoutForView();
  syncControls();
  await loadGraphView();
}

function setDefaultLayoutForView() {
  el("layoutSelect").value = DEFAULT_LAYOUT_BY_VIEW[state.viewMode] || "semantic";
}

function syncControls() {
  el("modeSelect").value = state.viewMode;
  el("depthSelect").value = String(state.depth);
  el("includeFields").checked = state.includeFields;
  el("includeInferred").checked = state.includeInferred;
  el("aggregateEdges").checked = state.aggregateEdges;
  el("enableGroups").checked = state.enableGroups;
  el("showEdgeLabels").checked = state.showEdgeLabels;
  el("searchInput").value = state.query;
}

function updateCounts() {
  const summary = currentGraph.summary || {};
  const hidden = currentGraph.hidden_counts || {};
  const warning = (summary.node_count || 0) > 80 ? " · 当前子图较大，建议使用搜索或 focus 模式" : "";
  el("nodeCount").textContent = `节点：${summary.node_count || 0}/${summary.total_node_count || 0}`;
  el("edgeCount").textContent = `关系：${summary.edge_count || 0}/${summary.total_edge_count || 0}`;
  el("viewStatus").textContent = `${VIEW_LABELS[state.viewMode]} / 隐藏表字段：${hidden.data_fields || 0} / 隐藏推断关系：${hidden.inferred_edges || 0}`;
  el("canvasStatus").textContent = `${summary.node_count || 0} 个节点 · ${summary.edge_count || 0} 条关系 · 隐藏表字段 ${hidden.data_fields || 0} · 隐藏推断关系 ${hidden.inferred_edges || 0}${warning}`;
}

function updateRelationSummary() {
  const groups = currentGraph.relation_groups || {};
  renderRelationGroupList(el("relationSummary"), groups, (type) => {
    state.relationFilter = state.relationFilter === type ? "" : type;
    applyRelationFilter();
    updateRelationSummary();
  });
}

function renderNodeTypeLegend() {
  const box = el("nodeTypeLegend");
  if (!box || !cy) return;
  const counts = {};
  cy.nodes().forEach((node) => {
    const type = node.data("type") || "unknown";
    counts[type] = (counts[type] || 0) + 1;
  });
  const entries = Object.entries(counts).sort((a, b) => a[0].localeCompare(b[0]));
  if (!entries.length) {
    box.innerHTML = `<div class="muted">当前没有节点</div>`;
    return;
  }
  box.innerHTML = entries
    .map(([type, count]) => {
      const checked = state.hiddenNodeTypes.has(type) ? "" : "checked";
      const color = NODE_TYPE_COLORS[type] || "#a3aab8";
      return `
        <label>
          <input type="checkbox" data-node-type="${escapeHtml(type)}" ${checked}>
          <i class="type-swatch" style="background:${escapeHtml(color)}"></i>
          <span>${escapeHtml(NODE_TYPE_LABELS[type] || TYPE_BADGES[type] || type)}</span>
          <em>${count}</em>
        </label>
      `;
    })
    .join("");
  box.querySelectorAll("[data-node-type]").forEach((input) => {
    input.addEventListener("change", () => {
      const type = input.dataset.nodeType;
      if (input.checked) state.hiddenNodeTypes.delete(type);
      else state.hiddenNodeTypes.add(type);
      applyNodeTypeFilter();
      runLayout();
    });
  });
}

function applyNodeTypeFilter() {
  if (!cy) return;
  cy.elements().removeClass("hidden-by-type");
  if (!state.hiddenNodeTypes.size) return;
  cy.nodes().forEach((node) => {
    if (state.hiddenNodeTypes.has(node.data("type"))) node.addClass("hidden-by-type");
  });
  cy.edges().forEach((edge) => {
    const sourceHidden = state.hiddenNodeTypes.has(edge.source().data("type"));
    const targetHidden = state.hiddenNodeTypes.has(edge.target().data("type"));
    if (sourceHidden || targetHidden) edge.addClass("hidden-by-type");
  });
}

function updateSelectedRelationSummary(nodeId) {
  if (!nodeId) {
    el("selectedRelationSummary").innerHTML = `<div class="muted">未选择节点</div>`;
    return;
  }
  const counts = {};
  cy.edges()
    .filter((edge) => edge.data("source") === nodeId || edge.data("target") === nodeId)
    .forEach((edge) => {
      const type = edge.data("type") || "unknown";
      counts[type] = (counts[type] || 0) + (edge.data("bundle_count") || 1);
    });
  renderRelationGroupList(el("selectedRelationSummary"), counts, (type) => {
    state.relationFilter = state.relationFilter === type ? "" : type;
    applyRelationFilter();
    updateRelationSummary();
    updateSelectedRelationSummary(nodeId);
  });
}

function renderRelationGroupList(box, groups, onClick) {
  const entries = Object.entries(groups);
  if (!entries.length) {
    box.innerHTML = `<div class="muted">当前没有边</div>`;
    return;
  }
  box.innerHTML = "";
  entries.forEach(([type, count]) => {
    const btn = document.createElement("button");
    btn.className = state.relationFilter === type ? "active" : "";
    btn.innerHTML = `<span>${escapeHtml(relationTypeLabel(type))}</span><strong>${count}</strong>`;
    btn.addEventListener("click", () => onClick(type));
    box.appendChild(btn);
  });
}

function renderDiagnostics() {
  const list = currentDiagnostics.items || [];
  const types = [...new Set(list.map((item) => item.type))].sort();
  const filter = el("diagnosticFilter").value;
  const existingOptions = [...el("diagnosticFilter").options].map((option) => option.value).join("|");
  if (existingOptions !== ["", ...types].join("|")) {
    el("diagnosticFilter").innerHTML = `<option value="">全部类型</option>${types.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(diagnosticTypeLabel(type))}</option>`).join("")}`;
    el("diagnosticFilter").value = filter;
  }
  const filtered = list.filter((item) => !filter || item.type === filter).slice(0, 160);
  if (!filtered.length) {
    el("diagnosticList").innerHTML = `<div class="muted">没有匹配的检查项</div>`;
    return;
  }
  const summary = currentDiagnostics.summary || {};
  el("diagnosticList").innerHTML = `
    <div class="diagnostic-item">
      <strong>${summary.error_count || 0} 个错误 / ${summary.warning_count || 0} 条警告</strong>
      <span>${summary.item_count || filtered.length} 个检查项</span>
    </div>
    ${filtered.map(renderDiagnosticItem).join("")}
  `;
  document.querySelectorAll("[data-diagnostic-node]").forEach((button) => button.addEventListener("click", () => jumpToNode(button.dataset.diagnosticNode)));
  document.querySelectorAll("[data-diagnostic-edit]").forEach((button) => button.addEventListener("click", async () => {
    const nodeId = button.dataset.diagnosticEdit;
    await jumpToNode(nodeId);
    if (!state.editMode) await toggleEditMode();
  }));
  updateEditModeUi();
}

function renderDiagnosticItem(item) {
  const nodeAction = item.node_id ? `<button data-diagnostic-node="${escapeHtml(item.node_id)}">定位节点</button>` : "";
  const editAction = item.node_id ? `<button data-diagnostic-edit="${escapeHtml(item.node_id)}" data-edit-only>打开编辑</button>` : "";
  return `
    <div class="diagnostic-item ${escapeHtml(item.severity)}">
      <strong>${escapeHtml(diagnosticTypeLabel(item.type))} / ${escapeHtml(severityLabel(item.severity))}</strong>
      <span>${escapeHtml(item.diagnostic_message_zh || item.message)}</span>
      <span>${escapeHtml(item.file || "-")} ${escapeHtml(item.node_id || "")}</span>
      <span>${escapeHtml(item.suggested_action_zh || item.suggested_action || "")}</span>
      <div class="diagnostic-actions">${nodeAction}${editAction}</div>
    </div>
  `;
}

function severityLabel(severity) {
  const labels = { error: "错误", warning: "警告", info: "提示" };
  return labels[severity] || severity || "-";
}

function applyRelationFilter() {
  if (!cy) return;
  cy.edges().removeClass("faded-relation");
  if (state.relationFilter) {
    cy.edges().filter((edge) => edge.data("type") !== state.relationFilter).addClass("faded-relation");
  }
}

function applyEdgeLabelMode() {
  if (!cy) return;
  cy.edges().removeClass("show-label");
  if (state.showEdgeLabels) cy.edges().addClass("show-label");
}

function applyLargeGraphLabelMode() {
  cy.nodes().removeClass("hide-label");
}

function toggleShellClass(className) {
  document.querySelector(".app-shell").classList.toggle(className);
  setTimeout(() => cy.resize().fit(undefined, 48), 160);
}

function enterFocusMode() {
  document.querySelector(".app-shell").classList.add("focus-mode");
  el("exitFocusBtn").hidden = false;
  setTimeout(() => cy.resize().fit(undefined, 48), 160);
}

function exitFocusMode() {
  document.querySelector(".app-shell").classList.remove("focus-mode");
  el("exitFocusBtn").hidden = true;
  setTimeout(() => cy.resize().fit(undefined, 48), 160);
}

async function toggleEditMode() {
  if (!state.editMode) {
    if (!(await requestEditModeForAction("编辑本体"))) return;
  } else {
    const decision = await confirmDirtyIfNeeded();
    if (decision === "cancel") return;
    state.editMode = false;
    updateEditModeUi();
    renderTaskActionPanel();
  }
}

async function requestEditModeForAction(actionLabel = "编辑") {
  if (state.editMode) return true;
  if (!confirm(`${actionLabel}会修改 ontology/*.yaml，保存前会自动备份。是否进入编辑模式？`)) {
    writeOutput({ message: "已取消进入编辑模式。", action: actionLabel });
    return false;
  }
  state.editMode = true;
  updateEditModeUi();
  renderTaskActionPanel();
  return true;
}

function updateEditModeUi() {
  el("editModeBtn").textContent = state.editMode ? "退出编辑模式" : "进入编辑模式";
  el("editModeStatus").textContent = state.editMode ? "编辑模式" : "浏览模式";
  el("editModeStatus").classList.toggle("dirty", state.editMode);
  document.querySelectorAll("[data-edit-only]").forEach((node) => {
    node.disabled = !state.editMode;
    node.hidden = !state.editMode && ["addNodeBtn", "addEdgeBtn"].includes(node.id);
  });
  document.querySelectorAll("#quickForm input, #quickForm textarea, #quickForm select").forEach((input) => {
    input.disabled = !state.editMode;
  });
  el("rawEditor").disabled = !state.editMode;
  updateDirtyUi();
}

function setOriginalRaw(objectId, raw, sourceFile) {
  state.originalRaw = cloneJson(raw);
  state.dirtyObjectId = objectId;
  state.dirtySourceFile = sourceFile;
  state.dirty = false;
  updateDirtyUi();
}

function markDirtyFromInspector() {
  if (!state.editMode || !selected) return;
  markDirty();
}

function markDirty() {
  state.dirty = true;
  state.dirtyObjectId = selected?.id?.() || state.dirtyObjectId;
  updateDirtyUi();
}

function clearDirty({ keepEditor }) {
  state.dirty = false;
  if (!keepEditor) {
    state.dirtyObjectId = "";
    state.dirtySourceFile = "";
    state.originalRaw = null;
  }
  updateDirtyUi();
}

function updateDirtyUi() {
  el("dirtyStatus").textContent = state.dirty ? `未保存修改：1 · ${state.dirtyObjectId}` : "未保存修改：0";
  el("dirtyStatus").classList.toggle("dirty", state.dirty);
  if (state.dirtySourceFile) loadFiles().catch(() => {});
}

async function confirmDirtyIfNeeded() {
  if (!state.dirty) return "continue";
  const decision = await openDirtyModal();
  if (decision === "save") {
    await saveSelected();
    return state.dirty ? "cancel" : "continue";
  }
  if (decision === "discard") {
    clearDirty({ keepEditor: false });
    return "continue";
  }
  return "cancel";
}

async function openAddNodeDialog(initialType = "SkillCapability", defaults = {}, options = {}) {
  if (initialType === "SkillCapability") {
    await openSkillCoverageEditor(defaults || {});
    return;
  }
  if (initialType === "IntentProfile") {
    await openIntentTemplateEditor(defaults || {});
    return;
  }
  if (!(await requestEditModeForAction(`新增${NODE_TYPE_LABELS[initialType] || "节点"}`))) return;
  await ensureOptions();
  const lockedType = options.lockedType !== false;
  const allowedTypes = options.allowedTypes || [initialType];
  el("modalTitle").textContent = `新增${NODE_TYPE_LABELS[initialType] || "节点"}`;
  const body = el("modalBody");
  const typeChooser = lockedType
    ? `<div class="wizard-fixed-type"><span>新增类型</span><strong>${escapeHtml(NODE_TYPE_LABELS[initialType] || initialType)}</strong><input id="newNodeType" type="hidden" value="${escapeHtml(initialType)}"></div>`
    : `<label>步骤 1：选择要新增的节点类型</label>
       <select id="newNodeType">${allowedTypes.map((type) => `<option value="${escapeHtml(type)}" ${type === initialType ? "selected" : ""}>${escapeHtml(NODE_TYPE_LABELS[type] || type)}</option>`).join("")}</select>`;
  body.innerHTML = `
    <div class="wizard-panel">
      ${typeChooser}
      <h3>步骤 2：填写核心信息</h3>
      <p class="wizard-help">只填写建模需要的核心字段；不确定的可选字段可以先留空。</p>
      <div id="newNodeForm" class="form-grid wizard-form"></div>
      <h3>步骤 3：确认将写入 YAML 的内容</h3>
      <p class="wizard-help">下面是保存时提交给后端的 JSON 预览。</p>
      <pre id="newNodePreview"></pre>
    </div>
  `;
  const render = () => renderNodeWizardForm(el("newNodeType").value, defaults);
  el("newNodeType").addEventListener("change", render);
  render();
  openModal(async () => {
    const nodeType = el("newNodeType").value;
    const data = readWizardData("newNodeForm");
    validateWizardRequired(nodeType, data);
    const nodeId = primaryValueForNode(nodeType, data);
    if (!nodeId) throw new Error("缺少节点主键字段");
    const result = await api("/api/graph/node", {
      method: "POST",
      body: JSON.stringify({ node_type: nodeType, node_id: nodeId, data }),
    });
    writeOutput(result);
    try {
      await refreshAll({ loadGraph: Boolean(state.focusId) });
    } catch (error) {
      writeOutput({ message: "新增节点已保存，但刷新页面失败，请手动刷新。", error: error.message, detail: error.detail });
    }
  });
}

function validateWizardRequired(nodeType, data) {
  const missing = [...(WIZARD_REQUIRED_FIELDS[nodeType] || new Set())].filter((field) => {
    const value = data[field];
    if (Array.isArray(value)) return value.length === 0;
    return value === undefined || value === null || String(value).trim() === "";
  });
  if (missing.length) {
    throw new Error(`请先填写必填项：${missing.map(fieldLabel).join("、")}`);
  }
}

function renderNodeWizardForm(nodeType, defaults = {}) {
  const fields = wizardFields(nodeType);
  const form = el("newNodeForm");
  form.innerHTML = "";
  fields.forEach((field) => {
    const fieldWrap = document.createElement("div");
    fieldWrap.className = "wizard-field";
    const label = document.createElement("label");
    const required = isWizardFieldRequired(nodeType, field.name);
    const helpText = wizardFieldHelp(nodeType, field);
    label.innerHTML = `
      <span>${escapeHtml(fieldLabel(field.name))}<i class="field-help-icon" tabindex="0" aria-label="${escapeHtml(helpText)}" data-tooltip="${escapeHtml(helpText)}">?</i></span>
      <em class="${required ? "required" : "optional"}">${required ? "必填" : "可选"}</em>
    `;
    const input = createWizardInput(field, defaults[field.name]);
    input.dataset.field = field.name;
    input.dataset.kind = field.kind || "text";
    if (required) input.required = true;
    input.addEventListener("input", updateNodePreview);
    input.addEventListener("change", updateNodePreview);
    fieldWrap.append(label, input);
    const help = wizardFieldHelp(nodeType, field);
    if (help) {
      const helpNode = document.createElement("small");
      helpNode.textContent = help;
      fieldWrap.append(helpNode);
    }
    form.append(fieldWrap);
  });
  updateNodePreview();
}

function wizardFields(nodeType) {
  const common = {
    SkillCapability: [
      ["skill_id"], ["skill_name"], ["description", "textarea"], ["enabled", "boolean"], ["target_object_type", "object"], ["supported_subject_types", "objects"], ["input_params", "tags"],
      ["supported_attributes", "attributes"], ["output_attributes", "attributes"], ["provides_fact_types", "fact_types"], ["supported_relations", "relations"], ["related_queries", "queries"], ["permission_scope"],
    ],
    Attribute: [["attribute_name"], ["attribute_name_zh"], ["description", "textarea"], ["object_types", "objects"], ["value_type"], ["aliases", "tags"], ["enabled", "boolean"]],
    IntentProfile: [["intent_name"], ["intent_name_zh"], ["trigger_aliases", "tags"], ["default_attributes", "attributes"], ["skill_priorities", "skills"], ["fact_requirements_template", "json"]],
    QueryCapability: [
      ["query_id"], ["query_name"], ["description", "textarea"], ["target_object_type", "object"], ["input_params", "tags"], ["required_params", "tags"],
      ["optional_params", "tags"], ["output_attributes", "attributes"], ["source_tables", "tables"],
    ],
    ObjectType: [["object_type"], ["object_type_zh"], ["description", "textarea"], ["enabled", "boolean"]],
    RelationType: [["relation_type"], ["relation_name_zh"], ["from_object_type", "object"], ["to_object_type", "object"], ["description", "textarea"], ["direction"], ["enabled", "boolean"]],
    DataTable: [["table_name"], ["table_name_zh"], ["description", "textarea"]],
    DataField: [["table_name", "table"], ["field_name"], ["field_name_zh"], ["semantic_type"], ["maps_to_attribute", "attribute"], ["description", "textarea"]],
  };
  return (common[nodeType] || []).map(([name, kind]) => ({ name, kind: kind || "text" }));
}

function isWizardFieldRequired(nodeType, fieldName) {
  return Boolean(WIZARD_REQUIRED_FIELDS[nodeType]?.has(fieldName));
}

function createWizardInput(field, value) {
  if (field.name === "permission_scope" && !value) value = "fund_public_data:read";
  if (field.kind === "textarea" || field.kind === "json") {
    const textarea = document.createElement("textarea");
    textarea.value = field.kind === "json" ? formatFormValue(value || {}) : formatFormValue(value);
    textarea.placeholder = field.kind === "json" ? "{}" : `填写${fieldLabel(field.name)}`;
    return textarea;
  }
  if (field.kind === "boolean") {
    const select = document.createElement("select");
    select.innerHTML = `<option value="true">启用</option><option value="false">停用</option>`;
    select.value = String(value !== false);
    return select;
  }
  if (["object", "attribute", "table"].includes(field.kind)) {
    const select = document.createElement("select");
    const source = field.kind === "object" ? currentOptions.object_types : field.kind === "attribute" ? currentOptions.attributes : currentOptions.data_tables;
    select.innerHTML = `<option value="">暂不选择</option>${(source || []).map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(optionLabel(item))}</option>`).join("")}`;
    select.value = value || "";
    return select;
  }
  if (["objects", "attributes", "skills", "queries", "tables", "fact_types", "relations"].includes(field.kind)) {
    const group = document.createElement("div");
    group.className = "multi-choice-list";
    const sourceMap = {
      objects: currentOptions.object_types,
      attributes: currentOptions.attributes,
      skills: currentOptions.skills,
      queries: currentOptions.queries,
      tables: currentOptions.data_tables,
      fact_types: currentOptions.fact_types,
      relations: currentOptions.relation_types,
    };
    const selectedValues = new Set(Array.isArray(value) ? value : value ? [value] : []);
    const options = sourceMap[field.kind] || [];
    group.innerHTML = options.length
      ? options.map((item) => `
        <label class="multi-choice-item">
          <input type="checkbox" value="${escapeHtml(item.value)}" ${selectedValues.has(item.value) ? "checked" : ""}>
          <span>${escapeHtml(optionLabel(item))}</span>
        </label>
      `).join("")
      : `<div class="muted">暂无可选项</div>`;
    return group;
  }
  const input = document.createElement("input");
  input.placeholder = field.kind === "tags" ? "多个值用逗号分隔" : `填写${fieldLabel(field.name)}`;
  input.value = Array.isArray(value) ? value.join(", ") : value || "";
  return input;
}

function fieldLabel(name) {
  return FIELD_LABELS[name] || name.replaceAll("_", " ");
}

function wizardFieldHelp(nodeType, field) {
  const required = isWizardFieldRequired(nodeType, field.name);
  const explicit = FIELD_HELP[field.name];
  if (explicit) return normalizeRequiredHelp(explicit, required);
  if (field.kind === "tags") return required ? "请至少填写一个值；多个值用逗号分隔。" : "多个值用逗号分隔；不需要时留空。";
  if (["objects", "attributes", "skills", "queries", "tables", "fact_types", "relations"].includes(field.kind)) {
    return required ? "请至少勾选一项；可以直接勾选多个。" : "可直接勾选多个；不需要时留空。";
  }
  if (["object", "attribute", "table"].includes(field.kind)) return required ? "请从下拉列表中选择一项。" : "可从下拉列表中选择；不需要时留空。";
  return required ? `${fieldLabel(field.name)}为必填项，请填写后再保存。` : `${fieldLabel(field.name)}为可选项，不确定时可先留空。`;
}

function normalizeRequiredHelp(text, required) {
  if (!required) return text;
  return text
    .replaceAll("；不确定时可先留空。", "。")
    .replaceAll("，不需要时留空。", "。")
    .replaceAll("；不需要时留空。", "。")
    .replaceAll("不确定时可先留空。", "请填写后再保存。")
    .replaceAll("不需要时留空。", "请填写后再保存。");
}

function optionLabel(item) {
  const value = item.value || item.id || "";
  const label = item.label && item.label !== value ? `${item.label}（${value}）` : value;
  return `${label}${item.type ? ` · ${NODE_TYPE_LABELS[item.type] || item.type}` : ""}`;
}

function updateNodePreview() {
  const preview = el("newNodePreview");
  if (!preview) return;
  try {
    preview.textContent = JSON.stringify(readWizardData("newNodeForm"), null, 2);
  } catch (error) {
    preview.textContent = error.message;
  }
}

function readWizardData(formId) {
  const data = {};
  document.querySelectorAll(`#${formId} [data-field]`).forEach((input) => {
    const field = input.dataset.field;
    const kind = input.dataset.kind;
    if (input.classList.contains("multi-choice-list")) data[field] = [...input.querySelectorAll('input[type="checkbox"]:checked')].map((option) => option.value).filter(Boolean);
    else if (input.multiple) data[field] = [...input.selectedOptions].map((option) => option.value).filter(Boolean);
    else if (kind === "boolean") data[field] = input.value === "true";
    else if (kind === "tags") data[field] = input.value.split(",").map((item) => item.trim()).filter(Boolean);
    else if (kind === "json") data[field] = input.value.trim() ? JSON.parse(input.value) : {};
    else if (input.value.trim() !== "") data[field] = input.value.trim();
  });
  return data;
}

function primaryValueForNode(nodeType, data) {
  const keys = {
    ObjectType: "object_type",
    Attribute: "attribute_name",
    SkillCapability: "skill_id",
    QueryCapability: "query_id",
    IntentProfile: "intent_name",
    RelationType: "relation_type",
    DataTable: "table_name",
    DataField: "field_name",
  };
  if (nodeType === "DataField") return data.table_name && data.field_name ? `${data.table_name}.${data.field_name}` : "";
  return data[keys[nodeType]] || "";
}

async function openEdgeDialog(prefill = {}) {
  if (!(await requestEditModeForAction("创建关系边"))) return;
  await ensureOptions();
  const nodes = allNodeOptions();
  const lockedEndpoints = Boolean(prefill.lockedEndpoints);
  el("modalTitle").textContent = lockedEndpoints ? "完善关系信息" : "创建关系";
  const endpointFields = lockedEndpoints
    ? `<div class="edge-endpoint-summary">
        <div><span>起点</span><strong>${escapeHtml(readableNodeName(prefill.source))}</strong></div>
        <div><span>终点</span><strong>${escapeHtml(readableNodeName(prefill.target))}</strong></div>
        <input id="edgeSource" type="hidden" value="${escapeHtml(prefill.source || "")}">
        <input id="edgeTarget" type="hidden" value="${escapeHtml(prefill.target || "")}">
      </div>`
    : `<label>起点节点</label>
       <input id="edgeSource" list="edgeNodeOptions" value="${escapeHtml(prefill.source || "")}" placeholder="搜索节点名称、ID 或类型">
       <label>终点节点</label>
       <input id="edgeTarget" list="edgeNodeOptions" value="${escapeHtml(prefill.target || "")}" placeholder="搜索节点名称、ID 或类型">
       <datalist id="edgeNodeOptions">${nodes.map((node) => `<option value="${escapeHtml(node.id)}">${escapeHtml(readableNodeName(node.id))}</option>`).join("")}</datalist>`;
  el("modalBody").innerHTML = `
    <div class="wizard-panel">
      ${endpointFields}
      <label>关系类型</label>
      <select id="edgeRelation"></select>
      <small id="edgeRelationHelp" class="wizard-help">先选起点和终点，系统会优先推荐常用建模关系。</small>
      <label>关系来源</label>
      <input value="显式关系，将写入 YAML" disabled>
      <label>中文原因</label>
      <textarea id="edgeReason" rows="3" placeholder="说明为什么需要这条关系，便于诊断和规划解释">${escapeHtml(prefill.reason_zh || "")}</textarea>
      <label>适用任务</label>
      <input id="edgeApplicableTasks" value="${escapeHtml((prefill.applicable_tasks || []).join(", "))}" placeholder="例如 analyze, compare；不确定可留空">
      <label>适用意图</label>
      <input id="edgeApplicableIntents" value="${escapeHtml((prefill.applicable_intents || []).join(", "))}" placeholder="例如 performance_overview；不确定可留空">
      <label>附加属性 JSON</label>
      <textarea id="edgeProps" rows="6" placeholder="{}">{}</textarea>
    </div>
  `;
  const refreshRelationOptions = () => {
    const select = el("edgeRelation");
    const source = el("edgeSource").value.trim();
    const target = el("edgeTarget").value.trim();
    const current = select.value || prefill.relation_type || "";
    const relationOptions = edgeRelationOptions(source, target);
    select.innerHTML = `<option value="">请选择关系类型</option>${relationOptions.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(relationOptionLabel(item))}</option>`).join("")}`;
    if ([...select.options].some((option) => option.value === current)) select.value = current;
    el("edgeRelationHelp").textContent = source && target ? "已根据起点和终点类型刷新推荐关系。" : "先选起点和终点，系统会优先推荐常用建模关系。";
  };
  ["edgeSource", "edgeTarget"].forEach((id) => {
    const node = el(id);
    node?.addEventListener("input", refreshRelationOptions);
    node?.addEventListener("change", refreshRelationOptions);
  });
  refreshRelationOptions();
  openModal(async () => {
    const source = el("edgeSource").value.trim();
    const target = el("edgeTarget").value.trim();
    const relationType = el("edgeRelation").value.trim();
    const props = JSON.parse(el("edgeProps").value || "{}");
    const reason = el("edgeReason").value.trim();
    const applicableTasks = splitCsv(el("edgeApplicableTasks").value);
    const applicableIntents = splitCsv(el("edgeApplicableIntents").value);
    if (reason) props.reason_zh = reason;
    if (applicableTasks.length) props.applicable_tasks = applicableTasks;
    if (applicableIntents.length) props.applicable_intents = applicableIntents;
    if (!source || !target || !relationType) throw new Error("起点节点、终点节点、关系类型都不能为空");
    if (source === target && !confirm("这是自环边，是否确认？")) return;
    const result = await api("/api/graph/edge", {
      method: "POST",
      body: JSON.stringify({ source, target, relation_type: relationType, properties: props }),
    });
    writeOutput(result);
    await refreshAll({ loadGraph: Boolean(state.focusId) });
  });
}

function edgeRelationOptions(source = "", target = "") {
  const map = new Map();
  const add = (item, group = "") => {
    const value = item.value || item.id;
    if (!value || map.has(value)) return;
    map.set(value, { ...item, value, group });
  };
  suggestedRelationsForEndpoints(source, target).forEach((item) => add(item, "推荐"));
  MODELING_RELATION_TYPES.forEach((item) => add(item, "建模关系"));
  (currentOptions.relation_types || []).forEach((item) => add(item, "业务关系"));
  return [...map.values()];
}

function suggestedRelationsForEndpoints(source, target) {
  const sourceType = nodeTypeFromId(source);
  const targetType = nodeTypeFromId(target);
  const suggestions = [];
  if (sourceType === "SkillCapability" && targetType === "Attribute") {
    suggestions.push(
      { value: "supports_attribute", label: "Skill 支持这个属性" },
      { value: "outputs_attribute", label: "Skill 输出这个属性" },
      { value: "provides_attribute", label: "Skill 提供这个属性" },
    );
  }
  if (sourceType === "SkillCapability" && targetType === "FactType") {
    suggestions.push({ value: "provides_fact_type", label: "Skill 提供这个事实类型" });
  }
  if (sourceType === "IntentProfile" && targetType === "FactType") {
    suggestions.push({ value: "requires_fact_type", label: "Intent 需要这个事实类型" });
  }
  if (sourceType === "SkillCapability" && targetType === "QueryCapability") {
    suggestions.push({ value: "related_query", label: "Skill 关联查询能力" });
  }
  if (sourceType === "IntentProfile" && targetType === "SkillCapability") {
    suggestions.push(
      { value: "has_skill", label: "Intent 关联 Skill" },
      { value: "recommends_skill", label: "Intent 推荐 Skill" },
    );
  }
  if (sourceType === "IntentProfile" && targetType === "Attribute") {
    suggestions.push({ value: "has_attribute", label: "Intent 默认包含属性" });
  }
  if (sourceType === "Attribute" && targetType === "DataField") {
    suggestions.push({ value: "maps_to_field", label: "属性映射到表字段" });
  }
  if (sourceType === "DataField" && targetType === "Attribute") {
    suggestions.push({ value: "mapped_to_field", label: "表字段映射到属性" });
  }
  if (targetType === "ObjectType" && ["SkillCapability", "QueryCapability"].includes(sourceType)) {
    suggestions.push({ value: "targets_object_type", label: "能力面向对象类型" });
  }
  return suggestions;
}

function nodeTypeFromId(nodeId = "") {
  return String(nodeId).includes(":") ? String(nodeId).split(":", 1)[0] : "";
}

function relationOptionLabel(item) {
  const value = item.value || item.id || "";
  const label = item.label && item.label !== value ? item.label : relationTypeLabel(value);
  const group = item.group ? `${item.group} · ` : "";
  return `${group}${label}（${value}）`;
}

function relationTypeLabel(type) {
  return RELATION_TYPE_LABELS[type] || type || "";
}

function readableNodeName(nodeId) {
  const node = allNodeOptions().find((item) => item.id === nodeId);
  if (!node) return nodeId || "-";
  const type = NODE_TYPE_LABELS[node.type] || node.type || "节点";
  const label = node.label && node.label !== node.id ? `${node.label}（${node.id}）` : node.id;
  return `${label} · ${type}`;
}

function allNodeOptions() {
  const fromGraph = (currentGraph.nodes || []).map((node) => ({
    id: node.data.id,
    label: node.data.label || node.data.id,
    type: node.data.type,
  }));
  const fromOptions = [
    ...(currentOptions.object_types || []),
    ...(currentOptions.attributes || []),
    ...(currentOptions.skills || []),
    ...(currentOptions.queries || []),
    ...(currentOptions.relation_types || []),
    ...(currentOptions.fact_types || []),
    ...(currentOptions.data_tables || []),
  ];
  const map = new Map();
  [...fromGraph, ...fromOptions].forEach((item) => {
    const id = item.id || item.value;
    if (!id) return;
    map.set(id, { id, value: id, label: item.label || id, type: item.type });
  });
  return [...map.values()].sort((a, b) => a.id.localeCompare(b.id));
}

async function startEdgeCreation(initialSource = "") {
  if (!(await requestEditModeForAction("创建关系边"))) return;
  if (typeof initialSource !== "string") initialSource = "";
  state.edgeDrawMode = true;
  state.edgeDraftSource = initialSource || "";
  cy.elements().removeClass("edge-draft-source");
  if (state.edgeDraftSource) cy.getElementById(state.edgeDraftSource).addClass("edge-draft-source");
  const message = state.edgeDraftSource
    ? "连线模式：已选择起点，请在图中点击终点节点。按 Esc 取消。"
    : "连线模式：请先点击起点节点，再点击终点节点。按 Esc 取消。";
  el("canvasStatus").textContent = message;
  writeOutput({ message });
}

function handleEdgeDrawNodeTap(node) {
  if (!state.edgeDraftSource) {
    state.edgeDraftSource = node.id();
    cy.elements().removeClass("edge-draft-source");
    node.addClass("edge-draft-source");
    const message = `连线模式：起点为 ${node.data("label") || node.id()}，请点击终点节点。按 Esc 取消。`;
    el("canvasStatus").textContent = message;
    writeOutput({ message });
    return;
  }
  const source = state.edgeDraftSource;
  const target = node.id();
  exitEdgeDrawMode();
  openEdgeDialog({ source, target, lockedEndpoints: true });
}

function exitEdgeDrawMode() {
  state.edgeDrawMode = false;
  state.edgeDraftSource = "";
  cy.elements().removeClass("edge-draft-source");
  updateCounts();
}

function openModal(onOk) {
  const modal = el("modal");
  const okBtn = el("modalOkBtn");
  okBtn.type = "button";
  clearModalError();
  const cancelBtn = modal.querySelector('.modal-actions button[value="cancel"]');
  const cancelHandler = (event) => {
    event.preventDefault();
    modal.close();
    clearModalError();
    cancelBtn?.removeEventListener("click", cancelHandler);
    okBtn.removeEventListener("click", handler);
  };
  const handler = async (event) => {
    event.preventDefault();
    clearModalError();
    okBtn.disabled = true;
    try {
      await onOk();
      modal.close();
      cancelBtn?.removeEventListener("click", cancelHandler);
      okBtn.removeEventListener("click", handler);
      clearModalError();
    } catch (error) {
      writeOutput({ error: error.message, detail: error.detail });
      showModalError(error);
      okBtn.disabled = false;
    }
  };
  cancelBtn?.setAttribute("type", "button");
  cancelBtn?.addEventListener("click", cancelHandler);
  okBtn.addEventListener("click", handler);
  modal.showModal();
}

function showModalError(error) {
  const body = el("modalBody");
  let node = el("modalError");
  if (!node) {
    node = document.createElement("div");
    node.id = "modalError";
    node.className = "modal-error";
    body.prepend(node);
  }
  const detail = error.detail ? JSON.stringify(error.detail, null, 2) : "";
  node.innerHTML = `
    <strong>保存失败</strong>
    <span>${escapeHtml(error.message || "请求失败")}</span>
    ${detail ? `<pre>${escapeHtml(detail)}</pre>` : ""}
  `;
}

function clearModalError() {
  el("modalError")?.remove();
}

function openDirtyModal() {
  return new Promise((resolve) => {
    const modal = el("modal");
    el("modalTitle").textContent = "未保存修改";
    el("modalBody").innerHTML = `<p>当前编辑对象 ${escapeHtml(state.dirtyObjectId)} 有未保存修改。</p>`;
    const actions = modal.querySelector(".modal-actions");
    actions.innerHTML = `
      <button id="dirtySaveBtn" type="button" value="save">保存</button>
      <button id="dirtyDiscardBtn" type="button" value="discard">放弃</button>
      <button id="dirtyCancelBtn" type="button" value="cancel">取消</button>
    `;
    const finish = (value) => {
      modal.close();
      restoreModalActions();
      resolve(value);
    };
    el("dirtySaveBtn").addEventListener("click", (event) => { event.preventDefault(); finish("save"); });
    el("dirtyDiscardBtn").addEventListener("click", (event) => { event.preventDefault(); finish("discard"); });
    el("dirtyCancelBtn").addEventListener("click", (event) => { event.preventDefault(); finish("cancel"); });
    modal.showModal();
  });
}

function openDiffModal(diff) {
  return new Promise((resolve) => {
    const modal = el("modal");
    el("modalTitle").textContent = "变更预览";
    el("modalBody").innerHTML = renderDiff(diff);
    const actions = modal.querySelector(".modal-actions");
    actions.innerHTML = `
      <button id="diffDiscardBtn" type="button">放弃修改</button>
      <button id="diffBackBtn" type="button">返回编辑</button>
      <button id="diffSaveBtn" type="button">确认保存</button>
    `;
    const finish = (value) => {
      modal.close();
      restoreModalActions();
      resolve(value);
    };
    el("diffDiscardBtn").addEventListener("click", (event) => { event.preventDefault(); finish("discard"); });
    el("diffBackBtn").addEventListener("click", (event) => { event.preventDefault(); finish("cancel"); });
    el("diffSaveBtn").addEventListener("click", (event) => { event.preventDefault(); finish("save"); });
    modal.showModal();
  });
}

function restoreModalActions() {
  const actions = el("modal").querySelector(".modal-actions");
  actions.innerHTML = `<button type="button" value="cancel">取消</button><button id="modalOkBtn" type="button" value="ok">确定</button>`;
}

function renderDiff(diff) {
  const section = (title, rows) => `
    <div>
      <h3>${escapeHtml(title)}</h3>
      ${rows.length ? rows.map((row) => `
        <div class="diff-row">
          <strong>${escapeHtml(row.key)}</strong>
          ${"oldValue" in row ? `<code>old: ${escapeHtml(JSON.stringify(row.oldValue, null, 2))}</code>` : ""}
          ${"newValue" in row ? `<code>new: ${escapeHtml(JSON.stringify(row.newValue, null, 2))}</code>` : ""}
        </div>
      `).join("") : `<div class="muted">无</div>`}
    </div>
  `;
  return `<div class="diff-list">${section("changed", diff.changed)}${section("added", diff.added)}${section("removed", diff.removed)}</div>`;
}

function readInspectorPayload() {
  const raw = JSON.parse(el("rawEditor").value || "{}");
  document.querySelectorAll("#quickForm [data-field]").forEach((input) => {
    raw[input.dataset.field] = parseFormValue(input.value, raw[input.dataset.field], input);
  });
  return raw;
}

function setRaw(raw) {
  el("rawEditor").value = JSON.stringify(raw || {}, null, 2);
}

function parseFormValue(text, original, input) {
  if (input?.tagName === "SELECT" && input.multiple) return [...input.selectedOptions].map((option) => option.value);
  const trimmed = String(text || "").trim();
  if (typeof original === "boolean") return trimmed === "true";
  if (Array.isArray(original) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) return trimmed ? JSON.parse(trimmed) : [];
  if (original && typeof original === "object") return trimmed ? JSON.parse(trimmed) : {};
  if (typeof original === "number" && trimmed !== "") return Number(trimmed);
  return text;
}

function formatFormValue(value) {
  if (Array.isArray(value) || (value && typeof value === "object")) return JSON.stringify(value, null, 2);
  if (value === undefined || value === null) return "";
  return String(value);
}

function edgeProperties(raw) {
  const props = { ...raw };
  ["edge_id", "source", "target", "from", "to", "relation_type", "properties"].forEach((key) => delete props[key]);
  if (raw.properties && typeof raw.properties === "object") Object.assign(props, raw.properties);
  return props;
}

function setInspectorTab(tab) {
  document.querySelectorAll(".inspector-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".inspector-tab").forEach((panel) => {
    panel.hidden = panel.dataset.panel !== tab;
  });
}

function showPathsToType(startId, targetType) {
  const paths = findShortestPaths(startId, targetType).slice(0, 12);
  setInspectorTab("impact");
  clearHighlight();
  if (!paths.length) {
    el("pathPanel").innerHTML = `<div class="path-item"><strong>路径查看</strong><span>当前子图中没有到 ${escapeHtml(targetType)} 的路径</span></div>`;
    return;
  }
  const pathElements = cy.collection();
  paths.forEach((path) => {
    path.nodes.forEach((nodeId) => pathElements.merge(cy.getElementById(nodeId)));
    path.edges.forEach((edgeId) => pathElements.merge(cy.getElementById(edgeId)));
  });
  cy.elements().difference(pathElements).addClass("faded");
  pathElements.addClass("path-highlight");
  el("pathPanel").innerHTML = paths.map((path) => `<div class="path-item"><strong>${escapeHtml(targetType)}</strong><span>${escapeHtml(path.nodes.join(" -> "))}</span></div>`).join("");
}

function findShortestPaths(startId, targetType) {
  const queue = [{ nodeId: startId, nodes: [startId], edges: [] }];
  const visited = new Set([startId]);
  const results = [];
  while (queue.length && results.length < 20) {
    const current = queue.shift();
    if (current.nodeId !== startId && cy.getElementById(current.nodeId).data("type") === targetType) {
      results.push(current);
      continue;
    }
    if (current.nodes.length > 5) continue;
    cy.getElementById(current.nodeId).connectedEdges().forEach((edge) => {
      const next = edge.data("source") === current.nodeId ? edge.data("target") : edge.data("source");
      if (visited.has(next)) return;
      visited.add(next);
      queue.push({ nodeId: next, nodes: [...current.nodes, next], edges: [...current.edges, edge.id()] });
    });
  }
  return results;
}

function toggleSelectedSkillEnabled() {
  if (!selected || !selected.isNode()) return;
  const raw = readInspectorPayload();
  raw.enabled = raw.enabled === false;
  setRaw(raw);
  buildQuickForm(selected.data("type"), raw);
  markDirty();
}

function handleShortcuts(event) {
  if (event.target?.tagName === "INPUT" || event.target?.tagName === "TEXTAREA") {
    if (event.key === "Escape") {
      if (state.edgeDrawMode) exitEdgeDrawMode();
      else el("modal").close();
    }
    return;
  }
  if (event.ctrlKey && event.key.toLowerCase() === "s") {
    event.preventDefault();
    saveSelected();
  } else if (event.key === "Escape") {
    if (state.edgeDrawMode) exitEdgeDrawMode();
    else if (el("modal").open) el("modal").close();
    else clearSelection();
  } else if (event.key.toLowerCase() === "f" && event.shiftKey) {
    if (state.selectedNodeId) focusOnNode(state.selectedNodeId, 2);
  } else if (event.key.toLowerCase() === "f") {
    if (state.selectedNodeId) focusOnNode(state.selectedNodeId, 1);
  } else if (event.key === "/") {
    event.preventDefault();
    el("searchInput").focus();
  } else if (event.key === "Delete") {
    deleteSelected();
  } else if (event.ctrlKey && event.key.toLowerCase() === "z") {
    event.preventDefault();
    alert("暂不支持撤销，请使用备份或放弃修改。");
  }
}

async function ensureOptions() {
  if (!currentOptions.object_types) await loadOptions();
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: { error: text.slice(0, 500), raw_response: text } };
    }
  }
  if (!res.ok) {
    const error = new Error(data.detail?.error || res.statusText);
    error.status = res.status;
    error.detail = data.detail || data;
    throw error;
  }
  return data;
}

function writeOutput(value) {
  el("output").textContent = JSON.stringify(value, null, 2);
}

function diffJson(oldValue, newValue) {
  const oldKeys = new Set(Object.keys(oldValue || {}));
  const newKeys = new Set(Object.keys(newValue || {}));
  const changed = [];
  const added = [];
  const removed = [];
  newKeys.forEach((key) => {
    if (!oldKeys.has(key)) added.push({ key, newValue: newValue[key] });
    else if (JSON.stringify(oldValue[key]) !== JSON.stringify(newValue[key])) changed.push({ key, oldValue: oldValue[key], newValue: newValue[key] });
  });
  oldKeys.forEach((key) => {
    if (!newKeys.has(key)) removed.push({ key, oldValue: oldValue[key] });
  });
  return { changed, added, removed };
}

function inferNodeIdFromMessage(message) {
  const patterns = [
    [/unknown supported_attributes: ([\w.:-]+)/, "Attribute"],
    [/unknown output_attribute: ([\w.:-]+)/, "Attribute"],
    [/unknown default_attribute: ([\w.:-]+)/, "Attribute"],
    [/unknown related_query: ([\w.:-]+)/, "QueryCapability"],
    [/unknown target_object_type: ([\w.:-]+)/, "ObjectType"],
    [/item ([\w.:-]+) references/, ""],
  ];
  for (const [regex, type] of patterns) {
    const match = String(message).match(regex);
    if (match) return type ? `${type}:${match[1]}` : match[1];
  }
  return "";
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function shortLabel(value, maxLen = 18) {
  const text = String(value || "");
  return text.length <= maxLen ? text : `${text.slice(0, maxLen - 1)}…`;
}

function hashString(value) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash.toString(16);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
