import unittest
from pathlib import Path
from ransomtriage.parsers.prefetch import PrefetchParser

class TestPrefetchParser(unittest.TestCase):

    def setUp(self):
        self.dummy_dir = Path(__file__).parent / "dummy_artifacts"
        self.pf_path = str(self.dummy_dir / "scenario_b" / "Prefetch" / "INVOICE_2026.PDF.EXE-87654321.pf")

    def test_prefetch_parser_valid(self):
        parser = PrefetchParser(self.pf_path)
        self.assertTrue(parser.validate())
        records = parser.parse()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["executable_name"], "INVOICE_2026.PDF.EXE")

if __name__ == "__main__":
    unittest.main()
