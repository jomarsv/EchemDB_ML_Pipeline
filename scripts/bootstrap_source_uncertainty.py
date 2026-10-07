"""Cluster-bootstrap uncertainty for nested out-of-fold predictions by DOI."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
LABELS = ["Ag", "Au"]
MODELS = ["auto_organizer", "knn", "forest"]
PAIRS = [("auto_organizer", "knn"), ("auto_organizer", "forest")]
PAIR_MODELS = {f"auto_minus_{other}": (auto, other) for auto, other in PAIRS}
METRICS = ["accuracy", "balanced_accuracy", "macro_f1"]


def score(y, predicted):
    result = {"accuracy": float(np.mean(y == predicted))}
    recalls, f1s = [], []
    for label in LABELS:
        actual = y == label
        guessed = predicted == label
        tp = int(np.count_nonzero(actual & guessed))
        fn = int(np.count_nonzero(actual & ~guessed))
        fp = int(np.count_nonzero(~actual & guessed))
        recall = tp / (tp + fn) if tp + fn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        recalls.append(recall)
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    result["balanced_accuracy"] = float(np.mean(recalls))
    result["macro_f1"] = float(np.mean(f1s))
    return result


def sample_source_indices(strata, rows_by_group, rng):
    sampled_groups = []
    for groups in strata.values():
        sampled_groups.extend(rng.choice(groups, size=len(groups), replace=True).tolist())
    return np.concatenate([rows_by_group[group] for group in sampled_groups])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replicates", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20261007)
    args = parser.parse_args()
    manifest_path = args.output.with_suffix(".json")
    if args.output.exists() or manifest_path.exists():
        raise FileExistsError("Output exists; choose a new versioned path.")
    if args.replicates < 1000:
        raise ValueError("Use at least 1000 bootstrap replicates.")

    data = pd.read_csv(args.predictions)
    required = {"model", "id_entrada", "source_group", "expected", "predicted"}
    if missing := required - set(data.columns):
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if set(data.expected.unique()) != set(LABELS):
        raise ValueError("This pilot bootstrap expects exactly Ag and Au.")
    if data.duplicated(["model", "id_entrada"]).any():
        raise ValueError("Predictions must have one row per model and curve.")

    curve_groups = data[["id_entrada", "source_group", "expected"]].drop_duplicates()
    if curve_groups.id_entrada.duplicated().any():
        raise ValueError("A curve maps to multiple DOI groups or labels.")
    source_labels = curve_groups.groupby("source_group").expected.nunique()
    if source_labels.gt(1).any():
        raise ValueError("A source spans labels; class-stratified DOI bootstrap is invalid.")
    strata = {
        label: sorted(curve_groups.loc[curve_groups.expected == label, "source_group"].unique())
        for label in LABELS
    }
    if any(not groups for groups in strata.values()):
        raise ValueError("Every label needs at least one independent DOI group.")

    missing_models = set(MODELS) - set(data.model.unique())
    if missing_models:
        raise ValueError(f"Missing comparison models: {sorted(missing_models)}")
    wide = data.pivot(index="id_entrada", columns="model", values="predicted")
    wide = wide.reindex(curve_groups.id_entrada)
    if wide[MODELS].isna().any().any():
        raise ValueError("Comparison models must predict every curve exactly once.")
    labels = curve_groups.expected.to_numpy()
    groups_by_id = curve_groups.source_group.to_numpy()
    rows_by_group = {
        group: np.flatnonzero(groups_by_id == group)
        for group in curve_groups.source_group.unique()
    }
    predictions = {model: wide[model].to_numpy() for model in MODELS}

    rng = np.random.default_rng(args.seed)
    bootstrap = {model: {metric: np.empty(args.replicates) for metric in METRICS} for model in MODELS}
    paired = {
        f"auto_minus_{other}": {metric: np.empty(args.replicates) for metric in METRICS}
        for _, other in PAIRS
    }

    for draw in range(args.replicates):
        row_indices = sample_source_indices(strata, rows_by_group, rng)
        y = labels[row_indices]
        scores = {model: score(y, predictions[model][row_indices]) for model in MODELS}
        for model in MODELS:
            for metric in METRICS:
                bootstrap[model][metric][draw] = scores[model][metric]
        for key, (reference, other) in zip(paired, PAIRS):
            for metric in METRICS:
                paired[key][metric][draw] = scores[reference][metric] - scores[other][metric]

    output_rows = []
    for model, draws in bootstrap.items():
        for metric in METRICS:
            point = score(labels, predictions[model])[metric]
            low, high = np.quantile(draws[metric], [0.025, 0.975])
            output_rows.append({"estimand": model, "metric": metric, "estimate": point,
                                "ci95_low": low, "ci95_high": high})
    for estimand, draws in paired.items():
        reference, other = PAIR_MODELS[estimand]
        for metric, values in draws.items():
            low, high = np.quantile(values, [0.025, 0.975])
            point = score(labels, predictions[reference])[metric] - score(labels, predictions[other])[metric]
            output_rows.append({"estimand": estimand, "metric": metric, "estimate": point,
                                "ci95_low": low, "ci95_high": high})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_rows).to_csv(args.output, index=False)
    manifest = {
        "method": "class-stratified nonparametric cluster bootstrap; DOI is the resampling unit",
        "replicates": args.replicates,
        "seed": args.seed,
        "labels": LABELS,
        "source_groups_by_label": {label: len(groups) for label, groups in strata.items()},
        "curves": int(curve_groups.id_entrada.nunique()),
        "input_sha256": hashlib.sha256(args.predictions.read_bytes()).hexdigest(),
        "interval": "empirical percentile 2.5th and 97.5th quantiles; exploratory with few DOI groups",
        "paired_differences": "Auto organizer minus comparator; paired resampling of identical DOI groups",
        "limitations": [
            "only nine DOI groups across two classes",
            "OOF predictions come from three outer folds and historically explored data",
            "intervals quantify source-resampling variability conditional on these predictions, not full retraining variability",
            "not a confirmatory significance test",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(pd.DataFrame(output_rows).to_string(index=False))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
