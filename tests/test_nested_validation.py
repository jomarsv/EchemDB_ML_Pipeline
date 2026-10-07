from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from echemdb_ml_pipeline.nested import CORE_FEATURES, fit_internal, make_splits, predict_bundle, vote


def fixture():
    return pd.DataFrame([{'id_entrada': f'row{i}', 'source_group': f'publication{i//2}',
                          'hash_curva': f'hash{i}', 'classe_alvo': ['Ag','Au'][i%2],
                          **{key: i%2 + i/100 + j for j,key in enumerate(CORE_FEATURES)}}
                         for i in range(48)])


class NestedIntegrity(unittest.TestCase):
    def test_all_partition_levels_are_disjoint_and_outer_coverage_once(self):
        frame = fixture()
        seen = []
        for train, test, inner in make_splits(frame):
            seen.extend(test)
            self.assertFalse(set(frame.iloc[train].source_group) & set(frame.iloc[test].source_group))
            for a,b in inner:
                self.assertFalse(set(frame.iloc[train[a]].source_group) & set(frame.iloc[train[b]].source_group))
                self.assertTrue(set(train[a]) | set(train[b]) == set(train))
        self.assertEqual(sorted(seen), list(range(len(frame))))

    def test_cross_source_duplicate_blocks_preflight(self):
        frame = fixture()
        frame.hash_curva = 'same_curve'
        with self.assertRaisesRegex(ValueError, 'overlap'):
            make_splits(frame)

    def test_outer_values_and_labels_cannot_change_internal_fit(self):
        frame = fixture()
        train,test,inner = make_splits(frame)[0]
        specs = {'majority': (DummyClassifier(strategy='most_frequent'), {}),
                 'knn': (KNeighborsClassifier(n_neighbors=3), {}),
                 'logistic': (LogisticRegression(max_iter=1000), {'model__C': [.1, 1.]})}
        first = fit_internal(frame.iloc[train][CORE_FEATURES], frame.iloc[train].classe_alvo, inner, specs)
        frame.loc[test, CORE_FEATURES] = 1e12
        frame.loc[test, 'classe_alvo'] = 'never_seen'
        second = fit_internal(frame.iloc[train][CORE_FEATURES], frame.iloc[train].classe_alvo, inner, specs)
        self.assertEqual(first[3], second[3])
        self.assertEqual(first[1:3], second[1:3])
        for name in first[0]:
            scaler = first[0][name].named_steps['scaler']
            np.testing.assert_allclose(scaler.mean_, frame.iloc[train][CORE_FEATURES].mean())
            np.testing.assert_equal(first[0][name].predict(frame.iloc[train][CORE_FEATURES]),
                                    second[0][name].predict(frame.iloc[train][CORE_FEATURES]))

    def test_vote_has_deterministic_ties(self):
        np.testing.assert_equal(vote([['Ag','Au'],['Au','Au']], [1,1], ['Ag','Au']), ['Ag','Au'])

    def test_saved_real_models_reproduce_every_exported_prediction(self):
        folder = ROOT/'outputs/stage3_nested_sce_v1'
        if not (folder/'COMPLETED.json').exists():
            self.skipTest('Run the pilot first')
        frame = pd.read_csv(folder/'cohort.csv').set_index('id_entrada')
        partitions = pd.read_csv(folder/'partitions.csv')
        for _, part in partitions.groupby(['outer_fold','inner_fold']):
            a = frame.loc[part[part.role == 'train'].id_entrada]
            b = frame.loc[part[part.role != 'train'].id_entrada]
            for col in ['source_group','hash_curva']:
                self.assertFalse(set(a[col]) & set(b[col]))
        holdout = pd.read_csv(ROOT/'outputs/scientific_v2/testes/amostras_teste_atributos_current_density.csv')
        self.assertFalse(set(frame.index) & set(holdout.id_entrada))
        exported = pd.read_csv(folder/'predictions.csv')
        self.assertFalse(exported.duplicated(['model','id_entrada']).any())
        for fold in [1,2,3]:
            bundle = joblib.load(folder/f'fold_{fold}.joblib')
            part = exported[exported.outer_fold == fold]
            ids = part[part.model == 'auto_organizer'].id_entrada.tolist()
            self.assertFalse(set(ids) & set(bundle['training_ids']))
            predictions = predict_bundle(bundle, frame.loc[ids])
            for name, actual in predictions.items():
                expected = part[part.model == name].set_index('id_entrada').loc[ids].predicted.to_numpy()
                np.testing.assert_equal(actual, expected)


if __name__ == '__main__':
    unittest.main()
