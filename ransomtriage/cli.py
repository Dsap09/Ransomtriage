import os
import sys
import argparse
import logging
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, total=0, desc="", **kwargs):
            self.total = total
            self.n = 0
            self.desc = desc
        def set_description(self, desc):
            self.desc = desc
        def update(self, n=1):
            self.n += n
        def close(self):
            pass
        @staticmethod
        def write(msg):
            sys.stderr.write(msg + "\n")


from .parsers.browser import BrowserParser
from .parsers.prefetch import PrefetchParser
from .parsers.amcache import AmcacheParser
from .correlator.engine import CorrelationEngine
from .scoring.risk_scorer import RiskScorer
from .reporters.html_reporter import HTMLReporter
from .reporters.csv_reporter import CSVReporter


class TqdmLoggingHandler(logging.Handler):
    """Logging handler that routes messages through tqdm.write to prevent progress bar corruption."""
    def emit(self, record):
        try:
            msg = self.format(record)
            if hasattr(tqdm, "write"):
                tqdm.write(msg)
            else:
                sys.stderr.write(msg + "\n")
        except Exception:
            self.handleError(record)


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.WARNING
    handler = TqdmLoggingHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]


def main():
    parser = argparse.ArgumentParser(
        description="RansomTriage v1.0 - Automated Execution Chain Analyzer for Incident Responders",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-a", "--artifacts", required=True, help="Path ke folder input yang berisi artifact Windows (History, Prefetch, Amcache)")
    parser.add_argument("-o", "--output", default="report.html", help="Path file output laporan HTML (default: report.html)")
    parser.add_argument("-c", "--csv", default="correlation_summary.csv", help="Path file output CSV terintegrasi (default: correlation_summary.csv)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Menampilkan log verbose/debug di terminal")

    args = parser.parse_args()
    setup_logging(args.verbose)

    input_dir = os.path.abspath(args.artifacts)
    if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
        print(f"[!] Error: Folder artifact input '{input_dir}' tidak ditemukan atau bukan directory.")
        sys.exit(1)

    print("============================================================")
    print("[+] RansomTriage v1.0 - Automated Execution Chain Analyzer")
    print("============================================================")
    print(f"[*] Input Directory: {input_dir}")
    print(f"[*] HTML Output    : {args.output}")
    print(f"[*] CSV Output     : {args.csv}")

    # Discover candidate files to calculate granular progress steps
    target_files = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            target_files.append(os.path.join(root, f))

    # Total steps: 1 step per discovered file + 4 main pipeline steps
    total_steps = max(len(target_files), 1) + 4
    pbar = tqdm(total=total_steps, desc="Progress Analisa", bar_format="{l_bar}{bar:30}| {percentage:3.0f}% [{elapsed}]")

    downloads = []
    executions = []
    amcache_records = []

    # Step 1: Discover & Parse Artifacts per file
    if target_files:
        for full_f in target_files:
            f_name = os.path.basename(full_f)
            f_lower = f_name.lower()
            pbar.set_description(f"Parsing: {f_name[:20]}")

            # Browser History SQLite
            if f_lower in ("history", "history.sqlite") or f_lower.endswith(".sqlite"):
                bp = BrowserParser(full_f)
                if bp.validate():
                    downloads.extend(bp.parse())

            # Prefetch .pf files
            elif f_lower.endswith(".pf"):
                pp = PrefetchParser(full_f)
                if pp.validate():
                    executions.extend(pp.parse())

            # Amcache .hve or .json files
            elif f_lower.endswith(".hve") or (f_lower.startswith("amcache") and f_lower.endswith(".json")):
                ap = AmcacheParser(full_f)
                if ap.validate():
                    amcache_records.extend(ap.parse())

            pbar.update(1)
    else:
        pbar.update(1)

    # Step 2: Correlation Engine
    pbar.set_description("Correlating Chains")
    correlator = CorrelationEngine(downloads, executions, amcache_records)
    correlated_events = correlator.correlate()
    pbar.update(1)

    # Step 3: Risk Scoring
    pbar.set_description("Calculating Risk Scores")
    scored_events = RiskScorer.score_all(correlated_events)
    pbar.update(1)

    # Step 4: HTML Report Generation
    pbar.set_description("Generating HTML Report")
    html_reporter = HTMLReporter(scored_events, input_dir)
    html_reporter.generate(args.output)
    pbar.update(1)

    # Step 5: CSV Exporter
    pbar.set_description("Exporting CSV Summary")
    csv_reporter = CSVReporter(scored_events)
    csv_reporter.generate(args.csv)
    pbar.update(1)

    pbar.set_description("Selesai")
    pbar.close()

    # Terminal Summary Output
    print("\n[+] Analisa selesai dalam hitungan detik!")
    print("------------------------------------------------------------")
    print(f"Total Download Artifacts  : {len(downloads)}")
    print(f"Total Prefetch Executions : {len(executions)}")
    print(f"Matches Execution Chain   : {sum(1 for e in scored_events if e.get('matched'))}")
    
    crit_count = sum(1 for e in scored_events if e.get("risk_level") in ("CRITICAL", "HIGH"))
    if crit_count > 0:
        print(f"[!] PERINGATAN: Ditemukan {crit_count} kejadian berisiko CRITICAL / HIGH!")

    abs_html_path = os.path.abspath(args.output).replace("\\", "/")
    abs_csv_path = os.path.abspath(args.csv).replace("\\", "/")
    print(f"\n[+] Laporan HTML: file:///{abs_html_path}")
    print(f"[+] Summary CSV : file:///{abs_csv_path}")

if __name__ == "__main__":
    main()
