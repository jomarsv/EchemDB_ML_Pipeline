# Revisao manual das novas curvas

Foi criada uma planilha de triagem para as 26 entradas novas da release 0.9.2.
Ela nao altera o conjunto de treinamento e todas as linhas começam como
`pendente_revisao_humana`, com `aceitar_treinamento=False`.

Arquivos:

- `outputs/release_review_0_9_2/revisao_manual_26_curvas.csv`: uma linha por curva.
- `outputs/release_review_0_9_2/revisao_por_fonte.csv`: resumo por DOI, classe e referencia.
- `outputs/release_review_0_9_2/manifest.json`: escopo da revisao.

Para cada curva, conferir no artigo e no suplemento: eletrodo de trabalho,
classe do material, referencia fisica e referencia do eixo, unidades, figura e
curva, eletrólito, temperatura, licença e se o DOI representa uma fonte
independente. O metal presente no sal ou no eletrólito nao deve ser usado como
rotulo do eletrodo.

Uma entrada só pode ser marcada como aceita depois que o revisor preencher
`decisao_final`, `referencia_verificada`, `licenca_verificada` e `observacoes`.
Depois disso, uma etapa separada deve recalcular hashes, curadoria e partições.
Não editar os CSVs de `scientific_v2` nem os resultados já publicados.

## Compatibilidade com o modelo atual

O arquivo `compatibility_decisions.csv` separa as entradas por modalidade.
Há 6 fontes de densidade de corrente, 2 fontes de corrente absoluta e 1 fonte
de Ru em densidade. A fonte de Cu com corrente absoluta não declara área do
eletrodo de trabalho, portanto não pode ser convertida de forma rastreável para
A/m2. A fonte de Pt declara área, mas deve ser convertida em uma etapa própria,
com registro da transformação e sem misturar o resultado com a corrente
absoluta histórica.

A conversão controlada da fonte Pt foi preparada em
`outputs/release_review_0_9_2/pt_density_conversion_v1/`. A área declarada é
0,283 cm2, convertida para 2,83e-5 m2, usando `j = i/A`. O arquivo contém os
pontos convertidos e o manifesto da transformação, mas continua como candidato:
é necessário reextrair os descritores, gerar novo hash e obter revisão antes
de qualquer treinamento.
