"""Check the browser-oriented scientific outputs without graphics dependencies."""
import unittest
import xml.etree.ElementTree as ET
from analysis.presentation import core_forest, design_protocol, interval, table, MODELS, DATASETS


class PresentationTests(unittest.TestCase):
    def test_interval_uses_supplied_values(self):
        self.assertEqual(interval({'estimate':.123456,'ci95':[-.04,.28]}), '0.1235 [-0.0400, 0.2800]')

    def test_markdown_escapes_cells(self):
        rendered = table(1, 'Example', ['x'], [['a|b']])
        self.assertIn('a\\|b', rendered)
        self.assertIn('\n\n| x |', rendered)

    def test_forest_has_nine_intervals(self):
        statistics = {'models': {m: {'core': {'complete_valid': {
            d: {'estimate':.3, 'ci95':[.2,.4]} for d in (*DATASETS,'macro')}}} for m in MODELS}}
        figure = core_forest(statistics)
        root = ET.fromstring(figure)
        self.assertEqual(sum('data-ci' in node.attrib for node in root.iter()), 9)
        self.assertEqual(figure.count('0.3000 [0.2000, 0.4000]'), 9)

    def test_design_names_all_four_disagreements(self):
        svg = design_protocol()
        ET.fromstring(svg)
        for phrase in ('A: P != R', 'B: P&#x27; != R&#x27;', 'C: P != P&#x27;', 'D: R != R&#x27;'):
            self.assertIn(phrase, svg)


if __name__ == '__main__':
    unittest.main()
