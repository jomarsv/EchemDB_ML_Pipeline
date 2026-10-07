"""Build table and figure for the expanded frozen external evaluation."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from audit_nested_inputs import ROOT


def main():
    base = ROOT / "outputs/density_candidate_0_9_2_v1"
    source = base / "external_expanded_frozen_v1"
    output = base / "article_artifacts_expanded_v3"
    if output.exists():
        raise ValueError("Expanded article artifacts exist; create a new version.")
    output.mkdir(parents=True)
    metrics = pd.read_csv(source / "metrics_by_frozen_fold.csv")
    selected = metrics[metrics.selected_in_development].copy()
    selected["hits"] = (selected.accuracy * selected.n).round().astype(int)
    selected[["fold", "model", "n", "hits", "accuracy", "balanced_accuracy", "macro_f1"]].to_csv(
        output / "table_expanded_frozen.csv", index=False
    )
    with (output / "table_expanded_frozen.tex").open("w", encoding="utf-8") as f:
        f.write("\\begin{table}[H]\n\\caption{Frozen-package performance on the 65-curve source-disjoint external test set.}\\label{tab:expandedfrozen}\n\\centering\\small\n")
        f.write("\\begin{tabular}{lrrrrr}\\toprule\nFold & Package & $n$ & Hits & Accuracy & Balanced accuracy & Macro-F1 \\\\\n\\midrule\n")
        for row in selected.itertuples():
            f.write(f"{row.fold.replace('fold_', '')} & {row.model} & {row.n} & {row.hits}/{row.n} & {row.accuracy*100:.1f}\% & {row.balanced_accuracy*100:.1f}\% & {row.macro_f1*100:.1f}\% \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n\\end{table}\n")
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=180)
    x = range(len(selected))
    width = 0.24
    for offset, col, label in [(-width, "accuracy", "Accuracy"), (0, "balanced_accuracy", "Balanced accuracy"), (width, "macro_f1", "Macro-F1")]:
        ax.bar([i + offset for i in x], selected[col] * 100, width, label=label)
    ax.set_xticks(list(x), [f"{r.fold}\\n{r.model}" for r in selected.itertuples()])
    ax.set_ylim(0, 100); ax.set_ylabel("Performance (%)")
    ax.grid(axis="y", alpha=0.25); ax.legend(frameon=True, facecolor="white", framealpha=0.85, edgecolor="none", ncols=3, loc="lower right", bbox_to_anchor=(0.99, 0.02))
    fig.tight_layout(); fig.savefig(output / "fig_expanded_frozen.pdf", bbox_inches="tight"); fig.savefig(output / "fig_expanded_frozen.png", bbox_inches="tight"); plt.close(fig)
    (output / "manifest.json").write_text(json.dumps({"test_records": 65, "test_sources": 15, "candidate_only": True, "no_refit": True}, indent=2), encoding="utf-8")
    print(selected.to_string(index=False))


if __name__ == "__main__":
    main()
