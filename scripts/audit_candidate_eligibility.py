"""Audit class/source support before candidate nested validation."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    part_dir = ROOT / 'outputs/density_candidate_0_9_2_v1/partitions'
    output = part_dir / 'eligibility.csv'
    if output.exists():
        raise ValueError('Eligibility report exists; create a new partition version.')
    train, test = pd.read_csv(part_dir / 'train.csv'), pd.read_csv(part_dir / 'test.csv')
    classes = sorted(set(train.classe_alvo) | set(test.classe_alvo))
    rows = []
    for label in classes:
        tr, te = train[train.classe_alvo.eq(label)], test[test.classe_alvo.eq(label)]
        train_sources, test_sources = tr.grupo_origem.nunique(), te.grupo_origem.nunique()
        both = bool(len(tr) and len(te))
        eligible = both and train_sources >= 2 and test_sources >= 2
        rows.append({'classe_alvo': label, 'train_curves': len(tr), 'train_sources': train_sources,
                     'test_curves': len(te), 'test_sources': test_sources, 'present_both': both,
                     'minimum_two_sources_each_side': eligible,
                     'status': 'avaliavel_por_fonte' if eligible else 'nao_avaliavel_com_esta_particao',
                     'reason': '' if eligible else ('sem_curvas_nos_dois_lados' if not both else 'fontes_independentes_insuficientes')})
    frame = pd.DataFrame(rows)
    frame.to_csv(output, index=False)
    manifest = {'classes_total': len(frame), 'classes_eligible': int(frame.minimum_two_sources_each_side.sum()),
                'classes_not_eligible': int((~frame.minimum_two_sources_each_side).sum()),
                'eligible_classes': frame.loc[frame.minimum_two_sources_each_side, 'classe_alvo'].tolist(),
                'models_fitted': 0, 'candidate_only': True, 'criterion': '>=2 independent DOIs in train and test'}
    (part_dir / 'eligibility_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    print(frame.to_string(index=False))


if __name__ == '__main__':
    main()
