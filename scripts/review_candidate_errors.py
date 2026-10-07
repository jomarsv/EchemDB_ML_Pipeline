"""Create a provenance-aware review list for frozen-fold errors."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1'
    eval_dir = base / 'external_frozen_eligible_v1'
    output = eval_dir / 'error_review.csv'
    if output.exists():
        raise ValueError('Error review exists; create a new version.')
    predictions = pd.read_csv(eval_dir / 'selected_predictions.csv')
    test = pd.read_csv(base / 'partitions/test.csv')
    columns = ['id_entrada', 'classe_alvo', 'grupo_origem', 'referencia', 'tipo_sinal', 'E_min', 'E_max', 'j_min', 'j_max']
    details = predictions.merge(test[columns], on='id_entrada', how='left', validate='many_to_one')
    details['erro'] = details.classe_real.ne(details.classe_predita)
    details['confusao'] = details.classe_real + '->' + details.classe_predita
    details['prioridade'] = details.apply(lambda row: 'alta' if row.classe_real == 'Ag' or row.confusao == 'Pt->Au' else 'media', axis=1)
    errors = details[details.erro].copy().sort_values(['prioridade', 'classe_real', 'grupo_origem', 'id_entrada'])
    errors.to_csv(output, index=False)
    summary = errors.groupby(['classe_real', 'classe_predita'], as_index=False).agg(
        errors=('id_entrada', 'size'), sources=('grupo_origem', 'nunique'), curves=('id_entrada', 'nunique'))
    summary.to_csv(eval_dir / 'error_summary.csv', index=False)
    source = errors.groupby(['classe_real', 'classe_predita', 'grupo_origem'], as_index=False).agg(errors=('id_entrada', 'size'))
    source.to_csv(eval_dir / 'error_summary_by_source.csv', index=False)
    manifest = {'error_rows': len(errors), 'unique_error_curves': int(errors.id_entrada.nunique()),
                'confusion_pairs': summary.to_dict('records'),
                'purpose': 'targeted provenance and data-collection review', 'candidate_only': True}
    (eval_dir / 'error_review_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(summary.to_string(index=False))
    print(errors[['fold', 'id_entrada', 'classe_real', 'classe_predita', 'grupo_origem', 'prioridade']].to_string(index=False))


if __name__ == '__main__':
    main()
