"""Classify candidate sources against the existing model modality."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    review = pd.read_csv(ROOT / 'outputs/release_review_0_9_2/revisao_manual_26_curvas.csv')
    rows = []
    for doi, group in review.groupby('doi', sort=True):
        signal_types = sorted(group.tipo_sinal.unique())
        area_status = 'not_required'
        if 'current' in signal_types:
            areas = []
            for path in group.metadados_path.drop_duplicates():
                payload = json.loads(Path(path).read_text(encoding='utf-8'))
                for resource in payload.get('resources', []):
                    for electrode in resource.get('metadata', {}).get('echemdb', {}).get('system', {}).get('electrodes', []):
                        if electrode.get('function') == 'working electrode':
                            areas.append(electrode.get('geometricElectrolyteContactArea'))
            area_status = 'declared_for_all_reviewed' if areas and all(areas) else 'missing_or_incomplete'
        if area_status == 'missing_or_incomplete':
            decision, reason = 'blocked_modality', 'current_requires_electrode_area_before_conversion_to_density'
        elif len(signal_types) > 1:
            decision, reason = 'split_by_modality', 'source contains more than one signal modality'
        else:
            decision, reason = 'compatible_modality_pending_scientific_review', 'potential reference and source conditions still require verification'
        rows.append({'doi': doi, 'class_expected': group.classe_rotulo_atual.iloc[0],
                     'curves': len(group), 'signal_types': '|'.join(signal_types),
                     'potential_references': '|'.join(sorted(group.referencia_eixo.unique())),
                     'area_status': area_status, 'decision': decision, 'reason': reason,
                     'accepted_training': False, 'reviewer': '', 'notes': ''})
    out = ROOT / 'outputs/release_review_0_9_2/compatibility_decisions.csv'
    if out.exists():
        raise ValueError('Compatibility decisions already exist; use a new version.')
    pd.DataFrame(rows).to_csv(out, index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main()
