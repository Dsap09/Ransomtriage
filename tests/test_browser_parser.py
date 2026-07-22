import os
import unittest
from pathlib import Path
from ransomtriage.parsers.browser import BrowserParser

class TestBrowserParser(unittest.TestCase):

    def setUp(self):
        self.dummy_dir = Path(__file__).parent / "dummy_artifacts"
        self.history_path = str(self.dummy_dir / "scenario_a" / "History")

    def test_browser_parser_valid(self):
        parser = BrowserParser(self.history_path)
        self.assertTrue(parser.validate())
        records = parser.parse()
        self.assertGreater(len(records), 0)
        self.assertEqual(records[0]["filename"], "laporan_keuangan.pdf")

    def test_browser_parser_invalid(self):
        parser = BrowserParser("non_existent_file.sqlite")
        self.assertFalse(parser.validate())
        self.assertEqual(parser.parse(), [])

if __name__ == "__main__":
    unittest.main()
