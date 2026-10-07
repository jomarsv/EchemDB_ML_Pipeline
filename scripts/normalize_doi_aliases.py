"""Record DOI aliases without rewriting source metadata or partition IDs."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


ALIASES = {
    '10.1002/ange.201706463': {
        'canonical_doi': '10.1002/anie.201706463',
        'reason': 'German/international journal DOI pair for the same article; verify publisher record before merge',
        'status': 'alias_review_required',
    },
}


def main():
    source_file = ROOT / 'outputs/release_review_0_9_2/source_screening.csv'
    output = ROOT / 'outputs/release_review_0_9_2/source_screening_with_aliases.csv'
    if output.exists():
        raise ValueError('Alias report already exists; use a new version.')
    frame = pd.read_csv(source_file)
    frame['canonical_doi'] = frame.doi.map(lambda value: ALIASES.get(value, {}).get('canonical_doi', value))
    frame['doi_alias_status'] = frame.doi.map(lambda value: ALIASES.get(value, {}).get('status', 'no_alias_detected'))
    frame['alias_reason'] = frame.doi.map(lambda value: ALIASES.get(value, {}).get('reason', ''))
    frame.to_csv(output, index=False)
    summary = frame.groupby('canonical_doi', as_index=False).agg(
        local_dois=('doi', lambda values: '|'.join(sorted(set(values)))),
        classes=('class_expected', lambda values: '|'.join(sorted(set(values)))),
        records=('doi', 'size'))
    summary.to_csv(output.parent / 'canonical_source_inventory.csv', index=False)
    (output.parent / 'doi_alias_manifest.json').write_text(json.dumps({
        'aliases_recorded': len(ALIASES), 'source_records': len(frame),
        'training_rewrite_performed': False,
        'rule': 'aliases are bibliographic identity hints; merge only after publisher verification',
    }, indent=2), encoding='utf-8')
    print(summary.to_string(index=False))


if __name__ == '__main__':
    main()
