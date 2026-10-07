"""Build a non-authoritative density candidate from one release plus audited conversion."""
import hashlib
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    release_dir = ROOT / 'outputs/release_0_9_2_audit'
    conversion_dir = ROOT / 'outputs/release_review_0_9_2/pt_density_conversion_v1'
    output_dir = ROOT / 'outputs/density_candidate_0_9_2_v1'
    if output_dir.exists():
        raise ValueError('Candidate output exists; create a new version.')
    release = pd.read_csv(release_dir / 'atributos_voltamogramas.csv')
    converted = pd.read_csv(conversion_dir / 'pt_density_features_v2.csv')
    base = release[release.tipo_sinal.eq('current_density')].copy()
    old_current = release[release.tipo_sinal.eq('current')][['id_entrada', 'tipo_sinal']]
    duplicate_mask = base.hash_curva.astype(str).duplicated(keep=False) & base.hash_curva.notna()
    duplicates = base[duplicate_mask].copy()
    base = base[~duplicate_mask].copy()
    converted['candidate_origin'] = 'area_conversion_from_current'
    base['candidate_origin'] = 'release_0_9_2_native_density'
    converted = converted[base.columns]
    combined = pd.concat([base, converted], ignore_index=True)
    if combined.id_entrada.duplicated().any() or combined.hash_curva.duplicated().any():
        raise ValueError('Candidate contains duplicate IDs or hashes after exclusions.')
    output_dir.mkdir(parents=True)
    combined.to_csv(output_dir / 'atributos_density_candidate.csv', index=False)
    duplicates.to_csv(output_dir / 'excluded_exact_duplicates.csv', index=False)
    old_current.to_csv(output_dir / 'excluded_absolute_current.csv', index=False)
    support = combined.groupby(['classe_alvo', 'grupo_origem'], as_index=False).agg(curvas=('id_entrada', 'size'))
    support.to_csv(output_dir / 'source_support.csv', index=False)
    manifest = {
        'protocol': 'density-candidate-v1', 'release': '0.9.2',
        'native_density_records': int(len(base)), 'converted_pt_records': int(len(converted)),
        'candidate_records': int(len(combined)), 'excluded_exact_duplicate_records': int(len(duplicates)),
        'excluded_absolute_current_records': int(len(old_current)), 'models_fitted': 0,
        'accepted_for_article': False, 'test_partition_created': False,
        'input_hashes': {str(p.resolve()): digest(p) for p in (
            release_dir / 'atributos_voltamogramas.csv', conversion_dir / 'pt_density_features_v2.csv')},
        'limitations': ['No source-based split created yet.', 'Potential strata remain native and unharmonized.',
                        'Candidate conversions require reviewer signoff.', 'Exact duplicate policy excludes every member.'],
    }
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
