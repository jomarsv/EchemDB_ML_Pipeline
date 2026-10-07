"""Summarize class-level frozen-fold failures without pooling repeated predictions."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1/external_frozen_eligible_v1'
    output = base / 'diagnostic_by_class.csv'
    if output.exists():
        raise ValueError('Diagnostic exists; create a new version.')
    metrics = pd.read_csv(base / 'selected_class_metrics.csv')
    metrics['priority'] = metrics.apply(lambda row: 'alta' if row.recall == 0 else 'media' if row.recall < 0.8 else 'baixa', axis=1)
    metrics['diagnostico'] = metrics.apply(lambda row: 'sem_acertos_na_dobra' if row.recall == 0 else 'recall_baixo' if row.recall < 0.8 else 'desempenho_aceitavel_nesta_dobra', axis=1)
    metrics.to_csv(output, index=False)
    predictions = pd.read_csv(base / 'selected_predictions.csv')
    matrices = []
    for fold, part in predictions.groupby('fold'):
        table = pd.crosstab(part.classe_real, part.classe_predita).reindex(index=['Ag', 'Au', 'Pt'], columns=['Ag', 'Au', 'Pt'], fill_value=0)
        table.insert(0, 'fold', fold)
        table.insert(1, 'classe_real', table.index)
        matrices.append(table.reset_index(drop=True))
    pd.concat(matrices, ignore_index=True).to_csv(base / 'confusion_by_fold.csv', index=False)
    manifest = {'critical_findings': [
        'Ag has only 3 external curves; its recall ranges from 0 to 0.667 across frozen folds.',
        'Au is more stable, with recall 0.867 to 0.933.',
        'Pt recall ranges from 0.743 to 0.971.',
        'Repeated predictions from different fold bundles must not be pooled as one confusion matrix.',
    ], 'candidate_only': True, 'model_selection_from_external_labels': False}
    (base / 'diagnostic_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(metrics.to_string(index=False))


if __name__ == '__main__':
    main()
