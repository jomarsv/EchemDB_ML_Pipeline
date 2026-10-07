# EchemDB ML Pipeline

**Version:** 0.1.0 ([changelog](CHANGELOG.md))  
**License:** MIT ([LICENSE](LICENSE))

Protótipo para transformar dados públicos do EchemDB, especialmente voltamogramas cíclicos, em tabelas de atributos, vetores interpolados, modelos exploratórios e um relatório técnico.

O projeto foi gerado a partir do prompt original em `prompt_cortex_echemdb_aprendizagem.txt`, com duas decisões práticas:

- não baixa nem inventa dados automaticamente;
- trabalha sobre uma cópia local/exportada do EchemDB ou sobre arquivos CSV/JSON/DataPackage fornecidos pelo usuário.

## Protocolo cientifico

A aplicacao proposta e a recuperacao assistida de metadados, com auditoria de
consistencia e revisao humana. O [protocolo de aplicacao e avaliacao](docs/protocolo_aplicacao_avaliacao_v1.md)
define tarefas, metricas e pendencias anteriores a validacao aninhada.
Top-3 e abstencao validada sao requisitos planejados, nao funcionalidades ja demonstradas.

Etapa 3: [validacao aninhada por fontes, piloto restrito](docs/etapa3_validacao_aninhada_piloto.md).
O motor Python foi executado em Ag/Au com referencia SCE declarada, separadamente do
app e sem reutilizar seu teste de 67 curvas. Nao e validacao dos 12 materiais.

## Estrutura

```text
echemdb-ml-pipeline/
  app/index.html
  app/app.js
  app/styles.css
  docs/revisao_prompt.md
  prompts/prompt_cortex_echemdb_ml_revisado.md
  run_pipeline.py
  requirements.txt
  src/echemdb_ml_pipeline/
```

## Instalação

```powershell
cd C:\Users\jomar\OneDrive\Documents\Playground\echemdb-ml-pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Uso

**Protocolo cientifico v2:** use os arquivos em `outputs/scientific_v2`, nao os CSVs
historicos diretamente em `outputs`. Consulte [integridade cientifica](docs/integridade_cientifica_v2.md)
para unidades, descritores, isolamento e limitacoes. Os resultados antigos precisam ser recalculados.

Para regenerar a copia local atual sem ajustar modelos exploratorios:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --input ..\echemdb-data-0.8.4\data\generated --output outputs\scientific_v2 --skip-models
.\.venv\Scripts\python.exe scripts\create_test_split.py
```

Informe uma pasta ou arquivo contendo dados exportados do EchemDB:

```powershell
python run_pipeline.py --input C:\caminho\para\electrochemistry-data --output outputs
```

Parâmetros úteis:

```powershell
python run_pipeline.py --input dados --output outputs --n-points 256 --min-points 20 --normalization max_abs
```

## Saídas

O pipeline tenta gerar:

```text
outputs/dados_brutos_indexados.csv
outputs/dados_limpos.csv
outputs/curvas_voltamogramas_plot.csv
outputs/atributos_voltamogramas.csv
outputs/curvas_interpoladas.csv
outputs/controle_qualidade.csv
outputs/relatorio_modelos.csv
outputs/matriz_confusao.png
outputs/pca_voltamogramas.png
outputs/clusters_voltamogramas.png
outputs/importancia_atributos.png
outputs/relatorio_tecnico.md
```

Algumas saídas só aparecem se houver dados suficientes e dependências instaladas. Por exemplo, a matriz de confusão exige pelo menos duas classes com amostras suficientes para treino e teste.

## App local

Para rodar a interface local:

```powershell
cd C:\Users\jomar\OneDrive\Documents\Playground\echemdb-ml-pipeline
.\.venv\Scripts\python.exe serve_app.py --port 8765
```

Depois abra:

```text
http://127.0.0.1:8765/
```

O servidor acima e necessario para extrair atributos de curvas novas usando o mesmo
codigo Python do pipeline. Abrir HTML diretamente ou usar `http.server` nao oferece essa API.

```text
C:\Users\jomar\OneDrive\Documents\Playground\echemdb-ml-pipeline\app\index.html
```

No app, importe os CSVs gerados pelo pipeline, principalmente:

```text
outputs/atributos_voltamogramas.csv
outputs/curvas_voltamogramas_plot.csv
outputs/curvas_interpoladas.csv
outputs/controle_qualidade.csv
outputs/relatorio_modelos.csv
```

O app permite:

- visualizar os dados coletados;
- desenhar voltamogramas físicos como densidade de corrente/corrente em função do potencial, `j(E)` ou `i(E)`;
- treinar e comparar técnicas de IA no navegador, incluindo k-NN, centróide mais próximo, Naive Bayes Gaussiano, árvore de decisão, floresta aleatória e ensemble ponderado;
- usar o modo `Auto organizer`, que avalia técnicas individuais e combinações por ensemble, escolhendo automaticamente a melhor opção pela acurácia de validação;
- usar o modo `Auto organizer balanceado`, que prioriza desempenho médio por classe quando há classes com poucas amostras;
- avaliar modelos congelados em CSV rotulado independente, sem escolher modelos nem pesos com os rotulos externos;
- escolher acuracia ou acuracia balanceada somente no desenvolvimento e revisar recall, precisao e F1 por classe;
- treinar com `Auto balanceamento`, `Pesos por classe`, `Sobreamostragem` ou `Sobreamostragem + pesos` para testar estratégias contra desbalanceamento;
- gerar diagnóstico automático de classes críticas e próximos passos de coleta/revisão;
- ver classes aprendidas, acurácia e matriz de confusão;
- carregar um novo CSV de curva `E,j` ou de atributos para testar a IA;
- exportar o estado do modelo, as predições e um relatório do experimento em Markdown.

### Comparar com teste externo

Para comparar o `Auto organizer` contra o k-NN anterior usando um conjunto separado:

1. Importe `outputs\scientific_v2\testes\atributos_treino_sem_teste_current_density.csv` em `Importar CSVs`.
2. Em `Aprendizagem`, mantenha `Densidade de corrente (A/m2)` e `classe_alvo`.
3. Selecione `Auto organizer balanceado` e o balanceamento desejado, antes de observar o teste.
4. Clique em `Treinar IA`. A selecao usa validacao por fonte dentro do desenvolvimento; depois os modelos sao reajustados no desenvolvimento inteiro e congelados.
5. Em `Testar IA`, selecione `outputs\scientific_v2\testes\amostras_teste_atributos_current_density.csv`.
6. Clique em `Avaliar modelos congelados`. A primeira linha continua sendo o modelo selecionado no desenvolvimento, mesmo que outro obtenha maior acuracia externa.
7. Use `Testar com a IA` para gerar predicoes individuais. Consulte tambem o desempenho por classe e o diagnostico.
8. Exporte o modelo e o relatorio. Nao ajuste configuracoes a partir destes resultados e depois apresente o mesmo teste como independente.

Para corrente, use os arquivos com sufixo `_current` e a grandeza `Corrente (A)`.
O teste atual dessa modalidade tem somente uma curva: nao sustenta uma estimativa de desempenho.
Os CSVs de atributos antigos sao rejeitados. Para graficos, importe `outputs/scientific_v2/dados_limpos.csv`.

## Curadoria de referencias e fontes

A auditoria versionada de referencias de potencial, duplicatas exatas e fontes
raras esta em [Curadoria cientifica](docs/curadoria_referencias_duplicatas_fontes.md).
As exportacoes `outputs/scientific_curation_v1/*_native.csv` preservam escalas
nativas distintas: nao importar como uma unica coorte harmonizada no app.
 A comparacao com a release oficial 0.9.2 esta em
[Comparacao da release 0.9.2](docs/comparacao_release_092.md); ela foi auditada,
mas ainda nao foi incorporada ao treinamento.

## Premissas

- O pipeline detecta colunas de potencial, corrente ou densidade de corrente por nomes comuns como `E`, `potential`, `voltage`, `i`, `current`, `j` e `current density`.
- Conversões de unidade só são feitas quando a unidade é reconhecida de forma simples, como `mV -> V`, `uA -> A` e `mA -> A`.
- Unidades ausentes, desconhecidas ou incompativeis excluem a curva do treino; corrente e densidade nao sao misturadas.
- A interpolação principal usa a ordem de aquisição da curva, não apenas o eixo de potencial, para preservar o laço de voltametria cíclica.
