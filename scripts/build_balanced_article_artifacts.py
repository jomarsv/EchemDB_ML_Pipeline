"""Build reproducible tables and figures for the balanced frozen evaluation."""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from audit_nested_inputs import ROOT


def wilson_interval(hits, n, z=1.959963984540054):
    if not n:
        return 0.0, 0.0
    p = hits / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def main():
    base = ROOT / "outputs/density_candidate_0_9_2_v1"
    source = base / "external_balanced_frozen_v1"
    partition = base / "partitions_balanced_v1"
    output = base / "article_artifacts_balanced_v5"
    if output.exists():
        raise ValueError("Article artifacts exist; create a new version.")
    output.mkdir(parents=True)

    metrics = pd.read_csv(source / "metrics_by_frozen_fold.csv")
    selected = metrics[metrics.selected_in_development].copy()
    predictions = pd.read_csv(source / "selected_predictions.csv")
    test = pd.read_csv(partition / "test.csv")
    metadata = test[["id_entrada", "doi", "grupo_origem", "classe_alvo"]].drop_duplicates()
    metadata = metadata.rename(columns={"classe_alvo": "classe_real"})
    predictions = predictions.merge(metadata, on=["id_entrada", "classe_real"], how="left")
    if predictions.doi.isna().any():
        raise ValueError("Some frozen predictions lack source metadata.")

    rows = []
    for row in selected.itertuples(index=False):
        hits = int(round(row.accuracy * row.n))
        low, high = wilson_interval(hits, int(row.n))
        rows.append({
            "fold": row.fold,
            "model": row.model,
            "n": int(row.n),
            "hits": hits,
            "accuracy": row.accuracy,
            "accuracy_ci95_low": low,
            "accuracy_ci95_high": high,
            "balanced_accuracy": row.balanced_accuracy,
            "macro_f1": row.macro_f1,
        })
    table = pd.DataFrame(rows)
    table.to_csv(output / "table_frozen_comparison.csv", index=False)

    class_rows = []
    for (fold, model, label), group in predictions.groupby(["fold", "model", "classe_real"], sort=False):
        hits = int((group.classe_real == group.classe_predita).sum())
        n = len(group)
        low, high = wilson_interval(hits, n)
        class_rows.append({"fold": fold, "model": model, "classe": label, "n": n,
                           "hits": hits, "recall": hits / n if n else 0,
                           "recall_ci95_low": low, "recall_ci95_high": high})
    pd.DataFrame(class_rows).to_csv(output / "table_by_class.csv", index=False)

    source_rows = []
    for (fold, model, doi, source_group), group in predictions.groupby(
        ["fold", "model", "doi", "grupo_origem"], sort=False
    ):
        hits = int((group.classe_real == group.classe_predita).sum())
        n = len(group)
        low, high = wilson_interval(hits, n)
        source_rows.append({"fold": fold, "model": model, "doi": doi,
                            "source_group": source_group, "n": n, "hits": hits,
                            "accuracy": hits / n if n else 0,
                            "accuracy_ci95_low": low, "accuracy_ci95_high": high,
                            "classes": ";".join(sorted(group.classe_real.unique()))})
    pd.DataFrame(source_rows).to_csv(output / "table_by_source.csv", index=False)

    labels = ["Accuracy", "Balanced accuracy", "Macro-F1"]
    columns = ["accuracy", "balanced_accuracy", "macro_f1"]
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=180)
    x = range(len(table))
    width = 0.24
    for offset, column, label in zip([-width, 0, width], columns, labels):
        ax.bar([i + offset for i in x], table[column] * 100, width=width, label=label)
    ax.set_xticks(list(x), [f"{r.fold}\n{r.model}" for r in table.itertuples()])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Performance (%)")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=True, facecolor="white", framealpha=0.85, edgecolor="none", ncols=3, loc="lower right", bbox_to_anchor=(0.99, 0.02))
    fig.tight_layout()
    fig.savefig(output / "figure_frozen_metrics.png", bbox_inches="tight")
    fig.savefig(output / "figure_frozen_metrics.pdf", bbox_inches="tight")
    plt.close(fig)

    manifest = {
        "input_metrics": str(source / "metrics_by_frozen_fold.csv"),
        "input_predictions": str(source / "selected_predictions.csv"),
        "output_tables": ["table_frozen_comparison.csv", "table_by_class.csv", "table_by_source.csv"],
        "output_figures": ["figure_frozen_metrics.png", "figure_frozen_metrics.pdf"],
        "confidence_interval": "Wilson 95% interval for binomial accuracy/recall; descriptive because n is small.",
        "no_retraining": True,
        "candidate_only": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output / "README.md").write_text(
        "# Artefatos para o artigo\n\n"
        "Tabelas e figura geradas exclusivamente a partir da avaliacao externa congelada. "
        "Cada fold representa um pacote congelado selecionado no desenvolvimento; "
        "nao se deve tratar as tres linhas como repeticoes independentes de um unico modelo.\n",
        encoding="utf-8",
    )
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
