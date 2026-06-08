const NODE_TYPES = [
  "ObjectType",
  "Attribute",
  "RelationType",
  "QueryCapability",
  "SkillCapability",
  "IntentProfile",
  "DataSource",
  "DataTable",
  "DataField",
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
    "input_params",
    "supported_attributes",
    "provides_fact_types",
    "output_attributes",
    "related_queries",
    "target_object_type",
  ],
  ObjectType: ["object_type", "object_type_zh", "description", "enabled"],
  Attribute: [
    "attribute_name",
    "attribute_name_zh",
    "object_type",
    "object_types",
    "data_type",
    "value_type",
    "description",
    "enabled",
  ],
  IntentProfile: ["intent_name", "trigger_aliases", "default_attributes", "skill_priorities"],
  QueryCapability: ["query_id", "query_name", "description", "input_params", "required_params", "optional_params", "output_attributes"],
  DataTable: ["table_name", "table_name_zh", "description"],
  DataField: ["field_name", "field_name_zh", "data_type", "semantic_type", "description"],
  DataSource: ["source_id", "source_type", "enabled", "description", "tables"],
  RelationType: ["relation_type", "from_object_type", "to_object_type", "description", "direction", "enabled"],
  PeriodVariant: ["code", "name_zh", "aliases", "table_suffix", "field_replacement"],
  InstanceRule: ["rule_id", "enabled", "source_tables", "object_type", "relation_type", "description"],
  Parameter: ["parameter_name"],
  Edge: ["edge_id", "source", "target", "relation_type"],
};

const VIEW_LABELS = {
  overview: "概览",
  requirement: "需求定位",
  skill: "Skill 设计",
  object_attribute: "对象属性",
  table_mapping: "表字段映射",
  full: "全图，高级模式",
};

const DEFAULT_LAYOUT_BY_VIEW = {
  overview: "concentric",
  requirement: "breadthfirst",
  skill: "cose",
  object_attribute: "breadthfirst",
  table_mapping: "breadthfirst",
  full: "cose",
};

const state = {
  viewMode: "requirement",
  query: "",
  focusId: "",
  depth: 2,
  includeFields: false,
  includeInferred: false,
  showEdgeLabels: false,
  relationFilter: "",
  selectedNodeId: "",
};

let cy;
let currentGraph = { nodes: [], edges: [], summary: { node_count: 0, edge_count: 0 }, search_results: [] };
let selected = null;
let edgeCreationSource = null;

const el = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  bindEvents();
  syncControls();
  refreshAll();
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
          label: "data(short_label)",
          "font-size": 10,
          "text-wrap": "none",
          "text-valign": "center",
          "text-halign": "center",
          width: "mapData(degree, 1, 80, 42, 82)",
          height: "mapData(degree, 1, 80, 34, 68)",
          "border-width": 1.5,
          "border-color": "#ffffff",
          color: "#1f2937",
          "background-color": "#a3aab8",
          "overlay-padding": 4,
        },
      },
      { selector: "node.hide-label", style: { label: "" } },
      { selector: "node.hide-label.selected-node, node.hide-label.neighbor-node", style: { label: "data(short_label)" } },
      { selector: 'node[type = "ObjectType"]', style: { "background-color": "#78aee8", shape: "ellipse" } },
      { selector: 'node[type = "Attribute"]', style: { "background-color": "#76c89b", shape: "round-rectangle" } },
      { selector: 'node[type = "SkillCapability"]', style: { "background-color": "#b79add", shape: "round-rectangle" } },
      { selector: 'node[type = "QueryCapability"]', style: { "background-color": "#e3ad62", shape: "hexagon" } },
      { selector: 'node[type = "IntentProfile"]', style: { "background-color": "#df8181", shape: "diamond" } },
      { selector: 'node[type = "DataTable"]', style: { "background-color": "#8fa3b8", shape: "rectangle" } },
      { selector: 'node[type = "DataField"]', style: { "background-color": "#e5e7eb", shape: "round-rectangle" } },
      { selector: 'node[type = "DataSource"]', style: { "background-color": "#82b5ad", shape: "barrel" } },
      { selector: 'node[type = "RelationType"]', style: { "background-color": "#475569", color: "#ffffff" } },
      { selector: 'node[type = "PeriodVariant"]', style: { "background-color": "#e7d85f", shape: "vee" } },
      { selector: 'node[type = "InstanceRule"]', style: { "background-color": "#9a6d3f", color: "#ffffff", shape: "tag" } },
      { selector: 'node[type = "Parameter"]', style: { "background-color": "#cbd5e1", shape: "rhomboid" } },
      { selector: 'node[enabled = false]', style: { opacity: 0.42 } },
      {
        selector: "edge",
        style: {
          width: 1.2,
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
      { selector: "edge.hover, edge:selected, edge.show-label", style: { label: "data(label)", opacity: 1 } },
      { selector: "edge:selected", style: { "line-color": "#2563eb", "target-arrow-color": "#2563eb", width: 2.2 } },
      { selector: ".faded", style: { opacity: 0.12, "text-opacity": 0.12 } },
      { selector: ".selected-node", style: { opacity: 1, "border-width": 4, "border-color": "#2563eb" } },
      { selector: ".neighbor-node", style: { opacity: 1, "border-width": 2, "border-color": "#0f172a" } },
      { selector: ".neighbor-edge", style: { opacity: 0.9, width: 2, "line-color": "#2563eb", "target-arrow-color": "#2563eb" } },
      { selector: ".faded-relation", style: { opacity: 0.08 } },
    ],
  });

  cy.on("tap", "node", (event) => {
    const node = event.target;
    if (edgeCreationSource && edgeCreationSource !== node.id()) {
      openEdgeDialog(edgeCreationSource, node.id());
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
    if (event.target === cy) {
      clearHighlight();
      selected = null;
      state.selectedNodeId = "";
      renderEmptyInspector();
      updateSelectedRelationSummary(null);
    }
  });
}

function bindEvents() {
  el("refreshBtn").addEventListener("click", refreshAll);
  el("layoutSelect").addEventListener("change", runLayout);
  el("saveBtn").addEventListener("click", saveSelected);
  el("saveSelectedBtn").addEventListener("click", saveSelected);
  el("deleteSelectedBtn").addEventListener("click", deleteSelected);
  el("validateBtn").addEventListener("click", validateOntology);
  el("seedBtn").addEventListener("click", seedOntology);
  el("searchBtn").addEventListener("click", search);
  el("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") search();
  });
  el("addNodeBtn").addEventListener("click", openAddNodeDialog);
  el("addEdgeBtn").addEventListener("click", startEdgeCreation);
  el("modeSelect").addEventListener("change", () => setViewMode(el("modeSelect").value));
  el("depthSelect").addEventListener("change", () => {
    state.depth = Number(el("depthSelect").value);
    loadGraphView();
  });
  el("includeInferred").addEventListener("change", () => {
    state.includeInferred = el("includeInferred").checked;
    loadGraphView();
  });
  el("includeFields").addEventListener("change", () => {
    state.includeFields = el("includeFields").checked;
    loadGraphView();
  });
  el("showEdgeLabels").addEventListener("change", () => {
    state.showEdgeLabels = el("showEdgeLabels").checked;
    applyEdgeLabelMode();
  });
  el("overviewBtn").addEventListener("click", () => setViewMode("overview"));
  el("requirementBtn").addEventListener("click", () => setViewMode("requirement"));
  el("skillBtn").addEventListener("click", () => setViewMode("skill"));
  el("objectAttributeBtn").addEventListener("click", () => setViewMode("object_attribute"));
  el("tableMappingBtn").addEventListener("click", () => setViewMode("table_mapping"));
  el("fullBtn").addEventListener("click", () => setViewMode("full"));
  el("toggleLeftBtn").addEventListener("click", () => toggleShellClass("left-collapsed"));
  el("toggleRightBtn").addEventListener("click", () => toggleShellClass("right-collapsed"));
  el("focusModeBtn").addEventListener("click", enterFocusMode);
  el("exitFocusBtn").addEventListener("click", exitFocusMode);
}

async function refreshAll() {
  await Promise.all([loadFiles(), loadGraphView()]);
}

async function loadFiles() {
  const res = await api("/api/files");
  el("ontologyRoot").textContent = `ontology: ${res.ontology_root}`;
  el("fileList").innerHTML = res.files
    .map((file) => {
      const cls = file.exists && !file.error ? "" : "file-missing";
      const suffix = file.error ? ` - ${file.error}` : file.modified_at || "missing";
      return `<div class="${cls}">${escapeHtml(file.name)}<br>${escapeHtml(suffix)}</div>`;
    })
    .join("");
}

async function loadGraphView() {
  const params = new URLSearchParams({
    view_mode: state.viewMode,
    depth: String(state.depth),
    include_fields: String(state.includeFields),
    include_inferred: String(state.includeInferred),
  });
  if (state.query) params.set("q", state.query);
  if (state.focusId) params.set("focus_id", state.focusId);
  currentGraph = await api(`/api/graph?${params.toString()}`);
  renderGraph();
  renderSearchResults(currentGraph.search_results || []);
  updateCounts();
  updateRelationSummary();
  writeOutput({ summary: currentGraph.summary, search_results: currentGraph.search_results, hidden_counts: currentGraph.hidden_counts });
  if (state.focusId) centerNode(state.focusId);
}

function renderGraph() {
  selected = null;
  cy.elements().remove();
  cy.add([...currentGraph.nodes, ...currentGraph.edges]);
  applyEdgeLabelMode();
  applyLargeGraphLabelMode();
  applyRelationFilter();
  runLayout();
  renderEmptyInspector();
}

function runLayout() {
  const name = el("layoutSelect").value;
  const options = {
    name,
    animate: false,
    fit: true,
    padding: 48,
    eles: cy.elements(),
  };
  if (name === "breadthfirst") {
    Object.assign(options, { directed: true, spacingFactor: 1.25, avoidOverlap: true });
  }
  if (name === "concentric") {
    Object.assign(options, { minNodeSpacing: 48, concentric: (node) => node.degree() });
  }
  if (name === "cose") {
    Object.assign(options, { idealEdgeLength: 130, nodeOverlap: 20, refresh: 20 });
  }
  cy.layout(options).run();
}

function selectElement(ele) {
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

function clearHighlight() {
  cy.elements().removeClass("selected-node neighbor-node neighbor-edge faded show-label");
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
  state.focusId = nodeId;
  state.depth = depth;
  syncControls();
  await loadGraphView();
}

async function expandOneHop(nodeId) {
  await focusOnNode(nodeId, 1);
}

async function expandTwoHop(nodeId) {
  await focusOnNode(nodeId, 2);
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

async function backToRequirementView() {
  state.viewMode = "requirement";
  state.focusId = "";
  state.includeFields = false;
  state.includeInferred = false;
  setDefaultLayoutForView();
  syncControls();
  await loadGraphView();
}

function showNodeInspector(node) {
  const data = node.data();
  el("inspectorTitle").textContent = data.id;
  el("inspectorMeta").textContent = `${data.type} / degree ${data.degree || 0}${data.field_count ? ` / ${data.field_count} fields` : ""}`;
  renderBasicInfo(data);
  setRaw(data.raw || {});
  buildQuickForm(data.type, data.raw || {});
  renderInspectorActions(data);
  showRelatedEdges(data.id);
  showFieldList(data);
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
  el("inspectorMeta").textContent = `${data.origin} edge / ${data.source} -> ${data.target}`;
  renderBasicInfo({
    id: data.id,
    type: "Edge",
    label: data.label,
    enabled: true,
    source_file: data.origin === "explicit" ? "schema_graph_edges.yaml" : data.raw?.from_file || "inferred",
  });
  setRaw(raw);
  buildQuickForm("Edge", raw);
  renderInspectorActions(null);
  showRelatedEdges(null);
  el("fieldList").innerHTML = "";
}

function renderEmptyInspector() {
  el("inspectorTitle").textContent = "未选择";
  el("inspectorMeta").textContent = "";
  el("contextActions").innerHTML = "";
  el("basicInfo").innerHTML = `<div class="muted">点击节点或边查看详情</div>`;
  el("quickForm").innerHTML = "";
  el("relatedEdges").innerHTML = "";
  el("fieldList").innerHTML = "";
  setRaw({});
}

function renderBasicInfo(data) {
  const raw = data.raw || {};
  const name = data.label || raw.skill_name || raw.object_type_zh || raw.attribute_name_zh || raw.query_name || raw.intent_name || data.id;
  const rows = [
    ["id", data.id],
    ["type", data.type],
    ["name", name],
    ["enabled", String(data.enabled !== false)],
    ["source yaml file", data.source_file || raw.from_file || "-"],
  ];
  el("basicInfo").innerHTML = rows
    .map(([key, value]) => `<div>${escapeHtml(key)}</div><strong>${escapeHtml(value)}</strong>`)
    .join("");
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
    `<button id="tableMappingBtnLocal">表字段映射</button>`,
    `<button id="backRequirementBtn">回到需求视图</button>`,
  ];
  if (data.type === "DataTable") {
    buttons.splice(2, 0, `<button id="expandFieldsBtn">展开字段</button>`);
  }
  box.innerHTML = buttons.join("");
  el("focusOneHopBtn").addEventListener("click", () => expandOneHop(data.id));
  el("focusTwoHopBtn").addEventListener("click", () => expandTwoHop(data.id));
  el("tableMappingBtnLocal").addEventListener("click", () => viewTableMapping(data.id));
  el("backRequirementBtn").addEventListener("click", backToRequirementView);
  if (data.type === "DataTable") {
    el("expandFieldsBtn").addEventListener("click", () => expandFields(data.id));
  }
}

function buildQuickForm(type, raw) {
  const fields = QUICK_FIELDS[type] || Object.keys(raw);
  const box = el("quickForm");
  box.innerHTML = "";
  fields.forEach((field) => {
    const label = document.createElement("label");
    label.textContent = field;
    if (typeof raw[field] === "boolean") {
      const select = document.createElement("select");
      select.dataset.field = field;
      select.innerHTML = `<option value="true">true</option><option value="false">false</option>`;
      select.value = String(raw[field]);
      box.append(label, select);
      return;
    }
    const input = document.createElement(field === "description" || typeof raw[field] === "object" ? "textarea" : "input");
    input.dataset.field = field;
    input.value = formatFormValue(raw[field]);
    box.append(label, input);
  });
}

function showRelatedEdges(nodeId) {
  const box = el("relatedEdges");
  if (!nodeId) {
    box.innerHTML = "";
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
      <button data-action="edit">编辑</button>
      <button data-action="delete" ${data.origin === "explicit" ? "" : "disabled"}>删除</button>
      <button data-action="jump">跳转</button>
    `;
    item.querySelector('[data-action="edit"]').addEventListener("click", () => selectElement(edge));
    item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteEdge(edge));
    item.querySelector('[data-action="jump"]').addEventListener("click", () => jumpToNode(otherId));
    box.appendChild(item);
  });
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
    item.addEventListener("click", () => {
      const fieldNodeId = `DataField:${data.identity}.${fieldName}`;
      jumpToNode(fieldNodeId);
    });
    box.appendChild(item);
  });
}

async function jumpToNode(nodeId) {
  const node = cy.getElementById(nodeId);
  if (node.length) {
    centerNode(nodeId);
  } else {
    await focusOnNode(nodeId, 2);
  }
}

async function saveSelected() {
  if (!selected) return;
  let raw;
  try {
    raw = readInspectorPayload();
  } catch (error) {
    writeOutput({ error: error.message });
    return;
  }
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
    el("lastSaved").textContent = `last saved: ${new Date().toLocaleString()}`;
    writeOutput(result);
    await loadGraphView();
  } catch (error) {
    writeOutput({ error: error.message, detail: error.detail });
  }
}

async function deleteSelected() {
  if (!selected) return;
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
    await loadGraphView();
  } catch (error) {
    const force =
      error.status === 409 &&
      confirm("节点仍有关联边。是否 force=true 删除节点并同步删除 schema_graph_edges.yaml 中相关显式边？");
    if (force) {
      const result = await api(`/api/graph/node/${encodeURIComponent(id)}?force=true`, { method: "DELETE" });
      writeOutput(result);
      selected = null;
      state.focusId = "";
      state.selectedNodeId = "";
      await loadGraphView();
    } else {
      writeOutput({ error: error.message, detail: error.detail });
    }
  }
}

async function deleteEdge(edge) {
  const id = edge.id();
  if (edge.data("origin") !== "explicit") {
    writeOutput({ error: "inferred edge 不能直接删除，请修改对应 YAML 来源。" });
    return;
  }
  if (!confirm(`确认删除显式边 ${id} ?`)) return;
  try {
    const result = await api(`/api/graph/edge/${encodeURIComponent(id)}`, { method: "DELETE" });
    writeOutput(result);
    selected = null;
    await loadGraphView();
  } catch (error) {
    writeOutput({ error: error.message, detail: error.detail });
  }
}

async function validateOntology() {
  const result = await api("/api/validate", { method: "POST" });
  el("validationStatus").textContent = result.ok
    ? `validation: ok (${result.warnings.length} warnings)`
    : `validation: ${result.errors.length} errors`;
  writeOutput(result);
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
  state.includeInferred = false;
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
      <span>${escapeHtml(item.type)} · ${escapeHtml(item.id)}</span>
      <em>matched: ${escapeHtml(item.matched_field || "-")}</em>
    `;
    btn.addEventListener("click", async () => {
      state.focusId = item.id;
      state.depth = 2;
      syncControls();
      await loadGraphView();
    });
    box.appendChild(btn);
  });
}

function setViewMode(viewMode) {
  state.viewMode = viewMode;
  state.focusId = "";
  state.query = "";
  state.relationFilter = "";
  state.includeFields = false;
  state.includeInferred = false;
  setDefaultLayoutForView();
  syncControls();
  loadGraphView();
}

function setDefaultLayoutForView() {
  el("layoutSelect").value = DEFAULT_LAYOUT_BY_VIEW[state.viewMode] || "cose";
}

function syncControls() {
  el("modeSelect").value = state.viewMode;
  el("depthSelect").value = String(state.depth);
  el("includeFields").checked = state.includeFields;
  el("includeInferred").checked = state.includeInferred;
  el("showEdgeLabels").checked = state.showEdgeLabels;
  el("searchInput").value = state.query;
}

function updateCounts() {
  const summary = currentGraph.summary || {};
  const hidden = currentGraph.hidden_counts || {};
  const warning = (summary.node_count || 0) > 80 ? " · 当前子图较大，建议使用搜索或 focus 模式" : "";
  el("nodeCount").textContent = `nodes: ${summary.node_count || 0}/${summary.total_node_count || 0}`;
  el("edgeCount").textContent = `edges: ${summary.edge_count || 0}/${summary.total_edge_count || 0}`;
  el("viewStatus").textContent = `${VIEW_LABELS[state.viewMode]} / hidden fields: ${hidden.data_fields || 0} / hidden inferred: ${hidden.inferred_edges || 0}`;
  el("canvasStatus").textContent = `${summary.node_count || 0} nodes · ${summary.edge_count || 0} edges · hidden fields ${hidden.data_fields || 0} · hidden inferred ${hidden.inferred_edges || 0}${warning}`;
}

function updateRelationSummary() {
  const groups = currentGraph.relation_groups || {};
  renderRelationGroupList(el("relationSummary"), groups, (type) => {
    state.relationFilter = state.relationFilter === type ? "" : type;
    applyRelationFilter();
    updateRelationSummary();
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
      counts[type] = (counts[type] || 0) + 1;
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
    btn.innerHTML = `<span>${escapeHtml(type)}</span><strong>${count}</strong>`;
    btn.addEventListener("click", () => onClick(type));
    box.appendChild(btn);
  });
}

function applyRelationFilter() {
  cy.edges().removeClass("faded-relation");
  if (state.relationFilter) {
    cy.edges().filter((edge) => edge.data("type") !== state.relationFilter).addClass("faded-relation");
  }
}

function applyEdgeLabelMode() {
  cy.edges().removeClass("show-label");
  if (state.showEdgeLabels) cy.edges().addClass("show-label");
}

function applyLargeGraphLabelMode() {
  cy.nodes().removeClass("hide-label");
  if ((currentGraph.summary?.node_count || 0) > 80) {
    cy.nodes().addClass("hide-label");
  }
}

function toggleShellClass(className) {
  document.querySelector(".app-shell").classList.toggle(className);
  setTimeout(() => cy.resize().fit(undefined, 48), 160);
}

function enterFocusMode() {
  const shell = document.querySelector(".app-shell");
  shell.classList.add("focus-mode");
  el("exitFocusBtn").hidden = false;
  setTimeout(() => cy.resize().fit(undefined, 48), 160);
}

function exitFocusMode() {
  const shell = document.querySelector(".app-shell");
  shell.classList.remove("focus-mode");
  el("exitFocusBtn").hidden = true;
  setTimeout(() => cy.resize().fit(undefined, 48), 160);
}

function openAddNodeDialog() {
  const body = el("modalBody");
  el("modalTitle").textContent = "新增节点";
  body.innerHTML = `
    <label>node_type</label>
    <select id="newNodeType">${NODE_TYPES.map((type) => `<option>${type}</option>`).join("")}</select>
    <label>node_id</label>
    <input id="newNodeId" placeholder="例如 get_fund_metric_values">
    <label>data JSON</label>
    <textarea id="newNodeJson" rows="10">{}</textarea>
  `;
  openModal(async () => {
    const nodeType = el("newNodeType").value;
    const nodeId = el("newNodeId").value.trim();
    const data = JSON.parse(el("newNodeJson").value || "{}");
    const result = await api("/api/graph/node", {
      method: "POST",
      body: JSON.stringify({ node_type: nodeType, node_id: nodeId, data }),
    });
    writeOutput(result);
    await loadGraphView();
  });
}

function startEdgeCreation() {
  if (selected && selected.isNode()) {
    edgeCreationSource = selected.id();
    writeOutput({ message: `source selected: ${edgeCreationSource}. Click target node.` });
  } else {
    writeOutput({ message: "请先选中 source 节点，再点击创建边。" });
  }
}

function openEdgeDialog(source, target) {
  const body = el("modalBody");
  el("modalTitle").textContent = "创建边";
  body.innerHTML = `
    <label>source</label><input id="edgeSource" value="${escapeHtml(source)}">
    <label>target</label><input id="edgeTarget" value="${escapeHtml(target)}">
    <label>relation_type</label><input id="edgeRelation" placeholder="必须存在于 relation_types.yaml">
    <label>properties JSON</label><textarea id="edgeProps" rows="8">{"score": 0.9}</textarea>
  `;
  openModal(async () => {
    const props = JSON.parse(el("edgeProps").value || "{}");
    const result = await api("/api/graph/edge", {
      method: "POST",
      body: JSON.stringify({
        source: el("edgeSource").value.trim(),
        target: el("edgeTarget").value.trim(),
        relation_type: el("edgeRelation").value.trim(),
        properties: props,
      }),
    });
    writeOutput(result);
    await loadGraphView();
  });
}

function openModal(onOk) {
  const modal = el("modal");
  const okBtn = el("modalOkBtn");
  const handler = async (event) => {
    event.preventDefault();
    try {
      await onOk();
      modal.close();
    } catch (error) {
      writeOutput({ error: error.message, detail: error.detail });
    } finally {
      okBtn.removeEventListener("click", handler);
    }
  };
  okBtn.addEventListener("click", handler);
  modal.showModal();
}

function readInspectorPayload() {
  const raw = JSON.parse(el("rawEditor").value || "{}");
  document.querySelectorAll("#quickForm [data-field]").forEach((input) => {
    raw[input.dataset.field] = parseFormValue(input.value, raw[input.dataset.field]);
  });
  return raw;
}

function setRaw(raw) {
  el("rawEditor").value = JSON.stringify(raw, null, 2);
}

function parseFormValue(text, original) {
  const trimmed = text.trim();
  if (typeof original === "boolean") return trimmed === "true";
  if (Array.isArray(original) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
    return trimmed ? JSON.parse(trimmed) : [];
  }
  if (original && typeof original === "object") {
    return trimmed ? JSON.parse(trimmed) : {};
  }
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

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
