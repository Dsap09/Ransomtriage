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


from .parsers.browser import BrowserParser
from .parsers.prefetch import PrefetchParser
from .parsers.amcache import AmcacheParser
from .correlator.engine import CorrelationEngine
from .scoring.risk_scorer import RiskScorer
from .reporters.html_reporter import HTMLReporter
from .reporters.csv_reporter import CSVReporter

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

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

    pbar = tqdm(total=5, desc="Progress Analisa", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}]")

    # Step 1: Discover & Parse Artifacts
    pbar.set_description("1/5 Discovering & Parsing Artifacts")
    
    downloads = []
    executions = []
    amcache_records = []

    # Find History files
    for root, _, files in os.walk(input_dir):
        for f in files:
            full_f = os.path.join(root, f)
            
            # Browser History SQLite
            if f.lower() in ("history", "history.sqlite") or f.lower().endswith(".sqlite"):
                bp = BrowserParser(full_f)
                if bp.validate():
                    downloads.extend(bp.parse())

            # Prefetch .pf files
            elif f.lower().endswith(".pf"):
                pp = PrefetchParser(full_f)
                if pp.validate():
                    executions.extend(pp.parse())

            # Amcache .hve or .json files
            elif f.lower().endswith(".hve") or (f.lower().startswith("amcache") and f.lower().endswith(".json")):
                ap = AmcacheParser(full_f)
                if ap.validate():
                    amcache_records.extend(ap.parse())

    pbar.update(1)

    # Step 2: Correlation Engine
    pbar.set_description("2/5 Running Correlation Engine")
    correlator = CorrelationEngine(downloads, executions, amcache_records)
    correlated_events = correlator.correlate()
    pbar.update(1)

    # Step 3: Delta-T Risk Scoring
    pbar.set_description("3/5 Calculating Risk Scores")
    scored_events = RiskScorer.score_all(correlated_events)
    pbar.update(1)

    # Step 4: HTML Report Generation
    pbar.set_description("4/5 Generating HTML Report")
    html_reporter = HTMLReporter(scored_events, input_dir)
    html_reporter.generate(args.output)
    pbar.update(1)

    # Step 5: CSV Exporter
    pbar.set_description("5/5 Exporting CSV Report")
    csv_reporter = CSVReporter(scored_events)
    csv_reporter.generate(args.csv)
    pbar.update(1)

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


