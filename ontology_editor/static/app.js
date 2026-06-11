const NODE_TYPES = [
  "ObjectType",
  "Attribute",
  "SkillCapability",
  "QueryCapability",
  "IntentProfile",
  "RelationType",
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
    "input_params",
    "supported_attributes",
    "output_attributes",
    "provides_fact_types",
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
  DataTable: ["table_name", "table_name_zh", "description"],
  DataField: ["field_name", "field_name_zh", "semantic_type", "data_type", "maps_to_attribute", "description"],
  DataSource: ["source_id", "source_type", "enabled", "description", "tables"],
  Edge: ["edge_id", "source", "target", "relation_type", "properties"],
};

const TASKS = [
  {
    id: "skill",
    title: "重构 Skill",
    description: "选择或新增 Skill，编辑输入参数、输出属性、事实类型、关联查询能力、关联 Intent。",
    viewMode: "skill",
    recommendedTypes: ["SkillCapability"],
    dashboard: "skill",
    includeInferred: true,
  },
  {
    id: "object_attribute",
    title: "设计对象属性",
    description: "选择对象类型，查看和编辑其属性、相关 Skill、相关查询能力。",
    viewMode: "object_attribute",
    recommendedTypes: ["ObjectType"],
    dashboard: "object_attribute",
    includeInferred: true,
  },
  {
    id: "intent",
    title: "设计 Intent 编排",
    description: "选择 Intent，编辑触发表达、默认属性、候选 Skill 和事实需求模板。",
    viewMode: "requirement",
    recommendedTypes: ["IntentProfile"],
    dashboard: "intent",
    includeInferred: true,
  },
  {
    id: "table_mapping",
    title: "检查表字段映射",
    description: "选择属性或数据表，查看属性到表字段和数据表的映射。",
    viewMode: "object_attribute",
    recommendedTypes: ["Attribute"],
    dashboard: "table_mapping",
    includeFields: false,
    includeInferred: true,
  },
  {
    id: "diagnostic",
    title: "全局检查",
    description: "查看校验错误、警告、孤立节点、未覆盖属性、未被 Intent 使用的 Skill。",
    viewMode: "overview",
    recommendedTypes: [],
    dashboard: "diagnostic",
    includeInferred: true,
  },
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
  requirement: ["IntentProfile", "ObjectType", "Attribute", "SkillCapability", "QueryCapability"],
  skill: ["ObjectType", "SkillCapability", "Attribute", "QueryCapability", "DataTable"],
  object_attribute: ["ObjectType", "Attribute", "SkillCapability", "QueryCapability"],
  table_mapping: ["ObjectType", "Attribute", "DataField", "DataTable"],
  overview: ["IntentProfile", "ObjectType", "SkillCapability", "QueryCapability", "Attribute"],
  full: ["IntentProfile", "ObjectType", "Attribute", "SkillCapability", "QueryCapability", "DataTable", "DataField", "RelationType"],
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
};

const NODE_TYPE_LABELS = {
  ObjectType: "对象类型",
  Attribute: "对象属性",
  SkillCapability: "Skill 能力",
  QueryCapability: "查询能力",
  IntentProfile: "Intent 编排",
  RelationType: "关系类型",
  DataTable: "数据表",
  DataField: "表字段",
  Edge: "关系边",
  BundleEdge: "聚合关系边",
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
};

const MODELING_RELATION_TYPES = [
  { value: "supports_attribute", label: "Skill 支持属性" },
  { value: "outputs_attribute", label: "Skill 输出属性" },
  { value: "provides_attribute", label: "Skill 提供属性" },
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
  permission_scope: "权限范围",
  value_type: "值类型",
  data_type: "数据类型",
  aliases: "别名",
  trigger_aliases: "触发表达",
  fact_requirements_template: "事实需求模板 JSON",
  source_tables: "来源数据表",
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
  provides_fact_types: "该 Skill 产出的事实类别，例如 metric_value、ranking、profile_fact。多个值用逗号分隔。",
  related_queries: "该 Skill 需要调用或依赖的查询能力，例如先查净值、再计算收益。",
  permission_scope: "该 Skill 所需的数据或功能权限范围；不确定时可先留空。",
  fact_requirements_template: "Intent 对事实的结构化需求模板。高级字段；不确定时可保持空对象 {}。",
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
  currentOptions = await api("/api/options");
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

function renderWorkbenchHome() {
  el("workbenchHome").classList.remove("hidden");
  el("workbenchHome").classList.remove("dashboard-home");
  el("workbenchHome").innerHTML = `
    <div class="workbench-panel">
      <h1>本体建模工作台</h1>
      <p>选择建模任务后会直接进入可操作工作台；高级图谱范围只放在顶部“更多”里。</p>
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

function renderTaskActionPanel() {
  const task = TASKS.find((item) => item.id === state.activeTaskId);
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
    skill: [
      `<button id="taskNewSkillBtn" data-edit-only>新增 Skill</button>`,
      `<button id="taskNewQueryBtn" data-edit-only>新增查询能力</button>`,
      `<button id="taskNewObjectBtn" data-edit-only>新增对象类型</button>`,
      `<button id="taskNewEdgeBtn" data-edit-only>创建关系边</button>`,
      `<button id="taskSkillCoverageBtn">查看 Skill 覆盖问题</button>`,
    ],
    object_attribute: [
      `<button id="taskNewObjectBtn" data-edit-only>新增对象类型</button>`,
      `<button id="taskNewAttributeBtn" data-edit-only>新增属性</button>`,
      `<button id="taskNewSkillForObjectBtn" data-edit-only>新增 Skill</button>`,
      `<button id="taskNewQueryBtn" data-edit-only>新增查询能力</button>`,
      `<button id="taskAttributeIssuesBtn">查看属性问题</button>`,
    ],
    intent: [
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
  on("taskNewSkillBtn", "click", () => openAddNodeDialog("SkillCapability", {}, { lockedType: true }));
  on("taskNewQueryBtn", "click", () => openAddNodeDialog("QueryCapability", {}, { lockedType: true }));
  on("taskNewAttributeBtn", "click", () => openAddNodeDialog("Attribute", {}, { lockedType: true }));
  on("taskNewSkillForObjectBtn", "click", () => openAddNodeDialog("SkillCapability", {}, { lockedType: true }));
  on("taskNewIntentBtn", "click", () => openAddNodeDialog("IntentProfile", {}, { lockedType: true }));
  on("taskNewTableBtn", "click", () => openAddNodeDialog("DataTable", {}, { lockedType: true }));
  on("taskNewDataFieldBtn", "click", () => openAddNodeDialog("DataField", {}, { lockedType: true }));
  on("taskNewEdgeBtn", "click", () => startEdgeCreation());
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
        ${Object.entries(byType).map(([type, count]) => `<button data-diagnostic-type="${escapeHtml(type)}"><strong>${escapeHtml(type)}</strong><span>${count}</span></button>`).join("")}
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

function filterDiagnostics(type) {
  el("diagnosticFilter").value = type || "";
  renderDiagnostics();
}

async function selectTask(taskId) {
  const task = TASKS.find((item) => item.id === taskId);
  if (!task) return;
  state.activeTaskId = task.id;
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
  renderTaskCandidates();
  renderTaskActionPanel();
  syncControls();
  renderEmptyInspector();
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
      : `<div class="muted">当前没有 Diagnostic 检查项</div>`;
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
  if (state.enableGroups && !state.focusId && ["overview", "requirement"].includes(state.viewMode)) {
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
  renderEmptyInspector();
  updateSelectedRelationSummary(null);
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
    buttons.push(`<button id="newQueryBtn" data-edit-only>新增查询能力</button>`);
  }
  if (data.type === "Attribute") {
    buttons.push(`<button id="linkSkillBtn" data-edit-only>关联 Skill</button>`);
    buttons.push(`<button id="linkQueryBtn" data-edit-only>关联查询能力</button>`);
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
  el("newSkillBtn")?.addEventListener("click", () => openAddNodeDialog("SkillCapability", { target_object_type: data.identity }));
  el("newQueryBtn")?.addEventListener("click", () => openAddNodeDialog("QueryCapability", { target_object_type: data.identity }));
  el("linkSkillBtn")?.addEventListener("click", () => openEdgeDialog({ target: data.id, relation_type: "supports_attribute" }));
  el("linkQueryBtn")?.addEventListener("click", () => openEdgeDialog({ target: data.id, relation_type: "outputs_attribute" }));
  el("linkFieldBtn")?.addEventListener("click", () => openEdgeDialog({ source: data.id, relation_type: "maps_to_field" }));
  el("toggleSkillBtn")?.addEventListener("click", () => toggleSelectedSkillEnabled());
  el("copySkillBtn")?.addEventListener("click", () => openAddNodeDialog("SkillCapability", { ...(data.raw || {}), skill_id: `${data.identity}_copy`, skill_name: `${data.label || data.identity} copy` }));
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
    el("diagnosticFilter").innerHTML = `<option value="">全部类型</option>${types.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`).join("")}`;
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
      <strong>${escapeHtml(item.type)} / ${escapeHtml(item.severity)}</strong>
      <span>${escapeHtml(item.message)}</span>
      <span>${escapeHtml(item.file || "-")} ${escapeHtml(item.node_id || "")}</span>
      <span>${escapeHtml(item.suggested_action || "")}</span>
      <div class="diagnostic-actions">${nodeAction}${editAction}</div>
    </div>
  `;
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
    if (!confirm("编辑会修改 ontology/*.yaml，保存前会自动备份。是否进入编辑模式？")) return;
    state.editMode = true;
  } else {
    const decision = await confirmDirtyIfNeeded();
    if (decision === "cancel") return;
    state.editMode = false;
  }
  updateEditModeUi();
  renderTaskActionPanel();
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
  if (!state.editMode) return;
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
      ["skill_id"], ["skill_name"], ["description", "textarea"], ["enabled", "boolean"], ["target_object_type", "object"], ["input_params", "tags"],
      ["supported_attributes", "attributes"], ["output_attributes", "attributes"], ["provides_fact_types", "tags"], ["related_queries", "queries"], ["permission_scope"],
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
  if (["objects", "attributes", "skills", "queries", "tables"].includes(field.kind)) {
    const group = document.createElement("div");
    group.className = "multi-choice-list";
    const sourceMap = {
      objects: currentOptions.object_types,
      attributes: currentOptions.attributes,
      skills: currentOptions.skills,
      queries: currentOptions.queries,
      tables: currentOptions.data_tables,
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
  if (["objects", "attributes", "skills", "queries", "tables"].includes(field.kind)) {
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
  if (!state.editMode) return;
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
  const relationOptions = edgeRelationOptions(prefill.source, prefill.target);
  el("modalBody").innerHTML = `
    <div class="wizard-panel">
      ${endpointFields}
      <label>关系类型</label>
      <select id="edgeRelation">
        <option value="">请选择关系类型</option>
        ${relationOptions.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === prefill.relation_type ? "selected" : ""}>${escapeHtml(relationOptionLabel(item))}</option>`).join("")}
      </select>
      <small class="wizard-help">关系类型必须已存在于关系类型 YAML 中。</small>
      <label>关系来源</label>
      <input value="显式关系，将写入 YAML" disabled>
      <label>附加属性 JSON</label>
      <textarea id="edgeProps" rows="6" placeholder="{}">{}</textarea>
    </div>
  `;
  openModal(async () => {
    const source = el("edgeSource").value.trim();
    const target = el("edgeTarget").value.trim();
    const relationType = el("edgeRelation").value.trim();
    const props = JSON.parse(el("edgeProps").value || "{}");
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

function startEdgeCreation(initialSource = "") {
  if (!state.editMode) return;
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
