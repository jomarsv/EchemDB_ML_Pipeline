# Curadoria de referencias, duplicatas e fontes

Auditoria executada em 18/09/2026 sobre scientific_v2 e os metadados locais
de electrochemistry-data 0.8.4. Esta etapa controla problemas conhecidos;
nao declara concluida a harmonizacao eletroquimica nem a coleta de novas fontes.

## Resultados e limites

- 332 curvas auditadas; 330 retidas na escala nativa e duas em quarentena.
- Desenvolvimento: 262 curvas (239 de densidade e 23 de corrente).
- Teste reservado: 68 curvas, sem mudanca de composicao.
- Nenhuma conversao de potencial aplicada e nenhuma fonte nova adicionada.
- Os arquivos originais, modelos e resultados anteriores foram preservados.
- O piloto SCE anterior nao contem o par em quarentena e nao foi reexecutado.

## Referencias de potencial

O registro compara a referencia declarada no eixo do recurso com a descricao
da figura; ausencia ou divergencia bloqueia a curva. Nenhuma divergencia foi
encontrada nestas 332 entradas. Isso nao valida a calibracao do experimento.
O eletrodo fisico e registrado separadamente: um experimento com Ag/AgCl pode
legitimamente ter um eixo ja convertido para RHE pelos autores.

Inventario antes da quarentena:

| Situacao | Curvas | Conduta |
|---|---:|---|
| SHE declarado | 18 | Manter valores originais |
| RHE declarado | 163 | Manter RHE; nao presumir pH/temperatura para converter |
| Ag ou Pt como referencia | 22 | Separar por DOI; exigir calibracao local |
| Outras referencias | 129 | Manter escala; revisar solucao interna e condicoes |

Nao foi aplicada uma constante universal de conversao. A temperatura e as
condicoes da referencia precisam ser conhecidas; ver a documentacao primaria
da [Gamry sobre SCE e temperatura](https://www.gamry.com/resources-2/electrochemical-calculators-tools/saturated-calomel-electrode-calculator/).
Metadados de eletrolito, referencia fisica, comentario da figura e hashes
dos arquivos estao em curation_registry.csv para revisao humana.

IMPORTANTE: development_native.csv e held_out_native.csv sao exportacoes de
curadoria, nao coortes harmonizadas prontas para importar no app. Contem
varias escalas. Filtrar por grandeza e referencia antes de modelar; rotulos
iguais ainda exigem verificacao das condicoes. Os estratos Ag|DOI e Pt|DOI
nao podem ganhar independencia pela simples adicao de curvas de outro DOI.
Nesse caso a prioridade e calibracao, nao completar mecanicamente a fila.

## Duplicata confirmada

Entradas bi_2018_minimizing_1_f3b_black e bi_2018_minimizing_1_f3b_blue:

- Os dois CSVs brutos sao identicos, inclusive SHA-256, com 7.408 linhas cada.
- Hash bruto: b5f07881b2cac39d23531fde7df8996716144d49b998c452ff8c2e7214b11d24.
- Os metadados locais declaram agua a 3014 ppm (preta) e 22800 ppm (azul).
- Ambas pertencem ao mesmo DOI e ao desenvolvimento.
- Ambas foram excluidas da nova selecao; nao ha evidencia para escolher qual
  das duas representa corretamente a serie experimental.

Fonte para conferir figura e material suplementar:
[Bi et al., Nature Communications](https://www.nature.com/articles/s41467-018-07674-0).
Antes de reintegrar, recuperar a curva correta ou redigitalizar a figura com
registro de proveniencia e revisao. Nenhuma correcao foi submetida ao EchemDB.
A triagem usa duplicatas exatas; nao garante ausencia de quase duplicatas.

## Fontes raras

Fontes independentes no desenvolvimento, apenas densidade de corrente:

| Classe | DOIs, todas as referencias | Lacuna por referencia |
|---|---:|---|
| Co | 2 | SCE e SHE tem um DOI cada |
| Cu | 2 | RHE e MSE-sat tem um DOI cada |
| Ir | 1 | RHE/SCE pertencem a uma unica fonte |
| Fe, Ni, Pb, Pd, Rh, Ru | 1 por classe | Sem diversidade de publicacoes |

Uma meta inicial de planejamento e quatro fontes por classe e estrato:
nesses casos sao necessarias pelo menos tres fontes adicionais compativeis.
Quatro nao e garantia de viabilidade dos folds ou precisao estatistica.
Repeticoes, sobreamostragem e figuras do mesmo artigo nao contam como novas
fontes. As publicacoes do teste reservado nao entram nesse total de treino.

collection_queue.csv registra as lacunas por classe, grandeza e referencia,
com campos para DOI candidato, URL, licenca, condicoes, revisor e decisao.
Para admitir dados: verificar o material do eletrodo de trabalho (nao o metal
dissolvido), referencia, unidade, area quando necessaria, aquisicao/digitalizacao,
licenca e independencia do DOI; depois verificar hashes e congelar a particao.

## Coleta: triagem inicial

O [catalogo oficial EchemDB](https://www.echemdb.org/cv/) anuncia o dataset
0.9.2, enquanto esta auditoria usa 0.8.4. A proxima aquisicao prioritaria e uma
copia versionada dessa distribuicao, comparada por DOI e hash: uma nova versao
nao implica automaticamente novas fontes. Ela ainda nao foi importada.

Outras pistas, ainda NAO elegiveis nem contadas como dados:

- [Rh(111), estudo original de voltametria](https://www.sciencedirect.com/science/article/pii/0022072888801025):
  conferir curvas de Rh limpo, DOI ja existente, escala e direitos de extracao;
  nao misturar curvas recobertas com Ag na classe Rh puro.
- [Dados FeCoNiCu](https://doi.org/10.48733/IFJPAN/VV0KPY): a descricao informa
  sais medidos sobre ouro; nao usar os nomes dos sais como rotulos Fe/Co/Ni
  do eletrodo. Nao admitido para suprir essas classes.
- [Ru/Pt(111)](https://pubs.acs.org/doi/10.1021/acssuschemeng.2c04584):
  sistema de superficie modificada; nao admitir automaticamente como Ru puro.

## Reproducao

Na raiz do projeto, executar em um diretorio de saida NOVO:

```powershell
.\.venv\Scripts\python.exe scripts/curate_scientific_inputs.py --output outputs/scientific_curation_v2
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_*.py
```

O script recusa sobrescrever uma saida existente, verifica isolamento por ID,
fonte e hash, e grava manifest.json com hashes das entradas e saidas. Os
registros individuais incluem hashes dos arquivos brutos e sidecars. Esta
curadoria nao altera automaticamente o app nem reajusta modelos existentes.
