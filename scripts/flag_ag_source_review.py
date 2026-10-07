"""Record the Ag source review and distinguish valid chemistry from model error."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1'
    test = pd.read_csv(base / 'partitions/test.csv')
    source = test[test.grupo_origem.eq('10.1007/pl00010123')].copy()
    source['decision'] = 'retain_label_pending_more_independent_Ag_sources'
    source['scientific_finding'] = 'Ag electrode in NaOH; oxide formation and corrosion features are plausible source-specific morphology'
    output = base / 'external_frozen_eligible_v1/ag_source_review.csv'
    if output.exists():
        raise ValueError('Ag review exists; create a new version.')
    source[['id_entrada', 'classe_alvo', 'referencia', 'eletrolito', 'unidade_sinal_usada', 'E_min', 'E_max', 'j_min', 'j_max', 'numero_pontos', 'decision', 'scientific_finding']].to_csv(output, index=False)
    manifest = {'doi': '10.1007/pl00010123', 'label_decision': 'Ag retained',
                'evidence': 'article title and abstract describe electrochemical behaviour of a silver electrode in NaOH using cyclic voltammetry',
                'anomaly_found': False, 'model_retrained': False, 'next_action': 'collect independent Ag sources',
                'primary_record': 'https://doi.org/10.1007/PL00010123'}
    (output.parent / 'ag_source_review_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(source[['id_entrada', 'j_min', 'j_max', 'decision']].to_string(index=False))


if __name__ == '__main__':
    main()
