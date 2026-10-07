const FEATURE_VERSION = "echemdb-features-v2";
const SCIENTIFIC_FEATURES = [
  "E_min", "E_max", "j_min", "j_max", "j_media", "j_desvio_padrao",
  "area_absoluta", "area_liquida", "E_pico_anodico", "j_pico_anodico",
  "E_pico_catodico", "j_pico_catodico", "separacao_picos", "razao_picos",
  "largura_pico_anodico", "largura_pico_catodico", "cruzamentos_zero",
  "derivada1_media", "derivada1_desvio", "derivada1_min", "derivada1_max",
  "derivada2_media", "derivada2_desvio",
];

function sourceGroup(row) {
  return String(row.grupo_origem || row.doi || "").trim().toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, "").replace(/^doi:\s*/, "");
}

function checkFeatureRows(rows, signalKind, requireGroups = false) {
  if (!rows.length) throw new Error("Nenhum atributo compativel carregado.");
  const expectedUnit = signalKind === "current" ? "A" : "A/m2";
  const ids = new Set();
  for (const row of rows) {
    if (row.versao_atributos !== FEATURE_VERSION) {
      throw new Error("Atributos antigos ou sem versao. Gere os CSVs com o pipeline v2.");
    }
    if (row.status !== "valido" || row.tipo_sinal !== signalKind ||
        row.unidade_potencial_usada !== "V" || row.unidade_sinal_usada !== expectedUnit) {
      throw new Error("Tipo de sinal ou unidade incompativel com o modelo.");
    }
    if (!row.id_entrada || ids.has(row.id_entrada)) throw new Error("Identificador ausente ou duplicado.");
    ids.add(row.id_entrada);
    if (!row.hash_curva) throw new Error("Hash de curva ausente. Regenere os atributos.");
    if (requireGroups && !sourceGroup(row)) throw new Error("Informe DOI ou grupo_origem para separar as fontes.");
    for (const feature of SCIENTIFIC_FEATURES) {
      if (!Object.hasOwn(row, feature)) throw new Error(`Atributo ausente: ${feature}`);
      const value = row[feature];
      const empty = value === null || value === undefined || String(value).trim() === "";
      if (!empty && !Number.isFinite(toNumber(value))) throw new Error(`Atributo invalido: ${feature}`);
    }
    if (SCIENTIFIC_FEATURES.slice(0, 8).some((key) => !Number.isFinite(toNumber(row[key])))) {
      throw new Error("Atributos basicos incompletos.");
    }
  }
}

function splitBySource(vectors) {
  const grouped = groupBy(vectors, (v) => sourceGroup(v.row));
  const keys = shuffleRows(Object.keys(grouped).sort(), seededRandom(20260917));
  if (keys.length < 2) throw new Error("Treino requer pelo menos duas fontes independentes.");
  const remaining = labelCounts(vectors);
  const test = [];
  const chosen = new Set();
  for (const key of keys) {
    if (test.length >= Math.ceil(vectors.length * 0.2)) break;
    const counts = labelCounts(grouped[key]);
    if (Object.entries(counts).some(([label, count]) => remaining[label] <= count)) continue;
    chosen.add(key);
    test.push(...grouped[key]);
    Object.entries(counts).forEach(([label, count]) => { remaining[label] -= count; });
  }
  if (!test.length) throw new Error("Fontes insuficientes para validacao sem remover classes do treino.");
  const train = vectors.filter((v) => !chosen.has(sourceGroup(v.row)));
  const hashes = new Set(train.map((v) => v.row.hash_curva));
  if (test.some((v) => hashes.has(v.row.hash_curva))) throw new Error("Curvas duplicadas entre fontes de treino e validacao.");
  return { train, test };
}

function checkIndependentTest(rows, model) {
  const ids = new Set(model.developmentIds);
  const groups = new Set(model.developmentGroups);
  const hashes = new Set(model.developmentHashes);
  for (const row of rows) {
    if (!sourceGroup(row)) throw new Error("Teste rotulado requer DOI ou grupo_origem independente.");
    if (ids.has(row.id_entrada) || groups.has(sourceGroup(row)) || hashes.has(row.hash_curva)) {
      throw new Error("Teste bloqueado: ID, fonte ou curva compartilhada com o desenvolvimento.");
    }
  }
}

function refitCandidate(result, prepared) {
  const previous = result.model;
  let model;
  if (previous.type === "ensemble") {
    model = { ...previous, baseModels: previous.baseModels.map((entry) => ({
      weight: entry.weight,
      model: trainTechnique(entry.model.type, { ...prepared, treeCount: entry.model.trees?.length }).model,
    })) };
  } else {
    model = trainTechnique(previous.type, { ...prepared, treeCount: previous.trees?.length }).model;
  }
  Object.assign(model, {
    features: prepared.features, scaler: prepared.scaler,
    trainSize: prepared.train.length, originalTrainSize: prepared.originalTrainSize,
    testSize: previous.testSize, classCounts: prepared.classCounts,
    accuracy: result.accuracy, balancedAccuracy: result.balancedAccuracy, macroF1: result.macroF1,
    confusion: previous.confusion, perClassMetrics: previous.perClassMetrics,
    version: FEATURE_VERSION, signalKind: prepared.rows[0].tipo_sinal,
    developmentIds: prepared.rows.map((row) => row.id_entrada),
    developmentGroups: [...new Set(prepared.rows.map(sourceGroup))],
    developmentHashes: prepared.rows.map((row) => row.hash_curva),
    validationIds: previous.validationIds || [],
    validationGroups: previous.validationGroups || [],
    trainOnlyClasses: previous.trainOnlyClasses || [],
    protocol: "source_disjoint_development_selection_frozen_external",
  });
  return { ...result, model };
}

async function canonicalTestRows() {
  const rows = state.pendingTestRows;
  const columns = Object.keys(rows[0] || {});
  if (columns.includes("E") && (columns.includes("j") || columns.includes("I"))) {
    const response = await fetch("/api/features", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows, defaults: {
        tipo_sinal: document.getElementById("newSignalKind").value,
        unidade_potencial_usada: document.getElementById("newPotentialUnit").value,
        unidade_sinal_usada: document.getElementById("newSignalUnit").value,
        grupo_origem: document.getElementById("newSource").value,
      } }),
    });
    if (!(response.headers.get("Content-Type") || "").includes("application/json")) {
      throw new Error("Extrator indisponivel. Inicie o aplicativo com serve_app.py.");
    }
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Falha na extracao.");
    return payload.rows;
  }
  return rows;
}

function metricPercent(value) {
  return Number.isFinite(value) ? `${Math.round(value * 100)}%` : "N/A";
}

function safeAction(action, onError) {
  return async (...args) => {
    try { await action(...args); }
    catch (error) {
      document.getElementById("actionError").textContent = error.message;
      if (onError) onError(error);
    }
  };
}
