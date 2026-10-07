"""Re-extract v2 descriptors from the converted Pt density candidate."""
import json
import sys
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT
sys.path.insert(0, str(ROOT / 'src'))
from echemdb_ml_pipeline.features import FEATURE_COLUMNS, _clean_curve, _extract_features
from echemdb_ml_pipeline.schema import CurveRecord


def main():
    source = ROOT / 'outputs/release_review_0_9_2/pt_density_conversion_v1/pt_current_converted_density_points.csv'
    output_dir = ROOT / 'outputs/release_review_0_9_2/pt_density_conversion_v1'
    output = output_dir / 'pt_density_features_v2.csv'
    if output.exists():
        raise ValueError('Feature output exists; create a new version.')
    points = pd.read_csv(source)
    rows = []
    for entry, group in points.groupby('id_entrada', sort=True):
        record = CurveRecord(
            entry_id=entry, reference=str(group.referencia.iloc[0]), doi=str(group.doi.iloc[0]),
            material_electrode=str(group.material_eletrodo.iloc[0]), electrolyte=str(group.eletrolito.iloc[0]),
            experiment_type='electrochemical', units={'E_unit': 'V', 'j_unit': 'A/m2'},
            frame=group[['E', 'j', 't']].copy(), source_path=None, potential_col='E', signal_col='j',
            time_col='t', signal_kind='current_density', raw_metadata={'grupo_origem': str(group.doi.iloc[0])})
        clean, status, reason = _clean_curve(record, min_points=20)
        row = _extract_features(record, clean, status)
        row['conversion_status'] = 'candidate_pending_reviewer_signoff'
        row['conversion_reason'] = '' if reason is None else reason
        rows.append(row)
    features = pd.DataFrame(rows)
    features = features[[*FEATURE_COLUMNS, 'conversion_status', 'conversion_reason']]
    features.to_csv(output, index=False)
    manifest = json.loads((output_dir / 'manifest.json').read_text(encoding='utf-8'))
    manifest.update({'feature_output': str(output.resolve()), 'feature_version': 'echemdb-features-v2',
                     'reextracted_records': len(features), 'reextracted_status': features.status.value_counts().to_dict(),
                     'accepted_training': False})
    (output_dir / 'manifest_v2.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(features[['id_entrada', 'tipo_sinal', 'unidade_sinal_usada', 'status', 'hash_curva']].to_string(index=False))


if __name__ == '__main__':
    main()
