"""Report numerical deltas separately from exact-byte curve identities."""
import json
import numpy as np
import pandas as pd
from audit_nested_inputs import ROOT


def main():
    old = pd.read_csv(ROOT / 'outputs/scientific_v2/dados_limpos.csv')
    new = pd.read_csv(ROOT / 'outputs/release_0_9_2_audit/dados_limpos.csv')
    previous = {key: group[['E', 'j']].to_numpy() for key, group in old.groupby('id_entrada', sort=False)}
    rows = []
    for key, group in new.groupby('id_entrada', sort=False):
        if key not in previous:
            continue
        a, b = previous[key], group[['E', 'j']].to_numpy()
        row = {'id_entrada': key, 'old_points': len(a), 'new_points': len(b), 'same_shape': a.shape == b.shape}
        if a.shape == b.shape:
            delta = np.abs(a - b)
            row.update(max_delta_E_V=float(delta[:, 0].max()), max_delta_signal_SI=float(delta[:, 1].max()),
                       equal_numeric=bool(np.array_equal(a, b)),
                       close_numeric=bool(np.allclose(a, b, rtol=1e-10, atol=1e-12)))
        rows.append(row)
    result = pd.DataFrame(rows)
    target = ROOT / 'outputs/release_comparison_0_9_2/numeric_deltas.csv'
    if target.exists():
        raise ValueError('Precision report already exists.')
    result.to_csv(target, index=False)
    print(json.dumps({'shared': len(result), 'same_shape': int(result.same_shape.sum()),
                      'equal_numeric': int(result.equal_numeric.sum()),
                      'close_numeric': int(result.close_numeric.sum()),
                      'rtol': 1e-10, 'atol': 1e-12}, indent=2))
    print(result[~result.close_numeric.fillna(False)].to_string(index=False))


if __name__ == '__main__':
    main()
