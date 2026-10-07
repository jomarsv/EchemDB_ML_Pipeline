# Integridade cientifica v2

Implementacao: 17/09/2026. Contrato: `echemdb-features-v2`.
Esta etapa corrige o processamento e as fronteiras de avaliacao; nao constitui
validacao experimental, estudo estatistico conclusivo ou garantia de publicacao.

## Dados regenerados

Fonte local: `../echemdb-data-0.8.4/data/generated`.
Saida nova: `outputs/scientific_v2`; os CSVs e resultados historicos foram preservados.
332 curvas validas: 308 de densidade de corrente em A/m2 e 24 de corrente em A.
Potencial em V. Quatro curvas de densidade em unidades baseadas em cm2 foram convertidas.
O erro que associava a unidade de tempo a coluna I foi removido por correspondencia exata.

Separacao reproduzivel (semente 20260917), por DOI/publicacao:

| Conjunto | Curvas | Fontes | Densidade | Corrente |
| --- | ---: | ---: | ---: | ---: |
| Desenvolvimento | 264 | 68 | 241 | 23 |
| Teste separado | 68 | 15 | 67 | 1 |

Intersecoes de DOI, ID e hash de curva entre esses conjuntos: zero.
Arquivos especificos por modalidade sao gerados em `outputs/scientific_v2/testes`.
O fracionamento aproximado de 20% preserva ao menos uma amostra de cada classe/modalidade
no desenvolvimento, sem quebrar grupos. Nao garante classes equilibradas no teste.

No teste de densidade nao ha Co, Fe, Ni, Pd, Rh, Ru ou Pb. Nao se pode atribuir desempenho
de generalizacao a essas classes. O teste de corrente tem apenas uma amostra.
Ha um par de curvas com hash identico dentro da base; permanece na mesma particao
e nao foi removido automaticamente. Sua origem deve ser revisada antes do benchmark.

IMPORTANTE: esta e uma redivisao da base ja explorada historicamente, nao uma nova coleta
cega. O isolamento computacional foi corrigido, mas nao apaga a exposicao previa aos dados.
Uma validacao confirmatoria exige novas fontes/experimentos mantidos fora do desenvolvimento.

## Unidades e descritores

Conversoes estritas: V/mV; A/mA/uA/nA; A/m2, mA/cm2, uA/cm2 e notacoes equivalentes
com expoente inverso, incluindo `mA cm-2`. Unidades desconhecidas ou dimensionalmente
incompativeis geram exclusao/erro. Nao se converte corrente em densidade sem area conhecida.

23 descritores candidatos (a disponibilidade no treino determina os efetivamente usados):

| Familia | Definicao e dimensao |
| --- | --- |
| Faixa de potencial | Minimo/maximo, V |
| Estatisticas do sinal | Minimo, maximo, media, desvio amostral, A ou A/m2 |
| Areas | Soma trapezoidal orientada em E e soma absoluta por incremento, sinal vezes V; nao sao carga eletrica |
| Picos | Extremos locais em ramos crescentes/decrescentes, potencial em V e amplitude nas unidades do sinal |
| Larguras | Cruzamentos interpolados a meia altura relativos a mediana do ramo, apenas na vizinhanca contigua do pico, V |
| Separacao/razao | Somente em ciclo com dois ramos e ambos os picos detectados; V e adimensional |
| Cruzamentos de zero | Mudancas de sinal na sequencia de aquisicao, contagem |
| Primeira derivada | Secantes por ramo: dS/dE; media, desvio, minimo, maximo |
| Segunda derivada | Diferenca das secantes dividida pela distancia entre pontos medios em E: d2S/dE2; media e desvio |

Retirado `inclinacao_media`, redundante com `derivada1_media`. Reversoes e patamares
nao sao atravessados nas derivadas. Picos ausentes permanecem ausentes, nao viram zero.
Os nomes anodico/catodico descrevem a direcao do ramo, nao comprovam atribuicao quimica
nem pareamento de um casal redox. A deteccao e geometrica/heuristica, com suavizacao local.
A mediana como linha de base e o resumo de multiplos ramos exigem validacao por especialista.

Referencias de potencial (RHE, SHE, Ag/AgCl etc.) NAO foram automaticamente harmonizadas.
Converter mV para V nao equivale a converter eletrodos de referencia. Area eletroativa,
velocidade de varredura, eletrólito, pH e ciclos ainda precisam de controle no estudo.
As curvas interpoladas usam ordem de aquisicao; nao devem ser chamadas de curva em E.

## Paridade de treino e inferencia

`features.py` e o extrator unico. O pipeline e `POST /api/features` chamam a mesma funcao.
O navegador nao reconstrói um subconjunto de atributos nem completa silenciosamente
um CSV antigo. Recebe todas as 23 colunas, versao, unidades, modalidade, ID e hash SHA-256
dos pares E/sinal convertidos. Valores ausentes permitidos mantem o mesmo tratamento.
O hash identifica igualdade exata, nao similaridade, copias redigitalizadas ou arredondadas.

CSV bruto: colunas E e j (ou I), id_entrada quando houver varias curvas, unidades e tipo_sinal
nos metadados ou explicitamente nos controles. Teste rotulado exige DOI/grupo_origem.
Nao renomeie a origem para contornar o bloqueio. Metadados declarados continuam sendo
responsabilidade do pesquisador; o aplicativo nao autentica a publicacao.

Imputacao pela media e escala sao ajustadas somente nos dados de treino da validacao
de desenvolvimento. Selecao por disponibilidade tambem usa apenas essa particao.
Sobreamostragem e pesos sao aplicados somente ao treino. No reajuste final, usa-se todo
o desenvolvimento, mantendo atributos, tecnica, numero de arvores e pesos do ensemble
selecionados previamente. A inferencia utiliza os parametros desse modelo congelado.

## Isolamento e interpretacao

- Validacao de desenvolvimento separada por fonte, antes do ajuste do preprocessamento.
- Top 3 e pesos do ensemble sao definidos no desenvolvimento; teste nao os altera.
- Avaliacao externa exige fontes, IDs e hashes nao presentes em todo o desenvolvimento.
- O ranking externo nao reordena candidatos nem escolhe o modelo ativo.
- Modelo exportado registra versao, atributos, escala, modalidade e proveniencia das particoes.
- Acuracia, acuracia balanceada e macro-F1 de conjunto vazio sao indefinidos, nao 100%.
- Macro-F1 inclui classes verdadeiras e preditas; recall medio considera classes com suporte real.
- Escores dos classificadores nao sao probabilidades calibradas.

A acuracia apresentada em Aprendizagem e de desenvolvimento, usada para selecao,
portanto otimista; nao e estimativa imparcial de desempenho final. Alterar configuracoes
apos examinar o teste transforma esse conjunto em desenvolvimento do pesquisador,
mesmo que o software nao o use automaticamente. O protocolo deve ser predefinido.
As implementacoes JS e scikit-learn continuam sendo modelos diferentes; resultados
de um nao podem ser atribuidos ao outro no artigo. Os scripts historicos de figuras/artigo
nao foram migrados nesta etapa. Nao os use para produzir novas conclusoes com a v2.

## Verificacao

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/scientific-integrity.test.cjs
```

Testes de conversoes, unidade I versus tempo, rejeicao de unidades desconhecidas,
derivada analitica em grade irregular, reversoes/patamares, largura local, direcao dos picos,
paridade de extracao e roundtrip SI, API HTTP, fonte disjunta, normalizacao sem vazamento,
rejeicao de schema antigo e sobreposicoes, congelamento independente dos rotulos externos,
metricas vazias e execucao das 28 configuracoes. Tambem ha teste com os CSVs reais regenerados.

Proxima etapa: revisar metadados eletroquimicos e duplicatas; estabelecer uma implementacao
de referencia; definir validacao agrupada aninhada, incerteza por fonte, baselines e nova
validacao externa. As metricas historicas (incluindo 91%) nao validam o protocolo corrigido.
