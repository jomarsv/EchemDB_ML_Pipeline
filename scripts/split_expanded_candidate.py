"""Create a predeclared expanded source-disjoint holdout."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from audit_nested_inputs import ROOT


def main():
    base = ROOT / "outputs/density_candidate_0_9_2_v1"
    source = base / "atributos_density_candidate.csv"
    output = base / "partitions_expanded_v1"
    if output.exists():
        raise ValueError("Expanded partition exists; create a new version.")
    frame = pd.read_csv(source)
    frame = frame[frame.classe_alvo.isin(["Ag", "Au", "Pt"])].copy()
    frame = frame[frame.id_entrada != "nishihara_1995_underpotential_75_f5b_solid"].copy()
    rng = np.random.default_rng(20260920)
    selected = []
    for label in ["Ag", "Au", "Pt"]:
        groups = sorted(frame.loc[frame.classe_alvo == label, "grupo_origem"].dropna().unique())
        if len(groups) < 6:
            raise ValueError(f"Need at least six source groups for {label}")
        selected.extend(rng.choice(groups, size=5, replace=False).tolist())
    selected = set(selected)
    test = frame[frame.grupo_origem.isin(selected)].copy()
    train = frame[~frame.grupo_origem.isin(selected)].copy()
    if set(train.hash_curva) & set(test.hash_curva):
        raise ValueError("Curve overlap")
    if set(train.grupo_origem) & set(test.grupo_origem):
        raise ValueError("Source overlap")
    if set(train.id_entrada) & set(test.id_entrada):
        raise ValueError("ID overlap")
    if set(train.classe_alvo) != {"Ag", "Au", "Pt"} or set(test.classe_alvo) != {"Ag", "Au", "Pt"}:
        raise ValueError("Class support missing")
    output.mkdir(parents=True)
    train.to_csv(output / "train.csv", index=False)
    test.to_csv(output / "test.csv", index=False)
    manifest = {
        "seed": 20260920,
        "criterion": "five randomly selected DOI/source groups per Ag, Au, Pt; sixth or more retained for development",
        "excluded_anomaly": "nishihara_1995_underpotential_75_f5b_solid",
        "train_records": len(train), "test_records": len(test),
        "train_sources": int(train.grupo_origem.nunique()), "test_sources": int(test.grupo_origem.nunique()),
        "test_support": test.groupby("classe_alvo").size().to_dict(),
        "selected_test_sources": sorted(selected),
        "train_sha256": hashlib.sha256((output / "train.csv").read_bytes()).hexdigest(),
        "test_sha256": hashlib.sha256((output / "test.csv").read_bytes()).hexdigest(),
        "candidate_only": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
