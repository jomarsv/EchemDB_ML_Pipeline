# Comparacao da release EchemDB 0.9.2

Auditoria executada em 18/09/2026. A release oficial foi baixada de
[electrochemistry-data 0.9.2](https://github.com/echemdb/electrochemistry-data/releases/tag/0.9.2)
e conferida pelo SHA-256 publicado: `6093b6a2ac10792e8582f69441e883bed6ed4eb662036cb2441edfa064df0354`.
O catalogo EchemDB informa 358 entradas e 93 fontes para essa versao
([catalogo CV](https://www.echemdb.org/cv/)).

## Decisao

A release foi extraida e auditada, mas **nenhuma entrada foi incorporada ao
treinamento**. Isso evita misturar uma representacao atualizada com o conjunto
0.8.4 usado nos resultados anteriores.

| Item | Resultado |
|---|---:|
| Entradas 0.8.4 | 332 |
| Entradas 0.9.2 | 358 |
| Novas entradas | 26 |
| Novos DOIs | 9 |
| Entradas com identidade compartilhada | 332 |
| Curvas com mesmo numero e valores proximos | 271 |
| Curvas com numero de pontos diferente | 36 |
| Modelos treinados com 0.9.2 | 0 |
| Entradas admitidas | 0 |

As 26 entradas novas abrangem 16 curvas de Cu, 6 de Pt e 4 de Ru. Elas sao
boas candidatas para reduzir lacunas, mas continuam pendentes de verificacao
de eletrodo, referencia, unidade, DOI, licenca e independencia da curva.
Nao contar automaticamente o Cu como fonte de uma classe apenas porque o
material aparece no eletrolito ou em uma liga.

## Por que a mistura foi bloqueada

Os 317 registros compartilhados que apresentam mudanca nao podem ser tratados
como a mesma observacao sem uma decisao de proveniencia. Em 36 casos, o numero
de pontos mudou. Em outros, a discretizacao permaneceu com o mesmo tamanho,
mas os valores convertidos de sinal mudaram. Isso pode ser uma correcao de
unidade, uma redigitalizacao ou uma alteracao de metadados; o relatorio local
nao permite atribuir a causa de forma segura.

O caso `bi_2018_minimizing_1_f3b_black/blue` permanece duplicado na release e
continua em quarentena. A 0.9.2 tambem introduz uma curva vermelha relacionada
ao mesmo artigo; isso exige leitura da figura e conferencia com o artigo antes
de reintegrar qualquer uma das tres curvas.

## Arquivos de auditoria

- `outputs/release_0_9_2_audit/`: extracao isolada da release, sem modelos.
- `outputs/release_comparison_0_9_2/release_comparison.csv`: registro por curva,
  sobreposicao com o teste, DOI novo, referencia e decisao de admissao.
- `outputs/release_comparison_0_9_2/support_by_reference.csv`: suporte por
  classe e referencia em cada versao.
- `outputs/release_comparison_0_9_2/numeric_deltas.csv`: diferenca numerica
  entre as curvas compartilhadas.
- `outputs/release_comparison_0_9_2/new_source_candidates.csv`: as 26 curvas
  novas para revisao humana.
- `outputs/release_comparison_0_9_2/manifest.json`: hashes e decisao de
  nao-incorporacao.

## Proximo procedimento

1. Revisar as 26 entradas novas e preencher a fila com referencia fisica,
   potencial, eletrodo de trabalho, condicoes e licenca.
2. Resolver a proveniencia das 317 curvas modificadas, escolhendo uma release
   unica para o artigo ou documentando uma migracao completa.
3. Recalcular a curadoria e as particoes a partir de uma unica versao.
4. So entao refazer a validacao aninhada por fonte e comparar os modelos.

Até essa decisao, os resultados do artigo continuam vinculados ao conjunto
`scientific_v2` e nao devem receber numeros da release 0.9.2.
