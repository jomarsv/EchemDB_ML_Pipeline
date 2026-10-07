"""Evaluate consensus abstention on expanded frozen bundles."""
import json
import sys
import joblib
import numpy as np
import pandas as pd
from audit_nested_inputs import ROOT
sys.path.insert(0, str(ROOT / "src"))
from echemdb_ml_pipeline.nested import CORE_FEATURES, vote


def main():
    base = ROOT / "outputs/density_candidate_0_9_2_v1"
    part, nested = base / "partitions_expanded_v1", base / "nested_expanded_v1"
    output = base / "abstention_expanded_v1"
    if output.exists():
        raise ValueError("Expanded abstention output exists; create a new version.")
    test = pd.read_csv(part / "test.csv")
    test["E_span"] = test.E_max - test.E_min
    records = []
    for path in sorted(nested.glob("fold_*.joblib")):
        bundle = joblib.load(path)
        base_predictions = {name: model.predict(test[CORE_FEATURES]) for name, model in bundle["models"].items()}
        selected = bundle["selected"]
        pred = (vote([base_predictions[m] for m in bundle["ensembles"][selected]["members"]],
                     bundle["ensembles"][selected]["weights"], bundle["labels"])
                if selected in bundle["ensembles"] else base_predictions[selected])
        for i, row in test.reset_index(drop=True).iterrows():
            votes = [p[i] for p in base_predictions.values()]
            agreement = max(votes.count(label) for label in bundle["labels"]) / len(votes)
            records.append({"fold": path.stem, "id_entrada": row.id_entrada,
                            "classe_real": row.classe_alvo, "classe_predita": pred[i],
                            "agreement": agreement, "correct": bool(pred[i] == row.classe_alvo)})
    frame = pd.DataFrame(records)
    rows = []
    for threshold in [0.6, 0.8, 1.0]:
        kept = frame[frame.agreement >= threshold]
        rows.append({"threshold_agreement": threshold, "total": len(frame), "retained": len(kept),
                     "abstentions": len(frame)-len(kept), "coverage": len(kept)/len(frame),
                     "selective_accuracy": kept.correct.mean() if len(kept) else np.nan,
                     "hits_retained": int(kept.correct.sum())})
    output.mkdir(parents=True)
    frame.to_csv(output / "frozen_predictions_with_agreement.csv", index=False)
    pd.DataFrame(rows).to_csv(output / "abstention_tradeoff.csv", index=False)
    (output / "manifest.json").write_text(json.dumps({"test_records_per_fold": len(test), "folds": 3,
        "decision_signal": "unweighted agreement among five fitted base classifiers",
        "external_labels_used_for_rule": False, "models_refit": 0, "candidate_only": True,
        "warning": "Heuristic selective-prediction signal; not calibrated probability."}, indent=2), encoding="utf-8")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
