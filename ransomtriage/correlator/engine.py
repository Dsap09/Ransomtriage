import os
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ransomtriage.correlator")

# Common dangerous double extensions or script extensions
SUSPICIOUS_EXTENSIONS = [
    ".pdf.exe", ".doc.exe", ".docx.exe", ".xls.exe", ".xlsx.exe",
    ".zip.exe", ".rar.exe", ".png.exe", ".jpg.exe", ".txt.exe",
    ".ps1", ".vbs", ".bat", ".cmd", ".js", ".hta"
]

def is_double_extension(filename: str) -> bool:
    """Checks if a filename has a double extension like Invoice.pdf.exe."""
    fn = filename.lower()
    return any(fn.endswith(ext) for ext in SUSPICIOUS_EXTENSIONS if ext.count(".") > 1)

class CorrelationEngine:
    """
    Core Novelty: Automatically correlates Browser Downloads with Prefetch / Amcache Executions.
    """

    def __init__(self, downloads: List[Dict[str, Any]], executions: List[Dict[str, Any]], amcache_records: List[Dict[str, Any]] = None):
        self.downloads = downloads
        self.executions = executions
        self.amcache_records = amcache_records or []

    def correlate(self) -> List[Dict[str, Any]]:
        correlated_events = []

        for dl in self.downloads:
            dl_fn = dl.get("filename", "").strip()
            dl_fn_lower = dl_fn.lower()
            dl_path = dl.get("full_path", "").lower()
            dl_end_time = dl.get("end_time")

            matched_exec = None
            match_method = None

            # 1. Check Exact Name Match in Prefetch
            for ex in self.executions:
                exec_fn = ex.get("executable_name", "").strip().lower()
                if dl_fn_lower and exec_fn and dl_fn_lower == exec_fn:
                    matched_exec = ex
                    match_method = "exact_name"
                    break

            # 2. Check Hash Match in Amcache (if exact match not found)
            if not matched_exec and self.amcache_records:
                for am in self.amcache_records:
                    am_fn = am.get("executable_name", "").strip().lower()
                    am_path = am.get("full_path", "").strip().lower()
                    if dl_fn_lower == am_fn or (dl_path and dl_path == am_path):
                        matched_exec = am
                        match_method = "amcache_hash_match"
                        break

            # 3. Check Script / Indirect Execution (e.g. script.ps1 executed by powershell.exe)
            if not matched_exec and dl_fn_lower:
                ext = os.path.splitext(dl_fn_lower)[1]
                if ext in [".ps1", ".vbs", ".bat", ".cmd", ".js"]:
                    for ex in self.executions:
                        ref_paths = [p.lower() for p in ex.get("referenced_paths", [])]
                        # Check if download filename or path is in referenced paths of launcher process
                        if any(dl_fn_lower in p for p in ref_paths) or any(dl_path in p for p in ref_paths if dl_path):
                            matched_exec = ex
                            match_method = "referenced_script_execution"
                            break

            # 4. Check Fuzzy / Double Extension Match
            if not matched_exec and is_double_extension(dl_fn):
                for ex in self.executions:
                    exec_fn = ex.get("executable_name", "").strip().lower()
                    if dl_fn_lower.startswith(exec_fn) or exec_fn in dl_fn_lower:
                        matched_exec = ex
                        match_method = "fuzzy_double_extension"
                        break

            event = {
                "download_id": dl.get("download_id"),
                "download_file": dl_fn,
                "download_path": dl.get("full_path"),
                "referrer_url": dl.get("referrer_url"),
                "download_time": dl_end_time,
                "mime_type": dl.get("mime_type"),
                "matched": matched_exec is not None,
                "match_method": match_method or ("unexecuted" if not matched_exec else "unknown"),
                "executed_process": matched_exec.get("executable_name") if matched_exec else None,
                "execution_time": matched_exec.get("execution_time") if matched_exec else None,
                "run_count": matched_exec.get("run_count", 0) if matched_exec else 0,
                "has_double_extension": is_double_extension(dl_fn)
            }

            correlated_events.append(event)

        return correlated_events
