"""Freeze a confirmed bibliographic alias as metadata only."""
import json
import pandas as pd
from audit_nested_inputs import ROOT


def main():
    base = ROOT / 'outputs/release_review_0_9_2/source_screening_with_aliases.csv'
    output = ROOT / 'outputs/release_review_0_9_2/source_screening_final_v1.csv'
    if output.exists():
        raise ValueError('Final screening already exists; create a new version.')
    frame = pd.read_csv(base)
    mask = frame.doi.eq('10.1002/ange.201706463')
    frame.loc[mask, 'doi_alias_status'] = 'confirmed_equivalent_journal_editions'
    frame.loc[mask, 'alias_reason'] = 'Publisher-linked German and International Edition records identify the same article; count once.'
    frame.loc[mask, 'decision'] = 'pending_full_text_and_figure_review'
    frame.to_csv(output, index=False)
    (output.parent / 'doi_alias_confirmation.json').write_text(json.dumps({
        'confirmed_aliases': {'10.1002/ange.201706463': '10.1002/anie.201706463'},
        'source': 'publisher-linked bibliographic records and peer-reviewed article record',
        'training_data_rewritten': False, 'source_count_deduplication_applied': False,
        'next_required_step': 'full-text and figure review before admission',
    }, indent=2), encoding='utf-8')
    print(frame.loc[mask, ['doi', 'canonical_doi', 'doi_alias_status', 'decision']].to_string(index=False))


if __name__ == '__main__':
    main()
