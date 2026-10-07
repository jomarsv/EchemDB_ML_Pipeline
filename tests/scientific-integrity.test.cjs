const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function harness() {
  const elements = new Map();
  const document = { addEventListener() {}, querySelectorAll() { return []; },
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, {value: '', textContent: '', innerHTML: ''});
      return elements.get(id);
    }};
  const ctx = vm.createContext({document, console, setTimeout, clearTimeout});
  for (const file of ['science.js', 'app.js']) vm.runInContext(fs.readFileSync(path.join(root, 'app', file), 'utf8'), ctx);
  vm.runInContext(`
    for (const name of ['renderAll','renderLearning','updateMetrics','renderExternalComparison',
      'renderExternalClassResults','renderDiagnostics','renderPredictions','renderExportSummary']) globalThis[name] = () => {};
    document.getElementById('targetColumn').value = 'classe_alvo';
    document.getElementById('signalKindSelect').value = 'current_density';
    document.getElementById('techniqueSelect').value = 'auto';
    document.getElementById('balanceStrategySelect').value = 'none';
    document.getElementById('knnK').value = '5';
    state.attributes = Array.from({length: 40}, (_, i) => ({
      ...Object.fromEntries(SCIENTIFIC_FEATURES.map((key,j) => [key, (i%2)*10 + i/100 + j/1000])),
      id_entrada: 'id' + i, classe_alvo: i%2 ? 'Au' : 'Pt',
      status: 'valido', tipo_sinal: 'current_density', unidade_sinal_usada: 'A/m2',
      unidade_potencial_usada: 'V', versao_atributos: FEATURE_VERSION,
      grupo_origem: '10.1/source' + Math.floor(i/2), hash_curva: 'hash' + i,
    }));
  `, ctx);
  return (code) => vm.runInContext(code, ctx);
}

test('scaler and feature availability never use development validation rows', () => {
  const run = harness();
  const before = run(`const before = prepareTrainingSet(); JSON.stringify({features:before.features,scaler:before.scaler})`);
  run(`const held = new Set(before.test.map(v => v.id));
    state.attributes.forEach(row => { if (held.has(row.id_entrada)) {
      row.j_max = 1e15; row.E_pico_anodico = null;
    }});`);
  assert.equal(run(`JSON.stringify({features:prepareTrainingSet().features,scaler:prepareTrainingSet().scaler})`), before);
  assert.equal(run(`before.test.some(v => before.train.some(t => sourceGroup(t.row) === sourceGroup(v.row)))`), false);
});

test('missing training import and wrong modality have distinct actionable errors', () => {
  const run = harness();
  run(`document.getElementById('signalKindSelect').value = 'current';`);
  assert.throws(() => run('prepareTrainingSet()'), /Grandeza selecionada sem amostras/);
  run('state.pendingTestRows = state.attributes; state.attributes = [];');
  assert.throws(() => run('prepareTrainingSet()'), /Nenhum CSV de atributos de treino importado/);
});

test('external evaluation errors appear beside the results, including missing file and model', async () => {
  const run = harness();
  await run('safeAction(compareExternalTechniques, showTestError)()');
  assert.match(run("document.getElementById('externalComparisonTable').innerHTML"), /Nenhum CSV de teste carregado/);
  run('state.pendingTestRows = state.attributes;');
  await run('safeAction(compareExternalTechniques, showTestError)()');
  assert.match(run("document.getElementById('testStatus').textContent"), /Treine e congele/);
  run('trainModel(); state.pendingTestRows = state.attributes;');
  await run('safeAction(compareExternalTechniques, showTestError)()');
  assert.match(run("document.getElementById('externalComparisonTable').innerHTML"), /Teste bloqueado/);
});

test('strict schema, modality, provenance and duplicate isolation', () => {
  const run = harness();
  run('trainModel()');
  assert.throws(() => run(`checkFeatureRows([{...state.attributes[0], versao_atributos:'old'}], 'current_density')`), /versao/);
  assert.throws(() => run(`checkFeatureRows(state.attributes, 'current')`), /incompativel/);
  assert.throws(() => run(`const partial = {...state.attributes[0]}; delete partial.derivada2_media; checkFeatureRows([partial], 'current_density')`), /ausente/);
  for (const key of ['id_entrada', 'grupo_origem', 'hash_curva']) {
    assert.throws(() => run(`checkIndependentTest([{id_entrada:'new',grupo_origem:'10.9/new',hash_curva:'new', ${key}:state.attributes[0].${key}}], state.model)`), /bloqueado/);
  }
  assert.throws(() => run(`checkIndependentTest([{id_entrada:'new',grupo_origem:'https://doi.org/'+state.attributes[0].grupo_origem,hash_curva:'new'}], state.model)`), /bloqueado/);
});

test('external labels cannot fit, reorder, or change a frozen model or ensemble weights', async () => {
  const run = harness();
  run(`trainModel();
    state.pendingTestRows = state.attributes.slice(0,6).map((row,i) => ({...row,
      id_entrada:'external'+i, grupo_origem:'10.9/external',hash_curva:'externalhash'+i}));
    trainTechnique = () => { throw new Error('Training forbidden during external evaluation'); };
  `);
  const before = run('JSON.stringify(state.frozenCandidates.map(r => exportableModel(r.model)))');
  await run('compareExternalTechniques()');
  assert.equal(run('JSON.stringify(state.frozenCandidates.map(r => exportableModel(r.model)))'), before);
  assert.equal(run('state.model === state.frozenCandidates[0].model'), true);
  assert.equal(run('state.externalResults[0].status'), 'selecionado_no_desenvolvimento');
  run(`state.pendingTestRows.forEach(row => { row.classe_alvo = row.classe_alvo === 'Au' ? 'Pt' : 'Au'; });`);
  await run('compareExternalTechniques()');
  assert.equal(run('JSON.stringify(state.frozenCandidates.map(r => exportableModel(r.model)))'), before);
});

test('empty metrics are not perfect; predicted-only classes count in macro F1', () => {
  const run = harness();
  assert.equal(run('evaluatePredictions([]).accuracy'), null);
  assert.equal(run('evaluatePredictions([]).balancedAccuracy'), null);
  assert.equal(run('evaluatePredictions([]).macroF1'), null);
  assert.equal(run(`evaluatePredictions([{expected:'Pt',predicted:'Pt'},{expected:'Pt',predicted:'Au'}]).classes`), 1);
  assert.ok(Math.abs(run(`evaluatePredictions([{expected:'Pt',predicted:'Pt'},{expected:'Pt',predicted:'Au'}]).macroF1`)-1/3)<1e-10);
});

test('all 28 development configurations freeze before external evaluation', async () => {
  const run = harness();
  run(`document.getElementById('balanceStrategySelect').value = 'auto'; trainModel();`);
  assert.equal(run('state.frozenCandidates.length'), 28);
  assert.equal(run('state.frozenCandidates.every(r => r.model.version === FEATURE_VERSION)'), true);
  assert.equal(run(`state.frozenCandidates.every(r => r.model.testSize > 0 && r.model.developmentIds.length === 40)`), true);
});

test('real v2 data can train and rejects the development CSV as external test', async (t) => {
  const file = path.join(root, 'outputs/scientific_v2/testes/atributos_treino_sem_teste.csv');
  if (!fs.existsSync(file)) { t.skip('Generate scientific_v2/testes first'); return; }
  const run = harness();
  run(`state.attributes = parseCsv(${JSON.stringify(fs.readFileSync(file, 'utf8'))}).rows; trainModel();`);
  run(`state.pendingTestRows = state.attributes.filter(row => row.tipo_sinal === state.model.signalKind);`);
  await assert.rejects(run('compareExternalTechniques()'), /bloqueado/);
  const external = path.join(root, 'outputs/scientific_v2/testes/amostras_teste_atributos.csv');
  run(`state.pendingTestRows = parseCsv(${JSON.stringify(fs.readFileSync(external, 'utf8'))}).rows.filter(row => row.tipo_sinal === state.model.signalKind);`);
  await run('compareExternalTechniques()');
  assert.equal(run('state.externalResults.length'), 7);
});
