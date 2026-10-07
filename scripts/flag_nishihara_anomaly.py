"""Flag the anomalous Nishihara trace for source-level review."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1'
    test = pd.read_csv(base / 'partitions/test.csv')
    source = test[test.grupo_origem.eq('10.1016/0022-0728(94)03803-b')].copy()
    typical_scale = source.j_max.abs().median()
    source['outlier_flag'] = source.j_max.abs() > 100 * typical_scale
    source['decision'] = source.outlier_flag.map({True: 'quarantine_redigitization', False: 'retain_pending_source_review'})
    output = base / 'external_frozen_eligible_v1/nishihara_source_review.csv'
    if output.exists():
        raise ValueError('Nishihara review exists; create a new version.')
    source[['id_entrada', 'classe_alvo', 'referencia', 'eletrolito', 'unidade_sinal_usada', 'j_min', 'j_max', 'numero_pontos', 'outlier_flag', 'decision']].to_csv(output, index=False)
    manifest = {'doi': '10.1016/0022-0728(94)03803-b', 'article_scope': 'Cu underpotential deposition on stepped Pt electrodes',
                'label_decision': 'Pt is retained as working-electrode material',
                'anomalous_curve': source.loc[source.outlier_flag, 'id_entrada'].tolist(),
                'action': 'exclude anomalous trace pending figure/source re-digitization', 'model_retrained': False,
                'primary_source': 'https://www.sciencedirect.com/science/article/pii/002207289403803B'}
    (output.parent / 'nishihara_source_review_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(source[['id_entrada', 'j_min', 'j_max', 'outlier_flag', 'decision']].to_string(index=False))


if __name__ == '__main__':
    main()
