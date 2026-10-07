# Particao por fonte da base candidata

Foi criada uma particao por DOI para a base candidata 0.9.2. Publicacoes
inteiras ficam em desenvolvimento ou teste; IDs, DOI e hashes nao se repetem
entre as partes. A divisao e exploratoria e nao altera o teste reservado do
artigo nem cria um resultado de desempenho.

Arquivos: `outputs/density_candidate_0_9_2_v1/partitions/`.

Antes de validar modelos, conferir suporte por classe em `support.csv`. Classes
com uma unica fonte nao sustentam uma avaliacao independente por fonte e devem
permanecer explicitamente marcadas como insuficientes.

A auditoria de elegibilidade está em `partitions/eligibility.csv`. O critério
operacional desta etapa exige pelo menos duas fontes independentes em
desenvolvimento e duas no teste para uma classe ser avaliada por fonte. Isso
não é uma garantia de poder estatístico; é apenas um bloqueio contra conclusões
baseadas em uma única publicação.
