import os
import sys
import argparse
import logging
import webbrowser
from pathlib import Path

# readline mengaktifkan arrow keys, history, dan line editing di input() pada Linux/macOS
try:
    import readline  # noqa: F401
except ImportError:
    pass  # Windows tanpa pyreadline — input() tetap berjalan normal

# Pastikan stdout/stderr menggunakan UTF-8 di Windows agar Unicode box characters tampil benar
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
from .utils.colors import Colors


# ============================================================
# ASCII ART LOGO
# ============================================================
LOGO = f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗  █████╗ ███╗   ██╗███████╗ ██████╗ ███╗   ███╗     ║
║   ██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔═══██╗████╗ ████║     ║
║   ██████╔╝███████║██╔██╗ ██║███████╗██║   ██║██╔████╔██║     ║
║   ██╔══██╗██╔══██║██║╚██╗██║╚════██║██║   ██║██║╚██╔╝██║     ║
║   ██║  ██║██║  ██║██║ ╚████║███████║╚██████╔╝██║ ╚═╝ ██║     ║
║   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝     ║
║                                                               ║
║   ████████╗██████╗ ██╗ █████╗  ██████╗ ███████╗              ║
║   ╚══██╔══╝██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝              ║
║      ██║   ██████╔╝██║███████║██║  ███╗█████╗                ║
║      ██║   ██╔══██╗██║██╔══██║██║   ██║██╔══╝                ║
║      ██║   ██║  ██║██║██║  ██║╚██████╔╝███████╗              ║
║      ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝              ║
║                                                               ║
║           Automated Execution Chain Analyzer                  ║
║              Forensic Tool for Ransomware Triage              ║
║                    v1.0 - TA Forensik Digital                ║
╚═══════════════════════════════════════════════════════════════╝{Colors.NC}
"""

MINI_BANNER = f"""{Colors.CYAN}╔═══════════════════════════════════════╗
║      RansomTriage v1.0                ║
║   Automated Execution Chain Analyzer  ║
╚═══════════════════════════════════════╝{Colors.NC}"""

MENU = f"""
{Colors.YELLOW}════════════════════════════════════════════════════════════════{Colors.NC}
  {Colors.GREEN}[1]{Colors.NC} Analyze Artifacts (CLI Mode)
  {Colors.CYAN}[2]{Colors.NC} Generate Dummy Data
  {Colors.YELLOW}[3]{Colors.NC} View Sample Report
  {Colors.BLUE}[4]{Colors.NC} Help / Usage
  {Colors.RED}[5]{Colors.NC} Exit
{Colors.YELLOW}════════════════════════════════════════════════════════════════{Colors.NC}
"""

HELP_TEXT = f"""
{Colors.CYAN}RansomTriage - Automated Execution Chain Analyzer{Colors.NC}

{Colors.YELLOW}Usage:{Colors.NC}
  ransomtriage -a <folder> -o <report.html> -c <summary.csv> -v

{Colors.YELLOW}Options:{Colors.NC}
  -a, --artifacts   Path to folder containing Windows artifacts
  -o, --output      Output HTML report filename
  -c, --csv         Output CSV summary filename
  -v, --verbose     Show detailed process information
  --no-open         Don't auto-open HTML report in browser
  -h, --help        Show this help message

{Colors.YELLOW}Example:{Colors.NC}
  ransomtriage -a tests/dummy_artifacts/scenario_b -o laporan.html -v
"""


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


def clear_screen():
    """Bersihkan layar terminal (cross-platform)."""
    os.system('cls' if sys.platform == 'win32' else 'clear')


def colorize_level(level_str):
    """Warnai level risiko berdasarkan tingkat keparahan."""
    level_upper = level_str.upper()
    if level_upper == "CRITICAL":
        return Colors.red(Colors.BOLD + level_str + Colors.NC)
    elif level_upper == "HIGH":
        return Colors.red(level_str)
    elif level_upper == "MEDIUM":
        return Colors.yellow(level_str)
    elif level_upper == "LOW":
        return Colors.green(level_str)
    else:
        return level_str


def run_analysis(artifact_path, output_html="laporan.html", output_csv="correlation_summary.csv", verbose=False, no_open=False):
    """
    Fungsi utama analisa artifact — bisa dipanggil dari CLI args maupun menu interaktif.
    """
    setup_logging(verbose)

    input_dir = os.path.abspath(artifact_path)
    if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
        print(f"\n  {Colors.red('[!] Error:')} Folder artifact input '{input_dir}' tidak ditemukan atau bukan directory.")
        return

    print(f"\n  {Colors.cyan('[*]')} Input Directory: {input_dir}")
    print(f"  {Colors.cyan('[*]')} HTML Output    : {output_html}")
    print(f"  {Colors.cyan('[*]')} CSV Output     : {output_csv}")

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
    html_reporter.generate(output_html)
    pbar.update(1)

    # Step 5: CSV Exporter
    pbar.set_description("Exporting CSV Summary")
    csv_reporter = CSVReporter(scored_events)
    csv_reporter.generate(output_csv)
    pbar.update(1)

    pbar.set_description("Selesai")
    pbar.close()

    # Terminal Summary Output
    print(f"\n  {Colors.green('[+]')} Analisa selesai!")
    print(f"  {Colors.YELLOW}{'─' * 58}{Colors.NC}")
    print(f"  Total Download Artifacts  : {Colors.cyan(str(len(downloads)))}")
    print(f"  Total Prefetch Executions : {Colors.cyan(str(len(executions)))}")
    print(f"  Matches Execution Chain   : {Colors.cyan(str(sum(1 for e in scored_events if e.get('matched'))))}")

    crit_count = sum(1 for e in scored_events if e.get("risk_level") in ("CRITICAL", "HIGH"))
    if crit_count > 0:
        print(f"\n  {Colors.red('[!] PERINGATAN:')} Ditemukan {Colors.bold(str(crit_count))} kejadian berisiko {Colors.red('CRITICAL / HIGH')}!")

    # Render direct ASCII summary table in terminal
    if scored_events:
        print(f"\n  {Colors.green('[+]')} HASIL ANALISA KORELASI:")
        print(f"  {'═' * 95}")
        header_str = f"  {'LEVEL':<10} | {'SCORE':<5} | {'DOWNLOAD FILE':<25} | {'EXECUTED PROCESS':<25} | {'DELTA-T':<8}"
        print(Colors.bold(header_str))
        print(f"  {'─' * 95}")
        for ev in scored_events:
            lvl = ev.get("risk_level", "BENIGN")
            score = str(ev.get("risk_score", 0))
            dl = (ev.get("download_file") or "")[:24]
            proc = (ev.get("executed_process") or "Tidak Dieksekusi")[:24]
            dt = f"{ev.get('delta_t_seconds'):.2f}s" if ev.get("delta_t_seconds") is not None else "-"
            lvl_colored = colorize_level(lvl)
            print(f"  {lvl_colored:<22} | {score:<5} | {dl:<25} | {proc:<25} | {dt:<8}")
        print(f"  {'═' * 95}")

    abs_html_path = os.path.abspath(output_html).replace("\\", "/")
    abs_csv_path = os.path.abspath(output_csv).replace("\\", "/")
    print(f"\n  {Colors.green('[+]')} File Laporan HTML  : {Colors.cyan(abs_html_path)}")
    print(f"  {Colors.green('[+]')} File Ringkasan CSV : {Colors.cyan(abs_csv_path)}")

    # Auto-open HTML report in default browser automatically
    if not no_open:
        try:
            file_url = f"file:///{abs_html_path}"
            webbrowser.open(file_url)
            print(f"  {Colors.cyan('[*]')} Meluncurkan laporan di browser otomatis: {file_url}")
        except Exception:
            pass


def show_menu():
    """Tampilkan menu interaktif dan kembalikan pilihan user."""
    print(LOGO)
    print(MENU)
    try:
        choice = input(f"  {Colors.GREEN}kat > {Colors.NC}")
        return choice.strip()
    except (EOFError, KeyboardInterrupt):
        return "5"


def interactive_mode():
    """Mode interaktif — loop menu sampai user memilih Exit."""
    while True:
        clear_screen()
        choice = show_menu()

        if choice == "1":
            # Analyze Artifacts
            print(f"\n  {Colors.cyan('─' * 50)}")
            try:
                folder = input(f"  {Colors.yellow('Masukkan path folder artifact:')} ")
                if not folder.strip():
                    print(f"  {Colors.red('[!]')} Path tidak boleh kosong.")
                    input(f"\n  {Colors.yellow('Tekan Enter untuk kembali ke menu...')}")
                    continue

                output = input(f"  {Colors.yellow('Nama file output HTML (default: laporan.html):')} ") or "laporan.html"
                csv_out = input(f"  {Colors.yellow('Nama file output CSV (default: correlation_summary.csv):')} ") or "correlation_summary.csv"
                verbose_input = input(f"  {Colors.yellow('Verbose mode? (y/n, default: y):')} ") or "y"
                verbose = verbose_input.lower().startswith("y")

                print(f"\n{MINI_BANNER}")
                run_analysis(folder.strip(), output.strip(), csv_out.strip(), verbose, no_open=False)
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {Colors.yellow('[*]')} Analisa dibatalkan.")

        elif choice == "2":
            # Generate Dummy Data
            print(f"\n  {Colors.cyan('[*]')} Menjalankan dummy data generator...")
            try:
                # Import dan jalankan langsung daripada os.system
                dummy_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "dummy_generator.py")
                if os.path.exists(dummy_script):
                    import subprocess
                    subprocess.run([sys.executable, dummy_script], check=False)
                else:
                    print(f"  {Colors.red('[!]')} File dummy_generator.py tidak ditemukan di: {dummy_script}")
            except Exception as e:
                print(f"  {Colors.red('[!]')} Error: {e}")

        elif choice == "3":
            # View Sample Report
            print(f"\n  {Colors.cyan('[*]')} Mencari laporan sampel...")
            sample_files = ["laporan_b.html", "laporan.html", "report.html"]
            opened = False
            for sf in sample_files:
                if os.path.exists(sf):
                    abs_path = os.path.abspath(sf).replace("\\", "/")
                    file_url = f"file:///{abs_path}"
                    webbrowser.open(file_url)
                    print(f"  {Colors.green('[+]')} Membuka {sf} di browser: {file_url}")
                    opened = True
                    break
            if not opened:
                print(f"  {Colors.yellow('[!]')} Tidak ditemukan laporan sampel. Jalankan analisa terlebih dahulu.")

        elif choice == "4":
            # Help / Usage
            print(HELP_TEXT)

        elif choice == "5":
            # Exit
            print(f"\n  {Colors.green('Terima kasih telah menggunakan RansomTriage!')}")
            print(f"  {Colors.cyan('Automated Execution Chain Analyzer - TA Forensik Digital')}\n")
            sys.exit(0)

        else:
            print(f"\n  {Colors.red('[!]')} Pilihan tidak valid! Silakan pilih 1-5.")

        try:
            input(f"\n  {Colors.yellow('Tekan Enter untuk kembali ke menu...')}")
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)


def main():
    # Jika tidak ada argumen, tampilkan menu interaktif
    if len(sys.argv) == 1:
        interactive_mode()
        return

    # Jika ada argumen, jalankan mode CLI normal
    parser = argparse.ArgumentParser(
        description="RansomTriage v1.0 - Automated Execution Chain Analyzer for Incident Responders",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-a", "--artifacts", required=True, help="Path ke folder input yang berisi artifact Windows (History, Prefetch, Amcache)")
    parser.add_argument("-o", "--output", default="report.html", help="Path file output laporan HTML (default: report.html)")
    parser.add_argument("-c", "--csv", default="correlation_summary.csv", help="Path file output CSV terintegrasi (default: correlation_summary.csv)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Menampilkan log verbose/debug di terminal")
    parser.add_argument("--no-open", action="store_true", help="Jangan membuka laporan HTML secara otomatis di browser")

    args = parser.parse_args()

    # Tampilkan mini banner berwarna
    print(f"\n{MINI_BANNER}")

    run_analysis(args.artifacts, args.output, args.csv, args.verbose, args.no_open)


if __name__ == "__main__":
    main()
