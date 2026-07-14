(function () {
  "use strict";

  var REQUIRED_COLUMNS = {
    id: ["序号", "id", "index", "question_id"],
    question: ["问题", "question", "query", "测试问题"],
    plain: ["朴素回答", "无OAG回答", "无 OAG回答", "plain_answer", "baseline_answer"],
    oag: ["OAG回答", "OAG 回答", "有OAG回答", "有 OAG回答", "oag_answer"]
  };
  var EXPECTED_RUNS = 5;
  var SCORE_TEXT_LIMIT = 12000;
  var TOKEN_TEXT_LIMIT = 5000;
  var UNIT_LIMIT = 18;
  var LCS_LIMIT = 420;
  var DIMENSIONS = [
    { key: "consensus", label: "共识相似", weight: 0.35 },
    { key: "coverage", label: "信息覆盖", weight: 0.20 },
    { key: "numeric", label: "数值一致", weight: 0.35 },
    { key: "structure", label: "结构一致性", weight: 0.10 }
  ];
  var state = {
    groups: [],
    filtered: [],
    currentIndex: 0,
    view: "single",
    warnings: [],
    sourceName: "",
    loading: false,
    loadingMessage: "",
    loadToken: 0
  };

  var els = {};

  document.addEventListener("DOMContentLoaded", function () {
    collectElements();
    bindEvents();
    loadDefaultCsv();
  });

  function collectElements() {
    [
      "csvInput", "reloadBtn", "noticePanel", "totalQuestions", "totalRuns",
      "plainAverage", "oagAverage", "advantageAverage", "advantageHint",
      "searchInput", "clearSearchBtn", "filterSelect", "sortSelect",
      "singleTab", "allTab", "emptyState", "singleView", "allView",
      "prevBtn", "nextBtn", "questionPosition", "questionText", "questionMeta",
      "currentAdvantage", "plainScoreLabel", "oagScoreLabel", "plainScoreBar",
      "oagScoreBar", "plainColumnMeta", "oagColumnMeta", "plainAnswers",
      "plainDimensionDetails", "oagDimensionDetails", "oagAnswers", "tableCount", "resultTableBody"
    ].forEach(function (id) {
      els[id] = document.getElementById(id);
    });
    els.cardTemplate = document.getElementById("answerCardTemplate");
  }

  function bindEvents() {
    els.csvInput.addEventListener("change", handleFileUpload);
    els.reloadBtn.addEventListener("click", loadDefaultCsv);
    els.searchInput.addEventListener("input", applyControls);
    els.clearSearchBtn.addEventListener("click", function () {
      els.searchInput.value = "";
      applyControls();
    });
    els.filterSelect.addEventListener("change", applyControls);
    els.sortSelect.addEventListener("change", applyControls);
    els.singleTab.addEventListener("click", function () { setView("single"); });
    els.allTab.addEventListener("click", function () { setView("all"); });
    els.prevBtn.addEventListener("click", function () { moveQuestion(-1); });
    els.nextBtn.addEventListener("click", function () { moveQuestion(1); });
    document.addEventListener("keydown", function (event) {
      if (state.view !== "single" || event.target.tagName === "INPUT" || event.target.tagName === "TEXTAREA") {
        return;
      }
      if (event.key === "ArrowLeft") moveQuestion(-1);
      if (event.key === "ArrowRight") moveQuestion(1);
    });
  }

  function handleFileUpload(event) {
    var file = event.target.files && event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      ingestCsvBuffer(reader.result, file.name);
    };
    reader.onerror = function () {
      state.groups = [];
      state.filtered = [];
      state.warnings = ["CSV 文件读取失败，请确认文件可访问。"];
      state.sourceName = file.name;
      render();
    };
    reader.readAsArrayBuffer(file);
  }

  function loadDefaultCsv() {
    fetch("./data/results.csv", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.arrayBuffer();
      })
      .then(function (buffer) {
        ingestCsvBuffer(buffer, "data/results.csv");
      })
      .catch(function () {
        state.groups = [];
        state.filtered = [];
        state.warnings = ["未能自动读取 data/results.csv。可直接点击“导入 CSV”选择测试结果文件；如果使用 file:// 打开页面，浏览器通常会阻止自动读取本地数据文件。"];
        state.sourceName = "";
        render();
      });
  }

  function ingestCsvBuffer(buffer, sourceName) {
    var token = state.loadToken + 1;
    state.loadToken = token;
    showLoading("正在读取并分析 CSV，请稍候...");
    setTimeout(function () {
      if (token !== state.loadToken) return;
      try {
        var decoded = decodeCsvBuffer(buffer);
        ingestCsv(decoded.text, sourceName, decoded.encoding, token);
      } catch (error) {
        state.groups = [];
        state.filtered = [];
        state.warnings = [error.message || String(error)];
        state.sourceName = sourceName;
        hideLoading();
        render();
      }
    }, 0);
  }

  function decodeCsvBuffer(buffer) {
    var candidates = ["utf-8", "gb18030", "gbk", "big5"];
    var best = null;
    candidates.forEach(function (encoding) {
      var decoded = decodeText(buffer, encoding);
      if (!decoded) return;
      var score = scoreDecodedCsv(decoded);
      if (!best || score > best.score) {
        best = { text: decoded, encoding: encoding, score: score };
      }
    });
    if (!best) {
      throw new Error("CSV 文件编码无法识别。请另存为 UTF-8 CSV 后重试。");
    }
    return best;
  }

  function decodeText(buffer, encoding) {
    try {
      return new TextDecoder(encoding, { fatal: false }).decode(buffer);
    } catch (error) {
      return "";
    }
  }

  function scoreDecodedCsv(text) {
    var firstLine = trimBom(String(text || "").split(/\r?\n/, 1)[0] || "");
    var score = 0;
    if (firstLine.indexOf("序号") >= 0) score += 4;
    if (firstLine.indexOf("问题") >= 0) score += 3;
    if (firstLine.indexOf("朴素回答") >= 0) score += 4;
    if (firstLine.indexOf("OAG回答") >= 0 || firstLine.indexOf("OAG 回答") >= 0) score += 4;
    score -= (firstLine.match(/\uFFFD/g) || []).length * 2;
    score -= (firstLine.match(/\u0000/g) || []).length * 2;
    return score;
  }

  function ingestCsv(text, sourceName, encoding, token) {
    try {
      var parsed = parseCsv(text);
      var normalized = normalizeRows(parsed);
      var groups = buildGroups(normalized.rows);
      state.groups = groups;
      state.filtered = groups.slice();
      state.warnings = normalized.warnings.slice();
      if (encoding && encoding !== "utf-8") {
        state.warnings.unshift("已按 " + encoding.toUpperCase() + " 编码读取 CSV。建议后续另存为 UTF-8 CSV，便于跨环境迁移。");
      }
      state.sourceName = sourceName;
      state.currentIndex = 0;
      els.searchInput.value = "";
      els.filterSelect.value = "all";
      els.sortSelect.value = "index";
      render();
      scoreGroupsChunked(groups, token, function () {
        if (token !== state.loadToken) return;
        state.warnings = normalized.warnings.concat(collectGroupWarnings(state.groups));
        applyControls();
        hideLoading();
        render();
      });
    } catch (error) {
      state.groups = [];
      state.filtered = [];
      state.warnings = [error.message || String(error)];
      state.sourceName = sourceName;
      hideLoading();
      render();
    }
  }

  function parseCsv(text) {
    var rows = [];
    var row = [];
    var value = "";
    var inQuotes = false;

    for (var i = 0; i < text.length; i += 1) {
      var ch = text[i];
      var next = text[i + 1];
      if (inQuotes) {
        if (ch === "\"" && next === "\"") {
          value += "\"";
          i += 1;
        } else if (ch === "\"") {
          inQuotes = false;
        } else {
          value += ch;
        }
      } else if (ch === "\"") {
        inQuotes = true;
      } else if (ch === ",") {
        row.push(value);
        value = "";
      } else if (ch === "\n") {
        row.push(value);
        rows.push(row);
        row = [];
        value = "";
      } else if (ch !== "\r") {
        value += ch;
      }
    }
    if (value.length > 0 || row.length > 0) {
      row.push(value);
      rows.push(row);
    }
    rows = rows.filter(function (item) {
      return item.some(function (cell) { return String(cell || "").trim() !== ""; });
    });
    if (rows.length < 2) {
      throw new Error("CSV 至少需要表头和一行数据。推荐表头：序号、问题、朴素回答、OAG回答。");
    }
    return rows;
  }

  function normalizeRows(rows) {
    var headers = rows[0].map(function (cell) { return trimBom(cell).trim(); });
    var columns = {};
    Object.keys(REQUIRED_COLUMNS).forEach(function (key) {
      columns[key] = findHeader(headers, REQUIRED_COLUMNS[key]);
    });

    var warnings = [];
    if (columns.id < 0 || columns.plain < 0 || columns.oag < 0) {
      throw new Error("CSV 缺少必要列。至少需要：序号、朴素回答、OAG回答；推荐增加“问题”列以支持问题搜索。");
    }
    if (columns.question < 0) {
      warnings.push("CSV 缺少“问题”列。页面仍可按序号和回答内容搜索，但无法展示真实问题文本；建议补充列：序号、问题、朴素回答、OAG回答。");
    }

    return {
      columns: columns,
      warnings: warnings,
      rows: rows.slice(1).map(function (row, index) {
        return {
          rowNumber: index + 2,
          id: getCell(row, columns.id),
          question: columns.question >= 0 ? getCell(row, columns.question) : "",
          plain: getCell(row, columns.plain),
          oag: getCell(row, columns.oag)
        };
      }).filter(function (row) {
        return row.id || row.question || row.plain || row.oag;
      })
    };
  }

  function findHeader(headers, names) {
    var lowerHeaders = headers.map(function (item) { return item.toLowerCase().replace(/\s+/g, ""); });
    for (var i = 0; i < names.length; i += 1) {
      var target = names[i].toLowerCase().replace(/\s+/g, "");
      var index = lowerHeaders.indexOf(target);
      if (index >= 0) return index;
    }
    return -1;
  }

  function getCell(row, index) {
    return index >= 0 && index < row.length ? String(row[index] || "").trim() : "";
  }

  function trimBom(value) {
    return String(value || "").replace(/^\uFEFF/, "");
  }

  function buildGroups(rows) {
    var map = new Map();
    rows.forEach(function (row) {
      var id = row.id || "未编号";
      if (!map.has(id)) {
        map.set(id, {
          id: id,
          question: row.question || "问题文本未提供",
          rows: [],
          plainAnswers: [],
          oagAnswers: [],
          warnings: []
        });
      }
      var group = map.get(id);
      if (row.question && group.question !== row.question && group.question !== "问题文本未提供") {
        group.warnings.push("同一序号存在不一致的问题文本，已使用第一条。");
      }
      if (group.question === "问题文本未提供" && row.question) {
        group.question = row.question;
      }
      group.rows.push(row);
      group.plainAnswers.push(row.plain);
      group.oagAnswers.push(row.oag);
    });

    var groups = Array.from(map.values());
    groups.forEach(function (group) {
      group.plainStats = pendingStats(group.plainAnswers);
      group.oagStats = pendingStats(group.oagAnswers);
      group.advantage = null;
      group.searchText = normalizeForSearch([
        group.id,
        group.question,
        group.plainAnswers.join("\n"),
        group.oagAnswers.join("\n")
      ].join("\n"));
      if (group.rows.length !== EXPECTED_RUNS) {
        group.warnings.push("序号 " + group.id + " 有 " + group.rows.length + " 行记录，预期为 5 行。");
      }
    });
    groups.sort(compareId);
    return groups;
  }

  function scoreGroupsChunked(groups, token, done) {
    var index = 0;
    var chunkSize = 4;
    function processChunk() {
      if (token !== state.loadToken) return;
      var end = Math.min(index + chunkSize, groups.length);
      for (; index < end; index += 1) {
        finalizeGroupStats(groups[index]);
      }
      state.loadingMessage = "正在计算稳定性：" + index + " / " + groups.length;
      render();
      if (index < groups.length) {
        setTimeout(processChunk, 0);
      } else {
        done();
      }
    }
    processChunk();
  }

  function finalizeGroupStats(group) {
    group.plainStats = computeStability(group.plainAnswers);
    group.oagStats = computeStability(group.oagAnswers);
    group.advantage = scoreAvailable(group.oagStats) && scoreAvailable(group.plainStats)
      ? round1(group.oagStats.score - group.plainStats.score)
      : null;
    if (group.plainStats.missingCount > 0) {
      group.warnings.push("序号 " + group.id + " 的无 OAG 回答存在 " + group.plainStats.missingCount + " 条缺失，已按测试环境噪声排除在评分外。");
    }
    if (group.oagStats.missingCount > 0) {
      group.warnings.push("序号 " + group.id + " 的有 OAG 回答存在 " + group.oagStats.missingCount + " 条缺失，已按测试环境噪声排除在评分外。");
    }
    if (!scoreAvailable(group.plainStats)) {
      group.warnings.push("序号 " + group.id + " 的无 OAG 有效回答少于 2 条，未计算稳定性分。");
    }
    if (!scoreAvailable(group.oagStats)) {
      group.warnings.push("序号 " + group.id + " 的有 OAG 有效回答少于 2 条，未计算稳定性分。");
    }
  }

  function pendingStats(answers) {
    var missingCount = answers.filter(isMissingAnswer).length;
    return {
      score: null,
      available: false,
      consensusScore: null,
      coverageScore: null,
      numericScore: null,
      structureScore: null,
      literalSimilarity: null,
      exactRate: null,
      completeness: answers.length ? round1(((answers.length - missingCount) / answers.length) * 100) : 0,
      missingCount: missingCount,
      validCount: answers.length - missingCount,
      explanations: {
        consensus: ["稳定性计算中..."],
        coverage: ["稳定性计算中..."],
        numeric: ["稳定性计算中..."],
        structure: ["稳定性计算中..."]
      }
    };
  }

  function collectGroupWarnings(groups) {
    var warnings = [];
    groups.forEach(function (group) {
      group.warnings.forEach(function (warning) { warnings.push(warning); });
    });
    return dedupe(warnings).slice(0, 12);
  }

  function computeStability(answers) {
    var normalized = answers.map(function (answer, index) {
      return {
        raw: String(answer || ""),
        analysis: analyzeAnswer(answer, index + 1),
        missing: isMissingAnswer(answer)
      };
    });
    var valid = normalized.filter(function (item) { return !item.missing; });
    var missingCount = normalized.filter(function (item) { return item.missing; }).length;
    var completeness = answers.length ? (answers.length - missingCount) / answers.length : 0;
    if (valid.length < 2) {
      return emptyStats(valid.length, missingCount, completeness);
    }
    var analyses = valid.map(function (item) { return item.analysis; });
    var corpusModel = buildCorpusModel(analyses);
    var consensus = scoreConsensus(analyses, corpusModel);
    var coverage = scoreCoverage(analyses);
    var numeric = scoreNumericConsistency(analyses);
    var structure = scoreStructure(analyses);
    var literal = scoreLiteral(analyses, corpusModel);
    var score = (
      consensus.score * 0.35 +
      coverage.score * 0.20 +
      numeric.score * 0.35 +
      structure.score * 0.10
    );
    return {
      score: round1(score),
      available: true,
      consensusScore: round1(consensus.score),
      coverageScore: round1(coverage.score),
      numericScore: round1(numeric.score),
      structureScore: round1(structure.score),
      literalSimilarity: round1(literal.average * 100),
      exactRate: round1(literal.exactRate * 100),
      completeness: round1(completeness * 100),
      missingCount: missingCount,
      validCount: valid.length,
      explanations: {
        consensus: consensus.explanations,
        coverage: coverage.explanations,
        numeric: numeric.explanations,
        structure: structure.explanations
      }
    };
  }

  function analyzeAnswer(answer, runNumber) {
    var raw = String(answer || "");
    var text = markdownToText(raw).slice(0, SCORE_TEXT_LIMIT);
    var units = splitInformationUnits(raw, text);
    var tokens = mixedTokens(text);
    return {
      runNumber: runNumber,
      raw: raw,
      text: text,
      normalizedText: normalizeAnswer(raw),
      units: units,
      tokens: tokens,
      tokenSet: dedupe(tokens),
      numbers: extractComparableValues(text),
      structure: extractStructure(raw, text)
    };
  }

  function markdownToText(raw) {
    return String(raw || "")
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/!\[[^\]]*\]\([^)]+\)/g, " ")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/^\s{0,3}#{1,6}\s*/gm, "")
      .replace(/^\s*[-*+]\s+/gm, "")
      .replace(/^\s*\d+\.\s+/gm, "")
      .replace(/[|`>*_~]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function splitInformationUnits(raw, text) {
    var source = String(raw || "").slice(0, SCORE_TEXT_LIMIT);
    var tableRows = source.split(/\r?\n/).filter(function (line) { return /^\s*\|.+\|\s*$/.test(line); });
    var listRows = source.split(/\r?\n/).filter(function (line) { return /^\s*([-*+]|\d+\.)\s+/.test(line); });
    var sentenceRows = String(text || "").split(/[。！？!?；;\n\r]+/);
    return tableRows.concat(listRows).concat(sentenceRows)
      .map(function (item) { return markdownToText(item).trim(); })
      .filter(function (item) { return item.length >= 4; })
      .slice(0, UNIT_LIMIT);
  }

  function mixedTokens(text) {
    var clean = normalizeAnswer(text).slice(0, TOKEN_TEXT_LIMIT);
    var tokens = [];
    var words = clean.match(/[a-zA-Z]+|\d+(?:\.\d+)?%?|[\u4e00-\u9fff]/g) || [];
    words.forEach(function (word) {
      if (word.length > 1 || /[\u4e00-\u9fff]/.test(word)) tokens.push(word);
    });
    var compact = clean.replace(/\s+/g, "").slice(0, TOKEN_TEXT_LIMIT);
    for (var n = 2; n <= 3; n += 1) {
      for (var i = 0; i <= compact.length - n; i += 1) {
        tokens.push("g" + n + ":" + compact.slice(i, i + n));
      }
    }
    return tokens.slice(0, 1200);
  }

  function extractComparableValues(text) {
    var source = String(text || "").slice(0, SCORE_TEXT_LIMIT);
    var values = [];
    var patterns = [
      /\b\d{6}\b/g,
      /-?\d+(?:\.\d+)?\s*%/g,
      /\d{4}[-/年]\d{1,2}([-/月]\d{1,2}日?)?/g,
      /第\s*\d+\s*名|前\s*\d+|TOP\s*\d+/gi,
      /\b[A-Z]\d+\b/g,
      /-?\d+(?:\.\d+)?/g
    ];
    patterns.forEach(function (regex) {
      var match;
      while ((match = regex.exec(source)) !== null) {
        var value = normalizeComparableValue(match[0]);
        if (value && !/^\d{4}$/.test(value)) values.push(value);
      }
    });
    return cleanupComparableValues(dedupe(values)).slice(0, 80);
  }

  function extractStructure(raw, text) {
    var source = String(raw || "").slice(0, SCORE_TEXT_LIMIT);
    var lines = source.split(/\r?\n/);
    return {
      headings: (source.match(/^\s{0,3}#{1,6}\s+/gm) || []).length,
      lists: lines.filter(function (line) { return /^\s*([-*+]|\d+\.)\s+/.test(line); }).length,
      tables: lines.filter(function (line) { return /^\s*\|.+\|\s*$/.test(line); }).length,
      codeBlocks: (source.match(/```/g) || []).length / 2,
      paragraphs: String(text || "").split(/[。！？!?]/).filter(function (item) { return item.trim().length > 6; }).length
    };
  }

  function scoreConsensus(analyses, corpusModel) {
    var matrix = pairwiseSimilarityMatrix(analyses, corpusModel);
    var pairs = flattenPairs(matrix);
    var mean = pairs.length ? average(pairs) : 0;
    var median = pairs.length ? percentile(pairs, 0.5) : 0;
    var lowerQuartile = pairs.length ? percentile(pairs, 0.25) : 0;
    var cluster = consensusCluster(matrix);
    var score = (
      calibrateSimilarity(mean) * 0.45 +
      calibrateSimilarity(median) * 0.25 +
      calibrateSimilarity(lowerQuartile) * 0.15 +
      cluster.coverage * 0.15
    ) * 100;
    return {
      score: score,
      explanations: [
        "多数派共识：" + cluster.coverageLabel + "；平均相似 " + round1(mean * 100) + "%；中位相似 " + round1(median * 100) + "%",
        "离群轮次：" + (cluster.outliers.length ? cluster.outliers.join("、") : "无明显离群")
      ]
    };
  }

  function scoreCoverage(analyses) {
    var coverageScores = analyses.map(function (source) {
      if (!source.units.length) return 0;
      var unitScores = source.units.map(function (unit) {
        var support = analyses.filter(function (target) { return target.runNumber !== source.runNumber; }).map(function (target) {
          return bestUnitSimilarity(unit, target.units);
        });
        return support.length ? average(support) : 0;
      });
      return calibrateSimilarity(average(unitScores));
    });
    var score = average(coverageScores) * 100;
    var consensusUnits = topConsensusUnits(analyses);
    var weakRuns = analyses.filter(function (analysis, index) {
      return coverageScores[index] < 0.55;
    }).map(function (analysis) { return "第" + analysis.runNumber + "轮"; });
    return {
      score: score,
      explanations: [
        "相似表达：" + (consensusUnits.length ? consensusUnits.join("；") : "未形成稳定相似表达"),
        "覆盖不足：" + (weakRuns.length ? weakRuns.join("、") : "无明显覆盖不足")
      ]
    };
  }

  function scoreNumericConsistency(analyses) {
    var sets = analyses.map(function (analysis) { return analysis.numbers; });
    var anyValues = sets.some(function (set) { return set.length > 0; });
    if (!anyValues) {
      return {
        score: 100,
        explanations: ["数值/实体：未检测到可比较数值，按中性一致处理。", "数值漂移：无"]
      };
    }
    var pairAverage = pairwiseSetAverage(sets);
    var counts = countKeys(sets);
    var stable = Object.keys(counts).filter(function (key) { return counts[key] >= Math.ceil(analyses.length * 0.8); });
    var partial = Object.keys(counts).filter(function (key) { return counts[key] > 0 && counts[key] < Math.ceil(analyses.length * 0.8); });
    var stableShare = Object.keys(counts).length ? stable.length / Object.keys(counts).length : 1;
    var score = (pairAverage * 0.70 + stableShare * 0.30) * 100;
    return {
      score: score,
      explanations: [
        "稳定数值/实体：" + (stable.length ? stable.slice(0, 8).join("、") : "无高频稳定项"),
        "数值漂移：" + (partial.length ? partial.slice(0, 8).join("、") : "无明显漂移")
      ]
    };
  }

  function calibrateSimilarity(value) {
    return Math.sqrt(clamp(value, 0, 1));
  }

  function scoreStructure(analyses) {
    var scores = [];
    for (var i = 0; i < analyses.length; i += 1) {
      for (var j = i + 1; j < analyses.length; j += 1) {
        scores.push(structureSimilarity(analyses[i].structure, analyses[j].structure));
      }
    }
    var averageScore = scores.length ? average(scores) : 0;
    var labels = structureLabels(analyses);
    return {
      score: averageScore * 100,
      explanations: [
        "结构特征：" + (labels.length ? labels.join("、") : "以普通段落为主")
      ]
    };
  }

  function scoreLiteral(analyses) {
    var pairs = [];
    var exact = 0;
    for (var i = 0; i < analyses.length; i += 1) {
      for (var j = i + 1; j < analyses.length; j += 1) {
        var score = similarity(analyses[i].normalizedText, analyses[j].normalizedText);
        pairs.push(score);
        if (analyses[i].normalizedText === analyses[j].normalizedText) exact += 1;
      }
    }
    return {
      average: pairs.length ? average(pairs) : 0,
      exactRate: pairs.length ? exact / pairs.length : 0
    };
  }

  function emptyStats(validCount, missingCount, completeness) {
    return {
      score: null,
      available: false,
      consensusScore: null,
      coverageScore: null,
      numericScore: null,
      structureScore: null,
      literalSimilarity: null,
      exactRate: null,
      completeness: round1(completeness * 100),
      missingCount: missingCount,
      validCount: validCount,
      explanations: {
        consensus: ["有效回答少于 2 条，无法形成共识比较。"],
        coverage: ["有效回答少于 2 条，无法比较信息覆盖。"],
        numeric: ["有效回答少于 2 条，无法比较数值一致性。"],
        structure: ["有效回答少于 2 条，无法比较结构一致性。"]
      }
    };
  }

  function isMissingAnswer(text) {
    var value = String(text == null ? "" : text).trim();
    if (!value) return true;
    var normalized = value
      .replace(/^["'`]+|["'`]+$/g, "")
      .replace(/\s+/g, "")
      .toLowerCase();
    return ["none", "null", "nan", "undefined", "空", "无", "无回答", "未回答", "n/a", "na"].indexOf(normalized) >= 0;
  }

  function normalizeAnswer(text) {
    return String(text || "")
      .replace(/```[\s\S]*?```/g, function (match) { return match.replace(/```/g, " "); })
      .replace(/`([^`]+)`/g, "$1")
      .replace(/!\[[^\]]*\]\([^)]+\)/g, " ")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/[#>*_\-|~]/g, " ")
      .replace(/[，。！？；：“”‘’、,.!?;:"'()[\]{}]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function normalizeForSearch(text) {
    return String(text || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function normalizeComparableValue(value) {
    return String(value || "")
      .replace(/\s+/g, "")
      .replace(/％/g, "%")
      .replace(/年|月/g, "-")
      .replace(/日/g, "")
      .toUpperCase();
  }

  function buildCorpusModel(analyses) {
    var documentFrequency = {};
    analyses.forEach(function (analysis) {
      dedupe(analysis.tokens).forEach(function (token) {
        documentFrequency[token] = (documentFrequency[token] || 0) + 1;
      });
    });
    var total = analyses.length;
    return { df: documentFrequency, total: total };
  }

  function pairwiseSimilarityMatrix(analyses, corpusModel) {
    var matrix = analyses.map(function () { return []; });
    for (var i = 0; i < analyses.length; i += 1) {
      for (var j = 0; j < analyses.length; j += 1) {
        if (i === j) matrix[i][j] = 1;
        else if (matrix[j][i] != null) matrix[i][j] = matrix[j][i];
        else matrix[i][j] = ensembleSimilarity(analyses[i], analyses[j], corpusModel);
      }
    }
    return matrix;
  }

  function ensembleSimilarity(a, b, corpusModel) {
    var cosine = tfidfCosine(a.tokens, b.tokens, corpusModel);
    var rouge = rougeL(a.normalizedText, b.normalizedText);
    var meteor = meteorLike(a.tokenSet, b.tokenSet);
    var overlap = jaccard(a.tokenSet, b.tokenSet);
    var containment = tokenContainment(a.tokenSet, b.tokenSet);
    var dice = characterDice(a.normalizedText, b.normalizedText);
    return clamp(cosine * 0.18 + rouge * 0.14 + meteor * 0.16 + overlap * 0.10 + containment * 0.17 + dice * 0.25, 0, 1);
  }

  function cleanupComparableValues(values) {
    var set = new Set(values);
    return values.filter(function (value) {
      if (/^-?\d+(?:\.\d+)?$/.test(value) && set.has(value + "%")) return false;
      return true;
    });
  }

  function tfidfCosine(tokensA, tokensB, corpusModel) {
    var vectorA = tfidfVector(tokensA, corpusModel);
    var vectorB = tfidfVector(tokensB, corpusModel);
    var dot = 0;
    var normA = 0;
    var normB = 0;
    Object.keys(vectorA).forEach(function (token) {
      normA += vectorA[token] * vectorA[token];
      if (vectorB[token]) dot += vectorA[token] * vectorB[token];
    });
    Object.keys(vectorB).forEach(function (token) {
      normB += vectorB[token] * vectorB[token];
    });
    return normA && normB ? dot / (Math.sqrt(normA) * Math.sqrt(normB)) : 0;
  }

  function tfidfVector(tokens, corpusModel) {
    var counts = {};
    tokens.forEach(function (token) { counts[token] = (counts[token] || 0) + 1; });
    var total = tokens.length || 1;
    var vector = {};
    Object.keys(counts).forEach(function (token) {
      var tf = counts[token] / total;
      var idf = Math.log((1 + corpusModel.total) / (1 + (corpusModel.df[token] || 0))) + 1;
      vector[token] = tf * idf;
    });
    return vector;
  }

  function rougeL(a, b) {
    var seqA = Array.from(String(a || "").replace(/\s+/g, "").slice(0, LCS_LIMIT));
    var seqB = Array.from(String(b || "").replace(/\s+/g, "").slice(0, LCS_LIMIT));
    if (!seqA.length || !seqB.length) return 0;
    if (seqA.length * seqB.length > 120000) {
      return similarity(seqA.join(""), seqB.join(""));
    }
    var lcs = lcsLength(seqA, seqB);
    var precision = lcs / seqA.length;
    var recall = lcs / seqB.length;
    return precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
  }

  function lcsLength(a, b) {
    var previous = new Array(b.length + 1).fill(0);
    var current = new Array(b.length + 1).fill(0);
    for (var i = 1; i <= a.length; i += 1) {
      for (var j = 1; j <= b.length; j += 1) {
        current[j] = a[i - 1] === b[j - 1] ? previous[j - 1] + 1 : Math.max(previous[j], current[j - 1]);
      }
      var temp = previous;
      previous = current;
      current = temp.fill(0);
    }
    return previous[b.length];
  }

  function meteorLike(tokensA, tokensB) {
    if (!tokensA.length || !tokensB.length) return 0;
    var setA = new Set(tokensA);
    var setB = new Set(tokensB);
    var matches = 0;
    setA.forEach(function (token) { if (setB.has(token)) matches += 1; });
    if (!matches) return 0;
    var precision = matches / setA.size;
    var recall = matches / setB.size;
    return (10 * precision * recall) / (recall + 9 * precision);
  }

  function tokenContainment(tokensA, tokensB) {
    if (!tokensA.length || !tokensB.length) return 0;
    var setA = new Set(tokensA);
    var setB = new Set(tokensB);
    var matches = 0;
    setA.forEach(function (token) { if (setB.has(token)) matches += 1; });
    return matches / Math.min(setA.size, setB.size);
  }

  function characterDice(a, b) {
    var charsA = Array.from(String(a || "").replace(/\s+/g, "").slice(0, TOKEN_TEXT_LIMIT));
    var charsB = Array.from(String(b || "").replace(/\s+/g, "").slice(0, TOKEN_TEXT_LIMIT));
    if (!charsA.length || !charsB.length) return 0;
    var counts = {};
    charsA.forEach(function (ch) { counts[ch] = (counts[ch] || 0) + 1; });
    var intersection = 0;
    charsB.forEach(function (ch) {
      if (counts[ch] > 0) {
        intersection += 1;
        counts[ch] -= 1;
      }
    });
    return (2 * intersection) / (charsA.length + charsB.length);
  }

  function flattenPairs(matrix) {
    var values = [];
    for (var i = 0; i < matrix.length; i += 1) {
      for (var j = i + 1; j < matrix.length; j += 1) {
        values.push(matrix[i][j]);
      }
    }
    return values;
  }

  function consensusCluster(matrix) {
    var pairs = flattenPairs(matrix);
    var threshold = pairs.length ? clamp(percentile(pairs, 0.25), 0.24, 0.62) : 0.45;
    var bestIndex = 0;
    var bestNeighbors = [];
    for (var i = 0; i < matrix.length; i += 1) {
      var neighbors = [];
      for (var j = 0; j < matrix.length; j += 1) {
        if (i === j || matrix[i][j] >= threshold) neighbors.push(j);
      }
      if (neighbors.length > bestNeighbors.length) {
        bestIndex = i;
        bestNeighbors = neighbors;
      }
    }
    var outliers = [];
    for (var k = 0; k < matrix.length; k += 1) {
      if (bestNeighbors.indexOf(k) < 0) outliers.push("第" + (k + 1) + "轮");
    }
    return {
      center: bestIndex,
      coverage: matrix.length ? bestNeighbors.length / matrix.length : 0,
      coverageLabel: bestNeighbors.length + "/" + matrix.length + " 轮进入多数派",
      outliers: outliers
    };
  }

  function bestUnitSimilarity(unit, units) {
    if (!units.length) return 0;
    var normalizedUnit = normalizeAnswer(unit);
    var unitTokens = dedupe(mixedTokens(unit));
    return Math.max.apply(null, units.slice(0, UNIT_LIMIT).map(function (target) {
      return lightweightTextSimilarity(normalizedUnit, unitTokens, target);
    }));
  }

  function lightweightTextSimilarity(normalizedA, tokensA, rawB) {
    var normalizedB = normalizeAnswer(rawB);
    var tokensB = dedupe(mixedTokens(rawB));
    return clamp(
      tokenContainment(tokensA, tokensB) * 0.42 +
      jaccard(tokensA, tokensB) * 0.28 +
      characterDice(normalizedA, normalizedB) * 0.30,
      0,
      1
    );
  }

  function topConsensusUnits(analyses) {
    var candidates = [];
    analyses.forEach(function (analysis) {
      analysis.units.slice(0, 6).forEach(function (unit) {
        var support = analyses.filter(function (target) { return target.runNumber !== analysis.runNumber; }).map(function (target) {
          return bestUnitSimilarity(unit, target.units);
        });
        candidates.push({ unit: unit, score: support.length ? average(support) : 0 });
      });
    });
    return candidates
      .filter(function (item) { return item.score >= 0.45; })
      .sort(function (a, b) { return b.score - a.score; })
      .map(function (item) { return item.unit.length > 36 ? item.unit.slice(0, 36) + "..." : item.unit; })
      .filter(function (item, index, arr) { return arr.indexOf(item) === index; })
      .slice(0, 4);
  }

  function pairwiseSetAverage(sets) {
    var scores = [];
    for (var i = 0; i < sets.length; i += 1) {
      for (var j = i + 1; j < sets.length; j += 1) {
        scores.push(jaccard(sets[i], sets[j]));
      }
    }
    return scores.length ? average(scores) : 0;
  }

  function jaccard(a, b) {
    var setA = new Set(a || []);
    var setB = new Set(b || []);
    var union = new Set(Array.from(setA).concat(Array.from(setB)));
    if (!union.size) return 1;
    var intersection = 0;
    setA.forEach(function (item) { if (setB.has(item)) intersection += 1; });
    return intersection / union.size;
  }

  function countKeys(sets) {
    var counts = {};
    sets.forEach(function (set) {
      dedupe(set).forEach(function (key) {
        counts[key] = (counts[key] || 0) + 1;
      });
    });
    return counts;
  }

  function structureSimilarity(a, b) {
    var keys = ["headings", "lists", "tables", "codeBlocks", "paragraphs"];
    var diff = 0;
    var maxTotal = 0;
    keys.forEach(function (key) {
      diff += Math.abs((a[key] || 0) - (b[key] || 0));
      maxTotal += Math.max(a[key] || 0, b[key] || 0);
    });
    return maxTotal ? clamp(1 - diff / maxTotal, 0, 1) : 1;
  }

  function structureLabels(analyses) {
    var totals = { headings: 0, lists: 0, tables: 0, codeBlocks: 0 };
    analyses.forEach(function (analysis) {
      Object.keys(totals).forEach(function (key) { totals[key] += analysis.structure[key] || 0; });
    });
    var labels = [];
    if (totals.headings) labels.push("标题");
    if (totals.lists) labels.push("列表");
    if (totals.tables) labels.push("表格");
    if (totals.codeBlocks) labels.push("代码块");
    return labels;
  }

  function scoreAvailable(stats) {
    return stats && stats.available && typeof stats.score === "number";
  }

  function scoreOrZero(stats) {
    return scoreAvailable(stats) ? stats.score : -1;
  }

  function dimensionOrZero(stats, key) {
    if (!scoreAvailable(stats)) return -1;
    return typeof stats[key] === "number" ? stats[key] : -1;
  }

  function dimensionAdvantage(group, key) {
    if (!scoreAvailable(group.oagStats) || !scoreAvailable(group.plainStats)) return -999;
    return dimensionOrZero(group.oagStats, key) - dimensionOrZero(group.plainStats, key);
  }

  function nullableNumber(value) {
    return typeof value === "number" ? value : -999;
  }

  function hasNumericDrift(stats) {
    return Boolean(stats && stats.explanations && stats.explanations.numeric && stats.explanations.numeric.some(function (line) {
      return line.indexOf("漂移") >= 0 && line.indexOf("无明显") < 0 && line.indexOf("无") !== line.length - 1;
    }));
  }

  function similarity(a, b) {
    if (!a && !b) return 0;
    if (!a || !b) return 0;
    if (a === b) return 1;
    var gramsA = ngrams(a);
    var gramsB = ngrams(b);
    var intersection = 0;
    gramsA.forEach(function (count, key) {
      if (gramsB.has(key)) intersection += Math.min(count, gramsB.get(key));
    });
    var totalA = sumMap(gramsA);
    var totalB = sumMap(gramsB);
    return totalA + totalB > 0 ? (2 * intersection) / (totalA + totalB) : 0;
  }

  function ngrams(text) {
    var clean = text.replace(/\s+/g, "");
    var size = clean.length > 80 ? 3 : 2;
    var map = new Map();
    if (clean.length <= size) {
      map.set(clean, 1);
      return map;
    }
    for (var i = 0; i <= clean.length - size; i += 1) {
      var key = clean.slice(i, i + size);
      map.set(key, (map.get(key) || 0) + 1);
    }
    return map;
  }

  function sumMap(map) {
    var total = 0;
    map.forEach(function (value) { total += value; });
    return total;
  }

  function applyControls() {
    var query = normalizeForSearch(els.searchInput.value);
    var filter = els.filterSelect.value;
    state.filtered = state.groups.filter(function (group) {
      if (query && group.searchText.indexOf(query) < 0) return false;
      if (filter === "consensusImproved") return scoreAvailable(group.oagStats) && scoreAvailable(group.plainStats) && group.oagStats.consensusScore - group.plainStats.consensusScore >= 8;
      if (filter === "coverageImproved") return scoreAvailable(group.oagStats) && scoreAvailable(group.plainStats) && group.oagStats.coverageScore - group.plainStats.coverageScore >= 8;
      if (filter === "numericConflict") return hasNumericDrift(group.plainStats) || hasNumericDrift(group.oagStats);
      if (filter === "insufficient") return !scoreAvailable(group.plainStats) || !scoreAvailable(group.oagStats);
      if (filter === "low") return (scoreAvailable(group.plainStats) && group.plainStats.score < 70) || (scoreAvailable(group.oagStats) && group.oagStats.score < 70);
      if (filter === "warning") return group.warnings.length > 0;
      return true;
    });
    sortGroups(state.filtered, els.sortSelect.value);
    if (state.currentIndex >= state.filtered.length) state.currentIndex = 0;
    render();
  }

  function showLoading(message) {
    state.loading = true;
    state.loadingMessage = message || "正在处理...";
    els.csvInput.disabled = true;
    els.reloadBtn.disabled = true;
    render();
  }

  function hideLoading() {
    state.loading = false;
    state.loadingMessage = "";
    els.csvInput.disabled = false;
    els.reloadBtn.disabled = false;
  }

  function sortGroups(groups, sort) {
    groups.sort(function (a, b) {
      if (sort === "advantageDesc") return nullableNumber(b.advantage) - nullableNumber(a.advantage) || compareId(a, b);
      if (sort === "advantageAsc") return nullableNumber(a.advantage) - nullableNumber(b.advantage) || compareId(a, b);
      if (sort === "consensusDesc") return dimensionAdvantage(b, "consensusScore") - dimensionAdvantage(a, "consensusScore") || compareId(a, b);
      if (sort === "coverageDesc") return dimensionAdvantage(b, "coverageScore") - dimensionAdvantage(a, "coverageScore") || compareId(a, b);
      if (sort === "numericDesc") return dimensionAdvantage(b, "numericScore") - dimensionAdvantage(a, "numericScore") || compareId(a, b);
      if (sort === "plainAsc") return scoreOrZero(a.plainStats) - scoreOrZero(b.plainStats) || compareId(a, b);
      if (sort === "oagAsc") return scoreOrZero(a.oagStats) - scoreOrZero(b.oagStats) || compareId(a, b);
      return compareId(a, b);
    });
  }

  function render() {
    renderNotices();
    renderSummary();
    if (state.loading) {
      els.emptyState.hidden = false;
      els.singleView.hidden = true;
      els.allView.hidden = true;
      els.emptyState.querySelector("h2").textContent = "正在处理 CSV";
      els.emptyState.querySelector("p").textContent = state.loadingMessage || "正在读取并计算稳定性...";
      return;
    }
    var hasData = state.filtered.length > 0;
    els.emptyState.hidden = state.groups.length > 0;
    els.singleView.hidden = !hasData || state.view !== "single";
    els.allView.hidden = !hasData || state.view !== "all";
    if (hasData && state.view === "single") renderCurrentQuestion();
    if (hasData && state.view === "all") renderTable();
    if (state.groups.length > 0 && state.filtered.length === 0) {
      els.emptyState.hidden = false;
      els.emptyState.querySelector("h2").textContent = "没有匹配的问题";
      els.emptyState.querySelector("p").innerHTML = "请调整搜索关键词或筛选条件。";
    } else {
      els.emptyState.querySelector("h2").textContent = "导入测试结果 CSV";
      els.emptyState.querySelector("p").innerHTML = "推荐 CSV 表头为：序号、问题、朴素回答、OAG回答。页面也会尝试读取 <code>data/results.csv</code>。";
    }
  }

  function renderNotices() {
    if (!state.warnings.length && state.sourceName) {
      els.noticePanel.hidden = true;
      els.noticePanel.innerHTML = "";
      return;
    }
    var messages = state.warnings.slice();
    if (state.sourceName) {
      messages.unshift("当前数据源：" + state.sourceName);
    }
    if (!messages.length) {
      els.noticePanel.hidden = true;
      return;
    }
    els.noticePanel.hidden = false;
    els.noticePanel.innerHTML = "<strong>数据提示</strong><ul>" + messages.map(function (message) {
      return "<li>" + escapeHtml(message) + "</li>";
    }).join("") + "</ul>";
  }

  function renderSummary() {
    var groups = state.groups;
    var rows = groups.reduce(function (total, group) { return total + group.rows.length; }, 0);
    var plainScores = groups.map(function (group) { return group.plainStats.score; }).filter(function (score) { return typeof score === "number"; });
    var oagScores = groups.map(function (group) { return group.oagStats.score; }).filter(function (score) { return typeof score === "number"; });
    var advantages = groups.map(function (group) { return group.advantage; }).filter(function (score) { return typeof score === "number"; });
    var plainAvg = plainScores.length ? average(plainScores) : null;
    var oagAvg = oagScores.length ? average(oagScores) : null;
    var advantageAvg = advantages.length ? average(advantages) : null;
    els.totalQuestions.textContent = String(groups.length);
    els.totalRuns.textContent = rows + " 条回答记录";
    els.plainAverage.textContent = plainAvg == null ? "--" : round1(plainAvg);
    els.oagAverage.textContent = oagAvg == null ? "--" : round1(oagAvg);
    els.advantageAverage.textContent = advantageAvg == null ? "--" : signed(round1(advantageAvg));
    els.advantageHint.textContent = advantageAvg == null ? "有效样本不足" : describeAdvantage(advantageAvg);
  }

  function renderCurrentQuestion() {
    var group = state.filtered[state.currentIndex];
    els.prevBtn.disabled = state.currentIndex <= 0;
    els.nextBtn.disabled = state.currentIndex >= state.filtered.length - 1;
    els.questionPosition.textContent = (state.currentIndex + 1) + " / " + state.filtered.length;
    els.questionText.textContent = group.question;
    els.questionMeta.textContent = "序号 " + group.id + " · " + group.rows.length + " 轮记录" + (group.warnings.length ? " · 数据异常" : "");
    els.currentAdvantage.textContent = group.advantage == null ? "--" : signed(group.advantage);
    els.currentAdvantage.className = group.advantage > 0 ? "good" : group.advantage < 0 ? "bad" : "";
    els.plainScoreLabel.textContent = formatScore(group.plainStats.score);
    els.oagScoreLabel.textContent = formatScore(group.oagStats.score);
    els.plainScoreBar.style.width = scoreAvailable(group.plainStats) ? clamp(group.plainStats.score, 0, 100) + "%" : "0";
    els.oagScoreBar.style.width = scoreAvailable(group.oagStats) ? clamp(group.oagStats.score, 0, 100) + "%" : "0";
    els.plainColumnMeta.textContent = statsText(group.plainStats);
    els.oagColumnMeta.textContent = statsText(group.oagStats);
    els.plainDimensionDetails.innerHTML = dimensionDetailsHtml(group.plainStats);
    els.oagDimensionDetails.innerHTML = dimensionDetailsHtml(group.oagStats);
    renderAnswerList(els.plainAnswers, group.plainAnswers);
    renderAnswerList(els.oagAnswers, group.oagAnswers);
  }

  function renderAnswerList(container, answers) {
    container.innerHTML = "";
    answers.forEach(function (answer, index) {
      var missing = isMissingAnswer(answer);
      var card = els.cardTemplate.content.firstElementChild.cloneNode(true);
      if (missing) card.classList.add("missing-answer");
      card.querySelector(".run-label").textContent = "第 " + (index + 1) + " 轮";
      card.querySelector(".length-label").textContent = missing ? "缺失回答" : normalizeAnswer(answer).length + " 字符";
      card.querySelector(".markdown-body").innerHTML = renderMarkdown(missing ? "（缺失回答，已排除在稳定性评分外）" : answer);
      card.querySelector(".raw-text").value = answer || "";
      card.querySelector(".toggle-expand").addEventListener("click", function () {
        card.classList.toggle("collapsed");
        this.textContent = card.classList.contains("collapsed") ? "展开" : "收起";
      });
      card.querySelector(".toggle-raw").addEventListener("click", function () {
        var raw = card.querySelector(".raw-text");
        raw.hidden = !raw.hidden;
        this.textContent = raw.hidden ? "查看原文" : "隐藏原文";
      });
      card.querySelector(".copy-answer").addEventListener("click", function () {
        copyText(answer || "", this);
      });
      container.appendChild(card);
    });
  }

  function renderTable() {
    els.tableCount.textContent = state.filtered.length + " 个结果";
    els.resultTableBody.innerHTML = state.filtered.map(function (group, index) {
      var statusClass = group.warnings.length ? "warning" : "";
      var statusText = group.warnings.length ? "需检查" : "正常";
      return [
        "<tr data-index=\"" + index + "\">",
        "<td>" + escapeHtml(group.id) + "</td>",
        "<td class=\"question-cell\">" + escapeHtml(group.question) + "</td>",
        "<td>" + formatScore(group.plainStats.score) + "</td>",
        "<td>" + formatScore(group.oagStats.score) + "</td>",
        "<td>" + scorePill(dimensionDiff(group, "consensusScore")) + "</td>",
        "<td>" + scorePill(dimensionDiff(group, "coverageScore")) + "</td>",
        "<td>" + scorePill(dimensionDiff(group, "numericScore")) + "</td>",
        "<td>" + scorePill(group.advantage) + "</td>",
        "<td>" + group.rows.length + " / " + EXPECTED_RUNS + "</td>",
        "<td><span class=\"status-pill " + statusClass + "\">" + statusText + "</span></td>",
        "</tr>"
      ].join("");
    }).join("");
    Array.from(els.resultTableBody.querySelectorAll("tr")).forEach(function (row) {
      row.addEventListener("click", function () {
        state.currentIndex = Number(row.getAttribute("data-index"));
        setView("single");
      });
    });
  }

  function setView(view) {
    state.view = view;
    els.singleTab.classList.toggle("active", view === "single");
    els.allTab.classList.toggle("active", view === "all");
    render();
  }

  function moveQuestion(delta) {
    var next = state.currentIndex + delta;
    if (next < 0 || next >= state.filtered.length) return;
    state.currentIndex = next;
    renderCurrentQuestion();
  }

  function renderMarkdown(input) {
    var text = escapeHtml(String(input || ""));
    var blocks = [];
    text = text.replace(/```([\s\S]*?)```/g, function (_, code) {
      var token = "\u0000CODE" + blocks.length + "\u0000";
      blocks.push("<pre><code>" + code.trim() + "</code></pre>");
      return token;
    });
    text = renderTables(text);
    text = text
      .replace(/^### (.*)$/gm, "<h3>$1</h3>")
      .replace(/^## (.*)$/gm, "<h2>$1</h2>")
      .replace(/^# (.*)$/gm, "<h1>$1</h1>")
      .replace(/^&gt; (.*)$/gm, "<blockquote>$1</blockquote>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, "<a href=\"$2\" target=\"_blank\" rel=\"noopener noreferrer\">$1</a>");
    text = renderLists(text);
    text = text.split(/\n{2,}/).map(function (chunk) {
      if (/^\s*<(h\d|ul|ol|pre|blockquote|table)/.test(chunk)) return chunk;
      return "<p>" + chunk.replace(/\n/g, "<br>") + "</p>";
    }).join("");
    blocks.forEach(function (block, index) {
      text = text.replace("\u0000CODE" + index + "\u0000", block);
    });
    return text;
  }

  function renderLists(text) {
    var lines = text.split("\n");
    var output = [];
    var listType = null;
    lines.forEach(function (line) {
      var unordered = line.match(/^\s*[-*]\s+(.+)$/);
      var ordered = line.match(/^\s*\d+\.\s+(.+)$/);
      if (unordered || ordered) {
        var nextType = unordered ? "ul" : "ol";
        if (listType !== nextType) {
          if (listType) output.push("</" + listType + ">");
          output.push("<" + nextType + ">");
          listType = nextType;
        }
        output.push("<li>" + (unordered ? unordered[1] : ordered[1]) + "</li>");
      } else {
        if (listType) {
          output.push("</" + listType + ">");
          listType = null;
        }
        output.push(line);
      }
    });
    if (listType) output.push("</" + listType + ">");
    return output.join("\n");
  }

  function renderTables(text) {
    var lines = text.split("\n");
    var output = [];
    for (var i = 0; i < lines.length; i += 1) {
      if (isTableLine(lines[i]) && i + 1 < lines.length && isDividerLine(lines[i + 1])) {
        var tableLines = [lines[i]];
        i += 2;
        while (i < lines.length && isTableLine(lines[i])) {
          tableLines.push(lines[i]);
          i += 1;
        }
        i -= 1;
        output.push(tableToHtml(tableLines));
      } else {
        output.push(lines[i]);
      }
    }
    return output.join("\n");
  }

  function isTableLine(line) {
    return /^\s*\|.+\|\s*$/.test(line);
  }

  function isDividerLine(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
  }

  function tableToHtml(lines) {
    var rows = lines.map(splitTableRow);
    var head = rows[0];
    var body = rows.slice(1);
    return "<table><thead><tr>" + head.map(function (cell) {
      return "<th>" + cell + "</th>";
    }).join("") + "</tr></thead><tbody>" + body.map(function (row) {
      return "<tr>" + row.map(function (cell) { return "<td>" + cell + "</td>"; }).join("") + "</tr>";
    }).join("") + "</tbody></table>";
  }

  function splitTableRow(line) {
    return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(function (cell) {
      return cell.trim();
    });
  }

  function copyText(text, button) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flashCopied(button); });
    } else {
      var textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
      flashCopied(button);
    }
  }

  function flashCopied(button) {
    var old = button.textContent;
    button.textContent = "已复制";
    setTimeout(function () { button.textContent = old; }, 1100);
  }

  function scorePill(value) {
    if (typeof value !== "number") {
      return "<span class=\"score-pill flat\">--</span>";
    }
    var cls = value > 0 ? "good" : value < 0 ? "bad" : "flat";
    return "<span class=\"score-pill " + cls + "\">" + signed(value) + "</span>";
  }

  function statsText(stats) {
    if (!scoreAvailable(stats)) {
      var missingText = stats.missingCount > 0 ? " · 缺失 " + stats.missingCount + " 条" : "";
      return "有效样本不足 · 有效回答 " + stats.validCount + " 条" + missingText;
    }
    var parts = [
      "稳定性 " + stats.score,
      "字面相似 " + stats.literalSimilarity + "%",
      "完全重复 " + stats.exactRate + "%",
      "有效回答 " + stats.validCount + " 条",
      "缺失 " + stats.missingCount + " 条"
    ];
    return parts.join(" · ");
  }

  function dimensionDetailsHtml(stats) {
    var dimensionRows = DIMENSIONS.map(function (dimension) {
      var key = dimension.key + "Score";
      var score = stats[key];
      return [
        "<div class=\"dimension-row\">",
        "<span>" + dimension.label + "</span>",
        "<strong>" + formatScore(score) + "</strong>",
        "<div class=\"mini-track\"><div style=\"width:" + (typeof score === "number" ? clamp(score, 0, 100) : 0) + "%\"></div></div>",
        "</div>"
      ].join("");
    }).join("");
    var explanation = [
      "<section><h4>多数派共识</h4><p>" + escapeHtml((stats.explanations.consensus || []).join("；")) + "</p></section>",
      "<section><h4>信息覆盖</h4><p>" + escapeHtml((stats.explanations.coverage || []).join("；")) + "</p></section>",
      "<section><h4>数值一致</h4><p>" + escapeHtml((stats.explanations.numeric || []).join("；")) + "</p></section>",
      "<section><h4>结构一致性</h4><p>" + escapeHtml((stats.explanations.structure || []).join("；")) + "</p></section>"
    ].join("");
    return "<div class=\"dimension-grid\">" + dimensionRows + "</div><div class=\"explain-grid\">" + explanation + "</div>";
  }

  function formatScore(value) {
    return typeof value === "number" ? String(round1(value)) : "--";
  }

  function dimensionDiff(group, key) {
    if (!scoreAvailable(group.oagStats) || !scoreAvailable(group.plainStats)) return null;
    return round1(group.oagStats[key] - group.plainStats[key]);
  }

  function describeAdvantage(value) {
    if (value >= 8) return "整体提升明显";
    if (value <= -8) return "需关注下降问题";
    return "整体差异不大";
  }

  function compareId(a, b) {
    var na = Number(a.id);
    var nb = Number(b.id);
    if (Number.isFinite(na) && Number.isFinite(nb)) return na - nb;
    return String(a.id).localeCompare(String(b.id), "zh-CN", { numeric: true });
  }

  function average(values) {
    if (!values.length) return 0;
    return values.reduce(function (sum, value) { return sum + value; }, 0) / values.length;
  }

  function stddev(values, mean) {
    if (!values.length) return 0;
    var variance = average(values.map(function (value) { return Math.pow(value - mean, 2); }));
    return Math.sqrt(variance);
  }

  function percentile(values, p) {
    if (!values.length) return 0;
    var sorted = values.slice().sort(function (a, b) { return a - b; });
    var index = clamp(p, 0, 1) * (sorted.length - 1);
    var lower = Math.floor(index);
    var upper = Math.ceil(index);
    if (lower === upper) return sorted[lower];
    var weight = index - lower;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function round1(value) {
    return Math.round(value * 10) / 10;
  }

  function signed(value) {
    return (value > 0 ? "+" : "") + round1(value);
  }

  function dedupe(values) {
    return Array.from(new Set(values));
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
