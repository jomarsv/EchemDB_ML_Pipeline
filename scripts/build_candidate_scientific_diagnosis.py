"""Consolidate candidate data, source and model limitations."""
import json
from pathlib import Path
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    base = ROOT / 'outputs/density_candidate_0_9_2_v1'
    output = base / 'scientific_diagnosis_v1'
    if output.exists():
        raise ValueError('Diagnosis exists; create a new version.')
    rows = [
        ('Ag', 'sources', 'alta', 'uma fonte independente no teste; recall varia entre dobras', 'coletar mais publicacoes Ag e manter o rotulo atual', 'nao_e_erro_de_rotulagem'),
        ('Au', 'model', 'media', 'confusoes com Pt em uma fonte do teste', 'revisar representacao e referencia; ampliar fontes', 'revisao_de_dados_e_modelo'),
        ('Pt', 'data_quality', 'alta', 'uma curva Nishihara apresenta escala extrema incompatível com curvas irmãs', 'redigitalizar f5b e manter em quarentena', 'problema_de_digitalizacao'),
        ('Pt', 'model', 'media', 'confusoes Pt->Au concentradas em Nishihara', 'reavaliar apos redigitalizacao e comparar sem f5b', 'nao_recodificar_classe'),
        ('Cu', 'evaluation', 'alta', 'uma fonte independente no teste; classe nao elegivel por fonte', 'coletar fontes Cu independentes antes de concluir desempenho', 'nao_reportar_desempenho_final'),
        ('Co/Fe/Ir/Ni/Pb/Pd/Rh/Ru', 'evaluation', 'alta', 'sem curvas no holdout candidato', 'criar fontes e teste independente', 'nao_confundir_com_acuracia_zero'),
        ('all', 'reference', 'alta', 'estratos RHE, SHE e Ag/AgCl nao harmonizados por conversao', 'revisar calibracao e manter estratos separados', 'nenhuma_conversao_automatica'),
    ]
    frame = pd.DataFrame(rows, columns=['classe', 'categoria', 'prioridade', 'evidencia', 'proximo_passo', 'interpretacao'])
    output.mkdir(parents=True)
    frame.to_csv(output / 'diagnostico_cientifico.csv', index=False)
    manifest = {'candidate_only': True, 'models_refit': 0, 'accepted_for_article': False,
                'key_conclusion': 'Ag limitation is source diversity, not label error',
                'required_before_final_claims': ['new independent sources', 'redigitize Nishihara f5b', 'reference-stratum review', 'frozen confirmatory split']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(frame.to_string(index=False))


if __name__ == '__main__':
    main()
