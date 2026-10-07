"""Evaluate expanded nested bundles on the untouched 65-curve holdout."""
import json
import sys
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.metrics import precision_recall_fscore_support

from audit_nested_inputs import ROOT
sys.path.insert(0, str(ROOT / "src"))
from echemdb_ml_pipeline.nested import CORE_FEATURES, predict_bundle


def main():
    base = ROOT / "outputs/density_candidate_0_9_2_v1"
    part = base / "partitions_expanded_v1"
    nested = base / "nested_expanded_v1"
    output = base / "external_expanded_frozen_v1"
    if output.exists():
        raise ValueError("Expanded frozen evaluation exists; create a new version.")
    test = pd.read_csv(part / "test.csv")
    test["E_span"] = test.E_max - test.E_min
    cohort = pd.read_csv(nested / "candidate_cohort.csv")
    if set(cohort.hash_curva) & set(test.hash_curva):
        raise ValueError("Development and external hashes overlap.")
    labels = ["Ag", "Au", "Pt"]
    X, y = test[CORE_FEATURES], test.classe_alvo
    metrics, class_rows, prediction_rows = [], [], []
    for fold_path in sorted(nested.glob("fold_*.joblib")):
        fold = fold_path.stem
        bundle = joblib.load(fold_path)
        for model, pred in predict_bundle(bundle, X).items():
            metrics.append({"fold": fold, "model": model, "n": len(y),
                            "accuracy": accuracy_score(y, pred),
                            "balanced_accuracy": balanced_accuracy_score(y, pred),
                            "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
                            "selected_in_development": model == bundle["selected"]})
            if model == bundle["selected"]:
                precision, recall, f1, support = precision_recall_fscore_support(y, pred, labels=labels, zero_division=0)
                class_rows.extend({"fold": fold, "model": model, "classe": label, "precision": p,
                                   "recall": r, "f1": score, "support": int(n)}
                                  for label, p, r, score, n in zip(labels, precision, recall, f1, support))
                prediction_rows.extend({"fold": fold, "model": model, "id_entrada": entry,
                                        "classe_real": real, "classe_predita": guessed}
                                       for entry, real, guessed in zip(test.id_entrada, y, pred))
    output.mkdir(parents=True)
    pd.DataFrame(metrics).to_csv(output / "metrics_by_frozen_fold.csv", index=False)
    pd.DataFrame(class_rows).to_csv(output / "selected_class_metrics.csv", index=False)
    pd.DataFrame(prediction_rows).to_csv(output / "selected_predictions.csv", index=False)
    manifest = {"partition": "partitions_expanded_v1", "test_records_total": len(test),
                "evaluated_records": len(test), "evaluated_classes": labels,
                "fold_bundles": len(list(nested.glob("fold_*.joblib"))),
                "external_labels_used_for_selection": False, "models_refit": 0,
                "candidate_only": True,
                "interpretation": "Each row is an independent frozen outer-fold bundle; do not pool repeated predictions as a single model."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(pd.DataFrame(metrics).query("selected_in_development").to_string(index=False))


if __name__ == "__main__":
    main()
