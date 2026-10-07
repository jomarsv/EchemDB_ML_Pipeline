"""Evaluate a transparent abstention rule on frozen external bundles."""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from audit_nested_inputs import ROOT

sys.path.insert(0, str(ROOT / "src"))
from echemdb_ml_pipeline.nested import CORE_FEATURES, vote


def main():
    base = ROOT / "outputs/density_candidate_0_9_2_v1"
    nested = base / "nested_balanced_v1"
    partition = base / "partitions_balanced_v1"
    output = base / "abstention_balanced_v1"
    if output.exists():
        raise ValueError("Abstention output exists; create a new version.")

    test = pd.read_csv(partition / "test.csv")
    test["E_span"] = test.E_max - test.E_min
    records = []
    for fold_path in sorted(nested.glob("fold_*.joblib")):
        fold = fold_path.stem
        bundle = joblib.load(fold_path)
        X = test[CORE_FEATURES]
        base_predictions = {name: model.predict(X) for name, model in bundle["models"].items()}
        selected_name = bundle["selected"]
        selected_prediction = vote(
            [base_predictions[m] for m in bundle["ensembles"][selected_name]["members"]],
            bundle["ensembles"][selected_name]["weights"],
            bundle["labels"],
        ) if selected_name in bundle["ensembles"] else base_predictions[selected_name]
        base_names = list(base_predictions)
        for i, row in test.reset_index(drop=True).iterrows():
            votes = [base_predictions[name][i] for name in base_names]
            agreement = max(votes.count(label) for label in bundle["labels"]) / len(votes)
            records.append({
                "fold": fold,
                "selected_model": selected_name,
                "id_entrada": row.id_entrada,
                "doi": row.doi,
                "classe_real": row.classe_alvo,
                "classe_predita": selected_prediction[i],
                "base_model_agreement": agreement,
                "correct": bool(selected_prediction[i] == row.classe_alvo),
            })

    predictions = pd.DataFrame(records)
    rows = []
    for threshold in [0.6, 0.8, 1.0]:
        retained = predictions[predictions.base_model_agreement >= threshold]
        n_total = len(predictions)
        n_retained = len(retained)
        hits = int(retained.correct.sum())
        rows.append({
            "threshold_agreement": threshold,
            "total": n_total,
            "retained": n_retained,
            "abstentions": n_total - n_retained,
            "coverage": n_retained / n_total if n_total else 0,
            "selective_accuracy": hits / n_retained if n_retained else np.nan,
            "hits_retained": hits,
            "rule": "inconclusivo when base-model agreement is below threshold",
        })

    output.mkdir(parents=True)
    predictions.to_csv(output / "frozen_predictions_with_agreement.csv", index=False)
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "abstention_tradeoff.csv", index=False)
    manifest = {
        "source": "nested_balanced_v1 frozen bundles",
        "test_records_per_fold": len(test),
        "folds": len(list(nested.glob("fold_*.joblib"))),
        "probabilities_available": False,
        "decision_signal": "unweighted agreement among five fitted base classifiers",
        "external_labels_used_for_rule": False,
        "models_refit": 0,
        "candidate_only": True,
        "warning": "Agreement is a heuristic selective-prediction signal, not a calibrated probability or formal conformal guarantee.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
