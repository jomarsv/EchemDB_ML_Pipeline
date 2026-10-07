# Validacao aninhada da base candidata

Foi executado o piloto aninhado somente para Ag, Au e Pt, as únicas classes
com pelo menos duas fontes independentes nos dois lados da partição. O teste
externo candidato permaneceu intocado e não participou da seleção.

O piloto é exploratório: a release 0.9.2 ainda precisa de revisão científica,
e as três curvas de Pt convertidas continuam marcadas como candidatas. Os
resultados não devem ser comparados diretamente aos resultados do artigo até
que a base seja aprovada e a partição seja congelada.

A avaliação dos bundles congelados no holdout está em
`outputs/density_candidate_0_9_2_v1/external_frozen_eligible_v1/`. Ela inclui
Ag, Au e Pt; Cu foi mantido em arquivo separado por possuir somente uma fonte
no teste. Cada dobra externa usa um bundle treinado antes e não reutiliza os
rótulos externos para seleção. As métricas das três dobras não devem ser
concatenadas como se fossem predições de um único modelo.

O diagnóstico por classe está em `external_frozen_eligible_v1/diagnostic_by_class.csv`.
Ag possui somente três curvas externas e recall entre 0 e 0,667 nas três
dobras. Au é mais estável, enquanto Pt varia entre as dobras. A matriz de
confusão foi salva por dobra; não foi criada uma matriz agrupada artificial.

O arquivo `external_frozen_eligible_v1/error_review.csv` lista cada erro com
ID, DOI, faixa de potencial e faixa de sinal. A prioridade é revisar primeiro
as curvas de Ag e as confusões Pt->Au. O resumo por DOI permite decidir se a
instabilidade vem de uma publicação específica ou de falta geral de fontes.

A revisão de `10.1016/0022-0728(94)03803-b` confirmou que o rótulo Pt é
cientificamente coerente: o artigo descreve deposição de Cu sobre eletrodos de
Pt escalonados ([ScienceDirect](https://www.sciencedirect.com/science/article/pii/002207289403803B)).
Entretanto, a curva `nishihara_1995_underpotential_75_f5b_solid` apresenta
densidade entre aproximadamente -17.927 e 22.686 A/m2, enquanto as curvas
irmãs estão na ordem de 10^-3 a 1 A/m2. Ela foi marcada para quarentena e
redigitalização, sem alterar o teste já avaliado e sem refazer o modelo.

A fonte Ag `10.1007/PL00010123` também foi revisada. O artigo descreve uma
eletrodo de prata em NaOH e voltametria cíclica, incluindo formação de óxidos
de prata ([registro bibliográfico](https://www.gu.edu.eg/Scholar/views/view_output.php?id=7031&tab=cited)).
O rótulo Ag foi mantido; não foi encontrada anomalia numérica equivalente à de
Nishihara. A confusão repetida com Au é tratada como falta de diversidade de
fontes/representação, não como motivo para recodificar a classe.

Foi feita uma análise de sensibilidade removendo somente essa curva do holdout.
Os bundles não foram reajustados nem reselecionados; a avaliação original foi
preservada. Os resultados complementares estão em
`external_frozen_clean_holdout_v1/comparison_with_original.csv`.
