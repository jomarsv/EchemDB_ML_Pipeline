import argparse
import hashlib
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from audit_nested_inputs import audit
from echemdb_ml_pipeline.features import FEATURE_VERSION
from echemdb_ml_pipeline.nested import run_nested


def prepare(folder, reference='SCE', min_sources=4):
    frame = audit(folder)
    development = pd.read_csv(folder/'testes/atributos_treino_sem_teste_current_density.csv')
    holdout = pd.read_csv(folder/'testes/amostras_teste_atributos_current_density.csv')
    frame['exclusion'] = ''
    frame.loc[~frame.id_entrada.isin(development.id_entrada), 'exclusion'] = 'outside_existing_development'
    frame.loc[(frame.exclusion == '') & (frame.potential_reference != reference), 'exclusion'] = 'different_reference'
    frame.loc[(frame.exclusion == '') & frame.duplicate_curve, 'exclusion'] = 'duplicate_pending_adjudication'
    cohort = frame[frame.exclusion == '']
    support = cohort.groupby('classe_alvo').source_group.nunique()
    eligible = support[support >= min_sources].index
    frame.loc[(frame.exclusion == '') & ~frame.classe_alvo.isin(eligible), 'exclusion'] = 'insufficient_sources'
    cohort = frame[frame.exclusion == ''].copy().sort_values('id_entrada').reset_index(drop=True)
    if not (cohort.versao_atributos.eq(FEATURE_VERSION).all()
            and cohort.unidade_sinal_usada.eq('A/m2').all()
            and cohort.unidade_potencial_usada.eq('V').all()
            and cohort.status.eq('valido').all()):
        raise ValueError('Invalid feature schema, units or status')
    if cohort.source_group.eq('').any() or cohort.id_entrada.duplicated().any():
        raise ValueError('Missing source or duplicate ID')
    for field in ['id_entrada', 'grupo_origem', 'hash_curva']:
        if set(cohort[field]) & set(holdout[field]):
            raise ValueError(f'Existing holdout overlaps cohort: {field}')
    cohort['E_span'] = cohort.E_max - cohort.E_min
    return cohort, frame


def main():
    parser = argparse.ArgumentParser(description='Restricted, exploratory source-nested SCE pilot; preserves previous holdout.')
    parser.add_argument('--input', type=Path, default=ROOT/'outputs/scientific_v2')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cohort, audit_frame = prepare(args.input)
    config = {'scope': 'SCE declared; density; >=4 sources/class; existing development only',
              'limitations': ['reference declaration not independently verified', 'no peak descriptors',
                              'not all materials', 'historically explored data', 'not the browser JS models'],
              'input_sha256': hashlib.sha256((args.input/'atributos_voltamogramas.csv').read_bytes()).hexdigest(),
              'development_sha256': hashlib.sha256((args.input/'testes/atributos_treino_sem_teste_current_density.csv').read_bytes()).hexdigest()}
    print(cohort.groupby('classe_alvo').agg(n=('id_entrada','size'), sources=('source_group','nunique')).to_string(), flush=True)
    summary = run_nested(cohort, args.output, config)
    audit_frame.to_csv(args.output/'eligibility_audit.csv', index=False)
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
