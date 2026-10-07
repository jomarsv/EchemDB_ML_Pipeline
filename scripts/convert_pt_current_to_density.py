"""Create a traceable Pt current-to-density candidate; do not retrain models."""
import hashlib
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    input_dir = ROOT / 'outputs/release_0_9_2_audit'
    output_dir = ROOT / 'outputs/release_review_0_9_2/pt_density_conversion_v1'
    if output_dir.exists():
        raise ValueError('Conversion output exists; create a new version.')
    clean_path = input_dir / 'dados_limpos.csv'
    clean = pd.read_csv(clean_path)
    target_doi = '10.1021/jp9533382'
    selected = clean[clean.doi.astype(str).str.lower().str.contains(target_doi.lower(), regex=False)].copy()
    if selected.empty or set(selected.tipo_sinal) != {'current'}:
        raise ValueError('Expected only current curves from the selected Pt source.')
    area_cm2 = 0.283
    area_m2 = area_cm2 * 1e-4
    selected['j_original_A'] = selected['j'].astype(float)
    selected['j'] = selected['j_original_A'] / area_m2
    selected['tipo_sinal'] = 'current_density'
    selected['unidade_sinal_usada'] = 'A/m2'
    selected['conversion_formula'] = 'j_A_m2 = i_A / (0.283 cm2 * 1e-4 m2/cm2)'
    selected['conversion_area_cm2'] = area_cm2
    selected['conversion_source'] = 'metadata: working-electrode geometricElectrolyteContactArea'
    selected['conversion_status'] = 'candidate_pending_feature_reextraction_and_review'
    output_dir.mkdir(parents=True)
    selected.to_csv(output_dir / 'pt_current_converted_density_points.csv', index=False)
    manifest = {
        'source_doi': target_doi, 'source_records': int(selected.id_entrada.nunique()),
        'source_points': int(len(selected)), 'area_cm2': area_cm2, 'area_m2': area_m2,
        'formula': 'j [A/m2] = i [A] / A [m2]', 'accepted_training': False,
        'models_refit': 0, 'requires': ['reextract_features', 'new_hash', 'unit_check', 'reviewer_signoff'],
        'input_hash': sha(clean_path), 'status': 'candidate_only',
    }
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
