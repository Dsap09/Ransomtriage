import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ransomtriage.scoring")

class RiskScorer:
    """
    Calculates Risk Score (0-100) based on Delta-T (execution time - download time)
    and suspicious filename indicators.
    """

    @staticmethod
    def calculate_score(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a correlated event dict and returns updated dict with:
        - delta_t_seconds: float
        - risk_score: int (0-100)
        - risk_level: str ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'BENIGN')
        - risk_reasons: List[str]
        """
        updated_event = dict(event)
        
        # If not executed at all
        if not event.get("matched") or not event.get("execution_time") or not event.get("download_time"):
            updated_event["delta_t_seconds"] = None
            updated_event["risk_score"] = 0
            updated_event["risk_level"] = "BENIGN"
            updated_event["risk_reasons"] = ["File di-download tetapi tidak pernah dieksekusi di sistem (Aman)."]
            return updated_event

        dl_time = event["download_time"]
        exec_time = event["execution_time"]

        # Calculate Delta-T in seconds
        if isinstance(dl_time, datetime.datetime) and isinstance(exec_time, datetime.datetime):
            delta_t = (exec_time - dl_time).total_seconds()
        else:
            delta_t = 0.0

        updated_event["delta_t_seconds"] = max(0.0, delta_t)

        score = 0
        reasons = []

        # 1. Delta-T Rules
        if delta_t < 5.0:
            score = 100
            reasons.append(f"Delta-T sangat singkat ({delta_t:.2f}s < 5s): Menandakan user langsung mengklik/dieksekusi otomatis (Critical).")
        elif delta_t < 60.0:
            score = 75
            reasons.append(f"Delta-T singkat ({delta_t:.2f}s < 60s): Menandakan eksekusi terjadi dalam 1 menit setelah download (High).")
        elif delta_t <= 300.0: # <= 5 minutes
            score = 50
            reasons.append(f"Delta-T sedang ({delta_t:.2f}s): Eksekusi terjadi dalam 5 menit setelah download.")
        else:
            score = 20
            reasons.append(f"Delta-T panjang ({delta_t:.2f}s > 5m): Eksekusi terjadi jauh setelah download.")

        # 2. Method-based adjustment (Script execution via PowerShell/Script host)
        if event.get("match_method") == "referenced_script_execution":
            if score < 90:
                score = 90
            reasons.append("Metode Eksekusi: Script dieksekusi secara otomatis melalui interpreter (e.g. PowerShell/CMD).")

        # 3. Double Extension indicator
        if event.get("has_double_extension"):
            score = 100
            reasons.append("Indikator Bahaya: Mendeteksi nama file dengan ekstensi ganda (e.g., .pdf.exe).")

        # Cap score between 0 and 100
        score = max(0, min(100, score))
        updated_event["risk_score"] = score

        # Set Risk Level tag
        if score >= 90:
            level = "CRITICAL"
        elif score >= 75:
            level = "HIGH"
        elif score >= 40:
            level = "MEDIUM"
        elif score > 0:
            level = "LOW"
        else:
            level = "BENIGN"

        updated_event["risk_level"] = level
        updated_event["risk_reasons"] = reasons

        return updated_event

    @classmethod
    def score_all(cls, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [cls.calculate_score(ev) for ev in events]
