# Fechamento da analise dos resultados v2

Data da revisao: 2026-10-07. Este documento consolida os artefatos encontrados
no repositorio; nao substitui revisao cientifica dos dados nem reexecucao
confirmatoria.

## Decisao executiva

**Decisao para esta etapa: usar a coorte conservadora da EchemDB 0.8.4, restrita
a densidade de corrente, potencial declarado SCE e classes Ag/Au.** Ela tem uma
auditoria de referencia, uma validacao aninhada por DOI ja executada e nao
depende da admissao ainda nao aprovada da release 0.9.2. O resultado existente
e apenas um piloto exploratorio: 43 curvas, nove fontes, duas classes; Auto
organizer e floresta obtiveram as mesmas 39/43 predicoes corretas (90,7% de
acuracia, 87,8% de acuracia balanceada e 87,8% de macro-F1). Esse piloto nao
prova desempenho confirmatorio e nao pode ser apresentado como generalizacao
para os demais materiais ou como vantagem do Auto organizer sobre a floresta.

A analise, portanto, **nao esta fechada como evidencia definitiva para artigo**.
A escolha acima fecha somente qual coorte deve orientar o proximo trabalho. A
release 0.9.2 e seus resultados ficam em quarentena ate a revisao de proveniencia,
referencias, conversoes e licencas.

## Hierarquia dos resultados

| Artefato | Escopo | Status e uso |
| --- | --- | --- |
| `outputs/scientific_v2` | EchemDB 0.8.4; 332 curvas; separacao inicial 264/68 por fonte | Integridade de unidades e paridade corrigidas, mas os resultados historicos nao foram recalculados pelo protocolo corrigido. Nao citar as metricas antigas como validacao v2. |
| `outputs/density_candidate_0_9_2_v1/nested_expanded_v1` | 203 curvas Ag/Au/Pt, 48 fontes no desenvolvimento, CV aninhada agrupada em 3 folds externos e 2 internos | Melhor estimativa interna candidata disponivel; exploratoria, nao confirmatoria. |
| `outputs/density_candidate_0_9_2_v1/external_expanded_frozen_v1` | 65 curvas Ag/Au/Pt, 15 fontes; tres bundles congelados | Melhor stress test externo candidato disponivel. Relatar cada bundle separadamente; nao combinar as tres linhas como se fossem um modelo ou tres repeticoes independentes. |
| `external_balanced_frozen_v1` e `external_frozen_eligible_v1` | Holdouts menores de 22 e 68 curvas | Analises anteriores/sensibilidade. Nao substituir a avaliacao expandida nem escolher um vencedor com base no teste. |
| `outputs/stage3_nested_sce_v1` | 43 curvas Ag/Au com referencia SCE | Piloto separado e mais antigo; nao representa os resultados v2 nem o desempenho geral do app. |

## Resultado interno aninhado candidato

O conjunto `nested_expanded_v1` contem 203 previsoes out-of-fold de 48 fontes,
para Ag, Au e Pt. A selecao foi feita dentro do desenvolvimento, usando
acuracia balanceada interna e macro-F1 como desempate. O modelo recebeu sete
descritores centrais: faixa de potencial, minimo, maximo, media e desvio do
sinal, area absoluta e area liquida. Portanto, esses numeros nao demonstram
desempenho usando todos os 23 descritores candidatos do extrator v2.

| Metodo avaliado | Acertos | Acuracia | Acuracia balanceada | Macro-F1 |
| --- | ---: | ---: | ---: | ---: |
| Auto organizer (selecao interna por fold) | 188/203 | 92,6% | 90,9% | 89,2% |
| k-NN | 189/203 | 93,1% | 89,0% | 87,8% |
| Floresta aleatoria | 187/203 | 92,1% | 89,5% | 89,3% |
| Ensemble completo | 187/203 | 92,1% | 90,4% | 87,6% |
| Baseline majoritaria | 121/203 | 59,6% | 33,3% | 24,9% |

Leitura: neste piloto, o Auto organizer teve a maior acuracia balanceada entre
as linhas da tabela, mas nao a maior acuracia nem o maior macro-F1. A diferenca
para k-NN e pequena e nao foi acompanhada por intervalo de incerteza ou teste
pareado; nao se deve afirmar superioridade estatistica. O ranking representa
apenas tres materiais relativamente bem suportados e sete descritores.

### Incerteza por fonte

Foi aplicado bootstrap nao parametrico estratificado por classe, reamostrando
DOIs inteiros (4 grupos Ag e 5 grupos Au), com 20.000 replicatas e semente
20261007. Os IC95% abaixo sao percentis 2,5--97,5 das predicoes out-of-fold;
as diferencas sao pareadas, sempre reamostrando os mesmos DOIs para os dois
metodos.

| Estimando | Metrica | Estimativa | IC95% por DOI |
| --- | --- | ---: | ---: |
| Auto organizer | Acuracia | 90,7% | 84,6--97,6% |
| Auto organizer | Acuracia balanceada | 87,8% | 76,5--97,4% |
| Auto organizer | Macro-F1 | 87,8% | 73,7--96,6% |
| k-NN | Acuracia | 74,4% | 59,1--86,7% |
| k-NN | Acuracia balanceada | 61,9% | 53,9--81,4% |
| k-NN | Macro-F1 | 62,8% | 52,6--76,4% |
| Auto menos k-NN | Acuracia | +16,3 p.p. | +3,4 a +33,3 p.p. |
| Auto menos k-NN | Acuracia balanceada | +25,9 p.p. | +2,9 a +38,8 p.p. |
| Auto menos k-NN | Macro-F1 | +24,9 p.p. | +5,4 a +39,6 p.p. |
| Auto menos floresta | Todas as tres metricas | 0,0 p.p. | 0,0 a 0,0 p.p. |

Embora os intervalos condicionais da diferenca Auto--k-NN nao incluam zero,
isso **nao** basta para declarar superioridade: ha apenas nove fontes, os
intervalos condicionam nas predicoes ja produzidas (nao repetem o ajuste e a
selecao de modelos em cada bootstrap) e a base foi historicamente examinada.
Auto organizer e floresta produziram exatamente as mesmas 43 predicoes, logo
nao ha diferenca observada entre esses dois procedimentos neste piloto. Os
intervalos sao exploratorios e nao substituem uma nova avaliacao independente.

O calculo e reproduzivel por `scripts/bootstrap_source_uncertainty.py`; os
resultados e parametros estao em `outputs/stage3_nested_sce_pinned_20261007/`
(`source_bootstrap_ci_final.csv` e `source_bootstrap_ci_final.json`). O ambiente
isolado foi registrado em `requirements-reproducibility.txt`.

## Holdout externo congelado candidato

A particao expandida reservou 65 curvas de 15 fontes (Ag=10, Au=17, Pt=38),
sem sobreposicao declarada de fonte com o desenvolvimento. A curva anomala de
Nishihara foi excluida nesta particao. Nenhum bundle foi reajustado com os
rotulos externos.

| Bundle escolhido no desenvolvimento | Acertos | Acuracia | Acuracia balanceada | Macro-F1 |
| --- | ---: | ---: | ---: | ---: |
| Floresta aleatoria, fold 1 | 61/65 | 93,8% | 91,6% | 90,6% |
| k-NN, fold 2 | 60/65 | 92,3% | 84,7% | 86,1% |
| Ensemble completo, fold 3 | 61/65 | 93,8% | 88,0% | 89,8% |

Os bundles sao tres objetos congelados derivados de folds diferentes e
avaliados no mesmo holdout. A variacao e uma analise de sensibilidade a
selecao/composicao do desenvolvimento, nao uma estimativa de variabilidade de
um unico modelo. Nao selecionar agora o bundle com maior escore externo como
se essa escolha fosse independente do teste.

Nos diagnosticos por classe, Ag e a classe mais fraca/instavel: tem somente
10 curvas externas e 5 fontes na particao, e o recall dos bundles ficou entre
60% e 80%. Au e Pt tiveram recalls altos neste holdout, mas os valores continuam
condicionados a esta particao e ao pequeno numero de fontes independentes.

## Numeros que nao devem ser usados

- Acuracia historica de 91% do split por linha e resultados derivados dos
  antigos 24 descritores: nao validam o contrato v2 nem respeitam a separacao
  por fonte.
- Os valores do holdout de 22 curvas (90,9%, 86,4%, 81,8%) nao sao o resultado
  final depois da expansao e revisao da particao.
- Os valores de 68 curvas nao devem ser misturados com a particao expandida de
  65 curvas; sao protocolos e composicoes diferentes.
- As metricas de selecao interna nao sao teste externo. Escores internos usados
  para escolher hiperparametros ou pesos sao otimistas.
- Os resultados do motor Python nao devem ser atribuidos aos modelos JavaScript
  do aplicativo. Sao implementacoes e configuracoes distintas.
- Nao afirmar identificacao universal de materiais, generalizacao para os 12
  materiais originais, ou validade para corrente absoluta. O holdout expandido
  cobre somente Ag, Au e Pt em densidade de corrente.

## Pendencias que impedem fechar a analise

1. **Aprovar a base e sua proveniencia.** `revisao_manual_26_curvas.csv` ainda
   tem as 26 novas entradas como pendentes e `aceitar_treinamento=False`.
   `source_screening_final_v1.csv` mantem os nove DOIs em revisao integral;
   nenhum foi admitido.
2. **Aprovar as conversoes de Pt.** A conversao de corrente para densidade,
   inclusive a area declarada, exige verificacao da curva, unidade, area,
   licenca e sinalizacao do pesquisador. Nao treinar com conversoes candidatas
   sem esse registro.
3. **Resolver referencias de potencial.** O manifesto da base candidata declara
   que os estratos permanecem nativos e nao harmonizados. Restrinja a analise a
   uma referencia/calibracao comparavel, ou defina e valide uma estrategia
   cientifica para tratar referencias distintas. Nao misturar escalas como se
   fossem equivalentes.
4. **Congelar uma coorte e um protocolo unicos.** Depois das decisoes acima,
   refazer curadoria, hashes, particao por DOI e nested CV com o conjunto final.
   A particao expandida atual e candidata e foi construida antes dos signoffs.
5. **Quantificar incerteza corretamente.** Gerar intervalos por fonte/DOI para
   a estimativa aninhada e intervalos apropriados para o holdout. Com 15 fontes
   e classes de suporte desigual, tratar intervalos como imprecisos; nao usar
   as tres previsoes repetidas do holdout como observacoes independentes.
6. **Reproduzir a analise congelada.** Executar os testes e os scripts a partir
   de uma instalacao documentada, guardar versoes, hashes e comandos, e verificar
   que as tabelas e figuras sao regeneradas sem editar CSVs manualmente.

## Proxima acao operacional

Nao atualizar o manuscrito com as metricas candidatas da 0.9.2. A validacao
aninhada da coorte SCE foi reexecutada em uma pasta nova:
`outputs/stage3_nested_sce_pinned_20261007/`, em ambiente virtual com as mesmas
versoes registradas no piloto (Python 3.12.7, scikit-learn 1.9.0, NumPy 1.26.4,
pandas 2.2.3). As 344 predicoes foram comparadas registro a registro com
`outputs/stage3_nested_sce_v1/`: **zero diferencas**; as escolhas por fold e
metricas agregadas tambem coincidiram exatamente. A reproducao anterior em
versoes mais novas foi preservada separadamente em
`outputs/stage3_nested_sce_reproduction_20261007/`.

Verificacao final: 25 testes Python e 8 testes JavaScript passaram no ambiente
isolado; sem avisos de versao ao carregar os bundles. O Python global continua
incompativel (NumPy 2.2.6 com extensoes binarias antigas de pandas/PyArrow) e
nao foi alterado. Foram calculados intervalos bootstrap por DOI para as metricas
OOF e diferencas pareadas. Ainda falta decidir como apresentar estes resultados
exploratorios no artigo da SoftwareX; eles nao tornam o estudo confirmatorio.
