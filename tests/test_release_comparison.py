import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compare_releases import overlap_flags


class ReleaseTests(unittest.TestCase):
    def test_renamed_or_changed_holdout_remains_protected(self):
        held = pd.DataFrame([{'id_entrada': 'old', 'source_group': 'doi', 'hash_curva': 'hash'}])
        for row in [dict(id_entrada='new', source_group='doi', hash_curva='changed'),
                    dict(id_entrada='old', source_group='corrected', hash_curva='changed'),
                    dict(id_entrada='new', source_group='new', hash_curva='hash')]:
            self.assertTrue(any(overlap_flags(row, held).values()))

    def test_independent_record_not_marked_as_test(self):
        held = pd.DataFrame([{'id_entrada': 'old', 'source_group': 'doi', 'hash_curva': 'hash'}])
        row = dict(id_entrada='new', source_group='new', hash_curva='new')
        self.assertFalse(any(overlap_flags(row, held).values()))
