# RansomTriage v1.0

```
╔═══════════════════════════════════════════════════════════════╗
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
╚═══════════════════════════════════════════════════════════════╝
```

**RansomTriage** adalah alat forensik digital berbasis CLI (Command Line Interface) menggunakan Python untuk menganalisis jejak ransomware pada sistem target Windows melalui korelasi otomatis artifact browser dan eksekusi sistem.

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
| :--- | :--- |
| **Correlation Engine** | Mengkorelasikan data download dari Browser (Chrome/Edge SQLite `History`) dengan data eksekusi sistem (Prefetch `.pf` & `Amcache.hve`) berdasarkan nama file, deteksi ekstensi ganda, dan hash matching. |
| **Delta-T Risk Scoring** | Menghitung skor risiko (0–100) berdasarkan selisih waktu antara aktivitas download dan eksekusi. |
| **Visualisasi HTML Interaktif** | Menghasilkan laporan HTML standalone dengan Diagram Sankey (*Referrer → Download → Execution*) dan Timeline Chart interaktif (Plotly). |
| **Export CSV Terintegrasi** | Menyimpan data ter-korelasi ke dalam satu file CSV terstruktur. |
| **ASCII Art & Warna ANSI** | Tampilan terminal profesional dengan logo ASCII art berwarna dan output berwarna berdasarkan level risiko. |
| **Menu Interaktif** | Menu bernomor (1–5) untuk pengguna yang tidak hafal argumen CLI — cukup jalankan `ransomtriage` tanpa argumen. |

---

## 🚀 Instalasi

```bash
# Instalasi langsung via GitHub
pip install git+https://github.com/Dsap09/Ransomtriage.git

# Atau clone dan install secara lokal:
git clone https://github.com/Dsap09/Ransomtriage.git
cd Ransomtriage
pip install .
```

### Dependensi

| Package | Fungsi |
| :--- | :--- |
| `pandas >= 1.3.0` | Manipulasi dan penggabungan data |
| `plotly >= 5.0.0` | Visualisasi grafik interaktif (Sankey & Timeline) |
| `jinja2 >= 3.0.0` | Template HTML untuk laporan |
| `tqdm >= 4.60.0` | Progress bar di terminal |
| `python-registry >= 1.3.1` | Parsing Amcache.hve (Windows Registry) |

---

## 📖 Cara Penggunaan

### Mode 1: Menu Interaktif

Jalankan tanpa argumen untuk masuk ke menu interaktif:

```bash
ransomtriage
# atau
python main.py
```

Tampilan yang akan muncul:

```
════════════════════════════════════════════════════════════════
  [1] Analyze Artifacts (CLI Mode)
  [2] Generate Dummy Data
  [3] View Sample Report
  [4] Help / Usage
  [5] Exit
════════════════════════════════════════════════════════════════

  kat >
```

### Mode 2: CLI dengan Argumen

Untuk penggunaan langsung tanpa menu:

```bash
# Analisa dasar
ransomtriage -a ./input_artifacts -o laporan.html

# Analisa dengan verbose dan custom CSV output
ransomtriage -a ./input_artifacts -o laporan.html -c hasil_korelasi.csv -v

# Tanpa auto-open browser
ransomtriage -a ./input_artifacts -o laporan.html --no-open
```

---

## ⚙️ Opsi Argumen CLI

| Argumen | Wajib? | Deskripsi | Default |
| :--- | :--- | :--- | :--- |
| `-a`, `--artifacts` | ✅ | Path ke folder yang berisi artifact Windows (`History`, `Prefetch`, `Amcache`) | — |
| `-o`, `--output` | ❌ | Path file output laporan HTML | `report.html` |
| `-c`, `--csv` | ❌ | Path file output CSV ringkasan korelasi | `correlation_summary.csv` |
| `-v`, `--verbose` | ❌ | Menampilkan detail log proses di terminal | `false` |
| `--no-open` | ❌ | Jangan membuka laporan HTML otomatis di browser | `false` |

---

## 🏗️ Struktur Project

```
Ransomtriage/
├── main.py                          # Entry point utama
├── setup.py                         # Konfigurasi instalasi
├── pyproject.toml                   # Build system config
├── requirements.txt                 # Daftar dependensi
├── ransomtriage/
│   ├── __init__.py
│   ├── cli.py                       # CLI handler, ASCII logo, menu interaktif
│   ├── utils/
│   │   ├── __init__.py
│   │   └── colors.py                # Kode warna ANSI untuk terminal
│   ├── parsers/
│   │   ├── base.py                  # Base class parser
│   │   ├── browser.py               # Parser SQLite History (Chrome/Edge)
│   │   ├── prefetch.py              # Parser file Prefetch (.pf)
│   │   └── amcache.py               # Parser Amcache.hve / JSON
│   ├── correlator/
│   │   └── engine.py                # Correlation Engine (inti novelty)
│   ├── scoring/
│   │   └── risk_scorer.py           # Delta-T Risk Scoring (0-100)
│   ├── reporters/
│   │   ├── html_reporter.py         # Generator laporan HTML + Plotly
│   │   └── csv_reporter.py          # Generator CSV terintegrasi
│   └── templates/
│       └── *.html                   # Template Jinja2 untuk laporan
└── tests/
    ├── dummy_generator.py           # Script pembuatan data dummy
    ├── dummy_artifacts/             # Data skenario uji (A, B, C)
    ├── test_browser_parser.py
    ├── test_prefetch_parser.py
    ├── test_correlator.py
    └── test_integration.py
```

---

## 🧪 Skenario Testing

Tools diuji menggunakan 3 skenario data sintetis di `tests/dummy_artifacts/`:

| Skenario | Deskripsi | Skor yang Diharapkan |
| :--- | :--- | :--- |
| **A — Normal/Benign** | File `laporan_keuangan.pdf` di-download, tidak pernah dieksekusi. | **0 (Aman)** |
| **B — Phishing** | File `Invoice_2026.pdf.exe` di-download dan dieksekusi dalam 3 detik. Deteksi ekstensi ganda. | **100 (Critical)** |
| **C — Silent PowerShell** | File `script.ps1` di-download, PowerShell muncul < 1 detik (serangan otomatis). | **90+ (High/Critical)** |

Jalankan test:

```bash
# Unit tests
python -m pytest tests/ -v

# Generate data dummy baru
python tests/dummy_generator.py
```

---

## 🖥️ Kompatibilitas

- **Python:** 3.9+
- **OS:** Kali Linux, Ubuntu, macOS, Windows 10+ (CMD/PowerShell)
- **Terminal:** Gunakan font monospace (Fira Code, Consolas, Ubuntu Mono) dengan background gelap untuk tampilan optimal
- **Warna ANSI:** Otomatis aktif di Windows 10+; fallback tanpa warna jika terminal tidak mendukung

---

## 📄 Lisensi

MIT License
