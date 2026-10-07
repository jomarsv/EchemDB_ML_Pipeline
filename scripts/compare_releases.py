"""Compare extracted releases without admitting data or changing test partitions."""
import argparse
import json
from pathlib import Path

import pandas as pd

from audit_nested_inputs import ROOT, audit
from curate_scientific_inputs import digest, reference_policy


def overlap_flags(row, holdout):
    return {f'heldout_{column}': str(row[column]) in set(holdout[column].dropna().astype(str))
            for column in ('id_entrada', 'source_group', 'hash_curva')}


def compare(old_dir, new_dir, output, archive):
    if output.exists():
        raise ValueError('Use a new output directory; comparison will not overwrite results.')
    old, new = audit(old_dir).fillna(''), audit(new_dir).fillna('')
    if old.id_entrada.duplicated().any() or new.id_entrada.duplicated().any():
        raise ValueError('Duplicate record IDs require manual reconciliation.')
    held_ids = set(pd.read_csv(old_dir / 'testes/amostras_teste_atributos.csv').id_entrada)
    held = old[old.id_entrada.isin(held_ids)]
    previous = old.set_index('id_entrada')
    new_sources = set(new.source_group) - set(old.source_group) - {''}
    old_hashes = set(old.hash_curva) - {''}
    rows = []
    for row in new.to_dict('records'):
        path = Path(row['metadata_path'])
        payload = json.loads(path.read_text(encoding='utf-8'))
        resources = [r for r in payload.get('resources', []) if r.get('name') == row['id_entrada']]
        meta = resources[0].get('metadata', {}).get('echemdb', {}) if len(resources) == 1 else {}
        refs = [str(f.get('reference', '')).strip() for f in meta.get('figureDescription', {}).get('fields', []) if f.get('name') == 'E']
        figure = refs[0] if len(refs) == 1 else ''
        policy = reference_policy(row['potential_reference'], figure, row['source_group'])
        item = {k: row[k] for k in ('id_entrada', 'classe_alvo', 'tipo_sinal', 'source_group', 'hash_curva', 'potential_reference', 'duplicate_curve')}
        item.update(overlap_flags(row, held))
        item.update(new_source=row['source_group'] in new_sources,
                    curve_seen_before=row['hash_curva'] in old_hashes,
                    metadata_sha256=digest(path), reference_decision=policy[0],
                    reference_reason=policy[1], reference_stratum=policy[2])
        if row['id_entrada'] in previous.index:
            before = previous.loc[row['id_entrada']]
            changes = [k for k in ('hash_curva', 'source_group', 'classe_alvo', 'tipo_sinal', 'potential_reference')
                       if row[k] != before[k]]
            item['changes'] = '|'.join(changes)
            item['metadata_changed'] = digest(path) != digest(before.metadata_path)
            item['release_status'] = 'changed' if changes else 'same_curve_identity'
        else:
            item.update(changes='', metadata_changed=False, release_status='added')
        item['admission'] = ('protected_holdout' if any(item[k] for k in item if k.startswith('heldout_')) else
                             'quarantine_duplicate' if row['duplicate_curve'] else
                             'quarantine_reference' if policy[0].startswith('quarantine') else
                             'manual_review_not_admitted')
        rows.append(item)
    records = pd.DataFrame(rows)
    output.mkdir(parents=True)
    records.to_csv(output / 'release_comparison.csv', index=False)
    records[records.new_source].to_csv(output / 'new_source_candidates.csv', index=False)
    records[records.duplicate_curve].to_csv(output / 'duplicates_new_release.csv', index=False)
    old[~old.id_entrada.isin(new.id_entrada)].to_csv(output / 'removed_records.csv', index=False)
    support = []
    for version, frame in [('0.8.4', old), ('0.9.2', new)]:
        counts = frame.groupby(['tipo_sinal', 'classe_alvo', 'potential_reference']).agg(
            curves=('id_entrada', 'size'), sources=('source_group', 'nunique')).reset_index()
        counts['version'] = version
        support.append(counts)
    pd.concat(support).to_csv(output / 'support_by_reference.csv', index=False)
    summary = {'old_records': len(old), 'new_records': len(new),
               'old_sources': old.source_group.nunique(), 'new_sources_total': new.source_group.nunique(),
               'new_dois': sorted(new_sources), 'counts': records.release_status.value_counts().to_dict(),
               'admission': records.admission.value_counts().to_dict(),
               'new_source_classes': sorted(records.loc[records.new_source, 'classe_alvo'].unique()),
               'archive_sha256': digest(archive),
               'official_archive_sha256': '6093b6a2ac10792e8582f69441e883bed6ed4eb662036cb2441edfa064df0354',
               'download_url': 'https://github.com/echemdb/electrochemistry-data/releases/download/0.9.2/data-0.9.2.zip',
               'inputs': {str(p.resolve()): digest(p) for folder in (old_dir, new_dir)
                          for p in (folder / 'atributos_voltamogramas.csv', folder / 'dados_brutos_indexados.csv')},
               'models_fitted': 0, 'records_admitted': 0}
    if summary['archive_sha256'] != summary['official_archive_sha256']:
        raise ValueError('Archive checksum differs from official release.')
    summary['output_hashes'] = {p.name: digest(p) for p in output.glob('*.csv')}
    (output / 'manifest.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--old', type=Path, default=ROOT / 'outputs/scientific_v2')
    parser.add_argument('--new', type=Path, default=ROOT / 'outputs/release_0_9_2_audit')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/release_comparison_0_9_2')
    parser.add_argument('--archive', type=Path, default=ROOT.parent / 'echemdb-data-0.9.2.zip')
    args = parser.parse_args()
    compare(args.old, args.new, args.output, args.archive)
