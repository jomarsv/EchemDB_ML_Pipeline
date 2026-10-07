# Etapa 3: validacao aninhada por fontes - piloto v1

Execucao em 18/09/2026. Status: motor implementado e piloto restrito executado.
Nao equivale ao encerramento da validacao cientifica de todos os materiais.
Nenhum ajuste foi feito para melhorar as metricas apos esta execucao.

## Por que um piloto restrito

A auditoria leu a referencia de potencial declarada no schema dos arquivos JSON
originais, associando cada recurso ao CSV correspondente. A base de densidade tem
RHE, SCE, SHE, Ag/AgCl e outras referencias. Nao foram aplicadas conversoes presumidas.
Classes com apenas uma fonte nao permitem treino e teste independentes dessa classe.
O exame eletroquimico dos picos e a adjudicacao das duplicatas continuam pendentes.

Para testar o protocolo sem contornar essas limitacoes, foi definido ANTES do ajuste:

- Somente os IDs do desenvolvimento anterior de densidade de corrente (241 curvas).
- Somente referencia SCE declarada; isso nao certifica as condicoes do eletrodo.
- Pelo menos quatro fontes por classe apos os filtros, com checagem das particoes reais.
- Excluir todos os integrantes de pares com hash identico se estiverem no recorte.
- Sete atributos fixos sem picos: amplitude de potencial, minimo, maximo, media e
  desvio do sinal, area absoluta e area orientada. Areas nao representam carga.

O recorte final tem **43 curvas, nove publicacoes e duas classes: Ag (11 curvas,
quatro fontes) e Au (32 curvas, cinco fontes)**. As 67 curvas do teste anterior nao
participaram de treino, selecao ou avaliacao deste piloto. O par duplicado encontrado
na base completa nao pertence ao recorte SCE; sua adjudicacao permanece necessaria.

Dos 332 registros auditados: 91 fora do desenvolvimento de densidade selecionado,
186 com outra referencia, 12 sem o minimo de fontes por classe, 43 incluidos.
As razoes sao exclusivas e seguem essa ordem, nao sao contagens sobrepostas.
RHE, embora numeroso, nao oferece duas classes com quatro fontes no desenvolvimento.
Ag/AgCl nao foi agrupado com SCE, nem tratado como uma referencia universal sem
conhecer sua composicao. Este recorte e metodologico, nao escolhido por acuracia.

## Implementacao e particoes

Motor Python/scikit-learn independente do app JS, identificado como `nested-core-v1`.
Tres folds externos e dois internos, StratifiedGroupKFold, semente 20260918.
Grupos: DOI normalizado. Preflight exige ambas as classes em cada treino e validacao,
sem intersecao de ID, fonte ou hash; falha antes do ajuste se o desenho for inviavel.
Cada curva aparece uma unica vez em teste externo por metodo.
O manifesto e as particoes sao escritos antes do primeiro treinamento.

Imputacao e padronizacao estao no Pipeline ajustado em cada treino interno. Os sete
atributos sao fixos por desenho, nao escolhidos pela disponibilidade do teste.
Hiperparametros usam media da acuracia balanceada dos folds internos, com ordem do
grid como desempate. Selecao entre metodos usa acuracia balanceada das predicoes
internas concatenadas, depois macro-F1 e ordem fixa. Essas duas agregacoes sao
explicitamente distintas. Nao houve sobreamostragem neste piloto.

Baselines: classe majoritaria, k-NN ponderado por distancia, regressao logistica,
SVM RBF e floresta aleatoria. Grids no manifesto: 1, 3, 6, 6 e 4 configuracoes,
respectivamente. Logistic/SVM/floresta incluem pesos de classe como opcao interna.
A floresta tem 100 arvores. Nao sao os mesmos estimadores nem os mesmos atributos
das execucoes anteriores do navegador: nao comparar porcentagens diretamente.

Ensembles: voto duro ponderado das quatro tecnicas nao triviais ou das tres melhores
internamente. Os pesos e os membros sao calculados antes de qualquer predicao externa.
"Top 3" aqui significa tecnicas, nao tres materiais sugeridos ao curador.
O Auto organizer seleciona entre individuais e ensembles somente no nivel interno;
nao inclui o baseline majoritario entre seus candidatos, embora ele seja avaliado.
As predicoes internas usadas apos ajuste de hiperparametros podem ser otimistas:
sao criterios de selecao, nao estimativas finais de desempenho.

Selecoes automaticas: SVM no fold 1; floresta nos folds 2 e 3. Cada fold salva todos
os modelos reajustados no respectivo treino externo. `predict_bundle` e a funcao
unica de inferencia desses artefatos e foi verificada contra o CSV exportado.
Arquivos joblib sao artefatos locais confiaveis; nao carregar joblib de terceiros.

## Resultados externos concatenados

| Metodo | Acertos | Acuracia | Acuracia balanceada | Macro-F1 |
| --- | ---: | ---: | ---: | ---: |
| Classe majoritaria | 32/43 | 74,4% | 50,0% | 42,7% |
| k-NN ajustado | 32/43 | 74,4% | 61,9% | 62,8% |
| Regressao logistica | 30/43 | 69,8% | 52,8% | 52,3% |
| SVM ajustada | 32/43 | 74,4% | 56,0% | 55,6% |
| Floresta ajustada | 39/43 | 90,7% | 87,8% | 87,8% |
| Ensemble completo | 34/43 | 79,1% | 65,1% | 67,0% |
| Ensemble top 3 | 34/43 | 79,1% | 65,1% | 67,0% |
| Auto organizer | 39/43 | 90,7% | 87,8% | 87,8% |

Essas metricas sao calculadas sobre as 43 predicoes externas concatenadas, nao pela
media simples das tres metricas de fold. Os valores por fold estao em `fold_metrics.csv`.
Auto organizer: 13/15, 11/12 e 15/16 acertos nos folds 1, 2 e 3.
Acuracia balanceada por fold: 92,3%, 75,0% e 92,9%, respectivamente.

Auto organizer e floresta apresentaram **as mesmas predicoes em todos os 43 registros**.
Nao ha evidencia de vantagem do procedimento automatico sobre esse baseline aqui.
Matriz do Auto organizer: Ag -> Ag 9, Ag -> Au 2, Au -> Ag 2, Au -> Au 30.
O baseline majoritario mostra por que acuracia geral isolada e insuficiente.
Nao foram calculados testes de significancia nem intervalos de confianca nesta etapa.

## Artefatos e reproducao

Auditoria completa: `outputs/stage3_audit/`.
Execucao preservada: `outputs/stage3_nested_sce_v1/`.

| Arquivo | Conteudo |
| --- | --- |
| manifest.json | Escopo, atributos, grids, sementes, versoes e hashes |
| eligibility_audit.csv | Todos os registros e motivos de exclusao |
| cohort.csv | Curvas/atributos efetivamente incluidos e fonte do metadado |
| partitions.csv | IDs de todos os treinos, validacoes internas e testes externos |
| internal_selection.json | Parametros, escores internos, pesos e escolhas por fold |
| predictions.csv | 344 linhas: 43 predicoes pareadas para cada um dos oito metodos |
| fold_metrics.csv | Metricas externas por fold |
| pooled_metrics.csv | Metricas externas concatenadas sem arredondamento |
| fold_1.joblib a fold_3.joblib | Modelos e regras congelados para cada fold |
| COMPLETED.json | Marcador de conclusao do motor |

Na pasta do projeto, para uma nova reproducao (sem sobrescrever a anterior):

```powershell
.\.venv\Scripts\python.exe scripts/audit_nested_inputs.py
.\.venv\Scripts\python.exe scripts/run_nested_validation.py --output outputs/stage3_nested_sce_replica
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/scientific-integrity.test.cjs
```

O comando recusa diretorio de experimento ja existente. A auditoria de entrada pode
ser regenerada, mas o benchmark e seus resultados sao separados dos arquivos do app.
Nao ha botao novo no navegador nesta etapa. Nao importar esses modelos Python no app JS.

## Limites e proxima decisao

O recorte de duas classes e nove fontes e pequeno e ja foi historicamente explorado.
SCE declarado nao elimina diferencas de eletrolito, pH, varredura, area, ciclos ou
protocolo de digitalizacao. Fontes distintas podem reutilizar experimentos; o DOI e
um proxy de independencia, a revisar. O piloto nao resolve o problema dos demais materiais.
Seu 90,7% nao e comparavel aos antigos 91% nem ao teste de 67 curvas com 12 classes no modelo.

Antes de ampliar: adjudicar duplicatas e referencias, revisar vocabulario de materiais
e representacoes e obter mais fontes das classes raras. A implementacao aninhada
agora pode sustentar a etapa 4, mas a alegacao de contribuicao exige ablacões e
baselines sob um escopo definido, nao selecao retrospectiva do recorte mais favoravel.
A etapa 5 ainda exige dados ineditos, incerteza por fonte e abstencao validada.
