"""Nomenclature coverage gate + data integrity (Tasks 8/10, TR-8.1/TR-9.1).

Muscles + organs must keep >= 90% Chinese-name coverage. Every assignment with
an id must resolve to a unique record. Functional groups are required for
mapped muscle/organ nodes so the structure tree can render 系统→区域→群→亚群.
Pure data/script checks; no browser needed.
"""
import json, unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NomenclatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nom = json.loads((ROOT / 'web' / 'nomenclature.json').read_text(encoding='utf-8'))
        cls.cov = json.loads((ROOT / 'tools' / 'data' / 'nomenclature_coverage.json').read_text(encoding='utf-8'))
        cls.records = cls.nom['records']
        cls.assignments = cls.nom['assignments']

    def test_record_ids_unique(self):
        ids = list(self.records)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.nom['recordCount'], len(self.records))

    def test_assignments_resolve(self):
        for a in self.assignments:
            if a.get('id'):
                self.assertIn(a['id'], self.records, f"assignment {a.get('name')} -> missing record")

    def test_muscles_organs_coverage_gate_90(self):
        self.assertGreaterEqual(self.cov['muscles_organs_coverage'], 90.0)
        for sysname in ('muscles', 'organs'):
            self.assertEqual(self.cov['systems'][sysname]['coverage'], 100.0)

    def test_mapped_muscle_organs_have_functional_group(self):
        # Every mapped muscle/organ node must be classifiable into a functional
        # group for the hierarchical tree (AC-5).
        missing = Counter()
        for a in self.assignments:
            if a['system'] not in ('muscles', 'organs') or not a.get('id'):
                continue
            rec = self.records[a['id']]
            if rec.get('zh') and not rec.get('group'):
                missing[a['system']] += 1
        self.assertEqual(dict(missing), {}, f"mapped nodes without group: {dict(missing)}")

    def test_wrist_curriculum_references_resolve(self):
        # Lightweight data-level mirror of tools/validate_curriculum.py so the
        # Python build gate and the packaging suite both protect the wrist lesson.
        cur = json.loads((ROOT / 'web' / 'curriculum.json').read_text(encoding='utf-8'))
        wrist = next(l for l in cur['lessons'] if l['id'] == 'wrist')
        self.assertTrue(wrist['complete'])
        ids = set()
        for step in wrist['assembly']:
            ids.update(step['ids'])
        for m in wrist['motions']:
            ids.update(m['movingIds'])
        unresolved = [i for i in ids if i not in self.records]
        self.assertEqual(unresolved, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
