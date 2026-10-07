"""Create a DOI-disjoint holdout for the density candidate."""
import hashlib
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT
from create_test_split import source_split


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source = ROOT / 'outputs/density_candidate_0_9_2_v1/atributos_density_candidate.csv'
    output = ROOT / 'outputs/density_candidate_0_9_2_v1/partitions'
    if output.exists():
        raise ValueError('Partition output exists; create a new candidate version.')
    frame = pd.read_csv(source)
    frame = frame[frame.status.eq('valido') & frame.classe_alvo.notna()].copy()
    if frame.tipo_sinal.nunique() != 1 or frame.tipo_sinal.iloc[0] != 'current_density':
        raise ValueError('Candidate must contain only current-density records.')
    train, test = source_split(frame, fraction=0.2)
    for left, right, name in [(train, test, 'id_entrada'), (train, test, 'grupo_origem'), (train, test, 'hash_curva')]:
        if set(left[name]) & set(right[name]):
            raise ValueError(f'Overlap detected in {name}.')
    output.mkdir(parents=True)
    train.to_csv(output / 'train.csv', index=False)
    test.to_csv(output / 'test.csv', index=False)
    partitions = pd.concat([train.assign(partition='development'), test.assign(partition='held_out')])
    partitions[['id_entrada', 'grupo_origem', 'classe_alvo', 'partition']].to_csv(output / 'partitions.csv', index=False)
    summary = partitions.groupby(['partition', 'classe_alvo'], as_index=False).agg(curves=('id_entrada', 'size'), sources=('grupo_origem', 'nunique'))
    summary.to_csv(output / 'support.csv', index=False)
    manifest = {'protocol': 'candidate-source-split-v1', 'seed': 20260917,
                'train_records': len(train), 'test_records': len(test),
                'train_sources': int(train.grupo_origem.nunique()), 'test_sources': int(test.grupo_origem.nunique()),
                'overlap': {'id_entrada': 0, 'grupo_origem': 0, 'hash_curva': 0},
                'models_fitted': 0, 'candidate_only': True, 'input_hash': digest(source),
                'output_hashes': {p.name: digest(p) for p in output.glob('*.csv')}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
