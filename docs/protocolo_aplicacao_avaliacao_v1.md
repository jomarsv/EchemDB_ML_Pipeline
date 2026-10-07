# Protocolo de aplicacao e avaliacao - v1

Data: 2026-09-18. Etapa 2 da preparacao cientifica.
Status: especificacao de trabalho, ainda nao implementada integralmente nem pre-registrada.
Este documento foi escrito DEPOIS da observacao dos resultados exploratorios.
Nao deve ser apresentado como protocolo anterior aos experimentos ja realizados.

## 1. Aplicacao e limites

Aplicacao principal: recuperacao assistida de metadados de material do eletrodo
em colecoes de voltamogramas. Aplicacao secundaria: priorizacao de registros
para auditoria de consistencia. Usuario: curador de dados ou pesquisador.

O sistema sugere candidatos para revisao, nao identifica composicao quimica,
nao substitui caracterizacao experimental e nao corrige automaticamente o banco.
O material normalmente conhecido funciona como referencia de avaliacao quando
seu rotulo e ocultado de forma controlada. A recuperacao com ocultacao mede um
cenario simulado: nao demonstra, sozinha, recuperacao em registros realmente incompletos.

Uma discordancia com o material declarado nao prova erro de metadado. Pode decorrer
de erro do modelo, condicoes experimentais diferentes, rotulo amplo ou curva ambigua.
O desempenho deve ser interpretado no dominio de condicoes representado no treino.

## 2. Perguntas e hipoteses a testar

Pergunta principal: quanto o sistema recupera corretamente o material de curvas
de publicacoes nao usadas no ajuste, comparado com baselines sob o mesmo protocolo?

Pergunta secundaria: uma lista curta de candidatos e uma regra de abstencao ajudam
o curador a revisar registros sem ocultar erros ou excluir silenciosamente classes raras?

Hipoteses de trabalho, NAO resultados: a selecao interna de tecnicas pode melhorar
desempenho entre classes; candidatos ordenados podem auxiliar a recuperacao;
a abstencao pode reduzir erros entre respostas emitidas ao custo de menor cobertura.
Nenhuma dessas melhorias e garantida pela arquitetura do Auto organizer.

## 3. Contrato de entrada e saida

| Elemento | Regra |
| --- | --- |
| Curva | Pares E e I ou j em ordem de aquisicao, sem ordenar globalmente por potencial |
| Unidades | Declaradas e verificadas; V, A ou A/m2 apos conversao |
| Modalidade | Corrente e densidade em modelos separados |
| Condicoes | Registrar referencia de potencial, eletrolito, pH, temperatura, velocidade de varredura, ciclo e area quando disponiveis; nao inventar ausencias |
| Proveniencia | ID, DOI/publicacao, experimento/figura quando conhecido e hash da curva |
| Alvo | Material do eletrodo segundo vocabulario curado e versionado |
| Saida prevista | Ate tres candidatos distintos ordenados, escore identificado como nao calibrado quando aplicavel, decisao e motivo |
| Decisoes previstas | sugestao, inconclusivo ou entrada_invalida |
| Revisao humana | Aceitar, rejeitar ou manter pendente; manter o rotulo original e a justificativa |

No experimento principal, os preditores sao exclusivamente descritores da curva.
Material declarado, classe_alvo, ID, nome de arquivo, DOI, referencia bibliografica,
autores e texto que revele o material nunca entram no vetor de atributos.
Proveniencia serve para agrupamento e rastreio. Condicoes experimentais servem
inicialmente para elegibilidade e analise de dominio, nao como preditores adicionais.
Um modelo com condicoes como preditores sera uma ablacao explicitamente identificada.

## 4. Tarefas experimentais

### T1 - Recuperacao com ocultacao de metadados

1. Curar a referencia e congelar os grupos de origem antes do benchmark.
2. Em cada teste externo do protocolo aninhado, ocultar o material de TODOS os
   registros da interface de inferencia, mantendo uma copia separada para pontuacao.
3. Extrair atributos pelo mesmo codigo do treino e inferir sem consultar rotulos.
4. Exportar candidatos, escores, decisao e proveniencia para cada registro.
5. Comparar com a referencia preservada. Nunca completar o material antes da predicao.

A ocultacao e artificial e controlada. Uma avaliacao futura com metadados realmente
ausentes exige recuperacao independente do rotulo por curador ou fonte primaria.

### T2 - Auditoria de consistencia

Usar os candidatos calculados SEM o material informado como entrada. Somente apos
a inferencia, comparar com o material declarado e sinalizar divergencias para revisao.
O sinal e uma suspeita, nao uma correcao. Registrar divergencias tambem em dados intactos.

Se forem simulados erros de rotulo, criar copias exclusivamente de avaliacao e manter
o original intacto. Taxas de corrupcao, mecanismo de troca, sementes e limiar de alerta
devem ser registrados antes da execucao e ajustados apenas internamente. Ainda pendentes.
Relatar precisao/recall de deteccao, falsos alertas em registros intactos e carga de revisao.
Resultados com corrupcao sintetica nao estimam automaticamente a prevalencia ou o
desempenho em erros reais. A validacao real depende de adjudicacao humana independente.

### T3 - Transferencia e abstencao (etapa 5)

Coletar publicacoes/experimentos ainda nao usados no desenvolvimento. Congelar modelos
e regras antes de revelar seus rotulos. Definir separadamente entradas invalidas,
classes nao cobertas e casos validos porem ambiguos.

O limiar de inconclusivo nao sera escolhido pelo teste externo nem por um valor
arbitrario de voto do k-NN. A escolha do escore, calibracao se viavel, limiar e criterio
de aceitacao sera validada internamente e registrada antes da avaliacao final.
Um escore alto nao garante que a curva esteja dentro do dominio de treinamento.

## 5. Metricas e convencoes propostas

Metrica primaria para selecao interna: acuracia balanceada entre classes com suporte
real na validacao. Desempate: macro-F1; persistindo empate, menor complexidade segundo
ordem de candidatos a ser registrada no manifesto antes da execucao.

Relatar tambem acuracia geral, macro-F1, matriz de confusao, precisao/recall/F1 por
classe e quantidade de curvas E de fontes por classe. Para comparabilidade com o app,
macro-F1 usa a uniao de classes verdadeiras e preditas, com divisao indefinida tratada
como zero no agregado; recall sem suporte e N/A na tabela. Publicar a lista de classes
de cada agregado: nao comparar medias com universos distintos como se fossem iguais.

Na recuperacao, acrescentar acerto top-1 e top-3, tambem resumidos por classe.
Top-3 tem denominador todas as curvas elegiveis, inclusive erros e abstencoes na
versao operacional; apresentar a analise de ranking sem abstencao separadamente.
Top-k so e informativo com numero de classes candidatas maior que k.

Na abstencao: cobertura = respostas emitidas / entradas elegiveis; risco seletivo =
erros entre respostas / respostas emitidas. Sem respostas, risco e N/A, nao zero.
Mostrar curva risco-cobertura e cobertura por classe; publicar contagem e motivos de
entradas invalidas separadamente. Nao usar acuracia apenas dos casos aceitos sem cobertura.

Incerteza deve respeitar a unidade de fonte/publicacao. Comparacoes entre modelos
precisam de preditores pareados nos mesmos registros e grupos, nao apenas porcentagens
arredondadas. A reamostragem de fontes sobre predicoes congeladas nao estima toda a
variabilidade de retreinamento. Metodo, sementes e convencoes de classes ausentes
nas replicas devem ser explicitados na etapa estatistica antes de sua execucao.

## 6. Encaminhamento para validacao aninhada

Usar uma implementacao de referencia versionada, com testes de paridade com a
inferencia. Nao atribuir resultados do scikit-learn aos modelos JS do navegador.
O particionamento agrupado mantem cada fonte em apenas um lado de cada divisao [1].
O nivel interno seleciona configuracoes; o externo estima seu desempenho [2].

Preparar manifesto com IDs, grupos, classes, folds, sementes, exclusoes e hashes.
Publicacoes que reutilizem o mesmo experimento devem formar um grupo conectado
quando essa relacao for identificada; DOI diferente nao garante independencia.
O mesmo manifesto externo sera usado por Auto organizer e baselines.

Dentro de CADA treino externo: selecionar atributos por disponibilidade, imputar,
normalizar, balancear, escolher hiperparametros e formar ensembles exclusivamente
com treino/validacao internos. Pesos de ensemble devem usar predicoes internas fora
da amostra. Reajustar no treino externo e predizer o fold externo apenas depois.
Pipelines ajudam a restringir o ajuste do preprocessamento a particao correta [3].

Antes de executar, auditar viabilidade das particoes pelo numero de fontes por classe.
Uma classe de uma unica fonte nao pode estar simultaneamente em treino e teste
independentes. Nao dividir essa fonte para resolver o problema. Registrar casos
sem suporte, limitar a alegacao de classificacao fechada e prever avaliacao separada
de classe nao coberta. Nao excluir resultados ruins nem escolher folds por acuracia.
Numero de folds, classes elegiveis, grids e orcamento ficam pendentes dessa auditoria;
o benchmark nao deve iniciar enquanto esses itens estiverem abertos.

Baselines previstos: classe majoritaria, k-NN, regressao logistica, SVM e floresta
aleatoria. Afinar baselines e Auto organizer internamente, registrar seus orcamentos
e tempos e comparar nos mesmos testes. Novos algoritmos nao sao a contribuicao por si.
Ablacoes previstas: familias de descritores, balanceamento, modelo individual versus
ensemble e representacao da curva. Executar somente com protocolo congelado.

## 7. Situacao atual e barreiras para a etapa 3

| Item | Situacao | Criterio de encerramento |
| --- | --- | --- |
| Aplicacao | Definida neste documento | Recuperacao assistida primaria; auditoria secundaria |
| Unidades e extrator | Implementados em v2 | Manter testes e contrato versionado |
| Referencia de potencial | Pendente | Tabela por registro; converter somente com metadados suficientes ou delimitar conjuntos comparaveis; documentar ausencias |
| Duplicatas | Pendente | Adjudicar pares e relacoes entre fontes; documentar manutencao/exclusao e grupo comum |
| Descritores de pico | Pendente | Revisao eletroquimica de curvas por modalidade, direcao, ruido e ciclos; registrar discrepancias e limites |
| Vocabulario de material | Pendente | Revisar substratos, revestimentos e ligas sem agrupamento quimicamente injustificado |
| Motor de referencia | Pendente | Escolher implementacao e verificar equivalencia treino/inferencia |
| Manifesto aninhado e grids | Pendente | Auditoria de fontes por classe e congelamento antes de executar |
| Top-3, abstencao e revisao humana | Planejados | Implementar e testar; nao anunciar como funcionalidades atuais |

O aplicativo atual classifica, compara modelos congelados e exporta predicoes.
Nao possui ainda o fluxo de curadoria humana nem abstencao validada descritos aqui.

O teste exploratorio de densidade ja observado tem 67 curvas de 14 fontes, cinco
classes reais e sete classes do modelo sem amostras. O k-NN selecionado acertou 50/67.
Isso e evidencia exploratoria, nao confirmacao desta nova aplicacao nem teste historicamente
cego. Preservar essa execucao; nao a usar para escolher limiares ou anunciar um novo vencedor.
A base historicamente examinada continua de desenvolvimento metodologico. A validacao
confirmatoria requer novas fontes; validacao aninhada nao desfaz exposicao historica.

## 8. Texto-base para o manuscrito

Este trabalho investiga a recuperacao assistida de metadados de material do eletrodo
em colecoes de voltamogramas, com aplicacao secundaria a priorizacao de registros
para auditoria. O objetivo nao e substituir a identificacao experimental do material,
mas avaliar em que medida descritores das curvas permitem sugerir candidatos para
revisao humana quando o metadado esta ausente ou apresenta possivel inconsistencia.
O protocolo proposto separa publicacoes entre ajuste e avaliacao, compara metodos sob
as mesmas particoes e explicita classes e condicoes sem suporte suficiente. Divergencias
entre predicao e metadado sao tratadas como sinais para investigacao, e nao como prova
de erro no registro. Candidatos ordenados e abstencao integram a avaliacao planejada;
sua utilidade operacional ainda precisa ser demonstrada.

Usar como enquadramento prospectivo; nao converter etapas planejadas em resultados
ou verbos no passado antes de implementa-las e avalia-las.

## Referencias metodologicas

[1] scikit-learn, GroupKFold: https://sklearn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html

[2] scikit-learn, Nested versus non-nested cross-validation:
https://scikit-learn.org/1.5/auto_examples/model_selection/plot_nested_cross_validation_iris.html

[3] scikit-learn, Common pitfalls and recommended practices:
https://github.com/scikit-learn/scikit-learn/blob/main/doc/common_pitfalls.rst

As convencoes de metricas, tarefas e barreiras acima sao decisoes deste protocolo;
as referencias sustentam os principios de particionamento e ajuste, nao validam
a utilidade eletroquimica do sistema nem constituem revisao do estado da arte.
