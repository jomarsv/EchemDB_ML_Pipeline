"""Create a predeclared class/source-balanced candidate split."""
import hashlib
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def rank_source(source, seed=20260919):
    return hashlib.sha256(f'{seed}|{source}'.encode()).hexdigest()


def main():
    source = ROOT / 'outputs/density_candidate_0_9_2_v1/atributos_density_candidate.csv'
    output = ROOT / 'outputs/density_candidate_0_9_2_v1/partitions_balanced_v1'
    if output.exists():
        raise ValueError('Balanced partition exists; create a new version.')
    frame = pd.read_csv(source)
    quarantined = 'nishihara_1995_underpotential_75_f5b_solid'
    frame = frame[~frame.id_entrada.eq(quarantined)].copy()
    selected = set()
    for label in ['Ag', 'Au', 'Pt']:
        sources = sorted(frame.loc[frame.classe_alvo.eq(label), 'grupo_origem'].unique(), key=rank_source)
        if len(sources) < 6:
            raise ValueError(f'Not enough sources for balanced split: {label}')
        selected.update(sources[:3])
    test = frame[frame.grupo_origem.isin(selected)].copy()
    train = frame[~frame.grupo_origem.isin(selected)].copy()
    if set(train.grupo_origem) & set(test.grupo_origem):
        raise ValueError('Source overlap')
    for col in ['id_entrada', 'hash_curva']:
        if set(train[col]) & set(test[col]):
            raise ValueError(f'Overlap in {col}')
    output.mkdir(parents=True)
    train.to_csv(output / 'train.csv', index=False)
    test.to_csv(output / 'test.csv', index=False)
    support = pd.concat([train.assign(partition='development'), test.assign(partition='held_out')]).groupby(['partition', 'classe_alvo'], as_index=False).agg(curves=('id_entrada', 'size'), sources=('grupo_origem', 'nunique'))
    support.to_csv(output / 'support.csv', index=False)
    manifest = {'protocol': 'class-source-balanced-v1', 'seed': 20260919, 'target_test_sources_per_class': 3,
                'excluded_quarantine_id': quarantined, 'train_records': len(train), 'test_records': len(test),
                'train_sources': int(train.grupo_origem.nunique()), 'test_sources': int(test.grupo_origem.nunique()),
                'selected_sources': sorted(selected), 'models_fitted': 0, 'candidate_only': True,
                'rule': 'three deterministic DOI sources for Ag, Au and Pt; other classes not forced into holdout'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    print(support.to_string(index=False))


if __name__ == '__main__':
    main()
