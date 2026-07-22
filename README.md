# RansomTriage v1.0

**RansomTriage** adalah alat forensik digital berbasis Command Line Interface (CLI) menggunakan Python yang berjalan di Kali Linux/Windows untuk menganalisis jejak ransomware pada sistem target Windows melalui korelasi otomatis artifact browser dan eksekusi sistem.

## Fitur Utama

1. **Correlation Engine (Korelasi Otomatis):** Mengkorelasikan data download dari Browser (Chrome/Edge SQLite `History`) dengan data eksekusi sistem (Prefetch `.pf` & `Amcache.hve`) berdasarkan nama file, deteksi ekstensi ganda, dan hash matching.
2. **Delta-T Risk Scoring:** Menghitung skor risiko (0 - 100) berdasarkan selisih waktu antara aktivitas download dan eksekusi.
3. **Visualisasi Output Interaktif (HTML):** Menghasilkan laporan HTML standalone yang dilengkapi Diagram Sankey (*Referrer* -> *Download* -> *Execution*) dan Timeline Chart interaktif (Plotly).
4. **Export CSV Terintegrasi:** Menyimpan data ter-korelasi ke dalam satu file CSV terstruktur.

## Instalasi

```bash
# Instalasi langsung via GitHub
pip install git+https://github.com/Dsap09/Ransomtriage.git

# Atau clone dan install secara lokal:
git clone https://github.com/Dsap09/Ransomtriage.git
cd Ransomtriage
pip install .
```

## Cara Penggunaan

```bash
# Menjalankan analisa dengan folder input artifact
ransomtriage -a ./input_artifacts -o laporan.html -c hasil_korelasi.csv

# Atau menjalankan melalui script utama:
python main.py -a ./input_artifacts -o laporan.html -c hasil_korelasi.csv -v
```

## Opsi Argumen CLI

- `-a`, `--artifacts` (Wajib): Path ke folder yang berisi file `History`, folder `Prefetch`, atau `Amcache.hve`.
- `-o`, `--output` (Opsional): Path file output laporan HTML (default: `report.html`).
- `-c`, `--csv` (Opsional): Path file output CSV ringkasan korelasi (default: `correlation_summary.csv`).
- `-v`, `--verbose` (Opsional): Menampilkan detail log proses di terminal.

## Lisensi
MIT License
