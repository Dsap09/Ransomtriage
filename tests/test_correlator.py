import unittest
from datetime import datetime, timezone
from ransomtriage.correlator.engine import CorrelationEngine
from ransomtriage.scoring.risk_scorer import RiskScorer

class TestCorrelatorAndScoring(unittest.TestCase):

    def test_scenario_a_benign(self):
        now = datetime.now(timezone.utc)
        downloads = [{
            "download_id": 1,
            "filename": "laporan_keuangan.pdf",
            "full_path": "C:\\Downloads\\laporan_keuangan.pdf",
            "referrer_url": "https://company.org/report",
            "end_time": now
        }]
        executions = [] # No execution
        correlator = CorrelationEngine(downloads, executions)
        events = correlator.correlate()
        scored = RiskScorer.score_all(events)
        
        self.assertEqual(len(scored), 1)
        self.assertFalse(scored[0]["matched"])
        self.assertEqual(scored[0]["risk_score"], 0)
        self.assertEqual(scored[0]["risk_level"], "BENIGN")

    def test_scenario_b_critical_double_extension(self):
        now = datetime.now(timezone.utc)
        dl_time = now
        exec_time = dl_time + datetime.resolution * 3000000 # +3 seconds

        downloads = [{
            "download_id": 1,
            "filename": "Invoice_2026.pdf.exe",
            "full_path": "C:\\Downloads\\Invoice_2026.pdf.exe",
            "referrer_url": "https://phishing.xyz/Invoice_2026.pdf.exe",
            "end_time": dl_time
        }]
        executions = [{
            "executable_name": "INVOICE_2026.PDF.EXE",
            "execution_time": exec_time,
            "run_count": 1
        }]

        correlator = CorrelationEngine(downloads, executions)
        events = correlator.correlate()
        scored = RiskScorer.score_all(events)

        self.assertEqual(len(scored), 1)
        self.assertTrue(scored[0]["matched"])
        self.assertEqual(scored[0]["risk_score"], 100)
        self.assertEqual(scored[0]["risk_level"], "CRITICAL")

if __name__ == "__main__":
    unittest.main()
