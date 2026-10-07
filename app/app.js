const state = {
  attributes: [],
  indexed: [],
  clean: [],
  curves: [],
  models: [],
  control: [],
  importedFiles: [],
  model: null,
  frozenCandidates: [],
  modelResults: [],
  externalResults: [],
  externalAudit: null,
  externalClassResults: [],
  diagnosticResults: [],
  tests: [],
  pendingTestRows: [],
  pendingTestName: "",
};

const DATASET_LABELS = {
  attributes: "Atributos",
  indexed: "Dados brutos indexados",
  clean: "Dados limpos",
  curves: "Curvas interpoladas",
  models: "Relatorio de modelos",
  control: "Controle de qualidade",
};

const EXCLUDED_FEATURES = new Set([
  "numero_pontos",
  "status",
  "normalizado",
  "id_entrada",
  "referencia",
  "doi",
  "material_eletrodo",
  "eletrolito",
  "classe_alvo",
  "tipo_sinal",
  "unidade_potencial_usada",
  "unidade_sinal_usada",
]);

const COLORS = ["#0e7c7b", "#b36b00", "#243447", "#7a3e9d", "#b42318", "#2f6f3e", "#6d5f00", "#005ea8"];
const BASE_TECHNIQUES = ["knn", "centroid", "naive_bayes", "decision_tree", "random_forest"];
const BALANCE_STRATEGIES = ["none", "class_weight", "oversample", "oversample_weight"];

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  drawBrandSparkline();
  renderAll();
});

function bindEvents() {
  document.getElementById("csvInput").addEventListener("change", importCsvFiles);
  document.getElementById("testInput").addEventListener("change", importTestFile);
  document.getElementById("trainButton").addEventListener("click", safeAction(trainModel));
  document.getElementById("runTestButton").addEventListener("click", safeAction(runPendingTest, showTestError));
  document.getElementById("compareExternalButton").addEventListener("click", safeAction(compareExternalTechniques, showTestError));
  document.getElementById("exportStateButton").addEventListener("click", downloadModelState);
  document.getElementById("downloadModelButton").addEventListener("click", downloadModelState);
  document.getElementById("downloadReportButton").addEventListener("click", downloadExperimentReport);
  document.getElementById("downloadAttributesButton").addEventListener("click", () => downloadCsv("atributos_app.csv", state.attributes));
  document.getElementById("downloadTestsButton").addEventListener("click", () => downloadCsv("testes_ia.csv", state.tests));
  document.getElementById("exportTestsButton").addEventListener("click", () => downloadCsv("testes_ia.csv", state.tests));
  document.getElementById("tableSearch").addEventListener("input", renderDataTable);
  document.getElementById("materialFilter").addEventListener("change", renderDataTable);
  document.getElementById("datasetSelect").addEventListener("change", renderDataTable);
  document.getElementById("curveSelect").addEventListener("change", renderCurveChart);
  for (const id of ["targetColumn", "techniqueSelect", "knnK", "balanceStrategySelect", "signalKindSelect"]) {
    document.getElementById(id).addEventListener("change", safeAction(trainModel));
  }

  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab));
  });
}

async function importCsvFiles(event) {
  document.getElementById("actionError").textContent = "";
  const files = [...event.target.files];
  for (const file of files) {
    const text = await file.text();
    const table = parseCsv(text);
    const kind = detectDataset(file.name, table.headers);
    state[kind] = table.rows;
    state.importedFiles = state.importedFiles.filter((item) => item.kind !== kind);
    state.importedFiles.push({ name: file.name, kind, rows: table.rows.length });
  }
  state.model = null;
  state.frozenCandidates = [];
  state.externalAudit = null;
  state.tests = [];
  state.modelResults = [];
  state.externalResults = [];
  state.externalClassResults = [];
  state.diagnosticResults = [];
  renderAll();
}

async function importTestFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  const text = await file.text();
  const table = parseCsv(text);
  state.pendingTestRows = table.rows;
  state.pendingTestName = file.name;
  state.tests = [];
  state.externalAudit = null;
  state.externalResults = [];
  state.externalClassResults = [];
  state.diagnosticResults = [];
  document.getElementById("testStatus").textContent = `${file.name} carregado`;
  renderPredictions();
  renderExternalComparison();
  renderExternalClassResults();
  renderDiagnostics();
}

function detectDataset(fileName, headers) {
  const name = fileName.toLowerCase();
  const lower = headers.map((header) => header.toLowerCase());
  if (name.includes("atributos_voltamogramas") || lower.includes("e_min") || lower.includes("j_max")) return "attributes";
  if (name.includes("dados_brutos_indexados") || lower.includes("arquivo_origem") || lower.includes("colunas_numericas")) return "indexed";
  if (name.includes("relatorio_modelos") || lower.includes("problema") || lower.includes("modelo")) return "models";
  if (name.includes("controle") || lower.includes("motivo_exclusao")) return "control";
  if (name.includes("curvas_interpoladas") || lower.some((header) => /^f\d{4}$/.test(header))) return "curves";
  if (name.includes("dados_limpos") || (lower.includes("e") && lower.includes("j"))) return "clean";
  return "attributes";
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell);
  if (row.some((value) => value.trim() !== "")) rows.push(row);

  const headers = rows.shift()?.map((header) => header.trim()) ?? [];
  const objects = rows.map((values) => {
    const object = {};
    headers.forEach((header, index) => {
      object[header] = values[index] ?? "";
    });
    return object;
  });
  return { headers, rows: objects };
}

function renderAll() {
  updateMetrics();
  updateFilters();
  updateCurveSelect();
  updateTargetSelect();
  renderDataTable();
  renderCurveChart();
  renderMaterialChart();
  renderScatterChart();
  renderLearning();
  renderPredictions();
  renderExternalComparison();
  renderExternalClassResults();
  renderDiagnostics();
  renderExportSummary();
}

function activateTab(tab) {
  document.querySelectorAll(".tab-button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tab}`));
  if (tab === "graficos") {
    renderCurveChart();
    renderMaterialChart();
    renderScatterChart();
  }
}

function updateMetrics() {
  const entries = new Set([
    ...state.attributes.map((row) => row.id_entrada),
    ...state.clean.map((row) => row.id_entrada),
    ...state.curves.map((row) => row.id_entrada),
  ].filter(Boolean));
  document.getElementById("metricEntries").textContent = entries.size.toString();
  document.getElementById("metricCurves").textContent = uniqueValues(state.clean, "id_entrada").length || state.curves.length || "0";
  document.getElementById("metricMaterials").textContent = materialCounts().length.toString();
  document.getElementById("metricModel").textContent = state.model ? metricPercent(state.model.accuracy) : "N/A";
}

function updateFilters() {
  const select = document.getElementById("materialFilter");
  const current = select.value;
  const materials = materialCounts().map((item) => item.label);
  select.innerHTML = `<option value="">Todos os materiais</option>${materials
    .map((material) => `<option value="${escapeHtml(material)}">${escapeHtml(material)}</option>`)
    .join("")}`;
  select.value = materials.includes(current) ? current : "";
}

function updateCurveSelect() {
  const select = document.getElementById("curveSelect");
  const current = select.value;
  const ids = uniqueValues(state.clean, "id_entrada");
  const curveIds = ids.length ? ids : state.curves.map((row) => row.id_entrada).filter(Boolean);
  select.innerHTML = curveIds.length
    ? curveIds.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(id)}</option>`).join("")
    : `<option value="">Sem curvas</option>`;
  select.value = curveIds.includes(current) ? current : curveIds[0] || "";
}

function updateTargetSelect() {
  const select = document.getElementById("targetColumn");
  const current = select.value;
  const columns = state.attributes[0] ? Object.keys(state.attributes[0]) : ["classe_alvo", "material_eletrodo"];
  const targetColumns = columns.filter((column) => ["classe_alvo", "material_eletrodo", "eletrolito", "tipo_sinal"].includes(column));
  select.innerHTML = targetColumns.map((column) => `<option value="${column}">${column}</option>`).join("");
  if (targetColumns.includes(current)) select.value = current;
  else select.value = targetColumns.includes("classe_alvo") ? "classe_alvo" : targetColumns[0] || "";
}

function renderDataTable() {
  const datasetKey = document.getElementById("datasetSelect").value;
  const search = document.getElementById("tableSearch").value.toLowerCase();
  const material = document.getElementById("materialFilter").value;
  const rows = getDataset(datasetKey).filter((row) => {
    const materialValue = row.material_eletrodo || row.material || "";
    const matchesMaterial = !material || materialValue === material;
    const matchesSearch = !search || Object.values(row).some((value) => String(value).toLowerCase().includes(search));
    return matchesMaterial && matchesSearch;
  });
  document.getElementById("activeDatasetLabel").textContent = `${rows.length} linhas`;
  document.getElementById("dataTable").innerHTML = renderTable(rows.slice(0, 400));
}

function renderCurveChart() {
  const canvas = document.getElementById("curveChart");
  const id = document.getElementById("curveSelect").value;
  if (!id) {
    drawEmpty(canvas, "Sem curvas carregadas");
    return;
  }
  const cleanRows = state.clean.filter((row) => row.id_entrada === id);
  if (cleanRows.length) {
    const points = cleanRows
      .map((row) => ({ x: toNumber(row.E), y: toNumber(row.j) }))
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
    const potentialUnit = cleanRows[0].unidade_potencial_usada || "V";
    const signalUnit = cleanRows[0].unidade_sinal_usada || "sinal";
    drawLineChart(canvas, points, `E (${potentialUnit})`, `${cleanRows[0].tipo_sinal === "current" ? "I" : "j"} (${signalUnit})`);
    return;
  }
  const curve = state.curves.find((row) => row.id_entrada === id);
  if (!curve) {
    drawEmpty(canvas, "Curva nao encontrada");
    return;
  }
  const points = featureColumns(curve).map((column, index) => ({ x: index, y: toNumber(curve[column]) }));
  drawLineChart(canvas, points, "indice de interpolacao", "sinal normalizado");
}

function renderMaterialChart() {
  const canvas = document.getElementById("materialChart");
  const counts = materialCounts();
  document.getElementById("materialCountLabel").textContent = `${counts.length} classes`;
  if (!counts.length) {
    drawEmpty(canvas, "Sem materiais");
    return;
  }
  drawBarChart(canvas, counts.slice(0, 12));
}

function renderScatterChart() {
  const canvas = document.getElementById("scatterChart");
  const rows = state.attributes
    .filter((row) => row.tipo_sinal === document.getElementById("signalKindSelect").value)
    .map((row) => ({
      x: toNumber(row.E_max) - toNumber(row.E_min),
      y: toNumber(row.j_max) - toNumber(row.j_min),
      label: row.material_eletrodo || row.classe_alvo || "desconhecido",
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  if (!rows.length) {
    drawEmpty(canvas, "Sem atributos numericos");
    return;
  }
  const current = document.getElementById("signalKindSelect").value === "current";
  drawScatter(canvas, rows, "E_range (V)", current ? "I_range (A)" : "j_range (A/m2)");
}

function trainModel() {
  state.externalAudit = null;
  document.getElementById("actionError").textContent = "";
  state.model = null;
  state.frozenCandidates = [];
  state.modelResults = [];
  state.tests = [];
  state.externalResults = [];
  state.externalClassResults = [];
  state.diagnosticResults = [];
  renderAll();
  const selected = document.getElementById("techniqueSelect").value || "auto";
  const rankBy = selected === "auto_balanced" ? "balancedAccuracy" : "accuracy";
  const results = trainSelectedWithBalanceStrategies(selected, selectedLearningBalanceStrategy(), {
    rankBy,
    useHoldout: true,
  });

  if (!results.length) {
    state.model = null;
    state.modelResults = [];
    renderLearning("Nenhuma tecnica pode ser treinada");
    updateMetrics();
    return;
  }

  state.modelResults = results.map((result, index) => ({
    tecnica: result.model.typeLabel,
    status: index === 0 ? selectedStatus(selected) : "avaliado",
    acuracia: `${Math.round(result.accuracy * 100)}%`,
    acuracia_balanceada: `${Math.round(result.balancedAccuracy * 100)}%`,
    macro_f1: `${Math.round(result.macroF1 * 100)}%`,
    acertos: `${result.hits}/${result.total}`,
    balanceamento: balanceStrategyLabel(result.model.balanceStrategy),
    treino: result.model.trainSize,
    treino_original: result.model.originalTrainSize,
    teste: result.model.testSize,
    atributos: result.model.features.length,
  }));
  state.frozenCandidates = results.map((result) => refitCandidate(result, prepareTrainingSet({
    useHoldout: false, balanceStrategy: result.model.balanceStrategy, features: result.model.features,
  })));
  state.model = state.frozenCandidates[0].model;
  renderLearning();
  updateMetrics();
  renderExternalComparison();
  renderExternalClassResults();
  renderDiagnostics();
}

function trainSelectedTechniques(selected, prepared, options = {}) {
  const rankBy = options.rankBy || (selected === "auto_balanced" ? "balancedAccuracy" : "accuracy");
  if (selected === "auto" || selected === "auto_balanced") {
    const singles = sortTechniqueResults(trainTechniqueList(BASE_TECHNIQUES, prepared), rankBy);
    const ensembles = [
      evaluateEnsemble(prepared, singles, "Auto organizer: ensemble ponderado", rankBy),
      evaluateEnsemble(prepared, singles.slice(0, 3), "Auto organizer: top 3 tecnicas", rankBy),
    ].filter(Boolean);
    return sortTechniqueResults([...singles, ...ensembles], rankBy);
  }

  if (selected === "compare") {
    return sortTechniqueResults(trainTechniqueList(BASE_TECHNIQUES, prepared), rankBy);
  }

  if (selected === "ensemble") {
    const singles = sortTechniqueResults(trainTechniqueList(BASE_TECHNIQUES, prepared), rankBy);
    const ensemble = evaluateEnsemble(prepared, singles, "Ensemble ponderado", rankBy);
    return ensemble ? [ensemble, ...singles] : singles;
  }

  return trainTechniqueList([selected], prepared);
}

function trainTechniqueList(techniques, prepared) {
  return techniques.map((technique) => trainTechnique(technique, prepared)).filter(Boolean);
}

function selectedStatus(selected) {
  if (selected === "auto") return "auto_escolhido";
  if (selected === "auto_balanced") return "auto_balanceado";
  if (selected === "ensemble") return "selecionado";
  return "melhor";
}

function sortTechniqueResults(results, rankBy) {
  return results.sort((a, b) => {
    const primary = metricScore(b, rankBy) - metricScore(a, rankBy);
    if (Math.abs(primary) > 0.005) return primary;
    if (rankBy === "balancedAccuracy") {
      const macro = (b.macroF1 || 0) - (a.macroF1 || 0);
      if (Math.abs(macro) > 0.005) return macro;
      return (b.accuracy || 0) - (a.accuracy || 0);
    }
    const balanced = (b.balancedAccuracy || 0) - (a.balancedAccuracy || 0);
    if (Math.abs(balanced) > 0.005) return balanced;
    return (b.macroF1 || 0) - (a.macroF1 || 0);
  });
}

function metricScore(result, rankBy) {
  const value = result?.[rankBy];
  return Number.isFinite(value) ? value : result?.accuracy || 0;
}

function trainSelectedWithBalanceStrategies(selected, balanceStrategy, options = {}) {
  const results = [];
  balanceStrategiesToEvaluate(balanceStrategy).forEach((strategy) => {
    const prepared = prepareTrainingSet({ balanceStrategy: strategy, useHoldout: options.useHoldout });
    if (!prepared) return;
    results.push(...trainSelectedTechniques(selected, prepared, { rankBy: options.rankBy }));
  });
  return sortTechniqueResults(results, options.rankBy || "accuracy");
}

function balanceStrategiesToEvaluate(strategy) {
  return strategy === "auto" ? BALANCE_STRATEGIES : [strategy || "none"];
}

function selectedLearningBalanceStrategy() {
  return document.getElementById("balanceStrategySelect")?.value || "none";
}

function selectedExternalBalanceStrategy() {
  return document.getElementById("externalBalanceStrategySelect")?.value || "none";
}

function balanceStrategyLabel(strategy) {
  const labels = {
    class_weight: "pesos por classe",
    none: "sem balanceamento",
    auto: "auto balanceamento",
    oversample: "sobreamostragem",
    oversample_weight: "sobreamostragem + pesos",
  };
  return labels[strategy] || labels.none;
}

function usesClassWeights(strategy) {
  return strategy === "class_weight" || strategy === "oversample_weight";
}

function usesOversampling(strategy) {
  return strategy === "oversample" || strategy === "oversample_weight";
}

function prepareTrainingSet(options = {}) {
  const useHoldout = options.useHoldout !== false;
  const balanceStrategy = options.balanceStrategy || selectedLearningBalanceStrategy();
  const target = document.getElementById("targetColumn").value || "classe_alvo";
  const k = Math.max(1, Math.min(25, Number.parseInt(document.getElementById("knnK").value, 10) || 5));
  const kind = document.getElementById("signalKindSelect")?.value || "current_density";
  if (!state.attributes.length) {
    throw new Error("Nenhum CSV de atributos de treino importado. Use Importar CSVs no topo e selecione atributos_treino_sem_teste_current_density.csv da pasta outputs/scientific_v2/testes. Selecionar CSV em Testar IA nao carrega o treino.");
  }
  if (!state.attributes.some((row) => row.tipo_sinal === kind)) {
    const available = [...new Set(state.attributes.map((row) => row.tipo_sinal).filter(Boolean))];
    if (!available.length) throw new Error("CSV sem tipo_sinal. Importe os atributos regenerados da pasta outputs/scientific_v2/testes.");
    throw new Error(`Grandeza selecionada sem amostras: ${kind}. Grandezas presentes no CSV: ${available.join(", ")}. Ajuste Grandeza do modelo em Aprendizagem.`);
  }
  const rows = state.attributes.filter((row) => row.status !== "excluido" && row.tipo_sinal === kind && row[target] && !["desconhecido", "unknown"].includes(String(row[target]).toLowerCase()));
  if (!rows.length) throw new Error(`Nenhuma amostra valida com rotulo em ${target}. Confira Classe alvo e a coluna status do CSV.`);
  checkFeatureRows(rows, kind, true);
  if (rows.length < 3 || uniqueValues(rows, target).length < 2) throw new Error("Dados insuficientes para treino.");
  const initial = rows.map((row) => ({ id: row.id_entrada, label: String(row[target]), row }));
  const partition = useHoldout ? splitBySource(initial) : { train: initial, test: [] };
  const features = options.features || inferNumericFeatures(partition.train.map((item) => item.row));
  if (features.length < 2) throw new Error("Atributos suficientes nao encontrados no treino.");
  const vectorize = (items) => items.map(({row}) => ({
    id: row.id_entrada || "",
    label: String(row[target]),
    values: features.map((feature) => toNumber(row[feature])),
    row,
  }));
  const split = { train: vectorize(partition.train), test: vectorize(partition.test) };
  const scaler = buildScaler(split.train.map((item) => item.values));
  [...split.train, ...split.test].forEach((item) => {
    item.scaled = scaleVector(item.values, scaler);
  });

  const rawTrain = split.train;
  const classWeights = buildClassWeights(rawTrain, balanceStrategy);
  const train = balanceTrainingRows(rawTrain, balanceStrategy);
  const test = split.test;
  return {
    balanceStrategy,
    classCounts: countBy(rows, target),
    classWeights,
    features,
    k,
    originalTrainSize: rawTrain.length,
    rows,
    scaler,
    target,
    test,
    train,
  };
}

async function compareExternalTechniques() {
  state.externalAudit = null;
  document.getElementById("actionError").textContent = "";
  state.externalResults = [];
  state.externalClassResults = [];
  state.diagnosticResults = [];
  renderExternalComparison();
  renderExternalClassResults();
  renderDiagnostics();
  if (!state.pendingTestRows.length) {
    state.externalResults = [];
    state.externalClassResults = [];
    state.diagnosticResults = [];
    throw new Error("Nenhum CSV de teste carregado. Use Selecionar CSV em Testar IA e escolha amostras_teste_atributos_current_density.csv.");
  }

  if (!state.frozenCandidates.length) throw new Error("Treine e congele os modelos antes do teste externo.");
  const pending = state.pendingTestRows;
  const frozen = state.model;
  const rows = await canonicalTestRows();
  if (state.model !== frozen || state.pendingTestRows !== pending) throw new Error("Dados alterados durante a extracao. Repita o teste.");
  checkFeatureRows(rows, state.model.signalKind);
  checkIndependentTest(rows, state.model);
  if (rows.some((row) => !expectedLabel(row, state.model.target))) throw new Error("Todas as curvas do teste devem ter rotulo.");
  const evaluated = state.frozenCandidates.map(({model}) => {
    const predictions = rows.map((row) => ({
      expected: expectedLabel(row, model.target),
      predicted: predictWithModel(scaleVector(model.features.map((key) => toNumber(row[key])), model.scaler), model).label,
    }));
    return { model, ...evaluatePredictions(predictions) };
  });

  if (!evaluated.length) {
    state.externalResults = [];
    state.externalClassResults = [];
    state.diagnosticResults = [];
    renderExternalComparison("Dados insuficientes ou CSV sem rotulo compativel");
    renderExternalClassResults();
    renderDiagnostics();
    return;
  }

  state.externalResults = evaluated.map((result, index) => ({
    tecnica: result.model.typeLabel,
    status: index === 0 ? "selecionado_no_desenvolvimento" : "modelo_congelado",
    acuracia: `${Math.round(result.accuracy * 100)}%`,
    acuracia_balanceada: `${Math.round(result.balancedAccuracy * 100)}%`,
    macro_f1: `${Math.round(result.macroF1 * 100)}%`,
    acertos: `${result.hits}/${result.total}`,
    balanceamento: balanceStrategyLabel(result.model.balanceStrategy),
    treino: result.model.trainSize,
    treino_original: result.model.originalTrainSize,
    teste_externo: result.total,
    classes_teste: result.classes,
    atributos: result.model.features.length,
  }));
  state.externalClassResults = perClassRows(evaluated[0].perClass);
  state.externalAudit = {
    ids: rows.map((row) => row.id_entrada),
    groups: [...new Set(rows.map(sourceGroup))],
    hashes: rows.map((row) => row.hash_curva),
    count: rows.length,
    classesNotTested: Object.keys(state.model.classCounts).filter((label) => !rows.some((row) => expectedLabel(row, state.model.target) === label)),
  };
  state.diagnosticResults = diagnosticRows(state.externalClassResults);
  document.getElementById("testStatus").textContent = `Modelo congelado: ${state.model.typeLabel}, teste ${metricPercent(evaluated[0].accuracy)}`;
  renderExternalComparison();
  renderExternalClassResults();
  renderDiagnostics();
  updateMetrics();
}

function showTestError(error) {
  const message = `Avaliacao nao concluida: ${error.message}`;
  document.getElementById("testStatus").textContent = message;
  document.getElementById("externalComparisonLabel").textContent = "Avaliacao nao concluida";
  document.getElementById("externalComparisonTable").innerHTML = `<div class="empty-state" role="alert">${escapeHtml(message)}</div>`;
}

function trainTechnique(technique, prepared) {
  let model;
  if (technique === "knn") model = buildKnnModel(prepared);
  if (technique === "centroid") model = buildCentroidModel(prepared);
  if (technique === "naive_bayes") model = buildNaiveBayesModel(prepared);
  if (technique === "decision_tree") model = buildDecisionTreeModel(prepared);
  if (technique === "random_forest") model = buildRandomForestModel(prepared);
  if (!model) return null;

  const predictions = prepared.test.map((item) => ({
    expected: item.label,
    predicted: predictWithModel(item.scaled, model).label,
  }));
  const metrics = evaluatePredictions(predictions);
  model.accuracy = metrics.accuracy;
  model.balancedAccuracy = metrics.balancedAccuracy;
  model.macroF1 = metrics.macroF1;
  model.confusion = buildConfusion(predictions);
  model.perClassMetrics = metrics.perClass;
  model.trainedAt = new Date().toISOString();
  model.validationIds = prepared.test.map((item) => item.id);
  model.validationGroups = [...new Set(prepared.test.map((item) => sourceGroup(item.row)))];
  model.trainOnlyClasses = Object.keys(prepared.classCounts).filter((label) => !prepared.test.some((item) => item.label === label));
  return { ...metrics, model };
}

function evaluateEnsemble(prepared, modelResults, label, weightBy = "accuracy") {
  const baseResults = modelResults.filter((result) => result?.model && !["ensemble"].includes(result.model.type));
  if (baseResults.length < 2) return null;
  const model = buildEnsembleModel(prepared, baseResults, label, weightBy);
  const predictions = prepared.test.map((item) => ({
    expected: item.label,
    predicted: predictWithModel(item.scaled, model).label,
  }));
  const metrics = evaluatePredictions(predictions);
  model.accuracy = metrics.accuracy;
  model.balancedAccuracy = metrics.balancedAccuracy;
  model.macroF1 = metrics.macroF1;
  model.confusion = buildConfusion(predictions);
  model.perClassMetrics = metrics.perClass;
  model.trainedAt = new Date().toISOString();
  model.validationIds = prepared.test.map((item) => item.id);
  model.validationGroups = [...new Set(prepared.test.map((item) => sourceGroup(item.row)))];
  model.trainOnlyClasses = Object.keys(prepared.classCounts).filter((label) => !prepared.test.some((item) => item.label === label));
  return { ...metrics, model };
}

function buildKnnModel(prepared) {
  return {
    type: "knn",
    typeLabel: `k-NN ponderado (k=${prepared.k})`,
    balanceStrategy: prepared.balanceStrategy,
    classWeights: prepared.classWeights,
    target: prepared.target,
    k: prepared.k,
    features: prepared.features,
    scaler: prepared.scaler,
    train: prepared.train,
    trainSize: prepared.train.length,
    originalTrainSize: prepared.originalTrainSize,
    testSize: prepared.test.length,
    classCounts: prepared.classCounts,
  };
}

function buildCentroidModel(prepared) {
  const groups = groupBy(prepared.train, (item) => item.label);
  const centroids = Object.entries(groups).map(([label, items]) => ({
    label,
    values: prepared.features.map((_, index) => mean(items.map((item) => item.scaled[index]))),
    count: items.length,
  }));
  return {
    type: "centroid",
    typeLabel: "Centroide mais proximo",
    balanceStrategy: prepared.balanceStrategy,
    classWeights: prepared.classWeights,
    target: prepared.target,
    features: prepared.features,
    scaler: prepared.scaler,
    centroids,
    trainSize: prepared.train.length,
    originalTrainSize: prepared.originalTrainSize,
    testSize: prepared.test.length,
    classCounts: prepared.classCounts,
  };
}

function buildNaiveBayesModel(prepared) {
  const groups = groupBy(prepared.train, (item) => item.label);
  const total = prepared.train.length;
  const classes = Object.entries(groups).map(([label, items]) => ({
    label,
    prior: items.length / total,
    means: prepared.features.map((_, index) => mean(items.map((item) => item.scaled[index]))),
    variances: prepared.features.map((_, index) => {
      const variance = varianceOf(items.map((item) => item.scaled[index]));
      return Math.max(variance, 1e-6);
    }),
    count: items.length,
  }));
  return {
    type: "naive_bayes",
    typeLabel: "Naive Bayes Gaussiano",
    balanceStrategy: prepared.balanceStrategy,
    classWeights: prepared.classWeights,
    target: prepared.target,
    features: prepared.features,
    scaler: prepared.scaler,
    classes,
    trainSize: prepared.train.length,
    originalTrainSize: prepared.originalTrainSize,
    testSize: prepared.test.length,
    classCounts: prepared.classCounts,
  };
}

function buildDecisionTreeModel(prepared) {
  const tree = buildDecisionTree(prepared.train, prepared.features, {
    classWeights: prepared.classWeights,
    featureCount: prepared.features.length,
    maxDepth: 6,
    minSize: 4,
    seed: 101,
  });
  return {
    type: "decision_tree",
    typeLabel: "Arvore de decisao",
    balanceStrategy: prepared.balanceStrategy,
    classWeights: prepared.classWeights,
    target: prepared.target,
    features: prepared.features,
    scaler: prepared.scaler,
    tree,
    trainSize: prepared.train.length,
    originalTrainSize: prepared.originalTrainSize,
    testSize: prepared.test.length,
    classCounts: prepared.classCounts,
  };
}

function buildRandomForestModel(prepared) {
  const treeCount = prepared.treeCount || Math.min(31, Math.max(15, Math.round(Math.sqrt(prepared.train.length) * 2)));
  const featureCount = Math.max(2, Math.round(Math.sqrt(prepared.features.length)));
  const trees = [];
  for (let index = 0; index < treeCount; index += 1) {
    const rng = seededRandom(2000 + index * 17);
    const sample = bootstrapSample(prepared.train, rng, prepared.classWeights);
    trees.push(
      buildDecisionTree(sample, prepared.features, {
        classWeights: prepared.classWeights,
        featureCount,
        maxDepth: 7,
        minSize: 3,
        seed: 3000 + index * 31,
      }),
    );
  }
  return {
    type: "random_forest",
    typeLabel: `Floresta aleatoria (${treeCount} arvores)`,
    balanceStrategy: prepared.balanceStrategy,
    classWeights: prepared.classWeights,
    target: prepared.target,
    features: prepared.features,
    scaler: prepared.scaler,
    trees,
    trainSize: prepared.train.length,
    originalTrainSize: prepared.originalTrainSize,
    testSize: prepared.test.length,
    classCounts: prepared.classCounts,
  };
}

function buildEnsembleModel(prepared, modelResults, label, weightBy = "accuracy") {
  const baseModels = modelResults.map((result) => ({
    model: result.model,
    weight: Math.max(metricScore(result, weightBy), 0.01),
  }));
  return {
    type: "ensemble",
    typeLabel: label,
    balanceStrategy: prepared.balanceStrategy,
    classWeights: prepared.classWeights,
    target: prepared.target,
    features: prepared.features,
    scaler: prepared.scaler,
    baseModels,
    trainSize: prepared.train.length,
    originalTrainSize: prepared.originalTrainSize,
    testSize: prepared.test.length,
    classCounts: prepared.classCounts,
  };
}

function renderLearning(message = "") {
  const model = state.model;
  document.getElementById("learningStatus").textContent = message || (model ? `${model.typeLabel}, desenvolvimento ${metricPercent(model.accuracy)}; classes sem validacao: ${(model.trainOnlyClasses || []).join(", ") || "nenhuma"}` : "Sem modelo");
  document.getElementById("statTrain").textContent = model ? model.trainSize : "0";
  document.getElementById("statTest").textContent = model ? model.testSize : "0";
  document.getElementById("statAccuracy").textContent = model ? metricPercent(model.accuracy) : "N/A";
  document.getElementById("statFeatures").textContent = model ? model.features.length : "0";
  document.getElementById("classCountLabel").textContent = model ? `${Object.keys(model.classCounts).length} classes` : "0 classes";
  document.getElementById("classSummary").innerHTML = model
    ? Object.entries(model.classCounts)
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => `<div class="class-pill"><strong>${escapeHtml(label)}</strong><span class="badge">${count}</span></div>`)
        .join("")
    : `<div class="empty-state">Treine o modelo com atributos importados.</div>`;
  renderModelComparison();
  renderConfusionMatrix();
}

function renderModelComparison() {
  const target = document.getElementById("modelComparison");
  if (!state.modelResults.length) {
    document.getElementById("comparisonLabel").textContent = "Aguardando treino";
    target.innerHTML = `<div class="empty-state">Selecione uma tecnica ou compare todas.</div>`;
    return;
  }
  document.getElementById("comparisonLabel").textContent = `${state.modelResults.length} configuracoes no desenvolvimento`;
  target.innerHTML = renderTable(state.modelResults);
}

function renderConfusionMatrix() {
  const target = document.getElementById("confusionMatrix");
  const model = state.model;
  if (!model || !model.confusion.labels.length) {
    document.getElementById("confusionLabel").textContent = "Aguardando treino";
    target.innerHTML = `<div class="empty-state">Sem matriz calculada.</div>`;
    return;
  }
  document.getElementById("confusionLabel").textContent = `${model.confusion.labels.length} classes`;
  const labels = model.confusion.labels;
  const rows = labels.map((expected) => {
    const cells = labels.map((predicted) => `<td class="confusion-cell">${model.confusion.matrix[expected]?.[predicted] || 0}</td>`).join("");
    return `<tr><th>${escapeHtml(expected)}</th>${cells}</tr>`;
  });
  target.innerHTML = `<table><thead><tr><th>Real \\ Predito</th>${labels.map((label) => `<th>${escapeHtml(label)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table>`;
}

async function runPendingTest() {
  document.getElementById("actionError").textContent = "";
  if (!state.model) {
    document.getElementById("testStatus").textContent = "Treine a IA primeiro";
    return;
  }
  if (!state.pendingTestRows.length) {
    document.getElementById("testStatus").textContent = "Carregue um CSV";
    return;
  }

  const pending = state.pendingTestRows;
  const frozen = state.model;
  const rows = await canonicalTestRows();
  if (state.model !== frozen || state.pendingTestRows !== pending) throw new Error("Dados alterados durante a extracao. Repita o teste.");
  checkFeatureRows(rows, state.model.signalKind);
  const labeled = rows.filter((row) => document.getElementById("newMaterial").value || expectedLabel(row, state.model.target));
  if (labeled.length) checkIndependentTest(labeled, state.model);
  const predictions = rows.map((row, index) => {
    const values = state.model.features.map((feature) => toNumber(row[feature]));
    const scaled = scaleVector(values, state.model.scaler);
    const prediction = predictWithModel(scaled, state.model);
    const expected = document.getElementById("newMaterial").value || expectedLabel(row, state.model.target);
    return {
      id_teste: row.id_entrada || `${state.pendingTestName || "teste"}_${index + 1}`,
      arquivo: state.pendingTestName,
      tecnica_ia: state.model.typeLabel,
      material_informado: expected,
      eletrolito: document.getElementById("newElectrolyte").value || row.eletrolito || "",
      classe_predita: prediction.label,
      escore_nao_calibrado: prediction.confidence.toFixed(3),
      resultado: predictionResult(expected, prediction.label),
      evidencia: prediction.evidence,
    };
  });
  state.tests.push(...predictions);
  document.getElementById("testStatus").textContent = predictionSummary(predictions);
  renderPredictions();
  renderExportSummary();
}

function rowsToPredictableFeatures(rows) {
  const columns = Object.keys(rows[0] || {});
  if (columns.includes("E_min") || columns.includes("j_max")) {
    return rows;
  }
  if (columns.includes("E") && columns.includes("j")) {
    throw new Error("Curvas brutas requerem o extrator canonico Python.");
  }
  return rows;
}

function buildExternalTestVectors(rows, prepared) {
  return rowsToPredictableFeatures(rows)
    .map((row, index) => {
      const values = prepared.features.map((feature) => toNumber(row[feature]));
      const hasFeatureSignal = values.some(Number.isFinite);
      const label = expectedLabel(row, prepared.target);
      if (!hasFeatureSignal || !label) return null;
      return {
        id: row.id_entrada || `${state.pendingTestName || "teste"}_${index + 1}`,
        label,
        row,
        scaled: scaleVector(values, prepared.scaler),
        values,
      };
    })
    .filter(Boolean);
}

function buildClassWeights(rows, strategy) {
  const counts = labelCounts(rows);
  const labels = Object.keys(counts);
  if (!usesClassWeights(strategy) || !labels.length) {
    return labels.reduce((acc, label) => {
      acc[label] = 1;
      return acc;
    }, {});
  }
  const total = rows.length;
  const classTotal = labels.length;
  return labels.reduce((acc, label) => {
    acc[label] = Math.min(12, total / (classTotal * counts[label]));
    return acc;
  }, {});
}

function balanceTrainingRows(rows, strategy) {
  if (!usesOversampling(strategy) || rows.length < 2) return rows;
  const groups = groupBy(rows, (item) => item.label);
  const sizes = Object.values(groups).map((items) => items.length);
  const targetSize = Math.max(...sizes);
  const rng = seededRandom(8701);
  const balanced = [];
  Object.values(groups).forEach((items) => {
    balanced.push(...items);
    for (let index = items.length; index < targetSize; index += 1) {
      const source = items[Math.floor(rng() * items.length)];
      balanced.push({ ...source, balancedCopy: true });
    }
  });
  return shuffleRows(balanced, rng);
}

function shuffleRows(rows, rng) {
  const shuffled = [...rows];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(rng() * (index + 1));
    [shuffled[index], shuffled[swap]] = [shuffled[swap], shuffled[index]];
  }
  return shuffled;
}

function evaluatePredictions(predictions) {
  const hits = predictions.filter((item) => item.expected === item.predicted).length;
  const total = predictions.length;
  const labels = [...new Set(predictions.flatMap((item) => [item.expected, item.predicted]).filter(Boolean))].sort();
  const perClass = labels.map((label) => {
    const actual = predictions.filter((item) => item.expected === label);
    const predictedAs = predictions.filter((item) => item.predicted === label);
    const truePositive = actual.filter((item) => item.predicted === label).length;
    const precision = predictedAs.length ? truePositive / predictedAs.length : 0;
    const recall = actual.length ? truePositive / actual.length : 0;
    const f1 = precision + recall ? (2 * precision * recall) / (precision + recall) : 0;
    return {
      label,
      f1,
      hits: truePositive,
      precision,
      predictedTotal: predictedAs.length,
      recall,
      support: actual.length,
    };
  });
  return {
    accuracy: total ? hits / total : null,
    balancedAccuracy: total ? mean(perClass.filter((item) => item.support > 0).map((item) => item.recall)) : null,
    classes: perClass.filter((item) => item.support > 0).length,
    hits,
    macroF1: perClass.length ? mean(perClass.map((item) => item.f1)) : null,
    perClass,
    total,
  };
}

function perClassRows(metrics) {
  return metrics
    .map((item) => ({
      classe: item.label,
      recall: item.support ? `${Math.round(item.recall * 100)}%` : "N/A",
      precisao: `${Math.round(item.precision * 100)}%`,
      f1: `${Math.round(item.f1 * 100)}%`,
      acertos: `${item.hits}/${item.support}`,
      total_real: item.support,
      preditos_como_classe: item.predictedTotal,
    }))
    .sort((a, b) => toPercentNumber(a.recall) - toPercentNumber(b.recall) || b.total_real - a.total_real);
}

function diagnosticRows(classRows) {
  return classRows
    .map((row) => {
      const recall = toPercentNumber(row.recall);
      const precision = toPercentNumber(row.precisao);
      const total = toNumber(row.total_real);
      const predicted = toNumber(row.preditos_como_classe);
      if (total === 0) return {
        classe: row.classe, prioridade: "media", problema: "sem amostras reais no teste",
        evidencia: `${predicted} falsos positivos; recall nao estimavel`,
        proximo_passo: "coletar fontes independentes desta classe",
      };
      if (recall === 0) {
        return {
          classe: row.classe,
          prioridade: "alta",
          problema: "sem acertos no teste",
          evidencia: `${row.acertos}, ${predicted} preditos como ${row.classe}`,
          proximo_passo: total < 3 ? "coletar mais curvas e manter no teste separado" : "revisar atributos e curvas confundidas",
        };
      }
      if (recall < 60) {
        return {
          classe: row.classe,
          prioridade: "media",
          problema: "baixo recall",
          evidencia: `${row.acertos}, recall ${row.recall}`,
          proximo_passo: "aumentar amostras e testar sobreamostragem",
        };
      }
      if (precision < 60) {
        return {
          classe: row.classe,
          prioridade: "media",
          problema: "muitos falsos positivos",
          evidencia: `${predicted} preditos como ${row.classe}, precisao ${row.precisao}`,
          proximo_passo: "comparar matriz de confusao e revisar classes parecidas",
        };
      }
      if (total < 3) {
        return {
          classe: row.classe,
          prioridade: "baixa",
          problema: "teste pequeno",
          evidencia: `${total} amostra(s) no teste`,
          proximo_passo: "validar com mais curvas antes de concluir desempenho",
        };
      }
      return null;
    })
    .filter(Boolean);
}

function toPercentNumber(value) {
  return toNumber(String(value).replace("%", ""));
}

function expectedLabel(row, target) {
  const materialTarget = ["classe_alvo", "material_eletrodo"].includes(target);
  const value = row[target] || (materialTarget ? row.classe_alvo || row.material_eletrodo || row.material : "") || "";
  const label = String(value).trim();
  if (!label || ["desconhecido", "unknown", "n/a"].includes(label.toLowerCase())) return "";
  return label;
}

function extractFeatureRowsFromClean(rows) {
  throw new Error("Use /api/features: extracao parcial no navegador desativada.");
}

function renderPredictions() {
  if (state.tests.length) {
    document.getElementById("testStatus").textContent = predictionSummary(state.tests);
  }
  document.getElementById("predictionTable").innerHTML = renderTable(state.tests);
}

function renderExternalComparison(message = "") {
  const label = document.getElementById("externalComparisonLabel");
  const table = document.getElementById("externalComparisonTable");
  if (!label || !table) return;
  if (!state.externalResults.length) {
    label.textContent = message || "Aguardando teste";
    table.innerHTML = `<div class="empty-state">${escapeHtml(message || "Carregue um CSV de teste e compare as tecnicas.")}</div>`;
    return;
  }
  label.textContent = `${state.externalResults.length} configuracoes congeladas`;
  table.innerHTML = renderTable(state.externalResults);
}

function renderExternalClassResults(message = "") {
  const label = document.getElementById("externalClassLabel");
  const table = document.getElementById("externalClassTable");
  if (!label || !table) return;
  if (!state.externalClassResults.length) {
    label.textContent = message || "Aguardando teste";
    table.innerHTML = `<div class="empty-state">Compare as tecnicas para ver recall, precisao e F1 por classe.</div>`;
    return;
  }
  const supported = state.externalClassResults.filter((row) => row.total_real > 0).length;
  label.textContent = `${supported} classes com amostras; sem teste: ${state.externalAudit?.classesNotTested.join(", ") || "nenhuma"}`;
  table.innerHTML = renderTable(state.externalClassResults);
}

function renderDiagnostics(message = "") {
  const label = document.getElementById("diagnosticLabel");
  const table = document.getElementById("diagnosticTable");
  if (!label || !table) return;
  if (!state.diagnosticResults.length) {
    label.textContent = message || "Aguardando teste";
    table.innerHTML = `<div class="empty-state">Compare as tecnicas para gerar recomendacoes.</div>`;
    return;
  }
  const high = state.diagnosticResults.filter((row) => row.prioridade === "alta").length;
  label.textContent = `${state.diagnosticResults.length} pontos, ${high} alta prioridade`;
  table.innerHTML = renderTable(state.diagnosticResults);
}

function renderExportSummary() {
  const count =
    state.attributes.length +
    state.curves.length +
    state.tests.length +
    state.externalResults.length +
    state.externalClassResults.length +
    state.diagnosticResults.length +
    (state.model ? 1 : 0);
  document.getElementById("exportSummary").textContent = `${count} itens`;
}

function predictionResult(expected, predicted) {
  if (!expected) return "sem_rotulo";
  return String(expected) === String(predicted) ? "acerto" : "erro";
}

function predictionSummary(rows) {
  const evaluated = rows.filter((row) => row.resultado === "acerto" || row.resultado === "erro");
  if (!evaluated.length) return `${rows.length} predicoes`;
  const hits = evaluated.filter((row) => row.resultado === "acerto").length;
  const accuracy = Math.round((hits / evaluated.length) * 100);
  return `${rows.length} predicoes, ${hits}/${evaluated.length} acertos (${accuracy}%)`;
}

function inferNumericFeatures(rows) {
  if (!rows.length) return [];
  return SCIENTIFIC_FEATURES.filter((column) => {
    const numericCount = rows.filter((row) => Number.isFinite(toNumber(row[column]))).length;
    return numericCount >= Math.max(3, Math.ceil(rows.length * 0.6));
  });
}

function buildScaler(vectors) {
  const columns = vectors[0]?.length || 0;
  const means = [];
  const stds = [];
  for (let column = 0; column < columns; column += 1) {
    const values = vectors.map((vector) => vector[column]).filter(Number.isFinite);
    means[column] = mean(values);
    stds[column] = standardDeviation(values) || 1;
  }
  return { means, stds };
}

function scaleVector(values, stats) {
  return values.map((value, index) => {
    const safeValue = Number.isFinite(value) ? value : stats.means[index];
    return (safeValue - stats.means[index]) / stats.stds[index];
  });
}

function stratifiedSplit(vectors) {
  return splitBySource(vectors);
}

function predictKnn(vector, train, k, classWeights = {}) {
  const neighbors = train
    .map((item) => ({ label: item.label, distance: euclidean(vector, item.scaled) }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, Math.min(k, train.length));
  const votes = {};
  neighbors.forEach((neighbor) => {
    const weight = (1 / (neighbor.distance + 1e-9)) * (classWeights[neighbor.label] || 1);
    votes[neighbor.label] = (votes[neighbor.label] || 0) + weight;
  });
  const total = Object.values(votes).reduce((sum, value) => sum + value, 0);
  const [label, score] = Object.entries(votes).sort((a, b) => b[1] - a[1])[0] || ["N/A", 0];
  return {
    label,
    confidence: total ? score / total : 0,
    evidence: neighbors.map((neighbor) => neighbor.label).join("; "),
    neighbors,
  };
}

function predictWithModel(vector, model) {
  if (model.type === "knn") return predictKnn(vector, model.train, model.k, model.classWeights);
  if (model.type === "centroid") return predictCentroid(vector, model.centroids, model.classWeights);
  if (model.type === "naive_bayes") return predictNaiveBayes(vector, model.classes, model.classWeights);
  if (model.type === "decision_tree") return predictDecisionTreeModel(vector, model.tree);
  if (model.type === "random_forest") return predictRandomForest(vector, model.trees);
  if (model.type === "ensemble") return predictEnsemble(vector, model.baseModels);
  return { label: "N/A", confidence: 0, evidence: "modelo_desconhecido" };
}

function predictCentroid(vector, centroids, classWeights = {}) {
  const ranked = centroids
    .map((centroid) => {
      const distance = euclidean(vector, centroid.values);
      const adjustedDistance = distance / Math.sqrt(classWeights[centroid.label] || 1);
      return { label: centroid.label, adjustedDistance, distance, count: centroid.count };
    })
    .sort((a, b) => a.adjustedDistance - b.adjustedDistance);
  const best = ranked[0] || { label: "N/A", adjustedDistance: 0, distance: 0 };
  const weights = ranked.slice(0, 5).map((item) => 1 / (item.adjustedDistance + 1e-9));
  const total = weights.reduce((sum, value) => sum + value, 0);
  return {
    label: best.label,
    confidence: total ? weights[0] / total : 0,
    evidence: ranked.slice(0, 5).map((item) => `${item.label}:${formatNumber(item.adjustedDistance)}`).join("; "),
  };
}

function predictNaiveBayes(vector, classes, classWeights = {}) {
  const scored = classes
    .map((classStats) => {
      const logLikelihood = vector.reduce((sum, value, index) => {
        const variance = classStats.variances[index] || 1e-6;
        const diff = value - classStats.means[index];
        return sum - 0.5 * Math.log(2 * Math.PI * variance) - (diff * diff) / (2 * variance);
      }, Math.log(Math.max((classStats.prior || 1e-12) * (classWeights[classStats.label] || 1), 1e-12)));
      return { label: classStats.label, score: logLikelihood };
    })
    .sort((a, b) => b.score - a.score);
  const best = scored[0] || { label: "N/A", score: 0 };
  const maxScore = best.score;
  const topScores = scored.slice(0, 5).map((item) => Math.exp(Math.max(-60, item.score - maxScore)));
  const total = topScores.reduce((sum, value) => sum + value, 0);
  return {
    label: best.label,
    confidence: total ? topScores[0] / total : 0,
    evidence: scored.slice(0, 5).map((item) => `${item.label}:${formatNumber(item.score)}`).join("; "),
  };
}

function predictDecisionTreeModel(vector, tree) {
  const leaf = traverseTree(vector, tree);
  const counts = leaf.weightedCounts || leaf.counts || {};
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  const confidence = total ? (counts[leaf.label] || 0) / total : 0;
  return {
    label: leaf.label,
    confidence,
    evidence: `folha:${leaf.label}; n=${total}`,
  };
}

function predictRandomForest(vector, trees) {
  const votes = {};
  trees.forEach((tree) => {
    const prediction = predictDecisionTreeModel(vector, tree);
    votes[prediction.label] = (votes[prediction.label] || 0) + 1;
  });
  const ranked = Object.entries(votes).sort((a, b) => b[1] - a[1]);
  const [label, count] = ranked[0] || ["N/A", 0];
  return {
    label,
    confidence: trees.length ? count / trees.length : 0,
    evidence: ranked.map(([name, value]) => `${name}:${value}`).join("; "),
  };
}

function predictEnsemble(vector, baseModels) {
  const votes = {};
  const evidence = [];
  baseModels.forEach((entry) => {
    const prediction = predictWithModel(vector, entry.model);
    const weight = entry.weight * Math.max(prediction.confidence, 0.05);
    votes[prediction.label] = (votes[prediction.label] || 0) + weight;
    evidence.push(`${entry.model.typeLabel}->${prediction.label}`);
  });
  const total = Object.values(votes).reduce((sum, value) => sum + value, 0);
  const [label, score] = Object.entries(votes).sort((a, b) => b[1] - a[1])[0] || ["N/A", 0];
  return {
    label,
    confidence: total ? score / total : 0,
    evidence: evidence.join("; "),
  };
}

function buildDecisionTree(rows, features, options, depth = 0) {
  const counts = labelCounts(rows);
  const weightedCounts = weightedLabelCounts(rows, options.classWeights);
  const label = majorityLabel(weightedCounts);
  if (depth >= options.maxDepth || rows.length <= options.minSize || Object.keys(counts).length <= 1) {
    return { counts, label, leaf: true, weightedCounts };
  }

  const split = bestSplit(rows, features, options, depth);
  if (!split || !split.left.length || !split.right.length) {
    return { counts, label, leaf: true, weightedCounts };
  }

  return {
    counts,
    featureIndex: split.featureIndex,
    label,
    left: buildDecisionTree(split.left, features, options, depth + 1),
    leaf: false,
    right: buildDecisionTree(split.right, features, options, depth + 1),
    threshold: split.threshold,
    weightedCounts,
  };
}

function bestSplit(rows, features, options, depth) {
  const featureIndices = chooseFeatureIndices(features.length, options.featureCount, options.seed + depth * 97);
  let best = null;
  featureIndices.forEach((featureIndex) => {
    const thresholds = candidateThresholds(rows.map((row) => row.scaled[featureIndex]));
    thresholds.forEach((threshold) => {
      const left = [];
      const right = [];
      rows.forEach((row) => {
        if (row.scaled[featureIndex] <= threshold) left.push(row);
        else right.push(row);
      });
      if (!left.length || !right.length) return;
      const score = splitGini(left, right, options.classWeights);
      if (!best || score < best.score) {
        best = { featureIndex, left, right, score, threshold };
      }
    });
  });
  return best;
}

function candidateThresholds(values) {
  const sorted = [...new Set(values.filter(Number.isFinite).sort((a, b) => a - b))];
  if (sorted.length <= 1) return [];
  const thresholds = [];
  const steps = Math.min(12, sorted.length - 1);
  for (let index = 1; index <= steps; index += 1) {
    const position = Math.floor((index * (sorted.length - 1)) / (steps + 1));
    const next = Math.min(position + 1, sorted.length - 1);
    thresholds.push((sorted[position] + sorted[next]) / 2);
  }
  return [...new Set(thresholds)];
}

function splitGini(left, right, classWeights = {}) {
  const leftWeight = totalRowWeight(left, classWeights);
  const rightWeight = totalRowWeight(right, classWeights);
  const total = leftWeight + rightWeight || left.length + right.length || 1;
  return (leftWeight / total) * giniImpurity(left, classWeights) + (rightWeight / total) * giniImpurity(right, classWeights);
}

function giniImpurity(rows, classWeights = {}) {
  const counts = weightedLabelCounts(rows, classWeights);
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0) || 1;
  return 1 - Object.values(counts).reduce((sum, count) => sum + (count / total) ** 2, 0);
}

function traverseTree(vector, node) {
  if (!node || node.leaf) return node || { counts: {}, label: "N/A" };
  if (vector[node.featureIndex] <= node.threshold) return traverseTree(vector, node.left);
  return traverseTree(vector, node.right);
}

function chooseFeatureIndices(total, count, seed) {
  const rng = seededRandom(seed);
  const indices = Array.from({ length: total }, (_, index) => index);
  for (let index = indices.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(rng() * (index + 1));
    [indices[index], indices[swap]] = [indices[swap], indices[index]];
  }
  return indices.slice(0, Math.min(count, total));
}

function bootstrapSample(rows, rng, classWeights = {}) {
  const weights = rows.map((row) => classWeights[row.label] || 1);
  const total = weights.reduce((sum, value) => sum + value, 0);
  if (!Number.isFinite(total) || total <= 0) {
    return Array.from({ length: rows.length }, () => rows[Math.floor(rng() * rows.length)]);
  }
  return Array.from({ length: rows.length }, () => weightedSample(rows, weights, total, rng));
}

function weightedSample(rows, weights, total, rng) {
  let threshold = rng() * total;
  for (let index = 0; index < rows.length; index += 1) {
    threshold -= weights[index];
    if (threshold <= 0) return rows[index];
  }
  return rows[rows.length - 1];
}

function labelCounts(rows) {
  return rows.reduce((acc, row) => {
    acc[row.label] = (acc[row.label] || 0) + 1;
    return acc;
  }, {});
}

function weightedLabelCounts(rows, classWeights = {}) {
  return rows.reduce((acc, row) => {
    acc[row.label] = (acc[row.label] || 0) + (classWeights[row.label] || 1);
    return acc;
  }, {});
}

function totalRowWeight(rows, classWeights = {}) {
  return rows.reduce((sum, row) => sum + (classWeights[row.label] || 1), 0);
}

function majorityLabel(counts) {
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "N/A";
}

function seededRandom(seed) {
  let value = seed % 2147483647;
  if (value <= 0) value += 2147483646;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function buildConfusion(predictions) {
  const labels = [...new Set(predictions.flatMap((item) => [item.expected, item.predicted]))].sort();
  const matrix = {};
  labels.forEach((expected) => {
    matrix[expected] = {};
    labels.forEach((predicted) => {
      matrix[expected][predicted] = 0;
    });
  });
  predictions.forEach((item) => {
    matrix[item.expected][item.predicted] += 1;
  });
  return { labels, matrix };
}

function getDataset(key) {
  return state[key] || [];
}

function materialCounts() {
  const source = state.attributes.length ? state.attributes : state.clean;
  const counts = countBy(source, (row) => row.material_eletrodo || row.material || row.classe_alvo || "desconhecido");
  return Object.entries(counts)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);
}

function renderTable(rows) {
  if (!rows.length) return `<div class="empty-state">Sem dados carregados.</div>`;
  const columns = Object.keys(rows[0]).slice(0, 28);
  const body = rows
    .map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(formatCell(row[column]))}</td>`).join("")}</tr>`)
    .join("");
  return `<table><thead><tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
}

function drawBrandSparkline() {
  const canvas = document.getElementById("brandSparkline");
  const ctx = canvas.getContext("2d");
  const points = Array.from({ length: 72 }, (_, index) => {
    const x = index / 71;
    const y = Math.sin(x * Math.PI * 3.6) * 0.35 + Math.sin(x * Math.PI * 9) * 0.08;
    return { x: 8 + x * 88, y: 20 - y * 22 };
  });
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#2dd4bf";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();
  ctx.fillStyle = "#f59e0b";
  ctx.beginPath();
  ctx.arc(54, 20, 3.4, 0, Math.PI * 2);
  ctx.fill();
}

function drawEmpty(canvas, text) {
  const ctx = prepareCanvas(canvas);
  ctx.fillStyle = "#65727c";
  ctx.font = "15px system-ui";
  ctx.textAlign = "center";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);
}

function drawLineChart(canvas, points, xLabel, yLabel) {
  const ctx = prepareCanvas(canvas);
  if (!points.length) {
    drawEmpty(canvas, "Sem pontos numericos");
    return;
  }
  const bounds = paddedBounds(points.map((point) => point.x), points.map((point) => point.y));
  drawAxes(ctx, canvas, bounds, xLabel, yLabel);
  ctx.strokeStyle = "#0e7c7b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  points.forEach((point, index) => {
    const px = map(point.x, bounds.xMin, bounds.xMax, 54, canvas.width - 22);
    const py = map(point.y, bounds.yMin, bounds.yMax, canvas.height - 42, 18);
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.stroke();
}

function drawBarChart(canvas, data) {
  const ctx = prepareCanvas(canvas);
  const maxValue = Math.max(...data.map((item) => item.value));
  const left = 130;
  const right = canvas.width - 20;
  const top = 20;
  const barHeight = Math.min(24, (canvas.height - 50) / data.length - 5);
  ctx.font = "12px system-ui";
  data.forEach((item, index) => {
    const y = top + index * (barHeight + 8);
    const width = map(item.value, 0, maxValue, 0, right - left);
    ctx.fillStyle = COLORS[index % COLORS.length];
    ctx.fillRect(left, y, width, barHeight);
    ctx.fillStyle = "#172026";
    ctx.textAlign = "right";
    ctx.fillText(truncate(item.label, 17), left - 8, y + barHeight - 6);
    ctx.textAlign = "left";
    ctx.fillText(String(item.value), left + width + 6, y + barHeight - 6);
  });
}

function drawScatter(canvas, points, xLabel, yLabel) {
  const ctx = prepareCanvas(canvas);
  const bounds = paddedBounds(points.map((point) => point.x), points.map((point) => point.y));
  const labels = [...new Set(points.map((point) => point.label))];
  drawAxes(ctx, canvas, bounds, xLabel, yLabel);
  points.forEach((point) => {
    const colorIndex = labels.indexOf(point.label) % COLORS.length;
    ctx.fillStyle = COLORS[colorIndex];
    ctx.beginPath();
    ctx.arc(
      map(point.x, bounds.xMin, bounds.xMax, 54, canvas.width - 22),
      map(point.y, bounds.yMin, bounds.yMax, canvas.height - 42, 18),
      4,
      0,
      Math.PI * 2,
    );
    ctx.fill();
  });
}

function prepareCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(320, Math.floor(rect.width * ratio));
  canvas.height = Math.max(220, Math.floor(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  canvas.width = rect.width;
  canvas.height = rect.height;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#fbfcfd";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  return ctx;
}

function drawAxes(ctx, canvas, bounds, xLabel, yLabel) {
  ctx.strokeStyle = "#d9e0e5";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(54, 18);
  ctx.lineTo(54, canvas.height - 42);
  ctx.lineTo(canvas.width - 22, canvas.height - 42);
  ctx.stroke();
  ctx.fillStyle = "#65727c";
  ctx.font = "12px system-ui";
  ctx.textAlign = "center";
  ctx.fillText(xLabel, canvas.width / 2, canvas.height - 10);
  ctx.save();
  ctx.translate(14, canvas.height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(yLabel, 0, 0);
  ctx.restore();
  ctx.textAlign = "left";
  ctx.fillText(formatNumber(bounds.yMax), 58, 28);
  ctx.fillText(formatNumber(bounds.yMin), 58, canvas.height - 46);
}

function downloadModelState() {
  const safeModel = exportableModel(state.model);
  downloadText(
    "echemdb_ia_estado.json",
    JSON.stringify(
      {
        importedFiles: state.importedFiles,
        model: safeModel,
        modelResults: state.modelResults,
        externalResults: state.externalResults,
        externalAudit: state.externalAudit,
        externalClassResults: state.externalClassResults,
        diagnosticResults: state.diagnosticResults,
        tests: state.tests,
      },
      null,
      2,
    ),
    "application/json",
  );
}

function downloadExperimentReport() {
  downloadText("relatorio_experimento_echemdb_ia.md", buildExperimentReport(), "text/markdown");
}

function buildExperimentReport() {
  const now = new Date().toISOString();
  const best = state.externalResults[0] || null;
  const knn = baselineKnnResult();
  const lines = [
    "# Relatorio do Experimento EchemDB IA",
    "",
    `Gerado em: ${now}`,
    "",
    "## Objetivo",
    "",
    "Avaliar tecnicas de aprendizagem de maquina para classificar voltamogramas ciclicos do EchemDB a partir de atributos numericos extraidos das curvas.",
    "",
    "## Dados",
    "",
    `- Arquivos importados: ${state.importedFiles.length ? state.importedFiles.map((item) => `${item.name} (${item.rows} linhas)`).join("; ") : "nao informado no estado atual"}`,
    `- Amostras de atributos carregadas: ${state.attributes.length}`,
    `- Arquivo de teste externo: ${state.pendingTestName || "nao carregado"}`,
    `- Curvas efetivamente avaliadas no teste externo: ${state.externalAudit?.count ?? "nao avaliado"}`,
    `- Fontes de teste: ${state.externalAudit?.groups.length ?? "nao avaliado"}`,
    `- Classes do modelo sem amostras no teste: ${state.externalAudit?.classesNotTested.join(", ") || "nenhuma ou teste nao realizado"}`,
    `- Contrato de atributos: ${state.model?.version || "sem modelo"}`,
    `- Grandeza: ${state.model?.signalKind || "sem modelo"}`,
    "- Teste bloqueia ID, fonte e hash compartilhados com desenvolvimento; nao comprova ineditismo historico da base.",
    "",
    "## Modelo Selecionado no Desenvolvimento",
    "",
  ];

  if (best) {
    lines.push(
      `- Tecnica: ${best.tecnica}`,
      `- Status: ${best.status}`,
      `- Balanceamento: ${best.balanceamento}`,
      `- Acuracia geral: ${best.acuracia}`,
      `- Acuracia balanceada: ${best.acuracia_balanceada}`,
      `- Macro F1: ${best.macro_f1}`,
      `- Acertos: ${best.acertos}`,
      `- Treino usado: ${best.treino} amostras geradas a partir de ${best.treino_original} amostras originais`,
      "",
    );
  } else {
    lines.push("Nenhuma comparacao externa foi executada neste estado.", "");
  }

  if (best && knn) {
    lines.push(
      "## Comparacao com k-NN",
      "",
      `- Modelo congelado: ${best.tecnica}, ${best.acuracia}, ${best.acertos}`,
      `- k-NN: ${knn.acuracia}, ${knn.acertos}, balanceamento ${knn.balanceamento}`,
      `- Diferenca aproximada: ${percentagePointDifference(best.acuracia, knn.acuracia)} pontos percentuais em acuracia geral`,
      "",
    );
  }

  lines.push(
    "## Comparacao de Tecnicas",
    "",
    markdownTable(state.externalResults),
    "",
    "## Desempenho por Classe",
    "",
    markdownTable(state.externalClassResults),
    "",
    "## Diagnostico",
    "",
    markdownTable(state.diagnosticResults),
    "",
    "## Conclusao Tecnica",
    "",
    experimentConclusion(best),
    "",
    "## Proximo Passo",
    "",
    "Priorizar fontes independentes para classes com pouco suporte. Nao reajustar a configuracao usando este teste. Uma nova selecao requer um novo teste final independente.",
    "",
  );

  return lines.join("\n");
}

function baselineKnnResult() {
  const knnRows = state.externalResults.filter((row) => String(row.tecnica || "").toLowerCase().includes("k-nn"));
  return knnRows.find((row) => row.balanceamento === "sem balanceamento") || knnRows[0];
}

function experimentConclusion(best) {
  if (!best) return "Execute a comparacao externa antes de concluir o experimento.";
  const highPriority = state.diagnosticResults.filter((row) => row.prioridade === "alta").map((row) => row.classe);
  const weakText = highPriority.length ? ` As classes de maior risco neste experimento sao ${highPriority.join(", ")}.` : "";
  return `O modelo ${best.tecnica}, selecionado no desenvolvimento com ${best.balanceamento}, foi avaliado sem reajuste no teste. Este resultado nao demonstra superioridade estatistica e depende das fontes e classes avaliadas.${weakText}`;
}

function markdownTable(rows) {
  if (!rows.length) return "Sem dados.";
  const columns = Object.keys(rows[0]);
  const header = `| ${columns.join(" |")} |`;
  const separator = `| ${columns.map(() => "---").join(" |")} |`;
  const body = rows.map((row) => `| ${columns.map((column) => markdownCell(row[column])).join(" |")} |`);
  return [header, separator, ...body].join("\n");
}

function markdownCell(value) {
  return String(value ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}

function percentagePointDifference(a, b) {
  const left = toPercentNumber(a);
  const right = toPercentNumber(b);
  if (!Number.isFinite(left) || !Number.isFinite(right)) return "N/A";
  return Math.round(left - right);
}

function exportableModel(model) {
  if (!model) return null;
  const exported = {
    version: model.version,
    signalKind: model.signalKind,
    protocol: model.protocol,
    developmentIds: model.developmentIds,
    developmentGroups: model.developmentGroups,
    developmentHashes: model.developmentHashes,
    validationIds: model.validationIds,
    validationGroups: model.validationGroups,
    trainOnlyClasses: model.trainOnlyClasses,
    accuracy: model.accuracy,
    balancedAccuracy: model.balancedAccuracy,
    balanceStrategy: model.balanceStrategy,
    classCounts: model.classCounts,
    classWeights: model.classWeights,
    features: model.features,
    macroF1: model.macroF1,
    originalTrainSize: model.originalTrainSize,
    trainSize: model.trainSize,
    testSize: model.testSize,
    perClassMetrics: model.perClassMetrics,
    scaler: model.scaler,
    target: model.target,
    trainedAt: model.trainedAt,
    type: model.type,
    typeLabel: model.typeLabel,
  };
  if (model.k) exported.k = model.k;
  if (model.train) exported.train = model.train.map((item) => ({ id: item.id, label: item.label, scaled: item.scaled }));
  if (model.centroids) exported.centroids = model.centroids;
  if (model.classes) exported.classes = model.classes;
  if (model.tree) exported.tree = model.tree;
  if (model.trees) exported.trees = model.trees;
  if (model.baseModels) {
    exported.baseModels = model.baseModels.map((entry) => ({
      model: exportableModel(entry.model),
      weight: entry.weight,
    }));
  }
  return exported;
}

function downloadCsv(fileName, rows) {
  if (!rows.length) {
    downloadText(fileName, "", "text/csv");
    return;
  }
  const columns = Object.keys(rows[0]);
  const lines = [columns.join(",")].concat(rows.map((row) => columns.map((column) => csvCell(row[column])).join(",")));
  downloadText(fileName, lines.join("\n"), "text/csv");
}

function downloadText(fileName, text, type) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

function featureColumns(row) {
  return Object.keys(row).filter((column) => /^f\d{4}$/.test(column));
}

function uniqueValues(rows, key) {
  return [...new Set(rows.map((row) => row[key]).filter(Boolean))];
}

function countBy(rows, keyOrFn) {
  const getter = typeof keyOrFn === "function" ? keyOrFn : (row) => row[keyOrFn];
  return rows.reduce((acc, row) => {
    const key = getter(row) || "desconhecido";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function groupBy(rows, getter) {
  return rows.reduce((acc, row) => {
    const key = getter(row);
    if (!acc[key]) acc[key] = [];
    acc[key].push(row);
    return acc;
  }, {});
}

function toNumber(value) {
  if (typeof value === "number") return value;
  if (value === null || value === undefined || value === "") return Number.NaN;
  const normalized = String(value).replace(",", ".");
  return normalized.trim() ? Number(normalized) : Number.NaN;
}

function mean(values) {
  const clean = values.filter(Number.isFinite);
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : 0;
}

function standardDeviation(values) {
  const clean = values.filter(Number.isFinite);
  if (clean.length < 2) return 0;
  const avg = mean(clean);
  return Math.sqrt(clean.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (clean.length - 1));
}

function varianceOf(values) {
  const clean = values.filter(Number.isFinite);
  if (clean.length < 2) return 1e-6;
  const avg = mean(clean);
  return clean.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (clean.length - 1);
}

function min(values) {
  const clean = values.filter(Number.isFinite);
  return clean.length ? Math.min(...clean) : "";
}

function max(values) {
  const clean = values.filter(Number.isFinite);
  return clean.length ? Math.max(...clean) : "";
}

function absoluteArea(points) {
  let area = 0;
  for (let index = 1; index < points.length; index += 1) {
    area += 0.5 * (Math.abs(points[index - 1].j) + Math.abs(points[index].j)) * Math.abs(points[index].E - points[index - 1].E);
  }
  return area;
}

function signedArea(points) {
  let area = 0;
  for (let index = 1; index < points.length; index += 1) {
    area += 0.5 * (points[index - 1].j + points[index].j) * (points[index].E - points[index - 1].E);
  }
  return area;
}

function zeroCrossings(values) {
  let count = 0;
  for (let index = 1; index < values.length; index += 1) {
    if ((values[index - 1] < 0 && values[index] >= 0) || (values[index - 1] >= 0 && values[index] < 0)) count += 1;
  }
  return count;
}

function euclidean(a, b) {
  return Math.sqrt(a.reduce((sum, value, index) => sum + (value - b[index]) ** 2, 0));
}

function paddedBounds(xValues, yValues) {
  let xMin = min(xValues);
  let xMax = max(xValues);
  let yMin = min(yValues);
  let yMax = max(yValues);
  if (xMin === xMax) {
    xMin -= 1;
    xMax += 1;
  }
  if (yMin === yMax) {
    yMin -= 1;
    yMax += 1;
  }
  const xPad = (xMax - xMin) * 0.04;
  const yPad = (yMax - yMin) * 0.08;
  return { xMin: xMin - xPad, xMax: xMax + xPad, yMin: yMin - yPad, yMax: yMax + yPad };
}

function map(value, inMin, inMax, outMin, outMax) {
  return outMin + ((value - inMin) / (inMax - inMin)) * (outMax - outMin);
}

function formatCell(value) {
  if (typeof value === "number") return formatNumber(value);
  const text = String(value ?? "").trim();
  const normalized = text.replace(",", ".");
  if (isPlainNumericText(normalized)) return formatNumber(Number.parseFloat(normalized));
  return value ?? "";
}

function isPlainNumericText(value) {
  return /^[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?$/i.test(value);
}

function formatNumber(value) {
  if (!Number.isFinite(value)) return "";
  if (Number.isInteger(value) && Math.abs(value) < 1000000) return value.toString();
  if (Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) return value.toExponential(2);
  return Number(value.toPrecision(4)).toString();
}

function truncate(value, size) {
  const text = String(value);
  return text.length > size ? `${text.slice(0, size - 1)}...` : text;
}

function csvCell(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
