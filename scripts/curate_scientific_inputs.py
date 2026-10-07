"""Conservative, reproducible curation without modifying original measurements."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from audit_nested_inputs import ROOT, audit


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference_policy(axis, figure, source):
    if not axis or axis == 'unknown' or not figure:
        return 'quarantine_reference', 'missing_axis_reference', ''
    if axis != figure:
        return 'quarantine_reference', 'schema_figure_disagreement', ''
    if axis in {'Ag', 'Pt'}:
        return 'native_only', 'quasi_reference_requires_local_calibration', f'{axis}|{source}'
    if axis == 'SHE':
        return 'native_only', 'already_declared_SHE_no_conversion', axis
    if axis == 'RHE':
        return 'native_only', 'SHE_conversion_requires_pH_temperature_and_conditions', axis
    return 'native_only', 'SHE_conversion_requires_documented_reference_conditions', axis


def classify_duplicates(frame):
    # Do not select a supposedly genuine trace merely by filename or row order.
    hashes = frame.hash_curva.fillna('').astype(str)
    return hashes.ne('') & hashes.duplicated(keep=False)


def source_gaps(frame, minimum=4):
    group = ['partition', 'tipo_sinal', 'reference_stratum', 'classe_alvo']
    counts = frame.groupby(group, dropna=False).agg(
        curves=('id_entrada', 'size'), independent_sources=('source_group', 'nunique')).reset_index()
    counts['minimum_sources_planning'] = minimum
    counts['additional_sources_needed'] = (minimum - counts.independent_sources).clip(lower=0)
    counts['status'] = counts.additional_sources_needed.map(
        lambda value: 'collect_independent_publications' if value else 'split_feasibility_still_required')
    return counts


def run(input_dir, output_dir):
    if output_dir.exists():
        raise ValueError('Output exists; use a new versioned directory.')
    frame = audit(input_dir)
    index_path = input_dir / 'dados_brutos_indexados.csv'
    feature_path = input_dir / 'atributos_voltamogramas.csv'
    index = pd.read_csv(index_path).set_index('id_entrada')
    train_path = input_dir / 'testes/atributos_treino_sem_teste.csv'
    test_path = input_dir / 'testes/amostras_teste_atributos.csv'
    train = set(pd.read_csv(train_path).id_entrada)
    test = set(pd.read_csv(test_path).id_entrada)
    if train & test:
        raise ValueError('Original partitions share IDs.')
    for column in ('source_group', 'hash_curva'):
        left = set(frame.loc[frame.id_entrada.isin(train), column].dropna())
        right = set(frame.loc[frame.id_entrada.isin(test), column].dropna())
        if left & right:
            raise ValueError(f'Original partitions share {column}.')
    records = []
    for row in frame.itertuples():
        raw = Path(index.loc[row.id_entrada, 'arquivo_origem'])
        sidecar = Path(row.metadata_path)
        payload = json.loads(sidecar.read_text(encoding='utf-8')) if sidecar.exists() else {}
        resources = [r for r in payload.get('resources', []) if Path(r.get('path', '')).name == raw.name]
        metadata = resources[0].get('metadata', {}).get('echemdb', {}) if len(resources) == 1 else {}
        field = index.loc[row.id_entrada, 'coluna_potencial']
        references = [str(f.get('reference', '')).strip()
                      for f in metadata.get('figureDescription', {}).get('fields', []) if f.get('name') == field]
        figure = references[0] if len(references) == 1 else ''
        status, reason, stratum = reference_policy(row.potential_reference, figure, row.source_group)
        system = metadata.get('system', {})
        electrolyte = system.get('electrolyte', {})
        record = {
            'figure_reference': figure, 'reference_decision': status,
            'reference_reason': reason, 'reference_stratum': stratum,
            'potential_conversion_applied': False,
            'physical_reference_metadata': json.dumps([e for e in system.get('electrodes', [])
                if e.get('function') == 'reference electrode'], ensure_ascii=True, sort_keys=True),
            'electrolyte_metadata': json.dumps(electrolyte, ensure_ascii=True, sort_keys=True),
            'source_metadata': json.dumps(metadata.get('source', {}), ensure_ascii=True, sort_keys=True),
            'figure_comment': metadata.get('figureDescription', {}).get('comment', ''),
            'metadata_sha256': digest(sidecar) if sidecar.exists() else '',
            'raw_path': str(raw), 'raw_sha256': digest(raw),
            'partition': 'development' if row.id_entrada in train else 'held_out' if row.id_entrada in test else 'unassigned',
        }
        records.append(record)
    frame = pd.concat([frame.reset_index(drop=True), pd.DataFrame(records)], axis=1)
    frame['duplicate_curve'] = classify_duplicates(frame)
    frame['curation_decision'] = [
        'quarantine_duplicate' if row.duplicate_curve else
        'quarantine_reference' if row.reference_decision == 'quarantine_reference' else
        'quarantine_source' if not row.source_group else
        'quarantine_partition' if row.partition == 'unassigned' else 'retain_native_reference'
        for row in frame.itertuples()]
    accepted = frame[frame.curation_decision == 'retain_native_reference']
    output_dir.mkdir(parents=True)
    frame.to_csv(output_dir / 'curation_registry.csv', index=False)
    frame[frame.duplicate_curve].to_csv(output_dir / 'duplicate_quarantine.csv', index=False)
    frame[frame.curation_decision != 'retain_native_reference'].to_csv(output_dir / 'quarantine.csv', index=False)
    gaps = source_gaps(accepted)
    gaps.to_csv(output_dir / 'source_gaps_by_reference.csv', index=False)
    pooled = accepted.groupby(['partition', 'tipo_sinal', 'classe_alvo']).agg(
        curves=('id_entrada', 'size'), sources=('source_group', 'nunique')).reset_index()
    pooled.to_csv(output_dir / 'source_inventory.csv', index=False)
    features = pd.read_csv(feature_path)
    for partition in ('development', 'held_out'):
        ids = set(accepted.loc[accepted.partition == partition, 'id_entrada'])
        features[features.id_entrada.isin(ids)].to_csv(output_dir / f'{partition}_native.csv', index=False)
    queue = gaps[(gaps.partition == 'development') & (gaps.additional_sources_needed > 0)].copy()
    for name in ('candidate_doi', 'data_url', 'license', 'reference_conditions', 'reviewer', 'decision'):
        queue[name] = ''
    queue.to_csv(output_dir / 'collection_queue.csv', index=False)
    manifest = {
        'protocol': 'conservative-curation-v1', 'input': str(input_dir.resolve()),
        'input_hashes': {str(p.resolve()): digest(p) for p in (index_path, feature_path, train_path, test_path)},
        'counts': frame.curation_decision.value_counts().to_dict(),
        'reference_decisions': frame.reference_reason.value_counts().to_dict(),
        'new_sources_added': 0, 'potential_conversions_applied': 0,
        'limitations': [
            'Native reference labels are not proof of cross-publication calibration.',
            'Native CSVs contain multiple reference strata: do not pool absolute potentials.',
            'Four sources is a planning threshold, not a statistical adequacy claim.',
            'Held-out publications remain held out; no model selection is performed.',
            'Exact duplicate screening does not rule out near duplicates.',
            'Collection queue is not evidence of new data acquisition.'],
    }
    manifest['output_hashes'] = {p.name: digest(p) for p in sorted(output_dir.glob('*.csv'))}
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'outputs/scientific_v2')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/scientific_curation_v1')
    args = parser.parse_args()
    run(args.input, args.output)
