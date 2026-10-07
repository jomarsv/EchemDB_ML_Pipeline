"""Record conservative DOI screening based on primary bibliographic pages."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


SOURCES = [
    ('10.1002/ange.201706463', 'Cu', 'Role of the Adsorbed Oxygen Species in the Selective Electrochemical Reduction of CO2 to Alcohols and Carbonyls on Copper Electrodes', 'Cu electrodes; pulsed voltammetry and related electrochemistry', 'https://doi.org/10.1002/anie.201706463', 'preliminarily_compatible'),
    ('10.1016/j.jelechem.2013.03.018', 'Cu', 'The electrochemical characterization of copper single-crystal electrodes in alkaline media', 'Cu single crystals; blank cyclic voltammetry in alkaline media', 'https://doi.org/10.1016/j.jelechem.2013.03.018', 'preliminarily_compatible'),
    ('10.1016/S0022-0728(03)00115-3', 'Cu', 'In situ STM study of the anodic oxidation of Cu(001) in 0.1 M NaOH', 'Cu(001); electrochemical STM and oxidation in NaOH', 'https://doi.org/10.1016/S0022-0728(03)00115-3', 'preliminarily_compatible'),
    ('10.1016/S0022-0728(80)80421-9', 'Cu', 'Oxygen electrosorption on copper single crystal electrodes in sodium hydroxide solution', 'Copper single-crystal electrodes in sodium hydroxide', 'https://doi.org/10.1016/S0022-0728(80)80421-9', 'preliminarily_compatible'),
    ('10.1021/acscatal.6b03147', 'Cu', 'Electrochemical Reduction of CO2 Using Copper Single-Crystal Surfaces: Effects of CO* Coverage on the Selective Formation of Ethylene', 'Cu(100), Cu(111), Cu(110); CV/LSV; RHE declared in abstract metadata', 'https://doi.org/10.1021/acscatal.6b03147', 'preliminarily_compatible'),
    ('10.2298/jsc0207531j', 'Cu', 'Surface reconstruction during the adsorption/desorption of OH species onto Cu(111) and Cu(100) in 0.1 M NaOH solution', 'Cu(111) and Cu(100); cyclic voltammetry; SHE reported', 'https://doi.org/10.2298/JSC0207531J', 'preliminarily_compatible'),
    ('10.1021/jp9533382', 'Pt', 'Oxygen reduction on platinum low-index single-crystal surfaces in alkaline solution', 'Pt(hkl) low-index single crystals; rotating ring-disk measurements', 'https://doi.org/10.1021/jp9533382', 'compatible_material_requires_curve_scope_check'),
    ('10.1038/nchem.771', 'Pt', 'Enhanced electrocatalysis of the oxygen reduction reaction based on patterning of platinum surfaces with cyanide', 'Platinum surfaces; oxygen reduction; cyanide-patterned surface', 'https://doi.org/10.1038/nchem.771', 'compatible_material_requires_surface_state_check'),
    ('10.1021/jp0041757', 'Ru', 'In Situ X-Ray Reflectivity and Voltammetry Study of Ru(0001) Surface Oxidation in Electrolyte Solutions', 'Ru(0001); voltammetry and X-ray reflectivity in acid solution', 'https://doi.org/10.1021/jp0041757', 'compatible_material_requires_curve_scope_check'),
]


def main():
    output = ROOT / 'outputs/release_review_0_9_2/source_screening.csv'
    if output.exists():
        raise ValueError('Screening already exists; create a new version before changing decisions.')
    frame = pd.DataFrame(SOURCES, columns=['doi', 'class_expected', 'title_primary', 'evidence_summary', 'primary_url', 'preliminary_status'])
    frame['decision'] = 'pending_full_text_and_figure_review'
    frame['accepted_training'] = False
    frame['reference_calibration_verified'] = False
    frame['license_verified'] = False
    frame['reviewer'] = ''
    frame['notes'] = ''
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    (output.parent / 'source_screening_manifest.json').write_text(json.dumps({
        'records': len(frame), 'accepted': 0,
        'screening_scope': 'bibliographic primary-page check; not a full-text admission decision',
        'required_before_admission': ['full_text_and_figure', 'reference_calibration', 'license', 'curve_identity', 'independent_source'],
    }, indent=2), encoding='utf-8')
    print(frame[['doi', 'class_expected', 'preliminary_status', 'decision']].to_string(index=False))


if __name__ == '__main__':
    main()
