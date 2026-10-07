"""Complementary frozen evaluation after quarantining one digitization outlier."""
import json
import sys
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

from audit_nested_inputs import ROOT
sys.path.insert(0, str(ROOT / 'src'))
from echemdb_ml_pipeline.nested import CORE_FEATURES, predict_bundle


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1'
    nested = base / 'nested_eligible_v1'
    old_eval = base / 'external_frozen_eligible_v1'
    output = base / 'external_frozen_clean_holdout_v1'
    if output.exists():
        raise ValueError('Clean evaluation exists; create a new version.')
    test = pd.read_csv(base / 'partitions/test.csv')
    excluded_id = 'nishihara_1995_underpotential_75_f5b_solid'
    evaluated = test[test.classe_alvo.isin(['Ag', 'Au', 'Pt']) & ~test.id_entrada.eq(excluded_id)].copy()
    evaluated['E_span'] = evaluated.E_max - evaluated.E_min
    X, y = evaluated[CORE_FEATURES], evaluated.classe_alvo
    rows = []
    for fold_path in sorted(nested.glob('fold_*.joblib')):
        fold = fold_path.stem
        bundle = joblib.load(fold_path)
        pred = predict_bundle(bundle, X)[bundle['selected']]
        rows.append({'fold': fold, 'model': bundle['selected'], 'n': len(y),
                     'accuracy': accuracy_score(y, pred),
                     'balanced_accuracy': balanced_accuracy_score(y, pred),
                     'macro_f1': f1_score(y, pred, average='macro', zero_division=0)})
    output.mkdir(parents=True)
    current = pd.DataFrame(rows)
    current.to_csv(output / 'metrics_by_frozen_fold.csv', index=False)
    original = pd.read_csv(old_eval / 'metrics_by_frozen_fold.csv').query('selected_in_development').copy()
    original = original[['fold', 'model', 'accuracy', 'balanced_accuracy', 'macro_f1']].rename(columns={
        'accuracy': 'original_accuracy', 'balanced_accuracy': 'original_balanced_accuracy', 'macro_f1': 'original_macro_f1'})
    comparison = original.merge(current, on=['fold', 'model'])
    comparison['delta_accuracy'] = comparison.accuracy - comparison.original_accuracy
    comparison['delta_balanced_accuracy'] = comparison.balanced_accuracy - comparison.original_balanced_accuracy
    comparison['delta_macro_f1'] = comparison.macro_f1 - comparison.original_macro_f1
    comparison.to_csv(output / 'comparison_with_original.csv', index=False)
    manifest = {'excluded_id': excluded_id, 'reason': 'quarantine_redigitization', 'records_evaluated': len(evaluated),
                'models_refit': 0, 'selection_changed': False, 'external_labels_used_for_selection': False,
                'interpretation': 'sensitivity analysis; not a replacement for the original frozen evaluation'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(comparison.to_string(index=False))


if __name__ == '__main__':
    main()
