import os
import shutil
import unittest
from pathlib import Path
from ransomtriage.cli import main as cli_main
import sys

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.dummy_dir = Path(__file__).parent / "dummy_artifacts"
        self.out_dir = Path(__file__).parent / "test_outputs"
        os.makedirs(self.out_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_scenario_a_cli(self):
        scen_a = str(self.dummy_dir / "scenario_a")
        html_out = str(self.out_dir / "scen_a_report.html")
        csv_out = str(self.out_dir / "scen_a_summary.csv")

        sys.argv = ["ransomtriage", "-a", scen_a, "-o", html_out, "-c", csv_out]
        cli_main()

        self.assertTrue(os.path.exists(html_out))
        self.assertTrue(os.path.exists(csv_out))

    def test_scenario_b_cli(self):
        scen_b = str(self.dummy_dir / "scenario_b")
        html_out = str(self.out_dir / "scen_b_report.html")
        csv_out = str(self.out_dir / "scen_b_summary.csv")

        sys.argv = ["ransomtriage", "-a", scen_b, "-o", html_out, "-c", csv_out]
        cli_main()

        self.assertTrue(os.path.exists(html_out))
        self.assertTrue(os.path.exists(csv_out))

    def test_scenario_c_cli(self):
        scen_c = str(self.dummy_dir / "scenario_c")
        html_out = str(self.out_dir / "scen_c_report.html")
        csv_out = str(self.out_dir / "scen_c_summary.csv")

        sys.argv = ["ransomtriage", "-a", scen_c, "-o", html_out, "-c", csv_out]
        cli_main()

        self.assertTrue(os.path.exists(html_out))
        self.assertTrue(os.path.exists(csv_out))

if __name__ == "__main__":
    unittest.main()
