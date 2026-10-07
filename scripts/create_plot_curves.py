from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "dados_limpos.csv"
OUTPUT = ROOT / "outputs" / "curvas_voltamogramas_plot.csv"
MAX_POINTS_PER_CURVE = 700
COLUMNS = [
    "id_entrada",
    "E",
    "j",
    "material_eletrodo",
    "eletrolito",
    "referencia",
    "tipo_sinal",
    "unidade_potencial_usada",
    "unidade_sinal_usada",
]


def downsample_curve(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if len(frame) > MAX_POINTS_PER_CURVE:
        step = max(1, len(frame) // MAX_POINTS_PER_CURVE)
        frame = frame.iloc[::step].head(MAX_POINTS_PER_CURVE)
    return frame[COLUMNS]


def main() -> None:
    current_id = None
    current_rows: list[dict[str, object]] = []
    total_rows = 0
    written = False

    for chunk in pd.read_csv(INPUT, chunksize=250_000):
        for row in chunk.to_dict(orient="records"):
            row_id = row["id_entrada"]
            if current_id is None:
                current_id = row_id
            if row_id != current_id:
                sampled = downsample_curve(current_rows)
                sampled.to_csv(OUTPUT, mode="w" if not written else "a", index=False, header=not written)
                total_rows += len(sampled)
                written = True
                current_rows = []
                current_id = row_id
            current_rows.append(row)

    if current_rows:
        sampled = downsample_curve(current_rows)
        sampled.to_csv(OUTPUT, mode="w" if not written else "a", index=False, header=not written)
        total_rows += len(sampled)

    print(f"arquivo,{OUTPUT}")
    print(f"linhas,{total_rows}")


if __name__ == "__main__":
    main()

