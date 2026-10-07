# Revisao do prompt original

## Pontos fortes

- Define claramente o dominio: eletroquimica, voltametria ciclica, dados do EchemDB e aprendizagem de maquina.
- Lista etapas relevantes de um fluxo cientifico: carregamento, limpeza, atributos, modelos, validacao, visualizacoes e relatorio.
- Inclui regras importantes contra invencao de dados e mistura indevida de unidades.
- Ja especifica arquivos esperados, o que facilita transformar o prompt em projeto executavel.

## Problemas praticos

- O escopo esta muito amplo para uma unica execucao sem uma versao fixa dos dados.
- A fonte `echemdb/electrochemistry-data` e citada, mas nao ha URL, versao, commit, tag ou contrato de schema.
- A estrutura real dos arquivos nao e especificada; sem isso, o leitor precisa inferir colunas e metadados.
- O prompt pede muitos modelos mesmo quando a base pode ser pequena, desbalanceada ou sem rotulos suficientes.
- A interpolacao por potencial pode distorcer voltamogramas ciclicos, porque a curva frequentemente tem ramos de ida e volta para o mesmo potencial.
- A padronizacao de unidades precisa diferenciar corrente de densidade de corrente; converter sem informacao de area do eletrodo pode gerar erro fisico.
- A deteccao de picos precisa de criterios de confiabilidade, caso contrario maximos e minimos espurios podem entrar no modelo.

## Melhorias aplicadas

- Transformei o pedido em um prompt operacional com entradas, saidas e criterios de aceite.
- Separei tarefas obrigatorias de tarefas condicionais dependentes de dados suficientes.
- Especifiquei comportamento quando faltam bibliotecas, metadados, unidades ou rotulos.
- Adicionei uma decisao metodologica para representar curvas completas pela ordem de aquisicao, preservando o ciclo.
- Gerei um prototipo Python que cria tabelas, atributos, vetores interpolados, graficos quando possivel e relatorio tecnico.

