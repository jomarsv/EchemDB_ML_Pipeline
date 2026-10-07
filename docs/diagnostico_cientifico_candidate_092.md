# Diagnostico cientifico da base candidata

O diagnóstico consolidado está em `outputs/density_candidate_0_9_2_v1/scientific_diagnosis_v1/diagnostico_cientifico.csv`.

A conclusão principal é que Ag deve permanecer rotulado como Ag: o artigo e os
metadados são coerentes. O recall instável decorre de uma única fonte
independente no teste, não de evidência para recodificar a classe. A fonte Pt
de Nishihara contém uma curva anômala que deve ser redigitalizada. Cu e as
classes raras não têm suporte independente suficiente no holdout para permitir
conclusões de desempenho.

Este diagnóstico é uma etapa de controle de qualidade. Não altera modelos,
partições ou resultados já calculados.
