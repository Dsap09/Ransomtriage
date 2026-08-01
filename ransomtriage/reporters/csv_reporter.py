import os
import csv
import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ransomtriage.reporters.csv")


class CSVReporter:
    """Exports correlated execution chain events into a clean, executive CSIRT CSV report."""

    def __init__(self, events: List[Dict[str, Any]]):
        self.events = events

    def generate(self, output_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        fieldnames = [
            "Risk Level",
            "Risk Score",
            "Download File",
            "Download Path",
            "Referrer URL",
            "Download Timestamp (UTC)",
            "Executed Process",
            "Execution Timestamp (UTC)",
            "Delta-T (Seconds)",
            "Match Method",
            "Run Count",
            "Risk Indicators & Analysis"
        ]

        # Sort events by risk_score descending (highest risk first)
        sorted_events = sorted(
            self.events,
            key=lambda e: (e.get("risk_score", 0), e.get("download_time") or datetime.datetime.min),
            reverse=True
        )

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for ev in sorted_events:
                dl_time = ev.get("download_time")
                if isinstance(dl_time, datetime.datetime):
                    dl_time_str = dl_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    dl_time_str = str(dl_time or "")

                exec_time = ev.get("execution_time")
                if isinstance(exec_time, datetime.datetime):
                    exec_time_str = exec_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    exec_time_str = str(exec_time or "")

                delta_t = ev.get("delta_t_seconds")
                delta_t_str = f"{delta_t:.2f}" if delta_t is not None else "-"

                reasons = ev.get("risk_reasons", [])
                reasons_str = " | ".join(reasons) if reasons else "No risk indicators"

                writer.writerow({
                    "Risk Level": ev.get("risk_level", "BENIGN"),
                    "Risk Score": ev.get("risk_score", 0),
                    "Download File": ev.get("download_file", ""),
                    "Download Path": ev.get("download_path", ""),
                    "Referrer URL": ev.get("referrer_url", ""),
                    "Download Timestamp (UTC)": dl_time_str,
                    "Executed Process": ev.get("executed_process") or "Tidak Dieksekusi",
                    "Execution Timestamp (UTC)": exec_time_str,
                    "Delta-T (Seconds)": delta_t_str,
                    "Match Method": ev.get("match_method", "-"),
                    "Run Count": ev.get("run_count", 0),
                    "Risk Indicators & Analysis": reasons_str
                })

        logger.info(f"CSV report successfully exported at '{output_path}'")
