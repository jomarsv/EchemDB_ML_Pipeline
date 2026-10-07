"""Read-only source audit; writes a new, explicit audit directory when invoked."""
import argparse
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def audit(folder):
    features = pd.read_csv(folder / 'atributos_voltamogramas.csv')
    index = pd.read_csv(folder / 'dados_brutos_indexados.csv')
    metadata = []
    for row in index.itertuples():
        path = Path(row.arquivo_origem).with_suffix('.json')
        reference, reason = 'unknown', 'sidecar_missing'
        if path.exists():
            payload = json.loads(path.read_text(encoding='utf-8'))
            resources = [r for r in payload.get('resources', [])
                         if Path(r.get('path', '')).name == Path(row.arquivo_origem).name]
            references = [str(field.get('reference', '')).strip()
                          for resource in resources
                          for field in resource.get('schema', {}).get('fields', [])
                          if field.get('name') == row.coluna_potencial]
            if references and all(references) and len(set(references)) == 1:
                reference, reason = references[0], 'declared_in_schema'
            else:
                reason = 'missing_or_ambiguous_reference'
        metadata.append({'id_entrada': row.id_entrada, 'potential_reference': reference,
                         'reference_status': reason, 'metadata_path': str(path)})
    frame = features.merge(pd.DataFrame(metadata), on='id_entrada', validate='one_to_one')
    frame['source_group'] = frame.grupo_origem.fillna('').str.strip().str.lower().str.replace(
        r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', regex=True)
    frame['duplicate_curve'] = frame.hash_curva.duplicated(keep=False)
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'outputs/scientific_v2')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/stage3_audit')
    args = parser.parse_args()
    frame = audit(args.input)
    args.output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output / 'records_audit.csv', index=False)
    summary = frame.groupby(['tipo_sinal', 'potential_reference', 'classe_alvo']).agg(
        curves=('id_entrada', 'size'), sources=('source_group', 'nunique'))
    summary.to_csv(args.output / 'reference_class_support.csv')
    frame[frame.duplicate_curve].to_csv(args.output / 'duplicate_candidates.csv', index=False)
    print(summary.to_string())


if __name__ == '__main__':
    main()
