"""Source-disjoint nested pilot. No external label is used for model selection."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

SEED = 20260918
CORE_FEATURES = ['E_span', 'j_min', 'j_max', 'j_media', 'j_desvio_padrao', 'area_absoluta', 'area_liquida']


def metrics(y, pred):
    return dict(accuracy=float(accuracy_score(y, pred)),
                balanced_accuracy=float(balanced_accuracy_score(y, pred)),
                macro_f1=float(f1_score(y, pred, average='macro', zero_division=0)),
                hits=int(np.sum(np.asarray(y) == np.asarray(pred))), n=len(y))


def candidate_specs(seed=SEED):
    return {
        'majority': (DummyClassifier(strategy='most_frequent'), {}),
        'knn': (KNeighborsClassifier(weights='distance'), {'model__n_neighbors': [3, 5, 9]}),
        'logistic': (LogisticRegression(max_iter=3000, random_state=seed),
                     {'model__C': [.1, 1., 10.], 'model__class_weight': [None, 'balanced']}),
        'svm': (SVC(kernel='rbf'), {'model__C': [.1, 1., 10.], 'model__class_weight': [None, 'balanced']}),
        'forest': (RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1),
                   {'model__max_depth': [4, None], 'model__class_weight': [None, 'balanced']}),
    }


def pipeline(estimator):
    return Pipeline([('imputer', SimpleImputer(strategy='mean', keep_empty_features=True)),
                     ('scaler', StandardScaler()), ('model', estimator)])


def rank_key(item):
    # Insertion order is the predeclared tie-breaker after the two metrics.
    return (item['balanced_accuracy'], item['macro_f1'])


def vote(predictions, weights, labels):
    predictions = np.asarray(predictions)
    scores = np.stack([np.sum((predictions == label) * np.asarray(weights)[:, None], axis=0)
                       for label in labels], axis=1)
    return np.asarray(labels)[np.argmax(scores, axis=1)]


def make_splits(frame, outer_folds=3, inner_folds=2, seed=SEED):
    labels = set(frame.classe_alvo)
    if len(labels) < 2 or frame.source_group.nunique() < outer_folds:
        raise ValueError('Insufficient classes/sources for the declared pilot')
    def validate(train, test):
        a, b = frame.iloc[train], frame.iloc[test]
        for col in ['id_entrada', 'source_group', 'hash_curva']:
            if set(a[col]) & set(b[col]):
                raise ValueError(f'Partition overlap: {col}')
        if set(a.classe_alvo) != labels or set(b.classe_alvo) != labels:
            raise ValueError('A declared fold lacks a class. Revise feasibility before fitting; do not retry seeds by score.')
    outer = StratifiedGroupKFold(n_splits=outer_folds, shuffle=True, random_state=seed)
    result = []
    for fold, (train, test) in enumerate(outer.split(frame, frame.classe_alvo, frame.source_group)):
        validate(train, test)
        sub = frame.iloc[train]
        inner = list(StratifiedGroupKFold(n_splits=inner_folds, shuffle=True, random_state=seed+fold+1)
                     .split(sub, sub.classe_alvo, sub.source_group))
        for a, b in inner:
            validate(train[a], train[b])
            if len(a) < 9:
                raise ValueError('Inner training set smaller than the maximum declared k=9')
        result.append((train, test, inner))
    return result


def fit_internal(X, y, inner, specs=None):
    specs = specs or candidate_specs()
    fitted, scores, oof = {}, {}, {}
    for name, (estimator, grid) in specs.items():
        search = GridSearchCV(pipeline(estimator), grid, cv=inner,
                              scoring={'balanced_accuracy': 'balanced_accuracy', 'macro_f1': 'f1_macro'},
                              refit='balanced_accuracy', error_score='raise', n_jobs=1)
        search.fit(X, y)
        fitted[name] = search.best_estimator_
        pred = cross_val_predict(clone(search.best_estimator_), X, y, cv=inner, method='predict', n_jobs=1)
        oof[name] = pred
        scores[name] = {**metrics(y, pred), 'params': search.best_params_,
                        'grid_balanced_accuracy': float(search.best_score_)}
    singles = [name for name in specs if name != 'majority']
    top = sorted(singles, key=lambda name: rank_key(scores[name]), reverse=True)[:3]
    ensembles = {}
    for name, members in [('ensemble_all', singles), ('ensemble_top3', top)]:
        weights = [max(scores[m]['balanced_accuracy'], .01) for m in members]
        ensembles[name] = {'members': members, 'weights': weights}
        pred = vote([oof[m] for m in members], weights, sorted(set(y)))
        scores[name] = {**metrics(y, pred), **ensembles[name]}
    eligible = singles + list(ensembles)
    selected = max(eligible, key=lambda name: rank_key(scores[name]))
    return fitted, ensembles, scores, selected


def predict_bundle(bundle, X):
    X = X[bundle['features']]
    predictions = {name: model.predict(X) for name, model in bundle['models'].items()}
    for name, item in bundle['ensembles'].items():
        predictions[name] = vote([predictions[m] for m in item['members']], item['weights'], bundle['labels'])
    predictions['auto_organizer'] = predictions[bundle['selected']].copy()
    return predictions


def run_nested(frame, out, config, outer_folds=3, inner_folds=2):
    if out.exists():
        raise FileExistsError(f'Refusing to overwrite an experiment: {out}')
    splits = make_splits(frame, outer_folds, inner_folds)
    out.mkdir(parents=True)
    X, y = frame[CORE_FEATURES], frame.classe_alvo
    memberships = []
    for fold, (train, test, inner) in enumerate(splits, 1):
        for role, ids in [('train', train), ('test', test)]:
            for idx in ids:
                memberships.append({'outer_fold': fold, 'inner_fold': 0, 'role': role,
                                    'id_entrada': frame.iloc[idx].id_entrada})
        for number, (a, b) in enumerate(inner, 1):
            for role, ids in [('train', train[a]), ('validation', train[b])]:
                for idx in ids:
                    memberships.append({'outer_fold': fold, 'inner_fold': number, 'role': role,
                                        'id_entrada': frame.iloc[idx].id_entrada})
    manifest = {**config, 'seed': SEED, 'outer_folds': outer_folds, 'inner_folds': inner_folds,
                'features': CORE_FEATURES, 'n': len(frame), 'sources': frame.source_group.nunique(),
                'labels': sorted(set(y)), 'status': 'exploratory_pilot_not_confirmatory',
                'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__,
                             'numpy': np.__version__, 'pandas': pd.__version__},
                'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'grids': {name: grid for name, (_, grid) in candidate_specs().items()},
                'tie_order': list(candidate_specs()) + ['ensemble_all', 'ensemble_top3'],
                'selection': 'inner pooled OOF balanced accuracy, then macro F1, then fixed order',
                'warning': 'Inner scores used for tuning/ensemble weighting are optimistic; only outer scores evaluate this procedure.'}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    pd.DataFrame(memberships).to_csv(out/'partitions.csv', index=False)
    frame.to_csv(out/'cohort.csv', index=False)
    records, fold_scores, decisions = [], [], []
    for fold, (train, test, inner) in enumerate(splits, 1):
        models, ensembles, scores, selected = fit_internal(X.iloc[train], y.iloc[train], inner)
        bundle = {'models': models, 'ensembles': ensembles, 'selected': selected,
                  'features': CORE_FEATURES, 'labels': sorted(set(y.iloc[train])),
                  'training_ids': frame.iloc[train].id_entrada.tolist(), 'version': 'nested-core-v1'}
        joblib.dump(bundle, out/f'fold_{fold}.joblib')
        predictions = predict_bundle(bundle, X.iloc[test])
        decisions.append({'fold': fold, 'selected': selected, 'inner_scores': scores})
        for name, pred in predictions.items():
            fold_scores.append({'fold': fold, 'model': name, **metrics(y.iloc[test], pred)})
            for idx, predicted in zip(test, pred):
                row = frame.iloc[idx]
                records.append({'outer_fold': fold, 'model': name, 'selected_internal': selected,
                                'id_entrada': row.id_entrada, 'source_group': row.source_group,
                                'expected': row.classe_alvo, 'predicted': predicted})
        print(f'Fold {fold}/{outer_folds} complete; internal selection: {selected}', flush=True)
    predictions = pd.DataFrame(records)
    predictions.to_csv(out/'predictions.csv', index=False)
    pd.DataFrame(fold_scores).to_csv(out/'fold_metrics.csv', index=False)
    (out/'internal_selection.json').write_text(json.dumps(decisions, indent=2), encoding='utf-8')
    summary = pd.DataFrame([{'model': name, **metrics(part.expected, part.predicted)}
                            for name, part in predictions.groupby('model', sort=False)])
    summary.to_csv(out/'pooled_metrics.csv', index=False)
    (out/'COMPLETED.json').write_text(json.dumps({'complete': True, 'folds': len(splits)}), encoding='utf-8')
    return summary
