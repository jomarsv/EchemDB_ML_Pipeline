"""Run the predeclared nested pilot on eligible candidate classes only."""
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT
sys.path.insert(0, str(ROOT / 'src'))
from echemdb_ml_pipeline.nested import run_nested


def main():
    part = ROOT / 'outputs/density_candidate_0_9_2_v1/partitions'
    output = ROOT / 'outputs/density_candidate_0_9_2_v1/nested_eligible_v1'
    if output.exists():
        raise ValueError('Nested output exists; create a new version.')
    frame = pd.read_csv(part / 'train.csv')
    frame = frame[frame.classe_alvo.isin(['Ag', 'Au', 'Pt'])].copy()
    frame['source_group'] = frame.grupo_origem
    frame['E_span'] = frame.E_max - frame.E_min
    if frame.source_group.nunique() < 3:
        raise ValueError('Too few candidate sources.')
    config = {'scope': 'density candidate 0.9.2; development only; eligible Ag Au Pt',
              'outer_folds': 3, 'inner_folds': 2, 'features': 'predeclared CORE_FEATURES',
              'selection_metric': 'inner balanced accuracy then macro F1',
              'limitations': ['exploratory candidate dataset', 'conversion candidate pending signoff',
                              'rare classes excluded from this pilot', 'external candidate test not used'],
              'input_sha256': hashlib.sha256((part / 'train.csv').read_bytes()).hexdigest(),
              'test_sha256': hashlib.sha256((part / 'test.csv').read_bytes()).hexdigest()}
    summary = run_nested(frame, output, config)
    (output / 'candidate_cohort.csv').write_text(frame.to_csv(index=False), encoding='utf-8')
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
