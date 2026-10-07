# Triagem bibliografica dos 9 DOIs novos

Foi feita uma primeira verificacao nas paginas primarias dos artigos. O
resultado confirma que os nove DOIs sao fontes reais e que os materiais
esperados aparecem nos artigos, mas isso ainda nao e suficiente para admitir
as curvas no treinamento.

| Classe | Resultado preliminar |
|---|---|
| Cu | 6 DOIs com evidencia de eletrodos/superficies de Cu e voltametria |
| Pt | 2 DOIs com superficies de Pt; revisar se as curvas sao de Pt puro ou estado modificado |
| Ru | 1 DOI com Ru(0001) e voltametria; revisar curvas e condicoes acidas |

Os artigos de Cu incluem superfícies Cu(001), Cu(100), Cu(110), Cu(111) e
eletrodos de cristal único. As fontes primárias descrevem voltametria ou
medições eletroquímicas relacionadas: [Schouten et al. 2013](https://doi.org/10.1016/j.jelechem.2013.03.018),
[Kunze et al. 2003](https://doi.org/10.1016/S0022-0728(03)00115-3),
[Droog e Schlenter 1980](https://doi.org/10.1016/S0022-0728(80)80421-9),
[Jovic e Jovic 2002](https://doi.org/10.2298/JSC0207531J) e
[Huang et al. 2017](https://doi.org/10.1021/acscatal.6b03147).

Para Pt, [Markovic et al. 1996](https://doi.org/10.1021/jp9533382) e
[Strmcnik et al. 2010](https://doi.org/10.1038/nchem.771) confirmam o material,
mas requerem conferir se a curva representa o estado de superfície que será
usado como classe Pt. Para Ru, [Wang et al. 2001](https://doi.org/10.1021/jp0041757)
descreve Ru(0001) e oxidação superficial; isso não autoriza misturar
automaticamente Ru limpo, oxidado ou modificado.

O arquivo [source_screening.csv](C:/Users/jomar/OneDrive/Documents/Playground/echemdb-ml-pipeline/outputs/release_review_0_9_2/source_screening.csv)
registra essa triagem. Todas as linhas permanecem `pending_full_text_and_figure_review`,
com `accepted_training=False`. Ainda faltam texto completo/figura, calibração
da referência de potencial, licença, identidade da curva e decisão de
independência da fonte.

Foi registrada uma possível equivalência bibliográfica entre
`10.1002/ange.201706463` e `10.1002/anie.201706463`. O primeiro é o identificador
presente no conjunto local; o segundo aparece como DOI da versão internacional
do artigo. Essa relação está em `source_screening_with_aliases.csv`, mas não
altera IDs, hashes, partições ou contagem de fontes até ser confirmada no
registro do editor.

A consulta ao registro bibliográfico confirmou que a versão publicada em inglês
usa `10.1002/anie.201706463`; uma cópia institucional também informa esse DOI
como a versão final revisada por pares
([registro institucional](https://pure-oai.bham.ac.uk/ws/files/42577997/CO2_pulses_accepted_manuscript.pdf)).
O alias foi marcado como `confirmed_equivalent_journal_editions` em
`source_screening_final_v1.csv`. A fonte conta como uma única publicação e ainda
não foi admitida no treinamento.
