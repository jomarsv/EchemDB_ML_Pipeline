# Parecer científico do Simulador EchemDB

Data: 16 de setembro de 2026. Objetivo: identificar o trabalho necessário para uma submissão competitiva a periódico seletivo e aderente a Engenharias IV.

## 1. Parecer executivo

O projeto tem uma base aproveitável para pesquisa: importação de dados públicos, extração de atributos, interface de exploração, modelos comparativos, resultados por classe, scripts estatísticos e um manuscrito. Entretanto, a versão auditada ainda não sustenta uma submissão forte baseada na superioridade do Auto organizer. Há problemas confirmados de unidades, seleção de modelos no próprio teste, divergência entre treinamento e inferência e insuficiência de fontes independentes para várias classes.

A prioridade deve ser a confiabilidade da cadeia de medição e avaliação. Acrescentar modelos, aumentar a acurácia exibida ou ampliar a bibliografia não resolve esses problemas. Uma versão corrigida pode produzir resultados numéricos menores e, mesmo assim, um artigo cientificamente mais convincente.

A contribuição mais promissora é uma metodologia reprodutível para analisar voltamogramas heterogêneos, com harmonização física, validação por fontes independentes e diagnóstico de confiabilidade. A seleção automática de modelos pode integrar essa metodologia, mas sua novidade e seu benefício precisam ser demonstrados por comparação e ablação.

Este parecer não promete aceitação nem atribui probabilidade de publicação. Seletividade editorial, adequação temática, contribuição e pareceres independentes continuam determinantes.

## 2. Escopo e evidências examinadas

Foram examinados o código Python do pipeline, `app/app.js`, a documentação local, as tabelas processadas, os scripts estatísticos e `main.tex`/`reference.tex` da pasta `plastic_article_20260824`. Foram executadas verificações pontuais em Python e Node, sem alterar o código de produção, o manuscrito ou os resultados existentes.

Os resultados históricos foram lidos dos arquivos estatísticos; não foi reexecutado o treinamento completo de todos os modelos nesta auditoria. A navegação visual do app e a compilação LaTeX não foram testadas nesta etapa. A pesquisa bibliográfica foi direcionada ao diagnóstico e ao enquadramento editorial, não uma revisão sistemática exaustiva.

Locais principais:

- Pipeline: `C:/Users/jomar/OneDrive/Documents/Playground/echemdb-ml-pipeline`.
- Manuscrito: `C:/Users/jomar/OneDrive/Documents/Playground/_codex_extracts/plastic_article_20260824`.
- Evidências históricas: subpasta `statistics` do manuscrito.

## 3. O que significa buscar uma revista “Qualis A” agora

A CAPES informa que a lista Qualis 2021–2024 é destinada às publicações daquele período e que o Qualis Periódicos não será utilizado no ciclo 2025–2028. Uma classificação histórica não assegura o enquadramento de um artigo publicado em 2026. Fonte: [comunicado oficial da CAPES](https://www.gov.br/capes/pt-br/assuntos/noticias/sobre-o-qualis-periodicos-na-avaliacao-quadrienal-2021-2024).

O documento de Engenharias IV revisado em abril de 2026 contempla Engenharia Elétrica e Engenharia Biomédica, incluindo instrumentação e processamento de sinais. Sua seção 7.1 descreve a avaliação de artigos com indicadores internacionais e verificação de aderência temática; também considera aspectos qualitativos da contribuição. Não se deve equiparar automaticamente Q1, fator de impacto ou um antigo estrato A ao resultado da avaliação atual. Fonte: [Documento de Área, especialmente páginas 15–16 e 31–32](https://www.gov.br/capes/pt-br/centrais-de-conteudo/17042026_ENG_IVDOC_AREA_2025_2028revisado_abril_26.pdf/@@display-file/file).

Assim, a estratégia deve combinar: periódico consolidado, contribuição reconhecível em instrumentação/sinais/sensoriamento, evidência experimental ou computacional robusta e consulta à regra aplicável ao programa de pós-graduação. Se houver exigência institucional de Qualis histórico, registrar ISSN e ciclo consultado; este parecer não verificou um estrato histórico individual para cada revista.

## 4. Retrato real da base local

A contagem direta encontrou 332 linhas, 332 identificadores distintos, 83 DOIs distintos e 84 strings de referência. Essas duas últimas contagens não são equivalentes e precisam ser descritas separadamente. Não há DOI ausente na tabela analisada. Uma normalização simples dos prefixos de DOI, espaços e capitalização manteve os 83 DOIs.

| Material | Curvas | DOIs distintos | Implicação para validação por publicação |
|---|---:|---:|---|
| Pt | 158 | 26 | Melhor suporte relativo; ainda há heterogeneidade experimental |
| Au | 106 | 33 | Melhor suporte relativo |
| Ag | 25 | 10 | Viável para investigação agrupada, com incerteza |
| Cu | 12 | 3 | Poucas fontes; quatro curvas com unidades não convertidas |
| Ir | 10 | 3 | Poucas fontes independentes |
| Pd | 6 | 1 | Não permite aprender e testar a classe em DOIs distintos |
| Rh | 4 | 1 | Mesma limitação |
| Co | 3 | 2 | Suporte muito limitado |
| Ni | 3 | 1 | Não permite validação fechada entre fontes |
| Pb | 2 | 1 | Mesma limitação |
| Ru | 2 | 1 | Mesma limitação |
| Fe | 1 | 1 | Um único exemplo e uma única fonte |

Pt e Au representam 79,5% das curvas. Ter milhares de pontos em um voltamograma não equivale a ter milhares de experimentos independentes. Da mesma forma, expandir 264 linhas para 1.512 instâncias por sobreamostragem não aumenta a quantidade de experimentos originais.

Foi encontrado um par de linhas numericamente idênticas, incluindo número de pontos: `bi_2018_minimizing_1_f3b_black` e `bi_2018_minimizing_1_f3b_blue`, ambas Au e do mesmo DOI. Ambas estão no treino histórico, portanto esse par não demonstra vazamento entre os dois arquivos históricos. É necessário conferir os arquivos de origem antes de decidir se são duplicação ou curvas legitimamente equivalentes.

## 5. Achados prioritários no código

### 5.1. Crítico: o teste externo participa da construção do ensemble

Em `app/app.js:485`, `compareExternalTechniques()` fornece os exemplos externos como `prepared.test` para treinar e comparar candidatos. Em `app/app.js:349`, os resultados desses candidatos determinam quais são os três melhores. Em `app/app.js:711`, seus escores determinam os pesos do ensemble. Em `app/app.js:532`, o vencedor desse mesmo teste se torna o modelo ativo.

Consequência: o teste não é apenas consultado para medir o desempenho. Seus rótulos influenciam a construção do preditor, e também a escolha do vencedor entre as configurações. Portanto, 62/68 acertos não representam uma avaliação independente do procedimento Auto organizer.

Correção necessária: selecionar algoritmo, balanceamento, hiperparâmetros, membros e pesos do ensemble exclusivamente no desenvolvimento. Congelar a configuração e avaliar no teste final sem qualquer realimentação. O modo exploratório pode continuar existindo, mas deve ser identificado como exploração e não produzir automaticamente um “modelo validado”. Esse cuidado é consistente com [Cawley e Talbot, sobre viés de seleção](https://www.jmlr.org/papers/v11/cawley10a.html).

Teste de aceitação: alterar os rótulos do teste final não pode mudar o modelo, seus pesos nem suas predições; apenas as métricas de avaliação podem mudar.

### 5.2. Crítico: unidades incorretas ou incompatíveis entram na matriz

Em `src/echemdb_ml_pipeline/features.py:371`, `_unit_for_column()` usa correspondência parcial de texto. A letra `I` pode corresponder ao `i` de `t_unit`, retornando segundos antes de alcançar `I_unit`.

Verificação executada: para `{'t_unit':'s', 'E_unit':'V', 'I_unit':'A'}`, a consulta da unidade de `I` retornou `s`. Na base processada, 24 curvas de corrente aparecem como `original_s`. O índice de origem informa `I_unit=A` nas 24: isso comprova rotulagem incorreta, mas não comprova, por si só, mudança numérica nesses valores, que já estavam em ampères.

O conversor também não reconhece quatro curvas de Cu: três `mA cm-2` e uma `uA cm-2`. Os testes retornaram os valores inalterados. Para densidade de corrente, 1 mA/cm² corresponde a 10 A/m², enquanto 1 µA/cm² corresponde a 0,01 A/m². O erro de escala pode afetar vários atributos.

Há ainda um problema físico distinto: 24 curvas representam corrente e 308 representam densidade de corrente. Colocar amplitudes em A e A/m² na mesma coluna de atributos não cria uma grandeza comparável. A padronização estatística não substitui a compatibilidade dimensional.

Correções: associar unidades às colunas por chaves exatas; interpretar as variantes efetivamente presentes; exigir tipo de grandeza; converter corrente para densidade somente quando a área e a convenção de normalização estiverem disponíveis e forem compatíveis. Caso contrário, separar modalidades ou comparar representações adimensionais justificadas, mantendo os metadados. Unidade não reconhecida deve impedir o uso quantitativo incompatível.

A API do próprio EchemDB oferece recursos de unidades, filtros e metadados que merecem ser avaliados antes de ampliar o parser manual: [documentação do unitpackage](https://echemdb.github.io/unitpackage/).

### 5.3. Alto: normalização antes da divisão interna

Em `app/app.js:460`, o scaler é ajustado com todos os vetores. A divisão só ocorre em `app/app.js:465`. A imputação também depende dessas médias. Isso incorpora informação da validação no pré-processamento do treino.

Foi executado um exemplo controlado: a média usada pelo scaler foi 104,5, enquanto a média dos exemplos efetivamente presentes no treino era 5. O exemplo confirma o caminho de vazamento, sem estimar o quanto ele afetou a acurácia histórica.

Correção: dividir primeiro; ajustar seleção de atributos, imputação e normalização apenas no treino de cada partição; aplicar a transformação congelada à validação. A documentação do [scikit-learn sobre vazamento de dados](https://scikit-learn.org/1.5/common_pitfalls.html) descreve esse padrão.

### 5.4. Alto: novas curvas não recebem o mesmo processamento do treino

O treinamento do app usa 24 atributos. `extractFeatureRowsFromClean()`, em `app/app.js:989`, retorna somente nove atributos numéricos para CSVs `E,j`: extremos, média, desvio, áreas e cruzamentos de zero. Não calcula os atributos de picos e derivadas.

Os demais 15 atributos são convertidos em valores ausentes e substituídos pela média no escalonamento. Assim, o teste de uma curva bruta segue um caminho diferente do teste de uma linha extraída pelo Python. Além disso, o importador de curva não exige metadados suficientes para harmonizar unidades.

Correção: um extrator canônico compartilhado entre treinamento e inferência. O teste de equivalência deve demonstrar que uma curva enviada ao app produz o mesmo vetor, na mesma ordem e nas mesmas unidades, que o pipeline. Um arquivo sem os dados necessários deve produzir diagnóstico de incompatibilidade, não uma classificação aparentemente completa.

### 5.5. Alto: métricas perfeitas quando não há teste

`evaluatePredictions()`, em `app/app.js:884`, retorna acurácia, acurácia balanceada e macro F1 iguais a 1 quando recebe uma lista vazia. Isso foi reproduzido em Node. O split interno mantém no treino classes com até duas amostras; certos pequenos conjuntos podem ficar sem teste.

Correção: retornar métrica indisponível e suporte zero; bloquear a classificação como validado. A interface deve distinguir “treinado” de “avaliado”.

### 5.6. Alto: a validação agrupada não valida o mesmo Auto organizer

`scripts/group_aware_validation.py:158` avalia sete configurações de classificadores, mas não o ensemble do app. A floresta agrupada usa scikit-learn com 150 árvores; o app usa implementação própria com 15 a 31 árvores, regras de cortes próprias e parâmetros diferentes.

O estudo agrupado já existente é valioso. Entretanto, comparar seus resultados com os do app altera simultaneamente o protocolo e a implementação/modelo. A diferença observada não pode ser atribuída integralmente à separação por DOI, e não demonstra como o próprio Auto organizer generaliza para fontes inéditas.

Correção: avaliar o mesmo conjunto de implementações em divisões por linha e por fonte. Incluir o procedimento completo de seleção automática dentro dos folds internos, mantendo os folds externos somente para avaliação. Documentar se o backend oficial será Python ou JavaScript e testar concordância se ambos forem mantidos.

### 5.7. Alto: rótulos sem suporte entre fontes e métricas não uniformes

O filtro `n >= 5`, em `scripts/group_aware_validation.py:265`, mantém Pd, apesar de todos os seus seis exemplos pertencerem a um único DOI. Quando esse DOI fica fora do treino, o classificador fechado não tem como aprender a classe Pd naquela partição. Seis classes da base apresentam esse problema estrutural.

O script suprime avisos de classes raras e de classes preditas ausentes em `y_true`. Além disso, o JavaScript calcula macro F1 somente sobre as classes reais presentes no teste; o scikit-learn, sem `labels` explícito, considera a união dos rótulos reais e preditos. As métricas não são necessariamente equivalentes.

Correção: definir a tarefa e sua população antes da avaliação. Para classificação fechada, exigir suporte em grupos independentes compatível com as divisões externas e internas; registrar ausências e não descartá-las silenciosamente. Para materiais inéditos, definir uma tarefa separada de rejeição de classe desconhecida. Usar política explícita e uniforme de rótulos, suporte e agregação de métricas.

### 5.8. Alto: descritores precisam de revisão eletroquímica

Em `features.py:255`, `derivada2` é calculada como `np.diff(d1)`, sem dividir novamente pelo espaçamento em potencial. Trata-se de diferença entre inclinações, não da segunda derivada em relação a E. O manuscrito descreve estatísticas de segunda derivada e deve ser corrigido junto com o código.

`inclinacao_media` e `derivada1_media` são idênticas por construção e isso foi confirmado nas 332 linhas. Em métodos de distância, duplicar um atributo altera implicitamente seu peso.

Em `features.py:353`, a largura de pico usa o primeiro e o último ponto de uma máscara global. Pode atravessar outros picos e ramos do voltamograma. A seleção de picos também não separa explicitamente varreduras anódicas/catódicas nem assegura um par redox correspondente.

Correções: segmentar ramos/ciclos preservando a ordem; calcular derivadas com espaçamento e suavização documentados; estimar largura local com cruzamentos interpolados; revisar a associação dos picos; remover redundâncias ou justificar pesos. Validar os descritores com sinais analíticos de resposta conhecida e com curvas anotadas por especialista.

A integral em E tem unidade de corrente vezes potencial, ou densidade de corrente vezes potencial. Ela não deve ser interpretada como carga sem considerar tempo ou velocidade de varredura e o ramo correspondente.

### 5.9. Médio: “confiança” não é probabilidade calibrada

Em `app/app.js:1155–1237`, os modelos usam definições distintas de confiança: distâncias relativas, escores de Naive Bayes, frequência de folhas e votos. O ensemble multiplica seu peso por essas confianças não calibradas. Alguns cálculos usam somente cinco classes candidatas.

Correção: chamar o valor atual de escore de decisão; avaliar calibração em dados de desenvolvimento separados por fonte antes de interpretá-lo como probabilidade. Se houver suporte, incluir Brier/log loss e curvas de calibração. Implementar rejeição por incompatibilidade ou fora de distribuição, com limiares definidos sem consultar o teste final.

### 5.10. Médio: balanceamento e floresta têm semântica própria

A floresta do app aplica pesos tanto na amostragem bootstrap quanto na impureza/voto das folhas (`app/app.js:684` e `1329`). Com sobreamostragem adicional, a compensação das classes pode ocorrer em vários pontos. Isso não equivale automaticamente à opção `class_weight` de uma biblioteca.

Não é possível atribuir causalmente os baixos escores de algumas combinações apenas à dupla ponderação sem ablação. É necessário documentar cada mecanismo e testar seus efeitos separadamente. O contador deve mostrar “configurações”, pois as 28 linhas correspondem a combinações de sete alternativas e quatro balanceamentos, não a 28 algoritmos distintos.

## 6. Como interpretar os resultados atuais

| Resultado salvo | Acurácia | Balanceada | Macro F1 | Uso defensável |
|---|---:|---:|---:|---|
| Ensemble escolhido no teste por linha, sobreamostragem | 91,2% | 74,6% | 67,9% | Exploração; teste influenciou seleção e pesos |
| k-NN sem balanceamento no mesmo teste | 80,9% | 38,7% | 41,3% | Baseline exploratório na mesma divisão |
| Seleção interna, dez repetições, teste por linha fixo | 86,9% | 65,2% | 62,3% | Análise de sensibilidade; mantém dependência de DOI |
| RF scikit-learn sem balanceamento, DOI separado, todas as classes | 78,4% | 46,8% | 37,1% | Benchmark agrupado preliminar |
| k-NN scikit-learn, DOI separado, todas as classes | 74,3% | 48,1% | 38,5% | Benchmark agrupado preliminar |
| RF com pesos, DOI separado, classes com pelo menos cinco curvas | 81,1% | 63,7% | 54,4% | Subconjunto diferente; ainda inclui classe com um DOI |

Fonte: arquivos `statistical_summary.json`, `validated_external_summary.json` e `group_aware_cv_summary.csv` em `statistics` do manuscrito. Valores agrupados são médias de folds salvos, não resultados novos desta auditoria.

A evidência atual não estabelece superioridade geral do Auto organizer. No benchmark agrupado com todas as classes, k-NN tem médias de acurácia balanceada e macro F1 superiores às da RF sem balanceamento, enquanto a RF apresenta maior acurácia geral. A conclusão depende da métrica e precisa de comparação pareada adequada.

Todos esses resultados dependem dos atributos auditados e devem ser recalculados após corrigir unidades e extração. As versões antigas devem ser preservadas como histórico, com identificação clara.

## 7. Estatística necessária para o artigo

O McNemar salvo apresenta sete discordâncias favoráveis ao ensemble e zero favoráveis ao k-NN, com p = 0,015625. O valor não constitui prova confirmatória de superioridade: houve seleção sobre o próprio teste, as curvas são agrupadas por fonte e a comparação foi escolhida entre várias configurações.

O bootstrap estratificado atual reamostra linhas dentro de cada classe. Uma classe com uma única curva sempre repete a mesma observação; não há como estimar a diversidade de futuras curvas dessa classe a partir dessa reamostragem. Os intervalos resultantes não incorporam adequadamente a incerteza entre publicações nem a seleção do vencedor.

Plano recomendado:

1. Fixar acurácia balanceada ou macro F1 como métrica primária antes dos novos experimentos; reportar a outra e acurácia geral como complementares.
2. Usar validação cruzada aninhada por fonte. No nível interno, selecionar pré-processamento, modelos, pesos e hiperparâmetros; no externo, medir o procedimento completo. A [documentação de validação aninhada](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) apresenta a distinção entre seleção e avaliação.
3. Salvar predições fora do treino com ID, DOI, repetição, fold, rótulo real, predito e escore. Calcular também métricas agrupadas a partir das predições completas de cada repetição, com política fixa de classes.
4. Comparar métodos nos mesmos grupos e apresentar diferenças pareadas de desempenho com intervalos. Considerar bootstrap/permutação por publicação ou desenho hierárquico justificado; registrar quando grupos reamostrados não permitem certa métrica.
5. Não tratar 50 folds sobrepostos como 50 experimentos independentes. Desvio padrão dos folds e percentis de dez repetições não são, automaticamente, intervalos de confiança populacionais.
6. Predefinir comparações primárias e tratar multiplicidade nas análises secundárias. Não buscar significância testando repetidamente o mesmo conjunto.
7. Separar um novo teste final por publicações ou por campanha experimental, após congelar o protocolo. O conjunto de 68 curvas, consultado repetidamente, deve permanecer como desenvolvimento exploratório.
8. Dimensionar a coleta pela precisão desejada, distribuição das classes, número de fontes e correlação intrafonte. Não fixar um número arbitrário de curvas como garantia de publicação.

Um resultado negativo bem explicado pode ser publicável: por exemplo, demonstrar que o aparente benefício de um ensemble desaparece quando fontes e unidades são controladas. A afirmação precisa corresponder aos dados.

## 8. Definir a pergunta de pesquisa e a contribuição

O sistema atual é predominantemente uma plataforma de processamento e classificação de dados existentes. Não foi identificado um solucionador físico gerando voltamogramas a partir de parâmetros eletroquímicos. “Simulador” pode permanecer como nome do projeto, mas o artigo deve distinguir plataforma analítica, modelo preditivo e simulação física.

Há uma pergunta prática a esclarecer: por que inferir o material de um eletrodo que normalmente já é conhecido durante o experimento? Aplicações possíveis incluem triagem de metadados, identificação de inconsistências e recuperação assistida de rótulos. Essas são hipóteses de uso que precisam de demonstração, não benefícios já comprovados.

Pergunta central sugerida: “Em que condições uma plataforma de análise de voltamogramas consegue transferir informação entre fontes experimentais heterogêneas e identificar quando sua classificação não é confiável?”

Hipóteses testáveis:

- H1: a harmonização dimensional e a representação dos ramos melhoram a generalização entre fontes, em relação ao processamento atual corrigido apenas estruturalmente.
- H2: o procedimento de seleção automática oferece benefício mensurável sobre um classificador único bem ajustado, com o mesmo orçamento de busca.
- H3: indicadores de qualidade e rejeição identificam entradas incompatíveis e reduzem erros nas previsões aceitas, com perda de cobertura explicitada.
- H4: parte do desempenho aparente é explicada por condições de aquisição e origem, além da informação associada ao material.

Não basta renomear votação ponderada como técnica nova. A contribuição pode ser metodológica e de aplicação, desde que haja uma lacuna demonstrada, protocolo reutilizável e evidência independente.

## 9. Experimentos e ablações com maior retorno científico

| Experimento | Comparação controlada | O que esclarece |
|---|---|---|
| Protocolo de separação | Mesmos modelos em divisão por linha e por DOI | Quanto a conclusão depende da origem das curvas |
| Harmonização | Unidades corrigidas, modalidades separadas e representação adimensional | Sensibilidade à compatibilidade física |
| Atributos | Conjunto atual revisado, sem redundâncias, atributos por ramo | Valor das escolhas de extração |
| Representação | Descritores versus vetores por ramo em potencial | Se a forma da curva acrescenta informação |
| Contexto | Curva apenas, metadados apenas, curva + metadados | Possíveis atalhos por condições experimentais |
| Balanceamento | Nenhum, pesos, reamostragem dentro do treino | Ganho real para classes minoritárias |
| Ensemble | Melhor modelo simples versus combinação congelada | Valor adicional do Auto organizer |
| Robustez | Ruído, densidade de pontos, pequenas perturbações justificadas | Sensibilidade à digitalização e aquisição |
| Transferência | Publicação, campanha, instrumento ou laboratório inéditos | Generalização operacional |
| Rejeição | Erro versus proporção de previsões aceitas | Utilidade da indicação “inconclusivo” |

Nenhuma ablação deve comparar populações diferentes sem explicitar a mudança. Perturbações e escalas de ruído devem ser fundamentadas na aquisição, e não escolhidas para favorecer um modelo. Deriva, deslocamento de referência e mudança de eletrólito não são sempre transformações que preservam o significado do sinal.

Para os modelos, incluir baselines simples (classe majoritária, regressão logística, k-NN) e alternativas tabulares (SVM, RF e gradient boosting). Usar bibliotecas consolidadas e orçamento comparável. SVM já existe no módulo Python exploratório `ml.py`, mas não participa das comparações do app ou do benchmark agrupado auditado. Aprendizado profundo não é requisito para esse artigo.

## 10. Metadados, física e coleta

Registrar por curva: grandeza e unidade, eletrodo de referência, material e orientação do eletrodo de trabalho, área e convenção de normalização, eletrólito e concentração, pH, temperatura, velocidade de varredura, número de ciclos, origem/digitalização e série experimental. Não inventar valores ausentes.

Converter mV para V não harmoniza eletrodos de referência. Toda conversão entre escalas deve exigir contexto suficiente e manter rastreabilidade. Também não é correto remover automaticamente dependências de velocidade de varredura, pois mecanismos diferentes podem responder de formas diferentes.

Separar ramos antes de interpolar em potencial. A interpolação atual por índice preserva a ordem do laço, mas não garante alinhamento físico entre curvas com potenciais iniciais, número de ciclos e amostragem diferentes. Interpolar globalmente em E após ordenar todos os pontos também não é solução, pois pode colapsar os dois ramos.

Para ampliar a base, priorizar diversidade de fontes em vez de apenas novas curvas do mesmo artigo. Pd, Ni, Pb, Rh, Ru e Fe precisam de fontes adicionais para avaliação fechada entre publicações; Co, Cu e Ir também têm cobertura limitada. Se a expansão não for viável, reduzir explicitamente a população-alvo e manter as classes insuficientes como análise exploratória ou teste de rejeição.

Uma campanha própria deve incluir eletrodos/preparações independentes, dias distintos, protocolo documentado e, quando possível, outro instrumento ou laboratório. Repetições do mesmo eletrodo não devem ser dispersas entre treino e teste como se fossem experimentos independentes. A coleta externa deve ocorrer depois de congelar as escolhas do modelo, ou ter suas partes de desenvolvimento e avaliação formalmente separadas.

## 11. Melhorias do app que sustentam a ciência

| Prioridade | Funcionalidade | Evidência verificável |
|---|---|---|
| Essencial | Motor canônico de extração e inferência | Mesmo CSV gera os mesmos atributos e predições em todos os caminhos |
| Essencial | Validador de unidades e metadados | Entrada incompatível identificada antes da classificação |
| Essencial | Separação explícita entre desenvolvimento e teste final | Teste final não altera a configuração do modelo |
| Essencial | Auditoria de fontes e duplicações | IDs e grupos compartilhados detectados e registrados |
| Essencial | Registro de experimento | Dados, versão, configuração, seeds, splits e predições exportáveis |
| Essencial | Estado “não avaliado” | Nenhuma métrica perfeita para suporte zero |
| Alta | Inspeção dos picos/ramos | Curva original e processada com decisões do extrator sobrepostas |
| Alta | Indicador de cobertura e rejeição | Predições inconclusivas identificáveis e mensuráveis |
| Alta | Relatório reprodutível | Tabelas e figuras do artigo regeneradas por um comando |
| Posterior | Melhorias visuais e novos algoritmos | Usabilidade, custo e benefício medidos após corrigir a metodologia |

Na inspeção realizada não foi encontrada uma suíte dedicada de testes automatizados do projeto. O arquivo `create_test_split.py` cria uma divisão de dados; não substitui testes do software. Também não foram encontrados arquivo de licença do projeto ou lockfile de dependências no escopo pesquisado. As pastas do simulador e do artigo aparecem como não rastreadas no repositório pai; isso não exclui cópias externas, mas não fornece rastreabilidade local de versões para o artigo.

Os testes prioritários devem cobrir conversões, separação de grupos, ausência de influência do teste no treino, cálculo das métricas, paridade dos atributos, exportação/importação de modelo e reprodução das tabelas. Versões exatas de dependências, licença compatível, instruções limpas e um pacote público versionado são entregas de reprodutibilidade.

## 12. Estado da arte e manuscrito

A bibliografia deve demonstrar conhecimento dos trabalhos diretamente relacionados. Uma meta numérica de referências não garante qualidade. Cada referência deve sustentar uma afirmação verificável e corresponder ao escopo do estudo.

Há um trabalho recente particularmente relevante: DUCK, publicado em Digital Discovery em 2026, apresenta uma plataforma para organização, análise e exploração de dados de voltametria cíclica com ontologia, grafo de conhecimento e interface web. Foi demonstrado em dados de laboratórios tradicionais e automatizados. Portanto, interface, organização de curvas e apelo FAIR, isoladamente, não são diferenciais suficientes. Fonte primária: [artigo DUCK, DOI 10.1039/d6dd00019c](https://www.sciencedirect.com/org/science/article/pii/S2635098X26000586).

O EchemDB também já possui infraestrutura de gerenciamento e interoperabilidade. O artigo deve separar claramente o que reutiliza do que acrescenta: [Engstfeld e colaboradores, Data Science Journal, 2025](https://datascience.codata.org/articles/10.5334/dsj-2025-013).

Preparar uma tabela de trabalhos relacionados com problema, dados, unidade de independência, representação, método, teste externo, código disponível e limitação. Comparar métricas numericamente apenas quando tarefas e populações forem comparáveis. Estudos de classificação de mecanismos não são baselines diretos de classificação de materiais.

Revisões necessárias no texto:

1. Reescrever o resumo a partir do protocolo corrigido e da contribuição principal; os 91% devem permanecer apenas como resultado exploratório histórico, se forem úteis à narrativa.
2. Especificar release exata da base, origem dos 332 registros, exclusões, unidades e distinção entre 83 DOIs e 84 strings de referência.
3. Apresentar equações, unidades e definições dos atributos; corrigir a descrição da segunda derivada e das larguras de pico.
4. Identificar as implementações JavaScript e scikit-learn, seus parâmetros e populações. Evitar apresentar resultados de modelos diferentes como um experimento controlado apenas sobre o split.
5. Trocar “28 técnicas” por “28 configurações” e identificar exatamente quais alternativas são equivalentes ou diferentes.
6. Reorganizar resultados em qualidade dos dados, validação principal, ablações, robustez e teste externo; mover rankings exploratórios extensos para suplemento.
7. Discutir resultados negativos e classes sem suporte. Um acerto em uma amostra não demonstra desempenho consolidado.
8. Regenerar automaticamente figuras/tabelas após cada versão final do benchmark.
9. Conferir referências primárias, metadados bibliográficos, atribuição dos dados, financiamento, contribuições e disponibilidade dos artefatos antes da submissão.

Figuras mais úteis: cadeia de medição e avaliação; distribuição de curvas e fontes por classe; efeitos do pré-processamento; comparação pareada dos modelos sob protocolo comum; matriz de confusão principal; ablações; robustez e rejeição. Capturas de tela do app podem ilustrar a ferramenta, mas não substituir evidência experimental.

## 13. Estratégia de periódicos

Os nomes abaixo são candidatos por escopo, não certificações de Qualis ou promessas de aceitação. A classificação histórica, quando exigida, ainda precisa ser conferida por ISSN e ciclo, e a aderência atual deve ser discutida com o programa.

| Candidato | Aderência possível | O que falta demonstrar |
|---|---|---|
| IEEE Transactions on Instrumentation and Measurement | Metodologia de medição, processamento e avaliação de sinais | Contribuição própria em medição, consistência física, incerteza e validação independente |
| IEEE Sensors Journal | Aplicação em sensores e processamento de sinais de sensores | Problema concreto de sensoriamento e impacto mensurável no sistema |
| Sensors | Sensores químicos, quimiometria e processamento de sinais | Aplicação bem delimitada, reprodutibilidade e comparação científica suficiente |

O [escopo oficial do IEEE TIM](https://ieee-ims.org/publication/ieee-tim) inclui desenvolvimento e avaliação de instrumentação e métodos para aquisição, processamento e representação de medições. Isso favorece uma contribuição metrológica demonstrada, e não apenas uma lista de classificadores.

O [IEEE Sensors Journal](https://ieee-sensors.org/ieee-sensors-journal/for-authors/) usa formato e instruções próprios; o template MDPI atual precisaria ser adaptado. O [escopo de Sensors](https://www.mdpi.com/journal/sensors/about) inclui sensores químicos, quimiometria e processamento de sinais. Em ambos os casos, a conexão do estudo com sensoriamento deve ser demonstrada.

Measurement e Electrochimica Acta também podem ser investigadas conforme a contribuição se concentre em metrologia ou conhecimento eletroquímico. As páginas oficiais de escopo dessas duas revistas não puderam ser recuperadas nesta consulta; não foram usados sites imitadores nem atribuídos estratos, quartis ou custos sem verificação.

A revista deve ser escolhida depois de definir a contribuição e o protocolo. O fato de o manuscrito já estar em MDPI não deve determinar o destino editorial.

## 14. Plano de execução por dependência

| Etapa | Entrega | Critério de conclusão |
|---|---|---|
| 1. Integridade | Conversor e extrator corrigidos, esquema de entrada e testes | Nenhuma unidade incompatível aceita silenciosamente; atributos equivalentes entre treino e inferência |
| 2. Base auditada | Inventário por material/fonte, duplicações e metadados | População-alvo definida e limitações de suporte registradas |
| 3. Avaliação canônica | Pipeline único com seleção aninhada e grupos | Zero sobreposição de grupos; pesos e hiperparâmetros independentes do teste externo |
| 4. Experimentos | Baselines, ablações, predições por fold e análise de incerteza | Comparações pareadas reprodutíveis, incluindo resultados desfavoráveis |
| 5. Transferência | Teste final por fonte ou campanha inédita | Evidência de desempenho e limites na população de uso definida |
| 6. Submissão | Manuscrito revisado, suplemento, código e dados versionados | Todas as afirmações ligadas a resultados reproduzíveis e escopo editorial adequado |

A coleta de novas fontes pode começar em paralelo à etapa 1, com protocolo e destinação dos dados registrados. O processamento definitivo e a decisão de modelo devem aguardar a cadeia corrigida. O cronograma depende principalmente do acesso a dados independentes e da capacidade experimental; não há prazo ou número de amostras que garanta aceitação.

## 15. Decisão recomendada

Não submeter a versão atual como demonstração de um classificador superior e validado para doze materiais. O próximo trabalho deve começar por unidades, paridade da extração e isolamento entre desenvolvimento e teste, antes de qualquer busca adicional de acurácia.

Depois dessas correções, executar o benchmark com o mesmo motor sob separação por fontes e seleção aninhada. Se o ganho do Auto organizer se mantiver, documentar seu efeito e custo; se não se mantiver, reformular a contribuição em torno das condições de generalização e da qualidade de dados. Uma pesquisa transparente sobre esses limites pode ser mais relevante do que uma alegação de alta acurácia que não resiste à auditoria.

As prioridades propostas aumentam a defensabilidade do trabalho para revisão por pares. A decisão editorial final dependerá da originalidade demonstrada, da qualidade da evidência e da adequação à revista escolhida.
