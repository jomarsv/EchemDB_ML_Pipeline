"""Create a human-review worksheet for new release entries; never admits data."""
import argparse
import json
from pathlib import Path

import pandas as pd

from audit_nested_inputs import ROOT


def compact(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return '' if value is None else str(value)


def review(input_dir, comparison_dir, output_dir):
    if output_dir.exists():
        raise ValueError('Output exists; use a new versioned review directory.')
    candidates = pd.read_csv(comparison_dir / 'new_source_candidates.csv')
    index = pd.read_csv(input_dir / 'dados_brutos_indexados.csv').set_index('id_entrada')
    rows = []
    for item in candidates.to_dict('records'):
        entry = item['id_entrada']
        raw = Path(index.loc[entry, 'arquivo_origem'])
        payload = json.loads(raw.with_suffix('.json').read_text(encoding='utf-8'))
        resources = [r for r in payload.get('resources', []) if Path(r.get('path', '')).name == raw.name]
        resource = resources[0] if len(resources) == 1 else {}
        meta = resource.get('metadata', {}).get('echemdb', {})
        system = meta.get('system', {})
        electrodes = system.get('electrodes', [])
        working = [e for e in electrodes if e.get('function') == 'working electrode']
        reference = [e for e in electrodes if e.get('function') == 'reference electrode']
        figure = meta.get('figureDescription', {})
        fields = {f.get('name'): f for f in figure.get('fields', [])}
        electrolyte = system.get('electrolyte', {})
        rows.append({
            'id_entrada': entry, 'doi': item['source_group'],
            'classe_rotulo_atual': item['classe_alvo'], 'tipo_sinal': item['tipo_sinal'],
            'figura': meta.get('source', {}).get('figure', ''),
            'curva': meta.get('source', {}).get('curve', ''),
            'eletrodo_trabalho': compact(working), 'eletrodo_referencia_fisico': compact(reference),
            'referencia_eixo': item['potential_reference'],
            'unidade_potencial': fields.get(index.loc[entry, 'coluna_potencial'], {}).get('unit', ''),
            'unidade_sinal': fields.get(index.loc[entry, 'coluna_sinal'], {}).get('unit', ''),
            'eletrolito': compact(electrolyte), 'temperatura': compact(system.get('temperature', electrolyte.get('temperature', ''))),
            'comentario_figura': figure.get('comment', ''), 'metadados_path': str(raw.with_suffix('.json')),
            'sha256_metadados': item['metadata_sha256'], 'sha256_curva': item['hash_curva'],
            'duplicata_exata': item['duplicate_curve'], 'sobreposicao_teste': any(item[k] for k in item if k.startswith('heldout_')),
            'decisao': 'pendente_revisao_humana', 'aceitar_treinamento': False,
            'motivo_bloqueio_inicial': 'release nova; verificar proveniencia, unidades, referencia e licenca',
            'revisor': '', 'fonte_figura_verificada': '', 'referencia_verificada': '',
            'licenca_verificada': '', 'decisao_final': '', 'observacoes': '',
        })
    table = pd.DataFrame(rows).sort_values(['classe_rotulo_atual', 'doi', 'id_entrada'])
    output_dir.mkdir(parents=True)
    table.to_csv(output_dir / 'revisao_manual_26_curvas.csv', index=False)
    source = table.groupby(['classe_rotulo_atual', 'doi', 'referencia_eixo'], as_index=False).agg(
        curvas=('id_entrada', 'size'), figuras=('figura', 'nunique'),
        eletrodos_trabalho=('eletrodo_trabalho', 'nunique'),
        unidades_potencial=('unidade_potencial', 'nunique'), unidades_sinal=('unidade_sinal', 'nunique'))
    source['decisao_fonte'] = 'pendente_revisao_humana'
    source.to_csv(output_dir / 'revisao_por_fonte.csv', index=False)
    manifest = {'candidate_curves': len(table), 'candidate_dois': int(table.doi.nunique()),
                'classes': sorted(table.classe_rotulo_atual.unique()), 'accepted': 0,
                'output': str(output_dir.resolve()),
                'required_review': ['eletrodo_trabalho', 'referencia_eixo', 'unidades', 'figura', 'licenca', 'independencia_doi']}
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'outputs/release_0_9_2_audit')
    parser.add_argument('--comparison', type=Path, default=ROOT / 'outputs/release_comparison_0_9_2')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/release_review_0_9_2')
    args = parser.parse_args()
    review(args.input, args.comparison, args.output)
