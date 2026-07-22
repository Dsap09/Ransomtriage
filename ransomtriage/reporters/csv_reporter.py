import os
import csv
import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ransomtriage.reporters.csv")

class CSVReporter:
    """Exports correlated execution chain events into a single integrated CSV report."""

    def __init__(self, events: List[Dict[str, Any]]):
        self.events = events

    def generate(self, output_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fieldnames = [
            "risk_level",
            "risk_score",
            "download_file",
            "download_path",
            "referrer_url",
            "download_time",
            "executed_process",
            "execution_time",
            "delta_t_seconds",
            "match_method",
            "run_count",
            "risk_reasons"
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for ev in self.events:
                dl_time_str = ev.get("download_time").isoformat() if isinstance(ev.get("download_time"), datetime.datetime) else str(ev.get("download_time") or "")
                exec_time_str = ev.get("execution_time").isoformat() if isinstance(ev.get("execution_time"), datetime.datetime) else str(ev.get("execution_time") or "")

                reasons_str = " | ".join(ev.get("risk_reasons", []))

                writer.writerow({
                    "risk_level": ev.get("risk_level", "BENIGN"),
                    "risk_score": ev.get("risk_score", 0),
                    "download_file": ev.get("download_file", ""),
                    "download_path": ev.get("download_path", ""),
                    "referrer_url": ev.get("referrer_url", ""),
                    "download_time": dl_time_str,
                    "executed_process": ev.get("executed_process") or "Unexecuted",
                    "execution_time": exec_time_str,
                    "delta_t_seconds": f"{ev.get('delta_t_seconds'):.2f}" if ev.get("delta_t_seconds") is not None else "",
                    "match_method": ev.get("match_method", ""),
                    "run_count": ev.get("run_count", 0),
                    "risk_reasons": reasons_str
                })

        logger.info(f"CSV report successfully exported at '{output_path}'")
