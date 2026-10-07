"""Run nested validation on the predeclared balanced candidate split."""
import hashlib
import sys
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT
sys.path.insert(0, str(ROOT / 'src'))
from echemdb_ml_pipeline.nested import run_nested


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1'
    part = base / 'partitions_balanced_v1'
    output = base / 'nested_balanced_v1'
    if output.exists():
        raise ValueError('Balanced nested output exists; create a new version.')
    frame = pd.read_csv(part / 'train.csv')
    frame = frame[frame.classe_alvo.isin(['Ag', 'Au', 'Pt'])].copy()
    frame['source_group'] = frame.grupo_origem
    frame['E_span'] = frame.E_max - frame.E_min
    config = {'scope': 'density candidate 0.9.2; balanced source split; Ag Au Pt',
              'outer_folds': 3, 'inner_folds': 2, 'selection_metric': 'inner balanced accuracy then macro F1',
              'limitations': ['candidate release pending final review', 'rare classes excluded', 'external balanced holdout unused'],
              'input_sha256': hashlib.sha256((part / 'train.csv').read_bytes()).hexdigest(),
              'test_sha256': hashlib.sha256((part / 'test.csv').read_bytes()).hexdigest()}
    summary = run_nested(frame, output, config)
    frame.to_csv(output / 'candidate_cohort.csv', index=False)
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
