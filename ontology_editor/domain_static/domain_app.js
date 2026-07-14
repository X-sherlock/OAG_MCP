"use strict";

const state = {
  config: null,
  domains: [],
  domainInput: null,
  loadedDomainInput: null,
  domainInputApplied: true,
  formMode: "new",
  currentPlan: null,
  currentDomainId: "",
  currentDomainVersionId: "",
  expandedDomainId: "",
  versionDialogDomainId: "",
  selectedVersionId: "",
  selectedVersionEdgeId: "",
  currentGraph: null,
  selectedElement: null,
  loadingState: "",
  cy: null,
  graphExpanded: false,
  graphHeight: 820,
  graphSpacing: 1,
  versionDetailCollapsed: false,
  versionDetailWidth: 400,
  refillActionsVisible: false,
  objectRowsCollapsed: false,
  attributeRowsCollapsed: false,
  modalResolve: null,
  feedbackText: "",
  lastPlanFeedback: "",
  planDiff: null,
  llmProvider: "configured",
  lightAppPrompt: "",
  lightAppSessionId: "",
  lightAppSessionContext: "",
  ddlDocuments: [],
  ddlAnalysis: null,
  ddlAnalysisRevision: 0,
  activeLlmRequestId: "",
  activeLlmController: null,
  cancellingLlm: false,
};

const examples = {
  repair: {
    domain_name: "售后维修",
    description: "售后维修领域，描述客户提交维修单、工程师处理维修单、设备关联故障。",
    objects: [
      { object_type: "Customer", object_type_zh: "客户", description: "提交维修申请的用户。" },
      { object_type: "RepairOrder", object_type_zh: "维修单", description: "售后维修服务单据。" },
      { object_type: "Engineer", object_type_zh: "工程师", description: "负责维修处理的人员。" },
    ],
    attributes: [
      { attribute_name: "order_status", attribute_name_zh: "维修单状态", object_types: ["RepairOrder"], value_type: "string", description: "维修单当前状态。" },
      { attribute_name: "fault_type", attribute_name_zh: "故障类型", object_types: ["RepairOrder"], value_type: "string", description: "设备故障分类。" },
      { attribute_name: "engineer_level", attribute_name_zh: "工程师等级", object_types: ["Engineer"], value_type: "string", description: "工程师技能等级。" },
    ],
    bulk_text: "客户提交维修单，维修单分配给工程师处理，维修单记录故障类型和处理状态。",
  },
  commerce: {
    domain_name: "电商订单",
    description: "电商交易订单领域，包含用户下单、订单支付、商品明细、物流配送和售后退款。",
    objects: [
      { object_type: "Customer", object_type_zh: "客户", description: "发起交易的用户。" },
      { object_type: "Order", object_type_zh: "订单", description: "交易主单。" },
      { object_type: "Product", object_type_zh: "商品", description: "订单中的商品。" },
      { object_type: "Payment", object_type_zh: "支付记录", description: "订单支付信息。" },
      { object_type: "Shipment", object_type_zh: "物流单", description: "订单配送信息。" },
    ],
    attributes: [
      { attribute_name: "order_status", attribute_name_zh: "订单状态", object_types: ["Order"], value_type: "string", description: "订单处理状态。" },
      { attribute_name: "order_amount", attribute_name_zh: "订单金额", object_types: ["Order"], value_type: "number", description: "订单总金额。" },
      { attribute_name: "payment_status", attribute_name_zh: "支付状态", object_types: ["Payment"], value_type: "string", description: "支付处理状态。" },
      { attribute_name: "tracking_number", attribute_name_zh: "运单号", object_types: ["Shipment"], value_type: "string", description: "物流追踪号。" },
    ],
    bulk_text: "客户可以创建多个订单；订单包含多个商品；订单支付后生成支付记录；发货后生成物流单。",
  },
  course: {
    domain_name: "在线课程",
    description: "在线教育课程学习领域，描述学生选课、观看课程、提交作业、教师批改和成绩反馈。",
    objects: [
      { object_type: "Student", object_type_zh: "学生", description: "学习课程的用户。" },
      { object_type: "Course", object_type_zh: "课程", description: "在线课程。" },
      { object_type: "Lesson", object_type_zh: "课时", description: "课程下的教学单元。" },
      { object_type: "Assignment", object_type_zh: "作业", description: "课程作业。" },
      { object_type: "Teacher", object_type_zh: "教师", description: "课程教师。" },
    ],
    attributes: [
      { attribute_name: "course_level", attribute_name_zh: "课程难度", object_types: ["Course"], value_type: "string", description: "课程难度等级。" },
      { attribute_name: "lesson_duration", attribute_name_zh: "课时时长", object_types: ["Lesson"], value_type: "number", description: "课时持续时间。" },
      { attribute_name: "assignment_status", attribute_name_zh: "作业状态", object_types: ["Assignment"], value_type: "string", description: "作业提交状态。" },
    ],
    bulk_text: "学生报名课程；课程由多个课时组成；课程包含作业；教师批改作业并反馈成绩。",
  },
  bond: {
    domain_name: "债券投资分析",
    description: "本领域用于描述债券从发行、上市交易、评级跟踪、价格行情、收益率计算、投资组合持仓到风险监控的核心对象和关系。系统需要能够识别债券、发行主体、担保主体、承销商、评级机构、交易市场、行情报价、投资组合、投资者、交易记录、收益率曲线和风险指标之间的关系，并支持围绕债券收益、价格波动、信用风险、久期风险、评级变化、持仓敞口等问题进行查询和分析。",
    objects: [
      { object_type: "Bond", object_type_zh: "债券", description: "固定收益类证券，包含债券代码、债券名称、期限、票面利率、付息方式、到期日等基础信息。" },
      { object_type: "Issuer", object_type_zh: "发行主体", description: "发行债券的企业、金融机构、地方政府或其他机构。" },
      { object_type: "Guarantor", object_type_zh: "担保主体", description: "为债券偿付提供担保的机构，可为空。" },
      { object_type: "Underwriter", object_type_zh: "承销商", description: "负责债券发行承销、销售或簿记建档的金融机构。" },
      { object_type: "CreditRating", object_type_zh: "信用评级", description: "评级机构对债券或发行主体给出的信用等级及评级展望。" },
      { object_type: "RatingAgency", object_type_zh: "评级机构", description: "提供债券评级、主体评级、评级调整和评级报告的机构。" },
      { object_type: "BondMarket", object_type_zh: "交易市场", description: "债券挂牌和交易的市场，例如银行间市场、交易所市场。" },
      { object_type: "BondQuote", object_type_zh: "债券行情", description: "某只债券在某个交易日、某个市场上的价格、收益率、成交量等行情数据。" },
      { object_type: "BondTransaction", object_type_zh: "债券交易", description: "投资者或组合买入、卖出债券形成的交易记录。" },
      { object_type: "BondHolding", object_type_zh: "债券持仓", description: "投资组合或投资者当前持有某只债券的数量、市值、成本和浮盈亏。" },
      { object_type: "BondPortfolio", object_type_zh: "债券组合", description: "由多只债券构成的投资组合，用于分析收益、风险和资产配置。" },
      { object_type: "Investor", object_type_zh: "投资者", description: "持有或交易债券的个人、机构或账户主体。" },
      { object_type: "YieldCurve", object_type_zh: "收益率曲线", description: "不同期限债券对应的市场收益率曲线，用于估值和利率风险分析。" },
      { object_type: "RiskIndicator", object_type_zh: "风险指标", description: "债券或组合的久期、凸性、信用利差、到期收益率、最大回撤等指标。" },
      { object_type: "CashflowSchedule", object_type_zh: "现金流计划", description: "债券未来付息、本金兑付、提前赎回等现金流安排。" },
      { object_type: "DefaultEvent", object_type_zh: "违约事件", description: "债券或发行主体发生的本金违约、利息违约、展期、重组等信用事件。" },
    ],
    attributes: [
      { attribute_name: "bond_code", attribute_name_zh: "债券代码", object_types: ["Bond"], value_type: "string", description: "债券在市场中的唯一代码。" },
      { attribute_name: "bond_name", attribute_name_zh: "债券名称", object_types: ["Bond"], value_type: "string", description: "债券简称或全称。" },
      { attribute_name: "bond_type", attribute_name_zh: "债券类型", object_types: ["Bond"], value_type: "string", description: "国债、地方债、金融债、企业债、公司债、可转债等。" },
      { attribute_name: "issue_date", attribute_name_zh: "发行日期", object_types: ["Bond"], value_type: "date", description: "债券正式发行的日期。" },
      { attribute_name: "maturity_date", attribute_name_zh: "到期日期", object_types: ["Bond"], value_type: "date", description: "债券本金最终兑付日期。" },
      { attribute_name: "coupon_rate", attribute_name_zh: "票面利率", object_types: ["Bond"], value_type: "number", description: "债券约定的年化票面利率。" },
      { attribute_name: "coupon_type", attribute_name_zh: "付息方式", object_types: ["Bond"], value_type: "string", description: "固定利率、浮动利率、贴现债、零息债等。" },
      { attribute_name: "face_value", attribute_name_zh: "面值", object_types: ["Bond"], value_type: "number", description: "单张债券的票面本金金额。" },
      { attribute_name: "remaining_term", attribute_name_zh: "剩余期限", object_types: ["Bond"], value_type: "number", description: "距离债券到期日的剩余时间。" },
      { attribute_name: "issuer_id", attribute_name_zh: "发行主体编号", object_types: ["Issuer"], value_type: "string", description: "发行主体的唯一标识。" },
      { attribute_name: "issuer_name", attribute_name_zh: "发行主体名称", object_types: ["Issuer"], value_type: "string", description: "发行债券的机构名称。" },
      { attribute_name: "issuer_type", attribute_name_zh: "发行主体类型", object_types: ["Issuer"], value_type: "string", description: "企业、金融机构、政府平台、地方政府等。" },
      { attribute_name: "industry", attribute_name_zh: "所属行业", object_types: ["Issuer"], value_type: "string", description: "发行主体所属行业。" },
      { attribute_name: "region", attribute_name_zh: "所属地区", object_types: ["Issuer"], value_type: "string", description: "发行主体注册地或主要经营地区。" },
      { attribute_name: "ownership_type", attribute_name_zh: "企业性质", object_types: ["Issuer"], value_type: "string", description: "国有企业、民营企业、央企、地方国企等。" },
      { attribute_name: "guarantor_id", attribute_name_zh: "担保主体编号", object_types: ["Guarantor"], value_type: "string", description: "担保主体的唯一标识。" },
      { attribute_name: "guarantor_name", attribute_name_zh: "担保主体名称", object_types: ["Guarantor"], value_type: "string", description: "为债券提供担保的机构名称。" },
      { attribute_name: "guarantee_type", attribute_name_zh: "担保方式", object_types: ["Guarantor"], value_type: "string", description: "全额担保、连带责任担保、抵押担保、质押担保等。" },
      { attribute_name: "guarantee_amount", attribute_name_zh: "担保金额", object_types: ["Guarantor"], value_type: "number", description: "担保覆盖的本金或本息金额。" },
      { attribute_name: "underwriter_id", attribute_name_zh: "承销商编号", object_types: ["Underwriter"], value_type: "string", description: "承销商的唯一标识。" },
      { attribute_name: "underwriter_name", attribute_name_zh: "承销商名称", object_types: ["Underwriter"], value_type: "string", description: "承销机构名称。" },
      { attribute_name: "underwriter_role", attribute_name_zh: "承销角色", object_types: ["Underwriter"], value_type: "string", description: "主承销商、联席主承销商、副主承销商、簿记管理人等。" },
      { attribute_name: "rating_id", attribute_name_zh: "评级编号", object_types: ["CreditRating"], value_type: "string", description: "单条评级记录的唯一标识。" },
      { attribute_name: "rating_target_type", attribute_name_zh: "评级对象类型", object_types: ["CreditRating"], value_type: "string", description: "债项评级或主体评级。" },
      { attribute_name: "rating_level", attribute_name_zh: "评级等级", object_types: ["CreditRating"], value_type: "string", description: "AAA、AA+、AA、A+ 等信用等级。" },
      { attribute_name: "rating_outlook", attribute_name_zh: "评级展望", object_types: ["CreditRating"], value_type: "string", description: "稳定、正面、负面、列入观察等。" },
      { attribute_name: "rating_date", attribute_name_zh: "评级日期", object_types: ["CreditRating"], value_type: "date", description: "评级结果生效或发布的日期。" },
      { attribute_name: "agency_id", attribute_name_zh: "评级机构编号", object_types: ["RatingAgency"], value_type: "string", description: "评级机构唯一标识。" },
      { attribute_name: "agency_name", attribute_name_zh: "评级机构名称", object_types: ["RatingAgency"], value_type: "string", description: "提供评级服务的机构名称。" },
      { attribute_name: "market_id", attribute_name_zh: "市场编号", object_types: ["BondMarket"], value_type: "string", description: "交易市场唯一标识。" },
      { attribute_name: "market_name", attribute_name_zh: "市场名称", object_types: ["BondMarket"], value_type: "string", description: "银行间市场、上交所、深交所、北交所等。" },
      { attribute_name: "listing_date", attribute_name_zh: "上市日期", object_types: ["BondMarket"], value_type: "date", description: "债券在该市场开始交易的日期。" },
      { attribute_name: "quote_id", attribute_name_zh: "行情编号", object_types: ["BondQuote"], value_type: "string", description: "行情记录唯一标识。" },
      { attribute_name: "trade_date", attribute_name_zh: "交易日期", object_types: ["BondQuote"], value_type: "date", description: "行情对应的交易日。" },
      { attribute_name: "clean_price", attribute_name_zh: "净价", object_types: ["BondQuote"], value_type: "number", description: "不含应计利息的债券价格。" },
      { attribute_name: "full_price", attribute_name_zh: "全价", object_types: ["BondQuote"], value_type: "number", description: "包含应计利息的债券价格。" },
      { attribute_name: "yield_to_maturity", attribute_name_zh: "到期收益率", object_types: ["BondQuote"], value_type: "number", description: "按当前价格持有至到期的年化收益率。" },
      { attribute_name: "volume", attribute_name_zh: "成交量", object_types: ["BondQuote"], value_type: "number", description: "当日成交数量或成交面额。" },
      { attribute_name: "transaction_id", attribute_name_zh: "交易编号", object_types: ["BondTransaction"], value_type: "string", description: "单笔交易记录唯一标识。" },
      { attribute_name: "transaction_date", attribute_name_zh: "交易日期", object_types: ["BondTransaction"], value_type: "date", description: "买入或卖出发生日期。" },
      { attribute_name: "transaction_type", attribute_name_zh: "交易方向", object_types: ["BondTransaction"], value_type: "string", description: "买入、卖出、回购、赎回等。" },
      { attribute_name: "transaction_price", attribute_name_zh: "交易价格", object_types: ["BondTransaction"], value_type: "number", description: "交易成交价格。" },
      { attribute_name: "transaction_amount", attribute_name_zh: "交易金额", object_types: ["BondTransaction"], value_type: "number", description: "交易对应的金额。" },
      { attribute_name: "holding_id", attribute_name_zh: "持仓编号", object_types: ["BondHolding"], value_type: "string", description: "持仓记录唯一标识。" },
      { attribute_name: "holding_quantity", attribute_name_zh: "持仓数量", object_types: ["BondHolding"], value_type: "number", description: "当前持有债券数量或面额。" },
      { attribute_name: "holding_cost", attribute_name_zh: "持仓成本", object_types: ["BondHolding"], value_type: "number", description: "当前持仓的成本金额。" },
      { attribute_name: "market_value", attribute_name_zh: "持仓市值", object_types: ["BondHolding"], value_type: "number", description: "按最新行情估算的持仓价值。" },
      { attribute_name: "unrealized_pnl", attribute_name_zh: "浮动盈亏", object_types: ["BondHolding"], value_type: "number", description: "当前持仓未实现收益或亏损。" },
      { attribute_name: "portfolio_id", attribute_name_zh: "组合编号", object_types: ["BondPortfolio"], value_type: "string", description: "投资组合唯一标识。" },
      { attribute_name: "portfolio_name", attribute_name_zh: "组合名称", object_types: ["BondPortfolio"], value_type: "string", description: "债券组合名称。" },
      { attribute_name: "portfolio_type", attribute_name_zh: "组合类型", object_types: ["BondPortfolio"], value_type: "string", description: "自营组合、理财组合、基金组合、保险资管组合等。" },
      { attribute_name: "nav", attribute_name_zh: "组合净值", object_types: ["BondPortfolio"], value_type: "number", description: "组合当前净值。" },
      { attribute_name: "investor_id", attribute_name_zh: "投资者编号", object_types: ["Investor"], value_type: "string", description: "投资者或账户唯一标识。" },
      { attribute_name: "investor_name", attribute_name_zh: "投资者名称", object_types: ["Investor"], value_type: "string", description: "投资者、机构或账户名称。" },
      { attribute_name: "investor_type", attribute_name_zh: "投资者类型", object_types: ["Investor"], value_type: "string", description: "银行、基金、保险、券商、个人等。" },
      { attribute_name: "curve_id", attribute_name_zh: "曲线编号", object_types: ["YieldCurve"], value_type: "string", description: "收益率曲线唯一标识。" },
      { attribute_name: "curve_date", attribute_name_zh: "曲线日期", object_types: ["YieldCurve"], value_type: "date", description: "收益率曲线对应日期。" },
      { attribute_name: "curve_type", attribute_name_zh: "曲线类型", object_types: ["YieldCurve"], value_type: "string", description: "国债收益率曲线、信用债收益率曲线、同业存单曲线等。" },
      { attribute_name: "tenor", attribute_name_zh: "期限点", object_types: ["YieldCurve"], value_type: "string", description: "1M、3M、1Y、3Y、5Y、10Y 等期限。" },
      { attribute_name: "curve_yield", attribute_name_zh: "曲线收益率", object_types: ["YieldCurve"], value_type: "number", description: "该期限点对应的市场收益率。" },
      { attribute_name: "risk_id", attribute_name_zh: "风险指标编号", object_types: ["RiskIndicator"], value_type: "string", description: "风险指标记录唯一标识。" },
      { attribute_name: "indicator_date", attribute_name_zh: "指标日期", object_types: ["RiskIndicator"], value_type: "date", description: "风险指标计算日期。" },
      { attribute_name: "duration", attribute_name_zh: "久期", object_types: ["RiskIndicator"], value_type: "number", description: "衡量债券价格对利率变化敏感程度的指标。" },
      { attribute_name: "convexity", attribute_name_zh: "凸性", object_types: ["RiskIndicator"], value_type: "number", description: "衡量久期随收益率变化而变化的指标。" },
      { attribute_name: "credit_spread", attribute_name_zh: "信用利差", object_types: ["RiskIndicator"], value_type: "number", description: "债券收益率相对无风险收益率的利差。" },
      { attribute_name: "max_drawdown", attribute_name_zh: "最大回撤", object_types: ["RiskIndicator"], value_type: "number", description: "债券或组合在一段时间内的最大跌幅。" },
      { attribute_name: "cashflow_id", attribute_name_zh: "现金流编号", object_types: ["CashflowSchedule"], value_type: "string", description: "现金流计划唯一标识。" },
      { attribute_name: "payment_date", attribute_name_zh: "支付日期", object_types: ["CashflowSchedule"], value_type: "date", description: "付息或兑付发生日期。" },
      { attribute_name: "payment_type", attribute_name_zh: "支付类型", object_types: ["CashflowSchedule"], value_type: "string", description: "利息、本金、提前赎回、回售等。" },
      { attribute_name: "payment_amount", attribute_name_zh: "支付金额", object_types: ["CashflowSchedule"], value_type: "number", description: "计划支付的现金流金额。" },
      { attribute_name: "default_id", attribute_name_zh: "违约事件编号", object_types: ["DefaultEvent"], value_type: "string", description: "违约事件唯一标识。" },
      { attribute_name: "default_date", attribute_name_zh: "违约日期", object_types: ["DefaultEvent"], value_type: "date", description: "违约或风险事件发生日期。" },
      { attribute_name: "default_type", attribute_name_zh: "违约类型", object_types: ["DefaultEvent"], value_type: "string", description: "本金违约、利息违约、展期、交叉违约等。" },
      { attribute_name: "default_amount", attribute_name_zh: "违约金额", object_types: ["DefaultEvent"], value_type: "number", description: "涉及违约的本金或利息金额。" },
      { attribute_name: "resolution_status", attribute_name_zh: "处置状态", object_types: ["DefaultEvent"], value_type: "string", description: "未处置、展期、重组、部分兑付、已兑付等。" },
    ],
    bulk_text: "债券由发行主体发行；发行主体可以发行多只债券；债券可以有一个或多个承销商参与发行；承销商在债券发行中承担主承销、联席主承销或簿记管理等角色；债券可以由担保主体提供担保；一个担保主体可以为多只债券提供担保；债券在一个或多个交易市场挂牌交易；交易市场产生债券行情；债券行情记录债券在某个交易日的净价、全价、到期收益率和成交量；评级机构对发行主体进行主体评级；评级机构也可以对具体债券进行债项评级；同一只债券在不同日期可以有多条信用评级记录；信用评级变化会影响债券的信用风险判断；投资者可以创建或管理债券组合；债券组合持有多只债券；债券持仓记录组合对某只债券的持仓数量、成本、市值和浮动盈亏；投资者通过债券交易买入或卖出债券；债券交易会改变债券持仓；债券未来会产生付息、本金兑付、回售或提前赎回等现金流；现金流计划属于具体债券；收益率曲线描述不同期限的市场收益率；债券估值和风险分析可以参考收益率曲线；风险指标可以针对单只债券计算，也可以针对债券组合计算；风险指标包括久期、凸性、信用利差、到期收益率、最大回撤等；发行主体或债券发生违约事件时，需要记录违约类型、违约金额和处置状态；违约事件会影响债券评级、债券价格、持仓风险和组合风险敞口。",
  },
};

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", async () => {
  initGraph();
  restoreProviderSettings();
  bindEvents();
  resetRows();
  renderDdlDocuments();
  await refreshBootstrap();
});

function bindEvents() {
  document.querySelectorAll("[data-provider]").forEach((button) => {
    button.addEventListener("click", () => setLlmProvider(button.dataset.provider));
  });
  $("configStatus").addEventListener("click", openLlmConfigDialog);
  $("llmConfigCloseBtn").addEventListener("click", closeLlmConfigDialog);
  $("llmConfigCancelBtn").addEventListener("click", closeLlmConfigDialog);
  $("llmConfigSaveBtn").addEventListener("click", saveLlmConfig);
  $("llmConfigDialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeLlmConfigDialog();
  });
  $("copyLightAppPromptBtn").addEventListener("click", copyLightAppPrompt);
  $("ddlFiles").addEventListener("change", (event) => addDdlFiles(event.target.files));
  $("clearDdlFilesBtn").addEventListener("click", clearDdlFiles);
  bindDdlDropzone();
  $("cancelLlmBtn").addEventListener("click", cancelActiveLlmRequest);
  $("addObjectRowBtn").addEventListener("click", () => {
    state.objectRowsCollapsed = false;
    renderObjectRows([...readObjectRows(), blankObject()]);
  });
  $("addAttributeRowBtn").addEventListener("click", () => {
    state.attributeRowsCollapsed = false;
    renderAttributeRows([...readAttributeRows(), blankAttribute()]);
  });
  $("runPlanBtn").addEventListener("click", () => runPlan(false));
  $("updateRefilledPlanBtn").addEventListener("click", () => runPlan(true));
  $("createRefilledPlanBtn").addEventListener("click", () => runPlan(false, { createNewDomain: true }));
  $("generateYamlBtn").addEventListener("click", generateYaml);
  $("viewPlanBtn").addEventListener("click", openPlanDialog);
  $("toggleGraphBtn").addEventListener("click", () => setGraphExpanded(!state.graphExpanded, true));
  $("graphSpacingRange").addEventListener("input", () => setGraphSpacing(Number($("graphSpacingRange").value || 1)));
  bindGraphResize();
  $("graphApplyInputBtn").addEventListener("click", applyLoadedDomainInput);
  $("graphRegeneratePlanBtn").addEventListener("click", () => runPlan(true));
  $("refreshDomainsBtn").addEventListener("click", refreshDomains);
  $("resetBtn").addEventListener("click", resetPage);
  $("addNodeBtn").addEventListener("click", () => openNodeDialog());
  $("addEdgeBtn").addEventListener("click", () => openEdgeDialog());
  $("planDialogCloseBtn").addEventListener("click", closePlanDialog);
  $("planDialogCancelBtn").addEventListener("click", closePlanDialog);
  $("planDialogRegenerateBtn").addEventListener("click", () => {
    closePlanDialog();
    runPlan(true);
  });
  $("planDialogGenerateBtn").addEventListener("click", generateYaml);
  $("versionDialogCloseBtn").addEventListener("click", closeVersionDialog);
  bindVersionDetailResize();
  bindVersionGraphPan();
  $("closeDrawerBtn").addEventListener("click", closeDrawer);
  $("dialogCloseBtn").addEventListener("click", closeDialog);
  $("dialogCancelBtn").addEventListener("click", closeDialog);
  $("appModalCloseBtn").addEventListener("click", () => closeAppModal(null));
  $("appModal").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeAppModal(null);
  });
  bindFeedbackInput("feedbackText");
  bindFeedbackInput("graphFeedbackText");
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => fillExample(button.dataset.example));
  });
}

async function refreshBootstrap() {
  await Promise.all([refreshConfig(), refreshDomains(), refreshLightAppPrompt()]);
}

async function refreshConfig() {
  try {
    state.config = await api("/api/domain-ontology/config-status");
    const node = $("configStatus");
    $("configuredProviderHint").textContent = state.config.configured
      ? `${state.config.model || "兼容模型"} · 服务端配置已就绪`
      : `服务端配置未完成：${state.config.error || state.config.config_path || "请检查配置文件"}`;
    renderProviderStatus(node);
  } catch (error) {
    showToast(error.message);
  }
}

function restoreProviderSettings() {
  const savedProvider = localStorage.getItem("domainOntology.llmProvider") || "configured";
  state.llmProvider = savedProvider === "light_app" ? "innovation_factory" : savedProvider;
  $("lightAppUrl").value = localStorage.getItem("domainOntology.lightAppUrl") || "";
  $("lightAppCancelUrl").value = localStorage.getItem("domainOntology.lightAppCancelUrl") || "";
  $("lightAppApiKey").value = sessionStorage.getItem("domainOntology.lightAppApiKey") || "";
  setLlmProvider(state.llmProvider);
}

function persistProviderSettings() {
  localStorage.setItem("domainOntology.llmProvider", state.llmProvider);
  localStorage.setItem("domainOntology.lightAppUrl", $("lightAppUrl").value.trim());
  localStorage.setItem("domainOntology.lightAppCancelUrl", $("lightAppCancelUrl").value.trim());
  sessionStorage.setItem("domainOntology.lightAppApiKey", $("lightAppApiKey").value);
  renderProviderStatus($("configStatus"));
}

function setLlmProvider(provider) {
  state.llmProvider = provider === "innovation_factory" ? "innovation_factory" : "configured";
  document.querySelectorAll("[data-provider]").forEach((button) => {
    button.classList.toggle("active", button.dataset.provider === state.llmProvider);
    button.setAttribute("aria-selected", button.dataset.provider === state.llmProvider ? "true" : "false");
  });
  $("configuredProviderPanel").classList.toggle("hidden", state.llmProvider !== "configured");
  $("lightAppProviderPanel").classList.toggle("hidden", state.llmProvider !== "innovation_factory");
  if (state.config) renderProviderStatus($("configStatus"));
}

function renderProviderStatus(node) {
  if (!node) return;
  const factoryReady = Boolean($("lightAppUrl")?.value.trim());
  const ready = state.llmProvider === "innovation_factory" ? factoryReady : Boolean(state.config?.configured);
  node.textContent = state.llmProvider === "innovation_factory" ? "创新工厂API" : "大模型API";
  node.className = `status-pill api-status-btn ${ready ? "ready" : "blocked"}`;
  node.title = ready
    ? "当前接入配置已就绪，点击修改"
    : "当前接入配置不完整，点击设置";
}

function openLlmConfigDialog() {
  restoreProviderSettings();
  if (!$("llmConfigDialog").open) $("llmConfigDialog").showModal();
}

function closeLlmConfigDialog() {
  restoreProviderSettings();
  if ($("llmConfigDialog").open) $("llmConfigDialog").close();
}

function saveLlmConfig() {
  if (state.llmProvider === "innovation_factory" && !$("lightAppUrl").value.trim()) {
    showToast("请填写创新工厂服务地址");
    return;
  }
  resetLightAppSession();
  persistProviderSettings();
  if ($("llmConfigDialog").open) $("llmConfigDialog").close();
  showToast("大模型接入配置已保存");
}

async function refreshLightAppPrompt() {
  try {
    const result = await api("/api/domain-ontology/light-app-prompt");
    state.lightAppPrompt = result.prompt || "";
    $("lightAppPromptText").textContent = state.lightAppPrompt || "提示词未配置";
  } catch (error) {
    $("lightAppPromptText").textContent = `提示词加载失败：${error.message}`;
  }
}

async function copyLightAppPrompt() {
  if (!state.lightAppPrompt) return;
  try {
    await navigator.clipboard.writeText(state.lightAppPrompt);
    $("copyLightAppPromptBtn").textContent = "已复制";
    window.setTimeout(() => { $("copyLightAppPromptBtn").textContent = "复制提示词"; }, 1400);
  } catch (error) {
    showToast("复制失败，请从提示词区域手动选择文本", { error: error.message });
  }
}

function readLlmSettings(requestId) {
  if (state.llmProvider === "configured") {
    if (!state.config?.configured) throw new Error("现有兼容模型尚未完成服务端配置");
    return { provider: "configured", request_id: requestId };
  }
  const endpointUrl = $("lightAppUrl").value.trim();
  if (!endpointUrl) throw new Error("请先在右上角配置创新工厂服务地址");
  ensureLightAppSession(state.currentDomainId || "draft");
  return {
    provider: "innovation_factory",
    endpoint_url: endpointUrl,
    session_id: state.lightAppSessionId,
    cancel_url: $("lightAppCancelUrl").value.trim(),
    api_key: $("lightAppApiKey").value,
    request_id: requestId,
  };
}

function ensureLightAppSession(context = "draft", forceNew = false) {
  const sessionContext = context || "draft";
  if (forceNew || !state.lightAppSessionId || state.lightAppSessionContext !== sessionContext) {
    state.lightAppSessionId = createSessionId();
    state.lightAppSessionContext = sessionContext;
  }
  return state.lightAppSessionId;
}

function resetLightAppSession() {
  state.lightAppSessionId = "";
  state.lightAppSessionContext = "";
}

async function refreshDomains() {
  try {
    const result = await api("/api/domain-ontology/domains");
    state.domains = result.domains || [];
    renderDomainList();
    if ($("versionDialog")?.open && state.versionDialogDomainId) {
      const domain = state.domains.find((item) => item.domain_id === state.versionDialogDomainId);
      if (domain) renderVersionDialog(domain);
    }
  } catch (error) {
    showToast(error.message);
  }
}

function renderDomainList() {
  const box = $("domainList");
  if (!state.domains.length) {
    box.innerHTML = `<div class="empty-state"><strong>暂无已生成领域</strong><span>确认生成后会显示在这里。</span></div>`;
    return;
  }
  box.innerHTML = state.domains.map((item) => `
    <button class="domain-item" type="button" data-domain-id="${escapeHtml(item.domain_id)}">
      <strong>${escapeHtml(item.domain_name || item.domain_id)}</strong>
      <span>${escapeHtml(item.domain_id)} · ${escapeHtml(item.modified_at || "")} · ${(item.versions || []).length} 个版本</span>
    </button>
  `).join("");
  box.querySelectorAll("[data-domain-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const domain = openVersionDialog(button.dataset.domainId);
      if (!domain) return;
      const versionId = currentViewedVersionForDomain(domain);
      if (versionId) await loadGraph(domain.domain_id, versionId, false, { scroll: false });
    });
  });
}

function openVersionDialog(domainId) {
  const domain = state.domains.find((item) => item.domain_id === domainId);
  if (!domain) return null;
  state.versionDialogDomainId = domainId;
  state.selectedVersionId = currentViewedVersionForDomain(domain);
  state.selectedVersionEdgeId = "";
  $("currentDomainStatus").textContent = `选择领域：${domain.domain_id}`;
  $("versionDialogTitle").textContent = domain.domain_name || domain.domain_id;
  $("versionDialogSubtitle").textContent = `${domain.domain_id} · ${(domain.versions || []).length} 个版本`;
  renderVersionDialog(domain);
  if (!$("versionDialog").open) $("versionDialog").showModal();
  return domain;
}

function closeVersionDialog() {
  if ($("versionDialog").open) $("versionDialog").close();
}

function syncVersionDialogLayout() {
  const body = $("versionDialog")?.querySelector(".version-dialog-body");
  if (!body) return;
  body.style.setProperty("--version-detail-width", `${state.versionDetailWidth}px`);
  body.classList.toggle("detail-collapsed", state.versionDetailCollapsed);
}

function setVersionDetailCollapsed(collapsed) {
  state.versionDetailCollapsed = collapsed;
  syncVersionDialogLayout();
  const button = $("versionDetailToggleBtn");
  if (button) button.textContent = collapsed ? "展开信息栏" : "收起信息栏";
}

function bindVersionDetailToggle() {
  const button = $("versionDetailToggleBtn");
  if (!button) return;
  button.textContent = state.versionDetailCollapsed ? "展开信息栏" : "收起信息栏";
  button.addEventListener("click", () => setVersionDetailCollapsed(!state.versionDetailCollapsed));
}

function bindVersionDetailResize() {
  const handle = $("versionDetailResizeHandle");
  const body = $("versionDialog")?.querySelector(".version-dialog-body");
  if (!handle || !body) return;
  let startX = 0;
  let startWidth = state.versionDetailWidth;
  handle.addEventListener("pointerdown", (event) => {
    if (state.versionDetailCollapsed) setVersionDetailCollapsed(false);
    startX = event.clientX;
    startWidth = state.versionDetailWidth;
    handle.setPointerCapture(event.pointerId);
    handle.classList.add("dragging");
    event.preventDefault();
  });
  handle.addEventListener("pointermove", (event) => {
    if (!handle.classList.contains("dragging")) return;
    const nextWidth = Math.max(300, Math.min(620, startWidth - (event.clientX - startX)));
    state.versionDetailWidth = Math.round(nextWidth);
    syncVersionDialogLayout();
  });
  const endDrag = (event) => {
    if (!handle.classList.contains("dragging")) return;
    handle.classList.remove("dragging");
    if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
  };
  handle.addEventListener("pointerup", endDrag);
  handle.addEventListener("pointercancel", endDrag);
  handle.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home"].includes(event.key)) return;
    event.preventDefault();
    if (state.versionDetailCollapsed) setVersionDetailCollapsed(false);
    if (event.key === "Home") state.versionDetailWidth = 400;
    if (event.key === "ArrowLeft") state.versionDetailWidth = Math.min(620, state.versionDetailWidth + 24);
    if (event.key === "ArrowRight") state.versionDetailWidth = Math.max(300, state.versionDetailWidth - 24);
    syncVersionDialogLayout();
  });
}

function bindVersionGraphPan() {
  const graph = $("versionGraph");
  if (!graph) return;
  let startX = 0;
  let startY = 0;
  let scrollLeft = 0;
  let scrollTop = 0;
  let dragging = false;
  graph.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    if (event.target.closest("button, textarea, input, select, a")) return;
    dragging = true;
    startX = event.clientX;
    startY = event.clientY;
    scrollLeft = graph.scrollLeft;
    scrollTop = graph.scrollTop;
    graph.setPointerCapture(event.pointerId);
    graph.classList.add("panning");
  });
  graph.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    graph.scrollLeft = scrollLeft - (event.clientX - startX);
    graph.scrollTop = scrollTop - (event.clientY - startY);
    event.preventDefault();
  });
  const endPan = (event) => {
    if (!dragging) return;
    dragging = false;
    graph.classList.remove("panning");
    if (graph.hasPointerCapture(event.pointerId)) graph.releasePointerCapture(event.pointerId);
  };
  graph.addEventListener("pointerup", endPan);
  graph.addEventListener("pointercancel", endPan);
}

function currentViewedVersionForDomain(domain) {
  if (state.currentDomainId === domain.domain_id && state.currentDomainVersionId) return state.currentDomainVersionId;
  return domain.current_version_id || (domain.versions || []).at(-1)?.version_id || "";
}

function renderVersionDialog(domain) {
  syncVersionDialogLayout();
  $("versionGraph").innerHTML = renderVersionTree(domain);
  bindVersionDialogEvents(domain);
  renderVersionDetail(domain);
}

function renderVersionTree(domain) {
  const versions = domain.versions || [];
  if (!versions.length) return `<div class="version-tree empty-state"><span>暂无版本</span></div>`;
  const layout = buildVersionTreeLayout(versions);
  return `
    <div class="version-tree version-map" style="width:${layout.width}px;height:${layout.height}px">
      <svg class="version-map-links" width="${layout.width}" height="${layout.height}" viewBox="0 0 ${layout.width} ${layout.height}" aria-hidden="true">
        <defs>
          <marker id="versionArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z"></path>
          </marker>
          <marker id="versionArrowDeleted" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z"></path>
          </marker>
        </defs>
        ${layout.edges.map((edge) => `
          <path class="version-link ${edge.version.deleted ? "deleted-version-link" : ""} ${edge.version.version_id === state.selectedVersionEdgeId ? "selected-version-link" : ""}" d="${escapeHtml(edge.path)}"></path>
          <path class="version-link-hit" d="${escapeHtml(edge.path)}" data-edge-version-id="${escapeHtml(edge.version.version_id)}"></path>
        `).join("")}
      </svg>
      ${layout.edges.map((edge) => `
        <button class="version-edge-label ${edge.version.deleted ? "deleted" : ""} ${edge.version.version_id === state.selectedVersionEdgeId ? "selected" : ""}" type="button" data-edge-version-id="${escapeHtml(edge.version.version_id)}" style="left:${edge.labelX}px;top:${edge.labelY}px">
          ${escapeHtml(edgeLabel(edge.version))}
        </button>
      `).join("")}
      ${layout.nodes.map((node) => {
        const version = node.version;
        return `
          <button class="version-node version-node-card ${version.deleted ? "deleted-version" : ""} ${version.version_id === state.selectedVersionId ? "viewing-version" : ""}" type="button" data-version-id="${escapeHtml(version.version_id)}" style="left:${node.x}px;top:${node.y}px">
            <span class="version-dot"></span>
            <strong>${escapeHtml(shortVersionId(version.version_id))}</strong>
            <em>${escapeHtml(version.created_at || "")}</em>
            <span class="version-badges">
              ${version.version_id === state.currentDomainVersionId && state.currentDomainId === domain.domain_id ? `<b class="viewing">正在查看</b>` : ""}
              ${!version.parent_version_id ? `<b class="root">初始</b>` : ""}
              ${version.deleted ? `<b class="deleted">已删除</b>` : ""}
            </span>
          </button>
        `;
      }).join("")}
    </div>
  `;
}

function buildVersionTreeLayout(versions) {
  const ordered = [...versions].sort((a, b) => String(a.created_at || "").localeCompare(String(b.created_at || "")));
  const versionById = new Map(ordered.map((version) => [version.version_id, version]));
  const childMap = new Map();
  ordered.forEach((version) => childMap.set(version.version_id, []));
  ordered.forEach((version) => {
    if (version.parent_version_id && childMap.has(version.parent_version_id)) {
      childMap.get(version.parent_version_id).push(version);
    }
  });
  childMap.forEach((children) => {
    children.sort((a, b) => String(a.created_at || "").localeCompare(String(b.created_at || "")));
  });

  const nodeWidth = 252;
  const nodeHeight = 86;
  const levelGap = 410;
  const rowGap = 178;
  const padding = 72;
  const nodes = [];
  const visited = new Set();
  let nextRow = 0;
  let maxDepth = 0;

  function place(version, depth) {
    if (!version || visited.has(version.version_id)) return null;
    visited.add(version.version_id);
    maxDepth = Math.max(maxDepth, depth);
    const children = childMap.get(version.version_id) || [];
    const childNodes = children.map((child) => place(child, depth + 1)).filter(Boolean);
    const y = childNodes.length
      ? Math.round((childNodes[0].y + childNodes[childNodes.length - 1].y) / 2)
      : padding + nextRow++ * rowGap;
    const node = { version, x: padding + depth * levelGap, y, width: nodeWidth, height: nodeHeight };
    nodes.push(node);
    return node;
  }

  const roots = ordered.filter((version) => !version.parent_version_id || !versionById.has(version.parent_version_id));
  roots.forEach((version) => place(version, 0));
  ordered.forEach((version) => {
    if (!visited.has(version.version_id)) place(version, 0);
  });

  const nodeById = new Map(nodes.map((node) => [node.version.version_id, node]));
  const edges = ordered
    .filter((version) => version.parent_version_id && nodeById.has(version.parent_version_id) && nodeById.has(version.version_id))
    .map((version) => {
      const parent = nodeById.get(version.parent_version_id);
      const child = nodeById.get(version.version_id);
      const sourceX = parent.x + nodeWidth;
      const sourceY = parent.y + nodeHeight / 2;
      const targetX = child.x;
      const targetY = child.y + nodeHeight / 2;
      const curve = Math.max(70, (targetX - sourceX) * 0.55);
      return {
        version,
        parent,
        child,
        path: `M ${sourceX} ${sourceY} C ${sourceX + curve} ${sourceY}, ${targetX - curve} ${targetY}, ${targetX} ${targetY}`,
        labelX: Math.round((sourceX + targetX) / 2 - 92),
        labelY: Math.round((sourceY + targetY) / 2 - 16),
      };
    });

  nodes.sort((a, b) => (a.x - b.x) || (a.y - b.y));
  return {
    nodes,
    edges,
    width: Math.max(980, padding * 2 + (maxDepth + 1) * nodeWidth + maxDepth * (levelGap - nodeWidth)),
    height: Math.max(620, padding * 2 + Math.max(1, nextRow) * rowGap),
  };
}

function edgeLabel(version) {
  const text = versionOperationText(version);
  return text.length > 18 ? `${text.slice(0, 18)}...` : text;
}

function versionOperationText(version) {
  return version.feedback
    || version.operation_summary
    || summarizeManualChange(version.manual_change)
    || version.summary
    || version.plan_summary
    || "无补充说明";
}

function summarizeManualChange(change) {
  if (!change || typeof change !== "object") return "";
  if (change.action === "upsert_node") return `新增/修改节点：${change.node_type || ""}:${change.node_id || ""}`;
  if (change.action === "delete_node") return `删除节点：${change.node_id || ""}`;
  if (change.action === "upsert_edge") return `新增/修改关系：${change.source || ""} -[${change.relation_type || ""}]-> ${change.target || ""}`;
  if (change.action === "delete_edge") return `删除关系：${change.edge_id || ""}`;
  return change.summary || change.action || "";
}

function bindVersionDialogEvents(domain) {
  $("versionGraph").querySelectorAll("[data-version-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedVersionId = button.dataset.versionId;
      state.selectedVersionEdgeId = "";
      renderVersionDialog(domain);
    });
  });
  $("versionGraph").querySelectorAll("[data-edge-version-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedVersionId = "";
      state.selectedVersionEdgeId = button.dataset.edgeVersionId;
      renderVersionDialog(domain);
    });
  });
}

function renderVersionDetail(domain) {
  const versions = domain.versions || [];
  const selectedVersion = versions.find((item) => item.version_id === state.selectedVersionId);
  const selectedEdge = versions.find((item) => item.version_id === state.selectedVersionEdgeId);
  if (selectedEdge) {
    $("versionDetail").className = "version-detail";
    $("versionDetail").innerHTML = renderVersionEdgeDetail(domain, selectedEdge);
    bindVersionDetailActions(domain);
    bindVersionDetailToggle();
    return;
  }
  if (!selectedVersion) {
    $("versionDetail").className = "version-detail empty-state";
    $("versionDetail").innerHTML = `${renderVersionDetailToggle()}<strong>选择一个版本或箭头</strong><span>点击版本节点查看 commit 留言；点击箭头查看本次迭代反馈。</span>`;
    bindVersionDetailToggle();
    return;
  }
  $("versionDetail").className = "version-detail";
  $("versionDetail").innerHTML = renderVersionCommitDetail(domain, selectedVersion);
  bindVersionDetailActions(domain);
  bindVersionDetailToggle();
}

function renderVersionDetailToggle() {
  return `<button type="button" id="versionDetailToggleBtn" class="version-detail-toggle">${state.versionDetailCollapsed ? "展开信息栏" : "收起信息栏"}</button>`;
}

function renderVersionCommitDetail(domain, version) {
  return `
    ${renderVersionDetailToggle()}
    <div class="version-detail-head">
      <strong>${escapeHtml(shortVersionId(version.version_id))}</strong>
      <span>${version.deleted ? "已删除版本" : "版本详情"}</span>
    </div>
    <dl class="version-meta">
      <dt>版本 ID</dt><dd>${escapeHtml(version.version_id)}</dd>
      <dt>父版本</dt><dd>${escapeHtml(version.parent_version_id || "无")}</dd>
      <dt>创建时间</dt><dd>${escapeHtml(version.created_at || "-")}</dd>
      <dt>Commit 留言</dt><dd>${escapeHtml(version.summary || "未提供摘要")}</dd>
      <dt>规划摘要</dt><dd>${escapeHtml(version.plan_summary || "未保存规划摘要")}</dd>
      ${version.deleted ? `<dt>删除时间</dt><dd>${escapeHtml(version.deleted_at || "-")}</dd>` : ""}
    </dl>
    <label>版本备注
      <textarea id="versionNoteText" rows="4" placeholder="为这个版本补充备注">${escapeHtml(version.note || "")}</textarea>
    </label>
    <div class="version-detail-actions">
      <button type="button" id="saveVersionNoteBtn">保存备注</button>
      ${version.deleted ? "" : `<button type="button" id="loadVersionBtn" class="primary-btn">加载此版本</button>`}
      ${version.deleted ? "" : `<button type="button" id="deleteVersionBtn" class="danger-btn">删除此版本</button>`}
    </div>
  `;
}

function renderVersionEdgeDetail(domain, version) {
  const operationText = versionOperationText(version);
  const manualChange = version.manual_change && Object.keys(version.manual_change).length
    ? `<dt>手动变更内容</dt><dd><pre class="version-change-json">${escapeHtml(JSON.stringify(version.manual_change, null, 2))}</pre></dd>`
    : "";
  return `
    ${renderVersionDetailToggle()}
    <div class="version-detail-head">
      <strong>${escapeHtml(shortVersionId(version.parent_version_id || ""))} → ${escapeHtml(shortVersionId(version.version_id))}</strong>
      <span>本次迭代</span>
    </div>
    <dl class="version-meta">
      <dt>变更摘要</dt><dd>${escapeHtml(version.summary || "未提供摘要")}</dd>
      <dt>用户反馈/操作摘要</dt><dd>${escapeHtml(operationText)}</dd>
      ${manualChange}
      <dt>说明</dt><dd>${escapeHtml(version.change_type === "manual" ? "该版本由手动画布编辑生成。" : "该版本由规划反馈生成。")}</dd>
    </dl>
    <div class="version-detail-actions">
      ${version.deleted ? "" : `<button type="button" id="loadVersionBtn" class="primary-btn">加载子版本</button>`}
    </div>
  `;
}

function bindVersionDetailActions(domain) {
  const activeVersionId = state.selectedVersionId || state.selectedVersionEdgeId;
  const loadBtn = $("loadVersionBtn");
  if (loadBtn) {
    loadBtn.addEventListener("click", async () => {
      closeVersionDialog();
      await loadGraph(domain.domain_id, activeVersionId);
    });
  }
  const saveNoteBtn = $("saveVersionNoteBtn");
  if (saveNoteBtn) {
    saveNoteBtn.addEventListener("click", () => saveVersionNote(domain.domain_id, activeVersionId));
  }
  const deleteBtn = $("deleteVersionBtn");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", () => deleteVersion(domain.domain_id, activeVersionId));
  }
}

async function saveVersionNote(domainId, versionId) {
  if (!domainId || !versionId) return;
  try {
    setLoading(true, "正在保存备注", "正在写入版本备注。");
    await api(`/api/domain-ontology/${encodeURIComponent(domainId)}/version-note`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId, note: $("versionNoteText").value }),
    });
    await refreshDomains();
    const domain = state.domains.find((item) => item.domain_id === domainId);
    if (domain) {
      state.versionDialogDomainId = domainId;
      state.selectedVersionId = versionId;
      state.selectedVersionEdgeId = "";
      renderVersionDialog(domain);
    }
  } catch (error) {
    showToast(error.message, error.detail);
  } finally {
    setLoading(false);
  }
}

async function deleteVersion(domainId, versionId) {
  if (!domainId || !versionId) return;
  const mode = await openAppModal({
    title: "删除版本",
    message: `删除版本 ${versionId} 后，该版本会在版本树中置灰保留。请选择后续版本的处理方式。`,
    actions: [
      { value: "reparent", label: "后续承接前序版本", className: "primary-btn" },
      { value: "cascade", label: "一并删除后续版本", className: "danger-btn" },
      { value: null, label: "取消" },
    ],
  });
  if (!mode) return;
  try {
    setLoading(true, "正在删除版本", mode === "reparent" ? "正在标记删除并重接后续版本。" : "正在标记删除该版本及其后续版本。");
    const result = await api(`/api/domain-ontology/${encodeURIComponent(domainId)}/version/${encodeURIComponent(versionId)}?mode=${encodeURIComponent(mode)}`, { method: "DELETE" });
    await refreshDomains();
    const domain = state.domains.find((item) => item.domain_id === domainId);
    if (domain) {
      state.versionDialogDomainId = domainId;
      state.selectedVersionId = versionId;
      state.selectedVersionEdgeId = "";
      renderVersionDialog(domain);
    }
    if (state.currentDomainId === domainId && result.deleted_version_ids?.includes(state.currentDomainVersionId) && result.current_version_id) {
      await loadGraph(domainId, result.current_version_id);
    }
  } catch (error) {
    showToast(error.message, error.detail);
  } finally {
    setLoading(false);
  }
}

function shortVersionId(versionId) {
  const text = String(versionId || "");
  return text.length > 14 ? `${text.slice(0, 9)}…${text.slice(-4)}` : text || "-";
}

function resetRows() {
  state.objectRowsCollapsed = false;
  state.attributeRowsCollapsed = false;
  renderObjectRows([blankObject()]);
  renderAttributeRows([blankAttribute()]);
}

function resetPage() {
  clearDomainInputForm();
  setFeedbackText("");
  state.domainInput = null;
  state.loadedDomainInput = null;
  state.domainInputApplied = true;
  state.formMode = "new";
  state.currentPlan = null;
  state.currentDomainId = "";
  state.currentDomainVersionId = "";
  state.expandedDomainId = "";
  resetLightAppSession();
  setRefillPlanActions(false);
  $("currentDomainStatus").textContent = "未生成领域";
  $("generateYamlBtn").disabled = true;
  $("viewPlanBtn").disabled = true;
  $("graphApplyInputBtn").disabled = true;
  $("graphRegeneratePlanBtn").disabled = true;
  $("graphSpacingControl").classList.add("hidden");
  setStep("input");
  renderPlanEmpty();
  $("planStatusPanel").classList.add("hidden");
  showGraphFeedbackPanel(false);
  closePlanDialog();
}

function clearDomainInputForm() {
  $("domainName").value = "";
  $("domainDescription").value = "";
  $("bulkText").value = "";
  clearDdlFiles();
  resetRows();
}

function fillExample(name) {
  const data = examples[name];
  if (!data) return;
  const wasExistingMode = state.formMode === "existing" && Boolean(state.currentDomainId);
  applyDomainInput(data, true);
  setFeedbackText("");
  state.domainInput = null;
  state.domainInputApplied = true;
  state.lastPlanFeedback = "";
  state.planDiff = null;
  if (wasExistingMode) {
    setRefillPlanActions(true);
  } else {
    state.loadedDomainInput = null;
    state.formMode = "new";
    state.currentDomainId = "";
    state.currentDomainVersionId = "";
    state.expandedDomainId = "";
    resetLightAppSession();
    setRefillPlanActions(false);
    $("currentDomainStatus").textContent = "未生成领域";
  }
  setStep("input");
}

function applyDomainInput(data, collapseLargeLists = false) {
  $("domainName").value = data.domain_name || data.name || "";
  $("domainDescription").value = data.description || "";
  $("bulkText").value = data.bulk_text || "";
  state.ddlDocuments = (data.ddl_documents || []).map((item) => ({
    name: item.name || "uploaded.sql",
    content: item.content || "",
    size: byteLength(item.content || ""),
  }));
  renderDdlDocuments();
  analyzeDdlDocuments();
  state.objectRowsCollapsed = Boolean(collapseLargeLists && (data.objects || []).length > 6);
  state.attributeRowsCollapsed = Boolean(collapseLargeLists && (data.attributes || []).length > 10);
  renderObjectRows(data.objects?.length ? data.objects : [blankObject()]);
  renderAttributeRows(data.attributes?.length ? data.attributes : [blankAttribute()]);
}

function applyLoadedDomainInput() {
  if (!state.loadedDomainInput) return;
  applyDomainInput(state.loadedDomainInput, true);
  state.domainInput = state.loadedDomainInput;
  state.domainInputApplied = true;
  state.formMode = "existing";
  setRefillPlanActions(true);
  setStep("input");
  $("domainName").scrollIntoView({ behavior: "smooth", block: "center" });
}

function setRefillPlanActions(visible) {
  state.refillActionsVisible = Boolean(visible);
  $("runPlanBtn").classList.toggle("hidden", state.refillActionsVisible);
  $("refillPlanActions").classList.toggle("hidden", !state.refillActionsVisible);
}

function blankObject() {
  return { object_type: "", object_type_zh: "", description: "" };
}

function bindDdlDropzone() {
  const dropzone = $("ddlDropzone");
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragging");
    });
  });
  dropzone.addEventListener("drop", (event) => addDdlFiles(event.dataTransfer.files));
  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      $("ddlFiles").click();
    }
  });
}

async function addDdlFiles(fileList) {
  const files = [...(fileList || [])];
  if (!files.length) return;
  if (state.ddlDocuments.length + files.length > 200) {
    showToast("单次最多上传 200 个 DDL 文件");
    return;
  }
  try {
    const additions = await Promise.all(files.map(async (file) => ({
      name: file.name,
      content: await file.text(),
      size: file.size,
    })));
    const currentBytes = state.ddlDocuments.reduce((sum, item) => sum + byteLength(item.content), 0);
    const addedBytes = additions.reduce((sum, item) => sum + byteLength(item.content), 0);
    if (currentBytes + addedBytes > 5 * 1024 * 1024) throw new Error("DDL 文件总大小不能超过 5 MB");
    const byName = new Map(state.ddlDocuments.map((item) => [item.name, item]));
    additions.forEach((item) => byName.set(item.name, item));
    state.ddlDocuments = [...byName.values()];
    renderDdlDocuments();
    analyzeDdlDocuments();
  } catch (error) {
    showToast(error.message);
  } finally {
    $("ddlFiles").value = "";
  }
}

function clearDdlFiles() {
  state.ddlDocuments = [];
  state.ddlAnalysis = null;
  state.ddlAnalysisRevision += 1;
  $("ddlFiles").value = "";
  renderDdlDocuments();
  renderDdlAnalysis();
}

function renderDdlDocuments() {
  const totalBytes = state.ddlDocuments.reduce((sum, item) => sum + byteLength(item.content), 0);
  const summary = $("ddlFileSummary");
  summary.textContent = state.ddlDocuments.length
    ? `已选择 ${state.ddlDocuments.length} 个文件，共 ${formatBytes(totalBytes)}`
    : "尚未选择文件";
  summary.classList.toggle("empty", !state.ddlDocuments.length);
  $("clearDdlFilesBtn").disabled = !state.ddlDocuments.length;
  $("ddlFileList").innerHTML = state.ddlDocuments.map((item, index) => `
    <div class="ddl-file-chip">
      <span title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
      <small>${escapeHtml(formatBytes(byteLength(item.content)))}</small>
      <button type="button" data-remove-ddl="${index}" aria-label="移除 ${escapeHtml(item.name)}">×</button>
    </div>
  `).join("");
  $("ddlFileList").querySelectorAll("[data-remove-ddl]").forEach((button) => {
    button.addEventListener("click", () => {
      state.ddlDocuments.splice(Number(button.dataset.removeDdl), 1);
      renderDdlDocuments();
      analyzeDdlDocuments();
    });
  });
}

async function analyzeDdlDocuments() {
  const revision = ++state.ddlAnalysisRevision;
  if (!state.ddlDocuments.length) {
    state.ddlAnalysis = null;
    renderDdlAnalysis();
    return;
  }
  const panel = $("ddlAnalysisPanel");
  panel.classList.remove("hidden");
  $("ddlAnalysisStatus").className = "ddl-analysis-status";
  $("ddlAnalysisStatus").textContent = "正在解析表、字段和主外键...";
  $("ddlAnalysisMetrics").innerHTML = "";
  $("ddlAnalysisDiagnostics").classList.add("hidden");
  try {
    const result = await api("/api/domain-ontology/analyze-ddl", {
      method: "POST",
      body: JSON.stringify({
        ddl_documents: state.ddlDocuments.map((item) => ({ name: item.name, content: item.content })),
      }),
    });
    if (revision !== state.ddlAnalysisRevision) return;
    state.ddlAnalysis = { ...result.summary, diagnostics: result.diagnostics || [] };
    renderDdlAnalysis();
  } catch (error) {
    if (revision !== state.ddlAnalysisRevision) return;
    state.ddlAnalysis = { error: error.message, diagnostics: [] };
    renderDdlAnalysis();
  }
}

function renderDdlAnalysis() {
  const panel = $("ddlAnalysisPanel");
  if (!state.ddlDocuments.length) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  const analysis = state.ddlAnalysis;
  if (!analysis) return;
  const status = $("ddlAnalysisStatus");
  if (analysis.error) {
    status.className = "ddl-analysis-status warning";
    status.textContent = `DDL 分析失败：${analysis.error}`;
    $("ddlAnalysisMetrics").innerHTML = "";
    return;
  }
  status.className = `ddl-analysis-status ${analysis.diagnostic_count ? "warning" : "ready"}`;
  status.textContent = analysis.over_single_call_token_budget
    ? "DDL 已完成结构化压缩；输入规模较大，仍将使用完整上下文单次规划。"
    : "DDL 已完成结构化压缩，将通过完整上下文单次调用完成规划。";
  $("ddlAnalysisMetrics").innerHTML = [
    ["表 / 字段", `${analysis.table_count} / ${analysis.column_count}`],
    ["原始 / 压缩", `${formatBytes(analysis.raw_bytes)} / ${formatBytes(analysis.compact_bytes)}`],
    ["DDL 预计 Token", Number(analysis.estimated_tokens || 0).toLocaleString()],
    ["执行方式", "完整上下文单次调用"],
  ].map(([label, value]) => `
    <div class="ddl-analysis-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>
  `).join("");
  const diagnostics = analysis.diagnostics || [];
  const diagnosticsNode = $("ddlAnalysisDiagnostics");
  diagnosticsNode.classList.toggle("hidden", !diagnostics.length);
  diagnosticsNode.textContent = diagnostics.slice(0, 3).map((item) => `${item.file || "DDL"}：${item.message}`).join("；");
}

function byteLength(text) {
  return new TextEncoder().encode(String(text || "")).length;
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function blankAttribute() {
  return { attribute_name: "", attribute_name_zh: "", object_types: [], value_type: "string", description: "" };
}

function renderObjectRows(rows) {
  const limit = 6;
  const collapsed = state.objectRowsCollapsed && rows.length > limit;
  $("objectRows").innerHTML = `
    <div class="edit-row header"><span>对象标识</span><span>中文名</span><span>描述</span><span></span></div>
    ${rows.map((row, index) => `
      <div class="edit-row ${collapsed && index >= limit ? "collapsed-extra-row" : ""}" data-object-row>
        <input data-field="object_type" value="${escapeHtml(row.object_type || "")}" placeholder="RepairOrder">
        <input data-field="object_type_zh" value="${escapeHtml(row.object_type_zh || "")}" placeholder="维修单">
        <input data-field="description" value="${escapeHtml(row.description || "")}" placeholder="对象说明">
        <button type="button" data-remove-row="${index}">删除</button>
      </div>
    `).join("")}
    ${rows.length > limit ? renderCollapsedRowsNotice("object", rows.length, limit, collapsed) : ""}
  `;
  bindCollapsedRowsNotice("object");
  $("objectRows").querySelectorAll("[data-remove-row]").forEach((button) => {
    button.addEventListener("click", () => {
      const rows = readObjectRows().filter((_, index) => String(index) !== button.dataset.removeRow);
      renderObjectRows(rows.length ? rows : [blankObject()]);
      syncAttributeObjectOptions();
    });
  });
  $("objectRows").querySelectorAll("[data-field='object_type'], [data-field='object_type_zh']").forEach((input) => {
    input.addEventListener("input", syncAttributeObjectOptions);
  });
}

function renderAttributeRows(rows) {
  const objectRows = readObjectRows();
  const limit = 10;
  const collapsed = state.attributeRowsCollapsed && rows.length > limit;
  $("attributeRows").innerHTML = `
    <div class="edit-row header"><span>属性标识</span><span>中文名</span><span>所属对象</span><span>值类型</span><span>描述</span><span></span></div>
    ${rows.map((row, index) => `
      <div class="edit-row ${collapsed && index >= limit ? "collapsed-extra-row" : ""}" data-attribute-row>
        <input data-field="attribute_name" value="${escapeHtml(row.attribute_name || "")}" placeholder="order_status">
        <input data-field="attribute_name_zh" value="${escapeHtml(row.attribute_name_zh || "")}" placeholder="维修单状态">
        ${renderObjectTypeSelect(row, objectRows)}
        <input data-field="value_type" value="${escapeHtml(row.value_type || "string")}" placeholder="string">
        <input data-field="description" value="${escapeHtml(row.description || "")}" placeholder="属性说明">
        <button type="button" data-remove-row="${index}">删除</button>
      </div>
    `).join("")}
    ${rows.length > limit ? renderCollapsedRowsNotice("attribute", rows.length, limit, collapsed) : ""}
  `;
  bindCollapsedRowsNotice("attribute");
  $("attributeRows").querySelectorAll("[data-remove-row]").forEach((button) => {
    button.addEventListener("click", () => {
      const rows = readAttributeRows().filter((_, index) => String(index) !== button.dataset.removeRow);
      renderAttributeRows(rows.length ? rows : [blankAttribute()]);
    });
  });
}

function renderCollapsedRowsNotice(kind, total, visibleCount, collapsed) {
  const label = kind === "object" ? "对象" : "属性";
  return `
    <div class="collapsed-rows-notice">
      <span>${collapsed ? `已回填 ${total} 个${label}，当前显示前 ${visibleCount} 个。` : `已展开全部 ${total} 个${label}。`}</span>
      <button type="button" data-toggle-rows="${kind}">${collapsed ? "展开全部" : "收起列表"}</button>
    </div>
  `;
}

function bindCollapsedRowsNotice(kind) {
  const button = document.querySelector(`[data-toggle-rows="${kind}"]`);
  if (!button) return;
  button.addEventListener("click", () => {
    if (kind === "object") {
      state.objectRowsCollapsed = !state.objectRowsCollapsed;
      renderObjectRows(readObjectRows());
      syncAttributeObjectOptions();
    } else {
      state.attributeRowsCollapsed = !state.attributeRowsCollapsed;
      renderAttributeRows(readAttributeRows());
    }
  });
}

function renderObjectTypeSelect(row, objectRows) {
  const selected = firstObjectType(row.object_types);
  const options = objectRows.map((item) => {
    const value = item.object_type || "";
    const label = item.object_type_zh ? `${item.object_type_zh} (${item.object_type || "未填写标识"})` : value || "未命名对象";
    return `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""} ${value ? "" : "disabled"}>${escapeHtml(label)}</option>`;
  }).join("");
  const legacyOption = selected && !objectRows.some((item) => (item.object_type || "") === selected)
    ? `<option value="${escapeHtml(selected)}" selected>${escapeHtml(selected)}（未在对象列表中）</option>`
    : "";
  return `
    <select data-field="object_types">
      <option value="">请选择对象</option>
      ${legacyOption}
      ${options}
    </select>
  `;
}

function firstObjectType(value) {
  if (Array.isArray(value)) return value[0] || "";
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean)[0] || "";
}

function syncAttributeObjectOptions() {
  const rows = readAttributeRows();
  renderAttributeRows(rows.length ? rows : [blankAttribute()]);
}

function readObjectRows() {
  return [...document.querySelectorAll("[data-object-row]")].map(readRow).filter((row) => row.object_type || row.object_type_zh || row.description);
}

function readAttributeRows() {
  return [...document.querySelectorAll("[data-attribute-row]")].map((node) => {
    const row = readRow(node);
    row.object_types = row.object_types ? [row.object_types] : [];
    return row;
  }).filter((row) => row.attribute_name || row.attribute_name_zh || row.description);
}

function readRow(node) {
  const row = {};
  node.querySelectorAll("[data-field]").forEach((input) => {
    row[input.dataset.field] = input.value.trim();
  });
  return row;
}

function readDomainInput() {
  const domainName = $("domainName").value.trim();
  if (!domainName) throw new Error("请填写领域名称");
  const input = {
    domain_name: domainName,
    description: $("domainDescription").value.trim(),
    objects: readObjectRows(),
    attributes: readAttributeRows(),
    bulk_text: $("bulkText").value.trim(),
    ddl_documents: state.ddlDocuments.map((item) => ({ name: item.name, content: item.content })),
  };
  if (!input.description && !input.objects.length && !input.attributes.length && !input.bulk_text && !input.ddl_documents.length) {
    throw new Error("请至少填写领域说明、对象、属性、批量说明或上传 DDL 文件");
  }
  return input;
}

async function runPlan(isRegenerate, options = {}) {
  let submittedFeedback = "";
  let previousPlan = null;
  try {
    const createNewDomain = Boolean(options.createNewDomain);
    submittedFeedback = readFeedbackText();
    previousPlan = isRegenerate && !createNewDomain && state.currentPlan ? clonePlain(state.currentPlan) : null;
    if (!isRegenerate || createNewDomain) {
      state.currentDomainId = "";
      state.currentDomainVersionId = "";
      state.expandedDomainId = "";
      state.formMode = "new";
    }
    if (state.llmProvider === "innovation_factory") {
      ensureLightAppSession(state.currentDomainId || "draft", !isRegenerate || createNewDomain);
    }
    state.domainInput = readDomainInput();
    const ddlRunText = state.ddlDocuments.length
        ? "正在将压缩后的 DDL 结构提交给大模型规划。"
        : "大模型正在分析对象、属性和潜在关系。";
    setLoading(true, isRegenerate ? "正在重新规划" : "正在生成规划方案", ddlRunText);
    setStep("plan");
    const result = await requestDomainPlan("/api/domain-ontology/plan", {
      domain_input: state.domainInput,
      previous_plan: isRegenerate && !createNewDomain ? state.currentPlan : null,
      feedback: submittedFeedback,
    }, {
      domainInput: state.domainInput,
      previousPlan: isRegenerate && !createNewDomain ? state.currentPlan : null,
      feedback: submittedFeedback,
    });
    if (!result) return;
    applyPlanResult(result.plan, previousPlan, submittedFeedback, state.formMode === "existing");
  } catch (error) {
    if (!error.cancelled) showToast(error.message, error.detail);
  } finally {
    setLoading(false);
  }
}

async function requestDomainPlan(url, payload, repairContext) {
  try {
    return await callDomainPlanApi(url, payload);
  } catch (error) {
    if (error.cancelled) throw error;
    const repairPayload = error.detail?.repair_payload;
    if (!error.detail?.repairable || !repairPayload) throw error;
    setLoading(false);
    const action = await openAppModal({
      title: "规划结果解析失败",
      message: "大模型已经返回内容，但不是合法 JSON。是否将原始输出和解析错误交回大模型重新输出？",
      detail: { error: error.message, parse_error: repairPayload.parse_error },
      actions: [
        { value: "repair", label: "让大模型重新输出", className: "primary-btn" },
        { value: null, label: "取消" },
      ],
    });
    if (action !== "repair") return null;
    setLoading(true, "正在重新输出规划", "正在把上一次模型输出和解析错误交回大模型修复。");
    return callDomainPlanApi("/api/domain-ontology/plan-repair", {
      domain_input: repairContext.domainInput,
      previous_plan: repairContext.previousPlan,
      feedback: repairContext.feedback,
      repair_payload: repairPayload,
    });
  }
}

async function callDomainPlanApi(url, payload) {
  const requestId = createRequestId();
  const controller = new AbortController();
  const llm = readLlmSettings(requestId);
  state.activeLlmRequestId = requestId;
  state.activeLlmController = controller;
  state.cancellingLlm = false;
  syncCancelLlmControl();
  try {
    return await api(url, {
      method: "POST",
      body: JSON.stringify({ ...payload, llm }),
      signal: controller.signal,
    });
  } finally {
    if (state.activeLlmRequestId === requestId) {
      state.activeLlmRequestId = "";
      state.activeLlmController = null;
      state.cancellingLlm = false;
      syncCancelLlmControl();
    }
  }
}

function createRequestId() {
  if (window.crypto?.randomUUID) return `domain-${window.crypto.randomUUID()}`;
  return `domain-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createSessionId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  const bytes = new Uint8Array(16);
  window.crypto?.getRandomValues?.(bytes);
  if (!bytes.some((value) => value)) {
    for (let index = 0; index < bytes.length; index += 1) bytes[index] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function cancelActiveLlmRequest() {
  const requestId = state.activeLlmRequestId;
  if (!requestId || state.cancellingLlm) return;
  state.cancellingLlm = true;
  syncCancelLlmControl();
  $("loadingText").textContent = "正在关闭连接并向模型平台发送停止指令...";
  try {
    let result = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      result = await api("/api/domain-ontology/cancel", {
        method: "POST",
        body: JSON.stringify({ request_id: requestId }),
      });
      if (result.found) break;
      await new Promise((resolve) => window.setTimeout(resolve, 150));
    }
    state.activeLlmController?.abort();
    const stopText = result?.stop_command_sent
      ? "模型平台已接收停止指令。"
      : result?.stop_note || "当前连接已关闭。";
    setLoading(false);
    showToast("已中止本次模型调用", stopText);
  } catch (error) {
    state.cancellingLlm = false;
    syncCancelLlmControl();
    showToast("中止调用失败", error.detail || error.message);
  }
}

function syncCancelLlmControl() {
  const visible = Boolean(state.activeLlmRequestId) && !$("loadingOverlay").hidden;
  $("cancelLlmBtn").classList.toggle("hidden", !visible);
  $("cancelLlmHint").classList.toggle("hidden", !visible);
  $("cancelLlmBtn").disabled = state.cancellingLlm;
  $("cancelLlmBtn").textContent = state.cancellingLlm ? "正在中止..." : "中止模型调用";
}

function applyPlanResult(plan, previousPlan, submittedFeedback, keepExistingActions = false) {
  state.currentPlan = plan;
  state.planDiff = previousPlan ? diffPlans(previousPlan, plan) : null;
  state.lastPlanFeedback = submittedFeedback;
  setFeedbackText("");
  setRefillPlanActions(keepExistingActions);
  renderPlan(plan);
  openPlanDialog();
}

function renderPlanEmpty() {
  $("planContent").className = "plan-status-card empty-state";
  $("planContent").innerHTML = `<strong>等待生成规划方案</strong><span>填写领域对象、属性和业务说明后，点击“生成规划方案”。</span>`;
  $("planDialogBody").innerHTML = "";
  state.lastPlanFeedback = "";
  state.planDiff = null;
}

function renderPlan(plan) {
  const relationships = plan.relationships || [];
  $("planStatusPanel").classList.remove("hidden");
  $("planContent").className = "plan-status-card";
  $("planContent").innerHTML = `
    <strong>已生成规划方案</strong>
    <span>${escapeHtml(plan.summary_zh || "已生成规划方案。")}</span>
    <div class="metric-grid">
      <div class="metric"><span>对象</span><strong>${(plan.objects || []).length}</strong></div>
      <div class="metric"><span>属性</span><strong>${(plan.attributes || []).length}</strong></div>
      <div class="metric"><span>关系</span><strong>${relationships.length}</strong></div>
      <div class="metric"><span>问题</span><strong>${(plan.open_questions || []).length}</strong></div>
    </div>
  `;
  $("viewPlanBtn").disabled = false;
  $("generateYamlBtn").disabled = false;
  renderPlanDialog(plan);
}

function renderPlanDialog(plan) {
  const relationships = plan.relationships || [];
  const feedbackReference = state.lastPlanFeedback
    ? `<div class="plan-feedback-reference"><strong>本轮调整反馈</strong><p>${escapeHtml(state.lastPlanFeedback)}</p></div>`
    : "";
  $("planDialogBody").innerHTML = `
    <div class="plan-summary-block">
      <p>${escapeHtml(plan.summary_zh || "已生成规划方案。")}</p>
      <div class="metric-grid">
        <div class="metric"><span>对象</span><strong>${(plan.objects || []).length}</strong></div>
        <div class="metric"><span>属性</span><strong>${(plan.attributes || []).length}</strong></div>
        <div class="metric"><span>关系</span><strong>${relationships.length}</strong></div>
        <div class="metric"><span>问题</span><strong>${(plan.open_questions || []).length}</strong></div>
      </div>
    </div>
    ${feedbackReference}
    ${renderPlanDiffSummary(state.planDiff)}
    ${renderObjectAttributeReview(plan, state.planDiff)}
    ${renderRelationshipGroups(relationships, state.planDiff)}
    ${renderDeletedPlanItems(state.planDiff, plan)}
    ${renderQuestionSection("待确认事项", plan.open_questions || [])}
    ${renderQuestionSection("调整说明", plan.revision_notes || [])}
  `;
}

function renderObjectAttributeReview(plan, diff = null) {
  const objects = plan.objects || [];
  const attributes = plan.attributes || [];
  if (!objects.length && !attributes.length) return "";
  const objectCards = objects.map((object) => {
    const objectId = object.object_type || "";
    const rows = attributes.filter((attr) => (attr.object_types || []).includes(objectId));
    const status = diffStatus(diff, "objects", objectId);
    return `
      <article class="object-attribute-card ${diffClass(status)}">
        <div class="object-attribute-head">
          <strong>${escapeHtml(object.object_type_zh || objectId || "未命名对象")}${renderDiffBadge(status)}</strong>
          <code>${escapeHtml(objectId || "-")}</code>
        </div>
        <p>${escapeHtml(object.description || "未提供对象说明。")}</p>
        <div class="attribute-chip-list">
          ${rows.map((attr) => renderAttributeChip(attr, diff)).join("") || `<span class="muted-chip">暂无属性</span>`}
        </div>
      </article>
    `;
  }).join("");
  const assigned = new Set();
  objects.forEach((object) => {
    const objectId = object.object_type || "";
    attributes.forEach((attr) => {
      if ((attr.object_types || []).includes(objectId)) assigned.add(attr.attribute_name);
    });
  });
  const unassigned = attributes.filter((attr) => !assigned.has(attr.attribute_name));
  const unassignedCard = unassigned.length ? `
    <article class="object-attribute-card warning">
      <div class="object-attribute-head">
        <strong>未归属属性</strong>
        <code>${unassigned.length} 个</code>
      </div>
      <div class="attribute-chip-list">
        ${unassigned.map((attr) => renderAttributeChip(attr, diff)).join("")}
      </div>
    </article>
  ` : "";
  return `
    <section class="object-attribute-section">
      <div class="relation-group-head">
        <h3>对象包含的属性</h3>
        <span>${attributes.length} 个属性</span>
      </div>
      <div class="object-attribute-grid">
        ${objectCards}
        ${unassignedCard}
      </div>
    </section>
  `;
}

function renderAttributeChip(attr, diff = null) {
  const status = diffStatus(diff, "attributes", attr.attribute_name || "");
  return `
    <span class="attribute-chip ${diffClass(status)}">
      <strong>${escapeHtml(attr.attribute_name_zh || attr.attribute_name || "未命名属性")}${renderDiffBadge(status)}</strong>
      <em>${escapeHtml(attr.attribute_name || "-")}</em>
    </span>
  `;
}

function renderRelationshipGroups(relationships, diff = null) {
  if (!relationships.length) {
    return `<div class="empty-state"><strong>暂无关系</strong><span>补充业务规则后重新规划。</span></div>`;
  }
  const groups = [
    { key: "object", title: "对象关系", rows: [], groupedByAttribute: false },
    { key: "object_attribute", title: "对象-属性关系", rows: [], groupedByAttribute: false },
    { key: "attribute_source", title: "属性作为起点的关系", rows: [], groupedByAttribute: true },
  ];
  relationships.forEach((item) => {
    const sourceType = relationEndpointType(item.source);
    const targetType = relationEndpointType(item.target);
    const key = sourceType === "Attribute"
      ? "attribute_source"
      : sourceType === "Attribute" || targetType === "Attribute"
        ? "object_attribute"
        : sourceType === "ObjectType" && targetType === "ObjectType"
        ? "object"
        : "object_attribute";
    groups.find((group) => group.key === key).rows.push(item);
  });
  return groups.filter((group) => group.rows.length).map((group) => `
    <section class="relation-group">
      <div class="relation-group-head">
        <h3>${escapeHtml(group.title)}</h3>
        <span>${group.rows.length} 条</span>
      </div>
      <div class="relationship-list">
        ${group.groupedByAttribute ? renderAttributeSourceGroups(group.rows, diff) : group.rows.map((item) => renderRelationshipCard(item, diff)).join("")}
      </div>
    </section>
  `).join("");
}

function renderAttributeSourceGroups(rows, diff = null) {
  const grouped = new Map();
  rows.forEach((item) => {
    const key = item.source || "未命名属性";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(item);
  });
  return [...grouped.entries()].map(([source, sourceRows]) => `
    <section class="attribute-relation-subgroup">
      <div class="attribute-relation-head">
        <strong>${escapeHtml(source)}</strong>
        <span>${sourceRows.length} 条关系</span>
      </div>
      ${sourceRows.map((item) => renderRelationshipCard(item, diff)).join("")}
    </section>
  `).join("");
}

function renderRelationshipCard(item, diff = null, forcedStatus = "") {
  const status = forcedStatus || diffStatus(diff, "relationships", relationshipKey(item));
  const explanationLabel = status === "deleted" ? "删除原因" : status === "added" ? "新增原因" : "关系原因";
  const explanation = status === "deleted"
    ? (item.deletion_reason_zh || item.change_reason_zh || item.reason_zh || "未提供删除原因。")
    : status === "added"
      ? (item.change_reason_zh || item.reason_zh || "未提供新增原因。")
      : (item.reason_zh || "未提供关系原因。");
  return `
    <article class="relation-card ${diffClass(status)}">
      <div class="relation-card-title">
        <strong>${escapeHtml(item.relation_name_zh || item.relation_type || "关系")}${renderDiffBadge(status)}</strong>
        <code>${escapeHtml(item.relation_type || "-")}</code>
      </div>
      <div class="relation-path">
        <span>${escapeHtml(item.source || "")}</span>
        <b>→</b>
        <span>${escapeHtml(item.target || "")}</span>
      </div>
      <p><strong>${explanationLabel}：</strong>${escapeHtml(explanation)}</p>
    </article>
  `;
}

function renderPlanDiffSummary(diff) {
  if (!diff || !diff.total) return "";
  return `
    <section class="plan-diff-summary">
      <div class="relation-group-head">
        <h3>本次变更</h3>
        <span>${diff.total} 处变化</span>
      </div>
      <div class="diff-metric-grid">
        ${renderDiffMetric("新增", diff.counts.added, "added")}
        ${renderDiffMetric("修改", diff.counts.modified, "modified")}
        ${renderDiffMetric("删除", diff.counts.deleted, "deleted")}
      </div>
    </section>
  `;
}

function renderDiffMetric(label, count, status) {
  return `<div class="diff-metric ${diffClass(status)}"><span>${label}</span><strong>${count}</strong></div>`;
}

function renderDeletedPlanItems(diff, plan = null) {
  if (!diff || !diff.totalDeleted) return "";
  const deletedObjects = diff.objects.deletedRows.map((item) => `
    <article class="object-attribute-card diff-deleted">
      <div class="object-attribute-head">
        <strong>${escapeHtml(item.object_type_zh || item.object_type || "未命名对象")}${renderDiffBadge("deleted")}</strong>
        <code>${escapeHtml(item.object_type || "-")}</code>
      </div>
      <p>${escapeHtml(item.description || "未提供对象说明。")}</p>
    </article>
  `).join("");
  const deletedAttributes = diff.attributes.deletedRows.map((item) => renderAttributeChip(item, { attributes: { added: [], modified: [], deleted: [item.attribute_name] } })).join("");
  const revisionExplanation = (plan?.revision_notes || []).filter(Boolean).join("；");
  const deletedRelationships = diff.relationships.deletedRows.map((item) => {
    return renderRelationshipCard({
      ...item,
      deletion_reason_zh: item.deletion_reason_zh || revisionExplanation || "新规划已不再包含此关系。",
    }, null, "deleted");
  }).join("");
  return `
    <section class="plan-deleted-section">
      <div class="relation-group-head">
        <h3>本次删除</h3>
        <span>${diff.totalDeleted} 项</span>
      </div>
      ${deletedObjects ? `<div class="object-attribute-grid">${deletedObjects}</div>` : ""}
      ${deletedAttributes ? `<div class="attribute-chip-list">${deletedAttributes}</div>` : ""}
      ${deletedRelationships ? `<div class="relationship-list">${deletedRelationships}</div>` : ""}
    </section>
  `;
}

function diffPlans(previousPlan, nextPlan) {
  const objectDiff = diffRows(previousPlan.objects || [], nextPlan.objects || [], "object_type", normalizeObjectForDiff);
  const attributeDiff = diffRows(previousPlan.attributes || [], nextPlan.attributes || [], "attribute_name", normalizeAttributeForDiff);
  const relationshipDiff = diffRows(previousPlan.relationships || [], nextPlan.relationships || [], relationshipKey, normalizeRelationshipForDiff);
  const counts = {
    added: objectDiff.added.length + attributeDiff.added.length + relationshipDiff.added.length,
    modified: objectDiff.modified.length + attributeDiff.modified.length + relationshipDiff.modified.length,
    deleted: objectDiff.deleted.length + attributeDiff.deleted.length + relationshipDiff.deleted.length,
  };
  return {
    objects: objectDiff,
    attributes: attributeDiff,
    relationships: relationshipDiff,
    counts,
    total: counts.added + counts.modified + counts.deleted,
    totalDeleted: objectDiff.deleted.length + attributeDiff.deleted.length + relationshipDiff.deleted.length,
  };
}

function diffRows(previousRows, nextRows, keyGetter, normalizer) {
  const previous = rowMap(previousRows, keyGetter);
  const next = rowMap(nextRows, keyGetter);
  const added = [];
  const modified = [];
  const deleted = [];
  const deletedRows = [];
  next.forEach((row, key) => {
    if (!previous.has(key)) added.push(key);
    else if (normalizer(previous.get(key)) !== normalizer(row)) modified.push(key);
  });
  previous.forEach((row, key) => {
    if (!next.has(key)) {
      deleted.push(key);
      deletedRows.push(row);
    }
  });
  return { added, modified, deleted, deletedRows };
}

function rowMap(rows, keyGetter) {
  const map = new Map();
  rows.forEach((row) => {
    if (!row || typeof row !== "object") return;
    const key = typeof keyGetter === "function" ? keyGetter(row) : row[keyGetter];
    if (key) map.set(String(key), row);
  });
  return map;
}

function normalizeObjectForDiff(row) {
  return stableJson({
    object_type_zh: row.object_type_zh || "",
    description: row.description || "",
    enabled: row.enabled !== false,
  });
}

function normalizeAttributeForDiff(row) {
  return stableJson({
    attribute_name_zh: row.attribute_name_zh || "",
    object_types: [...(row.object_types || [])].map(String).sort(),
    value_type: row.value_type || "string",
    description: row.description || "",
    enabled: row.enabled !== false,
  });
}

function normalizeRelationshipForDiff(row) {
  return stableJson({
    relation_name_zh: row.relation_name_zh || "",
    reason_zh: row.reason_zh || "",
  });
}

function relationshipKey(row) {
  return [row.source || "", row.relation_type || "", row.target || ""].join("::");
}

function stableJson(value) {
  return JSON.stringify(value);
}

function diffStatus(diff, section, key) {
  if (!diff || !key || !diff[section]) return "";
  if (diff[section].added.includes(key)) return "added";
  if (diff[section].modified.includes(key)) return "modified";
  if (diff[section].deleted.includes(key)) return "deleted";
  return "";
}

function diffClass(status) {
  return status ? `diff-${status}` : "";
}

function renderDiffBadge(status) {
  const labels = { added: "新增", modified: "修改", deleted: "删除" };
  return labels[status] ? `<span class="diff-badge ${diffClass(status)}">${labels[status]}</span>` : "";
}

function renderQuestionSection(title, rows) {
  rows = rows.filter(Boolean);
  if (!rows.length) return "";
  return `
    <section class="question-section">
      <h3>${escapeHtml(title)}</h3>
      <div class="question-list">
        ${rows.map((item) => `<div class="question-item"><span>${escapeHtml(item)}</span></div>`).join("")}
      </div>
    </section>
  `;
}

function relationEndpointType(value) {
  const text = String(value || "");
  if (text.startsWith("Attribute:")) return "Attribute";
  if (text.startsWith("ObjectType:")) return "ObjectType";
  return "";
}

function openPlanDialog() {
  if (!state.currentPlan) return;
  renderPlanDialog(state.currentPlan);
  if (!$("planDialog").open) $("planDialog").showModal();
}

function closePlanDialog() {
  if ($("planDialog").open) $("planDialog").close();
}

async function generateYaml() {
  if (!state.currentPlan || !state.domainInput) return;
  const wasPlanDialogOpen = $("planDialog").open;
  const generationFeedback = readFeedbackText() || state.lastPlanFeedback || "";
  try {
    setLoading(true, "正在生成 YAML 与关系图", "正在把已确认规划转换为可落盘结构，并写入独立领域目录。");
    const result = await api("/api/domain-ontology/generate", {
      method: "POST",
      body: JSON.stringify({
        domain_input: state.domainInput,
        plan: state.currentPlan,
        feedback: generationFeedback,
        domain_id: state.currentDomainId || "",
        parent_version_id: state.currentDomainVersionId || "",
      }),
    });
    closePlanDialog();
    setStep("graph");
    state.currentDomainId = result.domain_id;
    state.currentDomainVersionId = result.write?.version_id || result.graph?.version_id || "";
    state.expandedDomainId = result.domain_id;
    if (state.lightAppSessionId) state.lightAppSessionContext = result.domain_id;
    setRefillPlanActions(state.formMode === "existing");
    $("currentDomainStatus").textContent = `当前领域：${result.domain_id}${state.currentDomainVersionId ? ` / ${state.currentDomainVersionId}` : ""}`;
    renderPlan(state.currentPlan);
    renderGraph(result.graph);
    showGraphFeedbackPanel(true);
    scrollToGraphPanel();
    await refreshDomains();
  } catch (error) {
    showToast(error.message, error.detail);
    setStep("plan");
    renderPlan(state.currentPlan);
    if (wasPlanDialogOpen || state.currentPlan) openPlanDialog();
  } finally {
    setLoading(false);
  }
}

async function loadGraph(domainId, versionId = "", keepGraphFeedback = false, options = {}) {
  const shouldScroll = options.scroll !== false;
  try {
    setLoading(true, "正在加载领域图谱", "正在读取独立领域 YAML。");
    const url = `/api/domain-ontology/${encodeURIComponent(domainId)}/graph${versionId ? `?version_id=${encodeURIComponent(versionId)}` : ""}`;
    const graph = await api(url);
    if (state.currentDomainId !== domainId) resetLightAppSession();
    state.currentDomainId = domainId;
    state.currentDomainVersionId = graph.version_id || versionId || "";
    state.expandedDomainId = domainId;
    state.planDiff = null;
    if (graph.domain_input) {
      state.domainInput = graph.domain_input;
      state.loadedDomainInput = graph.domain_input;
      applyDomainInput(graph.domain_input, true);
      state.domainInputApplied = true;
      state.formMode = "existing";
      setRefillPlanActions(true);
    } else {
      state.loadedDomainInput = null;
      state.domainInputApplied = true;
      state.formMode = "existing";
      setRefillPlanActions(true);
    }
    if (graph.plan) {
      state.currentPlan = graph.plan;
      state.lastPlanFeedback = graph.feedback || "";
      renderPlan(graph.plan);
    }
    setFeedbackText(keepGraphFeedback ? state.feedbackText : "");
    $("currentDomainStatus").textContent = `当前领域：${domainId}${state.currentDomainVersionId ? ` / ${state.currentDomainVersionId}` : ""}`;
    setStep("graph");
    renderGraph(graph);
    showGraphFeedbackPanel(Boolean(state.currentPlan) || keepGraphFeedback);
    if ($("versionDialog")?.open && state.versionDialogDomainId === domainId) {
      const domain = state.domains.find((item) => item.domain_id === domainId);
      if (domain) renderVersionDialog(domain);
    }
    if (shouldScroll) scrollToGraphPanel();
  } catch (error) {
    showToast(error.message, error.detail);
  } finally {
    setLoading(false);
  }
}

function initGraph() {
  state.cy = cytoscape({
    container: $("cy"),
    elements: [],
    minZoom: 0.08,
    maxZoom: 3,
    wheelSensitivity: 0.08,
    style: [
      { selector: "node", style: { label: "data(label)", "text-wrap": "wrap", "text-max-width": 138, "font-size": 13, color: "#17211f", "background-color": "#8bd4cc", "border-color": "#ffffff", "border-width": 2, width: 76, height: 76 } },
      { selector: 'node[type = "Attribute"]', style: { "background-color": "#c5e8a8", shape: "round-rectangle", width: 82, height: 66 } },
      { selector: 'node[type = "RelationType"]', style: { "background-color": "#b7d7e8", shape: "diamond", width: 50, height: 50 } },
      { selector: "edge", style: { label: "data(label)", "curve-style": "bezier", "target-arrow-shape": "triangle", "line-color": "#8bbcb7", "target-arrow-color": "#8bbcb7", color: "#62726f", "font-size": 10, "text-background-color": "#fff", "text-background-opacity": 0.88, "text-background-padding": 2, width: 1.7 } },
      { selector: 'edge[type = "has_attribute"]', style: { label: "", width: 1.2, "line-color": "#b6d8d4", "target-arrow-color": "#b6d8d4" } },
      { selector: ".dimmed", style: { opacity: 0.16, "text-opacity": 0.12 } },
      { selector: "edge.dimmed", style: { opacity: 0.12, "text-opacity": 0.08 } },
      { selector: "node.related", style: { opacity: 1, "border-color": "#6fb9b2", "border-width": 3, "z-index": 80 } },
      { selector: "node.focused", style: { opacity: 1, "border-color": "#0f8f8a", "border-width": 5, "z-index": 100 } },
      { selector: "edge.focus-edge", style: { opacity: 1, width: 3.4, "line-color": "#0f8f8a", "target-arrow-color": "#0f8f8a", color: "#0f625f", "z-index": 90, "text-opacity": 1 } },
      { selector: ":selected", style: { "border-color": "#0f8f8a", "border-width": 4, "line-color": "#0f8f8a", "target-arrow-color": "#0f8f8a" } },
    ],
  });
  state.cy.on("tap", "node, edge", (event) => selectElement(event.target));
  state.cy.on("tap", (event) => {
    if (event.target === state.cy) closeDrawer();
  });
}

function renderGraph(graph) {
  state.currentGraph = graph;
  const nodes = (graph.nodes || [])
    .filter((node) => node.data.type !== "RelationType")
    .map((node) => ({ data: normalizeNodeData(node.data) }));
  const nodeIds = new Set(nodes.map((node) => node.data.id));
  const edges = (graph.edges || []).filter((edge) => nodeIds.has(edge.data.source) && nodeIds.has(edge.data.target)).map((edge) => ({ data: normalizeEdgeData(edge.data) }));
  setGraphExpanded(true, false);
  state.cy.elements().remove();
  state.cy.add([...nodes, ...edges]);
  clearGraphFocus();
  const hiddenRelationTypes = (graph.nodes || []).filter((node) => node.data.type === "RelationType").length;
  const hiddenText = hiddenRelationTypes ? ` · 关系类型 ${hiddenRelationTypes} 个作为边标签使用` : "";
  $("graphStatus").textContent = `${graph.domain?.domain_name || graph.domain_id || "领域"} · ${nodes.length} 个节点 · ${edges.length} 条关系${hiddenText}`;
  $("graphSubtitle").textContent = `保存位置：ontology/domains/${graph.domain_id || state.currentDomainId}`;
  $("addNodeBtn").disabled = false;
  $("addEdgeBtn").disabled = false;
  $("graphSpacingControl").classList.remove("hidden");
  setGraphSpacing(defaultGraphSpacing(nodes.length), false);
  layoutGraphForVisibleCanvas(nodes.length);
}

function setGraphSpacing(value, relayout = true) {
  const next = Math.max(0.75, Math.min(1.9, Number(value) || 1));
  state.graphSpacing = next;
  $("graphSpacingRange").value = String(next);
  $("graphSpacingValue").textContent = `${next.toFixed(2)}x`;
  if (relayout && state.cy?.elements().length) layoutGraphForVisibleCanvas(state.cy.nodes().length, false);
}

function defaultGraphSpacing(nodeCount) {
  if (nodeCount <= 14) return 0.95;
  if (nodeCount <= 28) return 1;
  if (nodeCount <= 46) return 1.08;
  return 1.18;
}

function layoutGraphForVisibleCanvas(nodeCount, refit = true) {
  window.requestAnimationFrame(() => {
    state.cy.resize();
    const positions = domainGraphPresetPositions();
    const layout = state.cy.layout({
      name: "preset",
      animate: false,
      fit: false,
      positions: (node) => positions[node.id()] || { x: 0, y: 0 },
    });
    layout.run();
    window.requestAnimationFrame(() => {
      state.cy.resize();
      if (refit) fitGraphForReading();
      else state.cy.center(state.cy.elements());
    });
  });
}

function domainGraphPresetPositions() {
  const nodes = state.cy.nodes().map((node) => ({ id: node.id(), type: node.data("type") || "" }));
  const objectNodes = nodes.filter((node) => node.type === "ObjectType");
  const attributeNodes = nodes.filter((node) => node.type === "Attribute");
  const otherNodes = nodes.filter((node) => node.type !== "ObjectType" && node.type !== "Attribute");
  const objectIds = new Set(objectNodes.map((node) => node.id));
  const attributeIds = new Set(attributeNodes.map((node) => node.id));
  const attributesByObject = new Map(objectNodes.map((node) => [node.id, []]));
  const assignedAttributes = new Set();

  state.cy.edges('[type = "has_attribute"]').forEach((edge) => {
    const source = edge.data("source");
    const target = edge.data("target");
    const objectId = objectIds.has(source) ? source : objectIds.has(target) ? target : "";
    const attributeId = attributeIds.has(target) ? target : attributeIds.has(source) ? source : "";
    if (!objectId || !attributeId || !attributesByObject.has(objectId)) return;
    attributesByObject.get(objectId).push(attributeId);
    assignedAttributes.add(attributeId);
  });

  const unassignedAttributes = attributeNodes.map((node) => node.id).filter((id) => !assignedAttributes.has(id));
  const columns = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(Math.max(1, objectNodes.length)))));
  const spacing = state.graphSpacing || 1;
  const groupWidth = 350 * spacing;
  const rowGap = 118 * spacing;
  const attrColumnGap = 145 * spacing;
  const attrRowGap = 94 * spacing;
  const positions = {};
  const rows = [];
  for (let index = 0; index < objectNodes.length; index += columns) {
    rows.push(objectNodes.slice(index, index + columns));
  }

  let rowTop = 90 * spacing;
  rows.forEach((row) => {
    const rowHeights = row.map((object) => {
      const attrs = uniqueStrings(attributesByObject.get(object.id) || []);
      return Math.max(255 * spacing, 166 * spacing + Math.ceil(attrs.length / 2) * attrRowGap);
    });
    row.forEach((object, colIndex) => {
      const baseX = 86 * spacing + colIndex * groupWidth;
      const objectX = baseX + groupWidth / 2;
      const objectY = rowTop;
      positions[object.id] = { x: objectX, y: objectY };
      const attrs = uniqueStrings(attributesByObject.get(object.id) || []);
      attrs.forEach((attrId, attrIndex) => {
        const side = attrIndex % 2 === 0 ? -1 : 1;
        const attrRow = Math.floor(attrIndex / 2);
        positions[attrId] = {
          x: objectX + side * (attrColumnGap / 2),
          y: objectY + 122 * spacing + attrRow * attrRowGap,
        };
      });
    });
    rowTop += Math.max(...rowHeights) + rowGap;
  });

  const tailNodes = [...unassignedAttributes, ...otherNodes.map((node) => node.id)].filter((id) => !positions[id]);
  const tailStartY = rowTop + 76 * spacing;
  tailNodes.forEach((id, index) => {
    positions[id] = {
      x: 170 * spacing + (index % columns) * groupWidth,
      y: tailStartY + Math.floor(index / columns) * attrRowGap,
    };
  });
  return positions;
}

function uniqueStrings(values) {
  return [...new Set((values || []).filter(Boolean))];
}

function normalizeNodeData(data) {
  return {
    ...data,
    label: data.label || data.short_label || data.identity || data.id,
  };
}

function normalizeEdgeData(data) {
  return {
    ...data,
    label: data.label || data.type || data.relation_type || "",
  };
}

function selectElement(element) {
  state.selectedElement = element;
  focusGraphNeighborhood(element);
  $("detailDrawer").classList.add("open");
  if (element.isNode()) renderNodeDrawer(element);
  else renderEdgeDrawer(element);
}

function focusGraphNeighborhood(element) {
  clearGraphFocus();
  if (!element || element.empty()) return;
  const all = state.cy.elements();
  all.addClass("dimmed");

  let focusEdges = state.cy.collection();
  let relatedNodes = state.cy.collection();

  if (element.isEdge()) {
    focusEdges = element;
    relatedNodes = element.connectedNodes();
  } else if (element.data("type") === "ObjectType") {
    focusEdges = element.connectedEdges('[type = "has_attribute"]');
    relatedNodes = focusEdges.connectedNodes().difference(element);
  } else if (element.data("type") === "Attribute") {
    focusEdges = element.connectedEdges('[type = "has_attribute"]');
    relatedNodes = focusEdges.connectedNodes().difference(element);
  } else {
    focusEdges = element.connectedEdges();
    relatedNodes = focusEdges.connectedNodes().difference(element);
  }

  if (!focusEdges.length && element.isNode()) {
    focusEdges = element.connectedEdges();
    relatedNodes = focusEdges.connectedNodes().difference(element);
  }

  const focused = element.union(focusEdges).union(relatedNodes);
  focused.removeClass("dimmed");
  relatedNodes.addClass("related");
  element.addClass("focused");
  focusEdges.addClass("focus-edge");
}

function clearGraphFocus() {
  if (!state.cy) return;
  state.cy.elements().removeClass("dimmed focused related focus-edge");
}

function renderNodeDrawer(node) {
  const data = node.data();
  $("drawerTitle").textContent = data.label || data.id;
  $("drawerMeta").textContent = `${typeLabel(data.type)} · ${data.id}`;
  $("drawerBody").className = "drawer-body";
  $("drawerBody").innerHTML = `
    <div class="field-grid">${renderNodeFields(data.type, data.raw || {})}</div>
    <textarea id="rawEditor" class="raw-preview">${escapeHtml(JSON.stringify(data.raw || {}, null, 2))}</textarea>
    <div class="drawer-actions">
      <button id="saveSelectedBtn" class="primary-btn" type="button">保存修改</button>
      <button id="deleteSelectedBtn" class="danger-btn" type="button">删除节点</button>
    </div>
  `;
  $("saveSelectedBtn").addEventListener("click", saveSelected);
  $("deleteSelectedBtn").addEventListener("click", deleteSelected);
}

function renderEdgeDrawer(edge) {
  const data = edge.data();
  const raw = { edge_id: data.raw?.edge_id || data.id, source: data.source, target: data.target, relation_type: data.type, ...(data.raw || {}) };
  $("drawerTitle").textContent = data.label || data.type;
  $("drawerMeta").textContent = `${data.source} → ${data.target}`;
  $("drawerBody").className = "drawer-body";
  $("drawerBody").innerHTML = `
    <div class="field-grid">
      <label>关系类型<input data-edge-field="relation_type" value="${escapeHtml(raw.relation_type || "")}"></label>
      <label>中文原因<textarea data-edge-field="reason_zh" rows="3">${escapeHtml(raw.reason_zh || "")}</textarea></label>
      <label>分值<input data-edge-field="score" value="${escapeHtml(raw.score || "")}"></label>
    </div>
    <textarea id="rawEditor" class="raw-preview">${escapeHtml(JSON.stringify(raw, null, 2))}</textarea>
    <div class="drawer-actions">
      <button id="saveSelectedBtn" class="primary-btn" type="button">保存关系</button>
      <button id="deleteSelectedBtn" class="danger-btn" type="button">删除关系</button>
    </div>
  `;
  $("saveSelectedBtn").addEventListener("click", saveSelected);
  $("deleteSelectedBtn").addEventListener("click", deleteSelected);
}

function renderNodeFields(type, raw) {
  const fields = {
    ObjectType: ["object_type", "object_type_zh", "description"],
    Attribute: ["attribute_name", "attribute_name_zh", "object_types", "value_type", "description"],
    RelationType: ["relation_type", "relation_name_zh", "description"],
  }[type] || Object.keys(raw);
  return fields.map((field) => {
    const value = Array.isArray(raw[field]) ? raw[field].join(", ") : raw[field] || "";
    const tag = field === "description" ? "textarea" : "input";
    const inner = tag === "textarea"
      ? `<textarea data-node-field="${field}" rows="3">${escapeHtml(value)}</textarea>`
      : `<input data-node-field="${field}" value="${escapeHtml(value)}">`;
    return `<label>${fieldLabel(field)}${inner}</label>`;
  }).join("");
}

async function saveSelected() {
  if (!state.selectedElement || !state.currentDomainId) return;
  try {
    if (state.selectedElement.isNode()) {
      const data = state.selectedElement.data();
      const payload = readNodeDrawerPayload(data.type, data.raw || {});
      const result = await api(`/api/domain-ontology/${encodeURIComponent(state.currentDomainId)}/node?version_id=${encodeURIComponent(state.currentDomainVersionId || "")}`, {
        method: "POST",
        body: JSON.stringify({ node_type: data.type, node_id: data.id, data: payload }),
      });
      state.currentDomainVersionId = result.version_id || state.currentDomainVersionId;
    } else {
      const data = state.selectedElement.data();
      const payload = readEdgeDrawerPayload(data.raw || {});
      const result = await api(`/api/domain-ontology/${encodeURIComponent(state.currentDomainId)}/edge?version_id=${encodeURIComponent(state.currentDomainVersionId || "")}`, {
        method: "POST",
        body: JSON.stringify({
          edge_id: payload.edge_id || data.id,
          source: payload.source || data.source,
          target: payload.target || data.target,
          relation_type: payload.relation_type || data.type,
          properties: edgeProperties(payload),
        }),
      });
      state.currentDomainVersionId = result.version_id || state.currentDomainVersionId;
    }
    await loadGraph(state.currentDomainId, state.currentDomainVersionId, !$("graphFeedbackPanel").classList.contains("hidden"));
  } catch (error) {
    showToast(error.message, error.detail);
  }
}

function readNodeDrawerPayload(type, original) {
  const payload = { ...original };
  document.querySelectorAll("[data-node-field]").forEach((input) => {
    const field = input.dataset.nodeField;
    payload[field] = field === "object_types" ? splitCsv(input.value) : input.value.trim();
  });
  if (type === "ObjectType") payload.object_type = payload.object_type || stripPrefix(state.selectedElement.id());
  if (type === "Attribute") payload.attribute_name = payload.attribute_name || stripPrefix(state.selectedElement.id());
  if (type === "RelationType") payload.relation_type = payload.relation_type || stripPrefix(state.selectedElement.id());
  return payload;
}

function readEdgeDrawerPayload(original) {
  const payload = { ...original };
  document.querySelectorAll("[data-edge-field]").forEach((input) => {
    const field = input.dataset.edgeField;
    payload[field] = input.value.trim();
  });
  return payload;
}

async function deleteSelected() {
  if (!state.selectedElement || !state.currentDomainId) return;
  const id = state.selectedElement.id();
  const confirmed = await openAppModal({
    title: "删除图谱元素",
    message: `确认删除 ${id}？该操作会生成一个新的手动编辑版本。`,
    actions: [
      { value: true, label: "确认删除", className: "danger-btn" },
      { value: false, label: "取消" },
    ],
  });
  if (!confirmed) return;
  try {
    if (state.selectedElement.isNode()) {
      const result = await api(`/api/domain-ontology/${encodeURIComponent(state.currentDomainId)}/node/${encodeURIComponent(id)}?force=true&version_id=${encodeURIComponent(state.currentDomainVersionId || "")}`, { method: "DELETE" });
      state.currentDomainVersionId = result.version_id || state.currentDomainVersionId;
    } else {
      const result = await api(`/api/domain-ontology/${encodeURIComponent(state.currentDomainId)}/edge/${encodeURIComponent(id)}?version_id=${encodeURIComponent(state.currentDomainVersionId || "")}`, { method: "DELETE" });
      state.currentDomainVersionId = result.version_id || state.currentDomainVersionId;
    }
    closeDrawer();
    await loadGraph(state.currentDomainId, state.currentDomainVersionId, !$("graphFeedbackPanel").classList.contains("hidden"));
  } catch (error) {
    showToast(error.message, error.detail);
  }
}

function openNodeDialog() {
  if (!state.currentDomainId) return;
  openDialog("新增节点", `
    <label>节点类型<select id="dialogNodeType"><option value="ObjectType">对象</option><option value="Attribute">属性</option><option value="RelationType">关系类型</option></select></label>
    <label>标识<input id="dialogNodeId" placeholder="StableIdentifier"></label>
    <label>中文名<input id="dialogNodeLabel" placeholder="中文名称"></label>
    <label>描述<textarea id="dialogNodeDesc" rows="3"></textarea></label>
    <label id="dialogObjectTypesWrap">所属对象<input id="dialogObjectTypes" placeholder="仅属性需要，例如 RepairOrder"></label>
  `, async () => {
    const nodeType = $("dialogNodeType").value;
    const id = $("dialogNodeId").value.trim();
    const label = $("dialogNodeLabel").value.trim();
    const desc = $("dialogNodeDesc").value.trim();
    if (!id) throw new Error("请填写节点标识");
    const data = nodeType === "ObjectType"
      ? { object_type: id, object_type_zh: label || id, description: desc, enabled: true }
      : nodeType === "Attribute"
        ? { attribute_name: id, attribute_name_zh: label || id, description: desc, value_type: "string", object_types: splitCsv($("dialogObjectTypes").value), enabled: true }
        : { relation_type: id, relation_name_zh: label || id, description: desc, enabled: true };
    const result = await api(`/api/domain-ontology/${encodeURIComponent(state.currentDomainId)}/node?version_id=${encodeURIComponent(state.currentDomainVersionId || "")}`, {
      method: "POST",
      body: JSON.stringify({ node_type: nodeType, node_id: id, data }),
    });
    state.currentDomainVersionId = result.version_id || state.currentDomainVersionId;
    await loadGraph(state.currentDomainId, state.currentDomainVersionId, !$("graphFeedbackPanel").classList.contains("hidden"));
  });
}

function openEdgeDialog() {
  if (!state.currentDomainId || !state.currentGraph) return;
  const nodeOptions = (state.currentGraph.nodes || [])
    .filter((node) => node.data.type !== "RelationType")
    .map((node) => `<option value="${escapeHtml(node.data.id)}">${escapeHtml(node.data.label || node.data.id)}</option>`)
    .join("");
  const relationOptions = [
    `<option value="has_attribute">拥有属性</option>`,
    ...(state.currentGraph.nodes || [])
      .filter((node) => node.data.type === "RelationType")
      .map((node) => `<option value="${escapeHtml(stripPrefix(node.data.id))}">${escapeHtml(node.data.label || node.data.id)}</option>`),
  ].join("");
  openDialog("新增关系", `
    <label>起点<select id="dialogEdgeSource">${nodeOptions}</select></label>
    <label>终点<select id="dialogEdgeTarget">${nodeOptions}</select></label>
    <label>关系类型<select id="dialogEdgeRelation">${relationOptions}</select></label>
    <label>中文原因<textarea id="dialogEdgeReason" rows="3"></textarea></label>
  `, async () => {
    const source = $("dialogEdgeSource").value;
    const target = $("dialogEdgeTarget").value;
    const relationType = $("dialogEdgeRelation").value;
    if (!source || !target || !relationType) throw new Error("请完整填写关系");
    const result = await api(`/api/domain-ontology/${encodeURIComponent(state.currentDomainId)}/edge?version_id=${encodeURIComponent(state.currentDomainVersionId || "")}`, {
      method: "POST",
      body: JSON.stringify({ source, target, relation_type: relationType, properties: { reason_zh: $("dialogEdgeReason").value.trim() } }),
    });
    state.currentDomainVersionId = result.version_id || state.currentDomainVersionId;
    await loadGraph(state.currentDomainId, state.currentDomainVersionId, !$("graphFeedbackPanel").classList.contains("hidden"));
  });
}

function openDialog(title, bodyHtml, onSave) {
  $("dialogTitle").textContent = title;
  $("dialogBody").innerHTML = bodyHtml;
  $("dialogOkBtn").onclick = async () => {
    try {
      await onSave();
      closeDialog();
    } catch (error) {
      showToast(error.message, error.detail);
    }
  };
  $("editDialog").showModal();
}

function closeDialog() {
  $("editDialog").close();
}

function closeDrawer() {
  state.selectedElement = null;
  clearGraphFocus();
  $("detailDrawer").classList.remove("open");
}

function bindFeedbackInput(id) {
  const node = $(id);
  if (!node) return;
  node.addEventListener("input", () => setFeedbackText(node.value, id));
}

function readFeedbackText() {
  return state.feedbackText.trim();
}

function setFeedbackText(value, sourceId = "") {
  state.feedbackText = value || "";
  ["feedbackText", "graphFeedbackText"].forEach((id) => {
    const node = $(id);
    if (node && id !== sourceId && node.value !== state.feedbackText) node.value = state.feedbackText;
  });
}

function showGraphFeedbackPanel(visible) {
  $("graphFeedbackPanel").classList.toggle("hidden", !visible);
  if (visible) setFeedbackText(state.feedbackText);
}

function bindGraphResize() {
  const handle = $("graphResizeHandle");
  const canvas = $("cy");
  if (!handle || !canvas) return;
  const defaultHeight = window.matchMedia("(max-width: 820px)").matches ? 580 : 820;
  setGraphCanvasHeight(defaultHeight, false);

  let dragStartY = 0;
  let dragStartHeight = defaultHeight;

  handle.addEventListener("pointerdown", (event) => {
    if (!state.graphExpanded) return;
    dragStartY = event.clientY;
    dragStartHeight = canvas.getBoundingClientRect().height || state.graphHeight || defaultHeight;
    handle.setPointerCapture(event.pointerId);
    handle.classList.add("dragging");
    event.preventDefault();
  });

  handle.addEventListener("pointermove", (event) => {
    if (!handle.classList.contains("dragging")) return;
    setGraphCanvasHeight(dragStartHeight + event.clientY - dragStartY, false);
  });

  const endDrag = (event) => {
    if (!handle.classList.contains("dragging")) return;
    handle.classList.remove("dragging");
    if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    resizeGraphCanvas(true);
  };
  handle.addEventListener("pointerup", endDrag);
  handle.addEventListener("pointercancel", endDrag);
  handle.addEventListener("keydown", (event) => {
    if (!["ArrowUp", "ArrowDown", "PageUp", "PageDown", "Home"].includes(event.key)) return;
    event.preventDefault();
    const step = event.key.startsWith("Page") ? 80 : 24;
    if (event.key === "Home") setGraphCanvasHeight(defaultHeight, true);
    if (event.key === "ArrowUp" || event.key === "PageUp") setGraphCanvasHeight(state.graphHeight - step, true);
    if (event.key === "ArrowDown" || event.key === "PageDown") setGraphCanvasHeight(state.graphHeight + step, true);
  });
}

function setGraphCanvasHeight(height, refit = false) {
  const nextHeight = Math.round(Math.max(420, Math.min(height, 1200)));
  state.graphHeight = nextHeight;
  $("graphBody").style.setProperty("--graph-canvas-height", `${nextHeight}px`);
  resizeGraphCanvas(refit);
}

function resizeGraphCanvas(refit = false) {
  if (!state.cy || !state.graphExpanded) return;
  window.requestAnimationFrame(() => {
    state.cy.resize();
    if (refit) fitGraphForReading();
  });
}

function setGraphExpanded(expanded, refit = false) {
  state.graphExpanded = expanded;
  $("graphBody").classList.toggle("collapsed", !expanded);
  $("toggleGraphBtn").textContent = expanded ? "收起画布" : "展开画布";
  if (expanded) resizeGraphCanvas(refit);
}

function scrollToGraphPanel() {
  window.requestAnimationFrame(() => {
    $("graphPanel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

function fitGraphForReading() {
  const elements = state.cy.elements();
  if (!elements.length) return;
  state.cy.fit(elements, 54);
  state.cy.center(elements);
}

function setStep(step) {
  document.querySelectorAll(".step").forEach((node) => node.classList.toggle("active", node.dataset.step === step));
}

function setLoading(loading, title = "正在处理", text = "请稍候...") {
  state.loadingState = loading ? title : "";
  $("loadingOverlay").hidden = !loading;
  $("loadingTitle").textContent = title;
  $("loadingText").textContent = text;
  syncCancelLlmControl();
  ["runPlanBtn", "updateRefilledPlanBtn", "createRefilledPlanBtn", "generateYamlBtn", "viewPlanBtn", "planDialogRegenerateBtn", "planDialogGenerateBtn", "graphApplyInputBtn", "graphRegeneratePlanBtn"].forEach((id) => {
    const node = $(id);
    if (!node) return;
    const needsPlan = ["generateYamlBtn", "viewPlanBtn", "planDialogRegenerateBtn", "planDialogGenerateBtn", "graphRegeneratePlanBtn"].includes(id);
    const needsLoadedInput = id === "graphApplyInputBtn";
    node.disabled = loading || (needsPlan && !state.currentPlan) || (needsLoadedInput && !state.loadedDomainInput);
  });
}

async function api(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      const cancelled = new Error("本次模型调用已中止");
      cancelled.cancelled = true;
      throw cancelled;
    }
    throw error;
  }
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: { error: text.slice(0, 500) } };
    }
  }
  if (!response.ok) {
    const error = new Error(data.detail?.error || response.statusText);
    error.detail = data.detail || data;
    throw error;
  }
  return data;
}

function showToast(message, detail) {
  openAppModal({
    title: "提示",
    message: String(message || "操作失败"),
    detail,
    actions: [{ value: null, label: "知道了", className: "primary-btn" }],
  });
}

function openAppModal({ title = "提示", message = "", detail = null, actions = [] } = {}) {
  const dialog = $("appModal");
  if (!dialog) return Promise.resolve(null);
  if (dialog.open) closeAppModal(null);
  $("appModalTitle").textContent = title;
  $("appModalMessage").textContent = message;
  const detailNode = $("appModalDetail");
  const detailText = detail
    ? typeof detail === "string"
      ? detail
      : JSON.stringify(detail, null, 2)
    : "";
  detailNode.textContent = detailText;
  detailNode.classList.toggle("hidden", !detailText);
  const actionBox = $("appModalActions");
  const modalActions = actions.length ? actions : [{ value: null, label: "关闭", className: "primary-btn" }];
  actionBox.innerHTML = modalActions.map((action, index) => `
    <button type="button" data-modal-action="${index}" class="${escapeHtml(action.className || "")}">${escapeHtml(action.label || "关闭")}</button>
  `).join("");
  return new Promise((resolve) => {
    state.modalResolve = resolve;
    actionBox.querySelectorAll("[data-modal-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = modalActions[Number(button.dataset.modalAction)];
        closeAppModal(action?.value ?? null);
      });
    });
    dialog.showModal();
  });
}

function closeAppModal(value = null) {
  const dialog = $("appModal");
  if (dialog?.open) dialog.close();
  const resolve = state.modalResolve;
  state.modalResolve = null;
  if (resolve) resolve(value);
}

function edgeProperties(raw) {
  const props = { ...raw };
  ["edge_id", "source", "target", "from", "to", "relation_type"].forEach((key) => delete props[key]);
  return props;
}

function splitCsv(value) {
  return String(value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function stripPrefix(value) {
  return String(value || "").split(":").slice(-1)[0];
}

function clonePlain(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function typeLabel(type) {
  return { ObjectType: "对象", Attribute: "属性", RelationType: "关系类型" }[type] || type || "节点";
}

function fieldLabel(field) {
  return {
    object_type: "对象标识",
    object_type_zh: "对象中文名",
    attribute_name: "属性标识",
    attribute_name_zh: "属性中文名",
    object_types: "所属对象",
    value_type: "值类型",
    relation_type: "关系类型",
    relation_name_zh: "关系中文名",
    description: "描述",
  }[field] || field;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
