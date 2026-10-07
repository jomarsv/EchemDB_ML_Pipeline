from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from echemdb_ml_pipeline.features import FEATURE_VERSION


def source_split(frame: pd.DataFrame, fraction: float = 0.2):
    if not 0 < fraction < 1:
        raise ValueError("Test fraction must be between zero and one.")
    if not frame["versao_atributos"].eq(FEATURE_VERSION).all():
        raise ValueError("Regenerate the feature table using the current extractor.")
    frame = frame.copy()
    sources = frame["grupo_origem"].fillna("").astype(str).str.strip().str.lower()
    sources = sources.str.replace(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", regex=True)
    if sources.eq("").any():
        raise ValueError("Every record must identify its source DOI/publication.")
    frame["grupo_origem"] = sources
    groups = sorted(sources.unique())
    np.random.default_rng(20260917).shuffle(groups)
    remaining = frame.groupby(["tipo_sinal", "classe_alvo"]).size().to_dict()
    selected, size = [], 0
    for group in groups:
        part = frame[sources.eq(group)]
        counts = part.groupby(["tipo_sinal", "classe_alvo"]).size().to_dict()
        if size >= len(frame) * fraction:
            break
        if all(remaining[key] > count for key, count in counts.items()):
            selected.append(group)
            size += len(part)
            for key, count in counts.items():
                remaining[key] -= count
    test = frame[sources.isin(selected)].copy()
    train = frame[~sources.isin(selected)].copy()
    if test.empty or train.empty:
        raise ValueError("Not enough independent sources for a holdout.")
    if set(train["hash_curva"]) & set(test["hash_curva"]):
        raise ValueError("Duplicate curves across publications: resolve before splitting.")
    return train, test


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "outputs/scientific_v2/atributos_voltamogramas.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/scientific_v2/testes")
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    frame = frame[frame["status"].eq("valido") & frame["classe_alvo"].notna()]
    train, test = source_split(frame)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in [("atributos_treino_sem_teste", train), ("amostras_teste_atributos", test)]:
        path = args.output / f"{name}.csv"
        rows.to_csv(path, index=False)
        print(f"{name}: {len(rows)} curves, {rows.grupo_origem.nunique()} sources; {path}")
        for kind, subset in rows.groupby("tipo_sinal"):
            subset.to_csv(args.output / f"{name}_{kind}.csv", index=False)


if __name__ == "__main__":
    main()
