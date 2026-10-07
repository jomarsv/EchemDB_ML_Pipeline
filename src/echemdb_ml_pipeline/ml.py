from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from .features import FEATURE_VERSION, NUMERIC_FEATURES


def run_models(features: pd.DataFrame, curves: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame()
    reports = []
    for kind, unit in [("current", "A"), ("current_density", "A/m2")]:
        subset = features[(features.tipo_sinal == kind) & (features.status == "valido")].copy()
        if subset.empty:
            continue
        if (not subset.versao_atributos.eq(FEATURE_VERSION).all()
                or not subset.unidade_sinal_usada.eq(unit).all()
                or not subset.unidade_potencial_usada.eq("V").all()):
            raise ValueError("Atributos ou unidades incompativeis com o protocolo v2")
        groups = subset.grupo_origem.fillna("").astype(str).str.strip().str.lower()
        groups = groups.str.replace(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", regex=True)
        if groups.eq("").any() or subset.hash_curva.isna().any():
            raise ValueError("Fonte ou hash ausente: avaliacao agrupada bloqueada")
        subset["grupo_origem"] = groups
        directory = output_dir / kind
        directory.mkdir(exist_ok=True)
        subcurves = curves[curves.tipo_sinal == kind] if not curves.empty else curves
        report = _run_models(subset, subcurves, directory)
        report["tipo_sinal"] = kind
        report["protocolo"] = "validacao_agrupada_exploratoria_sem_selecao"
        reports.append(report)
    return pd.concat(reports, ignore_index=True) if reports else pd.DataFrame()


def _run_models(features: pd.DataFrame, curves: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    try:
        from sklearn.cluster import DBSCAN, KMeans
        from sklearn.decomposition import PCA
        from sklearn.ensemble import IsolationForest, RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            davies_bouldin_score,
            f1_score,
            precision_score,
            recall_score,
            silhouette_score,
        )
        from sklearn.model_selection import GroupShuffleSplit
        from sklearn.neighbors import KNeighborsClassifier, LocalOutlierFactor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(
            [
                {
                    "problema": "todos",
                    "modelo": "sklearn",
                    "status": "ignorado",
                    "metrica": "dependencia_ausente",
                    "valor": np.nan,
                    "observacao": str(exc),
                }
            ]
        )

    X_features, y, feature_names = _feature_matrix(features)
    if X_features is None or y is None:
        rows.append(_row("classificacao_material", "todos", "ignorado", "motivo", np.nan, "dados insuficientes"))
    else:
        class_counts = y.value_counts()
        if len(class_counts) < 2 or len(y) < 6 or features.loc[y.index, "grupo_origem"].nunique() < 2:
            rows.append(
                _row(
                    "classificacao_material",
                    "todos",
                    "ignorado",
                    "motivo",
                    np.nan,
                    "menos de duas classes com amostras suficientes",
                )
            )
        else:
            groups = features.loc[y.index, "grupo_origem"]
            train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42).split(X_features, y, groups))
            X_train, X_test = X_features.iloc[train_idx], X_features.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            hashes = features.loc[y.index, "hash_curva"]
            if set(hashes.iloc[train_idx]) & set(hashes.iloc[test_idx]):
                raise ValueError("Curvas duplicadas entre fontes de treino e validacao")
            # Availability-based feature selection belongs to the training partition too.
            feature_names = X_train.columns[X_train.notna().any()].tolist()
            X_train, X_test = X_train[feature_names], X_test[feature_names]
            models = {
                "RandomForest": make_pipeline(SimpleImputer(), RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")),
                "SVM_RBF": make_pipeline(SimpleImputer(), StandardScaler(), SVC(kernel="rbf", class_weight="balanced")),
                "KNN": make_pipeline(
                    SimpleImputer(),
                    StandardScaler(),
                    KNeighborsClassifier(n_neighbors=max(1, min(5, len(X_train)))),
                ),
            }
            for model_name, model in models.items():
                if y_train.nunique() < 2:
                    rows.append(_row("classificacao_material", model_name, "ignorado", "motivo", np.nan, "treino com uma classe"))
                    continue
                model.fit(X_train, y_train)
                pred = model.predict(X_test)
                metrics = {
                    "accuracy": accuracy_score(y_test, pred),
                    "precision_weighted": precision_score(y_test, pred, average="weighted", zero_division=0),
                    "recall_weighted": recall_score(y_test, pred, average="weighted", zero_division=0),
                    "f1_weighted": f1_score(y_test, pred, average="weighted", zero_division=0),
                }
                for metric_name, value in metrics.items():
                    rows.append(_row("classificacao_material", model_name, "ok", metric_name, value, "features"))
                labels = sorted(y.unique())
                matrix = confusion_matrix(y_test, pred, labels=labels)
                _plot_confusion(matrix, labels, model_name, output_dir / f"matriz_confusao_{model_name}.png")
                _plot_importance(model.steps[-1][1], feature_names, output_dir / f"importancia_{model_name}.png")

    X_curves, curve_labels = _curve_matrix(curves)
    if X_curves is None:
        rows.append(_row("agrupamento", "todos", "ignorado", "motivo", np.nan, "curvas interpoladas insuficientes"))
    else:
        X_scaled = make_pipeline(SimpleImputer(), StandardScaler()).fit_transform(X_curves)
        n_components = min(2, X_scaled.shape[0], X_scaled.shape[1])
        if n_components >= 2:
            pca = PCA(n_components=2, random_state=42)
            coords = pca.fit_transform(X_scaled)
            rows.append(_row("agrupamento", "PCA", "ok", "variancia_pc1", pca.explained_variance_ratio_[0], "curvas"))
            rows.append(_row("agrupamento", "PCA", "ok", "variancia_pc2", pca.explained_variance_ratio_[1], "curvas"))
            _plot_pca(coords, curve_labels, output_dir / "pca_voltamogramas.png")

            if len(X_scaled) >= 4:
                k = min(5, max(2, int(np.sqrt(len(X_scaled)))))
                kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
                clusters = kmeans.fit_predict(X_scaled)
                rows.extend(_cluster_metrics("KMeans", X_scaled, clusters, silhouette_score, davies_bouldin_score))
                _plot_clusters(coords, clusters, output_dir / "clusters_voltamogramas.png")

                dbscan = DBSCAN(eps=0.8, min_samples=max(2, min(5, len(X_scaled) // 10 or 2)))
                dbscan_labels = dbscan.fit_predict(X_scaled)
                rows.extend(_cluster_metrics("DBSCAN", X_scaled, dbscan_labels, silhouette_score, davies_bouldin_score))

        if len(X_scaled) >= 10:
            isolation = IsolationForest(random_state=42, contamination="auto")
            scores = isolation.fit_predict(X_scaled)
            anomaly_count = int(np.sum(scores == -1))
            rows.append(_row("anomalias", "IsolationForest", "ok", "anomalias_detectadas", anomaly_count, "curvas"))
            lof = LocalOutlierFactor(n_neighbors=max(2, min(20, len(X_scaled) - 1)))
            lof_scores = lof.fit_predict(X_scaled)
            rows.append(_row("anomalias", "LocalOutlierFactor", "ok", "anomalias_detectadas", int(np.sum(lof_scores == -1)), "curvas"))
        else:
            rows.append(_row("anomalias", "todos", "ignorado", "motivo", np.nan, "menos de 10 curvas validas"))

    return pd.DataFrame(rows)


def _feature_matrix(features: pd.DataFrame) -> tuple[pd.DataFrame | None, pd.Series | None, list[str]]:
    if features.empty or "classe_alvo" not in features:
        return None, None, []
    valid = features[(features["status"] == "valido") & features["classe_alvo"].notna()].copy()
    valid = valid[~valid["classe_alvo"].isin(["", "unknown", "desconhecido"])]
    numeric = valid[list(NUMERIC_FEATURES)].apply(pd.to_numeric, errors="coerce")
    if valid.empty or numeric.empty:
        return None, None, []
    return numeric, valid["classe_alvo"].astype(str), list(numeric.columns)


def _curve_matrix(curves: pd.DataFrame) -> tuple[pd.DataFrame | None, pd.Series | None]:
    if curves.empty:
        return None, None
    columns = [column for column in curves.columns if column.startswith("f")]
    if len(columns) < 2 or len(curves) < 2:
        return None, None
    labels = curves["material_eletrodo"].fillna("desconhecido") if "material_eletrodo" in curves else None
    return curves[columns], labels


def _cluster_metrics(model_name: str, X: np.ndarray, labels: np.ndarray, silhouette_score, davies_bouldin_score) -> list[dict[str, Any]]:
    unique = set(labels)
    if len(unique - {-1}) < 2:
        return [_row("agrupamento", model_name, "ignorado", "motivo", np.nan, "menos de dois grupos nao-ruido")]
    return [
        _row("agrupamento", model_name, "ok", "silhouette", silhouette_score(X, labels), "curvas"),
        _row("agrupamento", model_name, "ok", "davies_bouldin", davies_bouldin_score(X, labels), "curvas"),
        _row("agrupamento", model_name, "ok", "numero_grupos", len(unique - {-1}), "curvas"),
    ]


def _plot_confusion(matrix: np.ndarray, labels: list[str], title: str, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except Exception:  # noqa: BLE001
        return
    plt.figure(figsize=(max(6, len(labels) * 0.8), max(4, len(labels) * 0.7)))
    sns.heatmap(matrix, annot=True, fmt="d", xticklabels=labels, yticklabels=labels, cmap="Blues")
    plt.title(f"Matriz de confusao - {title}")
    plt.xlabel("Predito")
    plt.ylabel("Real")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _plot_importance(model: Any, feature_names: list[str], path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return
    if model is None or not hasattr(model, "feature_importances_"):
        return
    values = np.asarray(model.feature_importances_)
    order = np.argsort(values)[-20:]
    plt.figure(figsize=(8, max(4, len(order) * 0.3)))
    plt.barh([feature_names[index] for index in order], values[order])
    plt.title("Importancia dos atributos")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _plot_pca(coords: np.ndarray, labels: pd.Series | None, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return
    plt.figure(figsize=(7, 5))
    if labels is None:
        plt.scatter(coords[:, 0], coords[:, 1], s=28)
    else:
        for label in sorted(set(labels.astype(str))):
            mask = labels.astype(str) == label
            plt.scatter(coords[mask, 0], coords[mask, 1], s=28, label=label)
        plt.legend(fontsize=8, loc="best")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title("PCA dos voltamogramas interpolados")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _plot_clusters(coords: np.ndarray, labels: np.ndarray, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return
    plt.figure(figsize=(7, 5))
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=labels, s=28, cmap="tab10")
    plt.colorbar(scatter, label="Cluster")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title("Agrupamento dos voltamogramas")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def _row(problem: str, model: str, status: str, metric: str, value: Any, note: str) -> dict[str, Any]:
    return {
        "problema": problem,
        "modelo": model,
        "status": status,
        "metrica": metric,
        "valor": value,
        "observacao": note,
    }
