import os
import sqlite3
import struct
import datetime
import json
from pathlib import Path

# Helper functions for Webkit Epoch timestamp handling
WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

def datetime_to_webkit(dt: datetime.datetime) -> int:
    """Convert datetime to Webkit microsecond timestamp (used in Chrome/Edge SQLite)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    delta = dt - WEBKIT_EPOCH
    return int(delta.total_seconds() * 1_000_000)

def datetime_to_filetime(dt: datetime.datetime) -> int:
    """Convert datetime to Windows FILETIME (100-nanosecond intervals since Jan 1, 1601)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    delta = dt - WEBKIT_EPOCH
    return int(delta.total_seconds() * 10_000_000)

def create_sqlite_history(db_path: str, download_items: list):
    """
    Creates a synthetic Chrome/Edge History SQLite database.
    download_items: list of dicts containing:
        - current_path: str
        - target_path: str
        - start_time: datetime.datetime
        - end_time: datetime.datetime
        - referrer_url: str
        - tab_url: str
        - mime_type: str
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Chrome/Edge downloads and urls schema
    cursor.execute("""
        CREATE TABLE downloads (
            id INTEGER PRIMARY KEY,
            guid TEXT,
            current_path TEXT,
            target_path TEXT,
            start_time INTEGER,
            received_bytes INTEGER,
            total_bytes INTEGER,
            state INTEGER,
            danger_type INTEGER,
            interrupt_reason INTEGER,
            hash BLOB,
            end_time INTEGER,
            opened INTEGER,
            last_access_time INTEGER,
            transient INTEGER,
            referrer TEXT,
            site_url TEXT,
            tab_url TEXT,
            tab_referrer_url TEXT,
            http_method TEXT,
            by_ext_id TEXT,
            by_ext_name TEXT,
            etag TEXT,
            last_modified TEXT,
            mime_type TEXT,
            original_mime_type TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            visit_count INTEGER,
            typed_count INTEGER,
            last_visit_time INTEGER,
            hidden INTEGER
        );
    """)

    for idx, item in enumerate(download_items, start=1):
        start_webkit = datetime_to_webkit(item["start_time"])
        end_webkit = datetime_to_webkit(item["end_time"])
        
        cursor.execute("""
            INSERT INTO downloads (
                id, guid, current_path, target_path, start_time, received_bytes, total_bytes,
                state, danger_type, interrupt_reason, end_time, opened, referrer, tab_url, mime_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, 0, ?, 0, ?, ?, ?)
        """, (
            idx,
            f"guid-{idx}",
            item["current_path"],
            item["target_path"],
            start_webkit,
            1024500,
            1024500,
            end_webkit,
            item.get("referrer_url", "https://example.com/download"),
            item.get("tab_url", "https://example.com"),
            item.get("mime_type", "application/octet-stream")
        ))

        cursor.execute("""
            INSERT INTO urls (id, url, title, visit_count, typed_count, last_visit_time, hidden)
            VALUES (?, ?, ?, 1, 0, ?, 0)
        """, (idx, item.get("referrer_url", "https://example.com"), "Download Page", start_webkit))

    conn.commit()
    conn.close()

def create_mock_prefetch_binary(pf_path: str, exec_name: str, run_count: int, last_run_dt: datetime.datetime, path_strings: list):
    """
    Creates a synthetic binary Windows Prefetch (.pf) file matching SCCA header version 30 (Windows 10/11 uncompressed).
    """
    os.makedirs(os.path.dirname(pf_path), exist_ok=True)
    
    # 0x00: Format Version (30 = 0x1E)
    # 0x04: Signature 'SCCA'
    version = 30
    signature = b"SCCA"
    file_size = 4096
    
    # Executable Name UTF-16LE, padded to 60 bytes (30 WCHARs)
    exec_name_encoded = exec_name.upper().encode("utf-16le")
    exec_name_bytes = exec_name_encoded.ljust(60, b"\x00")[:60]
    
    hash_val = 0x12345678
    
    # Header format:
    # 4 bytes int version, 4 bytes sig, 4 bytes unknown, 4 bytes file_size, 60 bytes exec_name, 4 bytes hash, 4 bytes sig2
    header = struct.pack("<I 4s I I 60s I I", version, signature, 17, file_size, exec_name_bytes, hash_val, 0)
    
    # Header is 84 bytes
    header_len = 84
    sec_ptr_len = 32 # 8 integers
    
    sec1_offset = header_len + sec_ptr_len # 116
    sec1_entries = 1
    sec2_offset = sec1_offset + 64 # 180
    sec2_entries = len(path_strings)
    
    # Encode path strings in UTF-16LE
    paths_raw = "\x00".join(path_strings) + "\x00\x00"
    paths_encoded = paths_raw.encode("utf-16le")
    
    sec3_offset = sec2_offset
    sec3_size = len(paths_encoded)
    sec3_entries = 1
    sec4_offset = sec3_offset + sec3_size
    sec4_entries = 1
    
    section_pointers = struct.pack("<I I I I I I I I", sec1_offset, sec1_entries, sec2_offset, sec2_entries, sec3_offset, sec3_size, sec4_offset, sec4_entries)
    
    # Last execution timestamp (FILETIME)
    filetime_val = datetime_to_filetime(last_run_dt)
    
    # File info section (Section 1 - 64 bytes)
    sec1_data = b"\x00" * 32 + struct.pack("<Q", filetime_val) + struct.pack("<I", run_count) + b"\x00" * 20
    
    content = header + section_pointers + sec1_data + paths_encoded
    content = content.ljust(file_size, b"\x00")

    
    with open(pf_path, "wb") as f:
        f.write(content)

def create_mock_amcache_json(amcache_path: str, records: list):
    """
    Creates a synthetic JSON representation for Amcache.hve records.
    records: list of dicts with keys: name, path, sha1, first_execution
    """
    os.makedirs(os.path.dirname(amcache_path), exist_ok=True)
    with open(amcache_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

def generate_all_scenarios(base_dir: str):
    """Generates synthetic artifacts for Scenario A, B, and C."""
    base_path = Path(base_dir)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # =========================================================================
    # SCENARIO A: Normal / Benign
    # File downloaded: laporan_keuangan.pdf
    # Prefetch: No execution of pdf or executable.
    # Expected Risk Score: 0 (Benign)
    # =========================================================================
    scen_a_dir = base_path / "scenario_a"
    dl_a = [{
        "current_path": "C:\\Users\\Victim\\Downloads\\laporan_keuangan.pdf",
        "target_path": "C:\\Users\\Victim\\Downloads\\laporan_keuangan.pdf",
        "start_time": now - datetime.timedelta(minutes=30),
        "end_time": now - datetime.timedelta(minutes=29, seconds=50),
        "referrer_url": "https://company.internal/reports/laporan_keuangan.pdf",
        "mime_type": "application/pdf"
    }]
    create_sqlite_history(str(scen_a_dir / "History"), dl_a)
    # Create irrelevant prefetch (e.g. CHROME.EXE, NOTEPAD.EXE)
    create_mock_prefetch_binary(
        str(scen_a_dir / "Prefetch" / "CHROME.EXE-12345678.pf"),
        "CHROME.EXE", 5, now - datetime.timedelta(minutes=10),
        ["\\DEVICE\\HARDDISKVOLUME1\\PROGRAM FILES\\GOOGLE\\CHROME\\CHROME.EXE"]
    )

    # =========================================================================
    # SCENARIO B: Phishing Double Extension Execution
    # File downloaded: Invoice_2026.pdf.exe
    # Executed 3 seconds after download complete!
    # Expected Risk Score: 100 (Critical)
    # =========================================================================
    scen_b_dir = base_path / "scenario_b"
    dl_time_b = now - datetime.timedelta(minutes=15)
    exec_time_b = dl_time_b + datetime.timedelta(seconds=3)
    
    dl_b = [{
        "current_path": "C:\\Users\\Victim\\Downloads\\Invoice_2026.pdf.exe",
        "target_path": "C:\\Users\\Victim\\Downloads\\Invoice_2026.pdf.exe",
        "start_time": dl_time_b - datetime.timedelta(seconds=5),
        "end_time": dl_time_b,
        "referrer_url": "https://phishing-site.xyz/download/Invoice_2026.pdf.exe",
        "mime_type": "application/x-msdownload"
    }]
    create_sqlite_history(str(scen_b_dir / "History"), dl_b)
    
    create_mock_prefetch_binary(
        str(scen_b_dir / "Prefetch" / "INVOICE_2026.PDF.EXE-87654321.pf"),
        "INVOICE_2026.PDF.EXE", 1, exec_time_b,
        ["\\DEVICE\\HARDDISKVOLUME1\\USERS\\VICTIM\\DOWNLOADS\\INVOICE_2026.PDF.EXE"]
    )
    
    create_mock_amcache_json(
        str(scen_b_dir / "Amcache.json"),
        [{
            "name": "Invoice_2026.pdf.exe",
            "path": "C:\\Users\\Victim\\Downloads\\Invoice_2026.pdf.exe",
            "sha1": "a1b2c3d4e5f678901234567890abcdef12345678",
            "first_execution": exec_time_b.isoformat()
        }]
    )

    # =========================================================================
    # SCENARIO C: Silent Download via PowerShell Script
    # File downloaded: script.ps1
    # Executed via powershell.exe < 1s after download!
    # Expected Risk Score: 90 (High Risk)
    # =========================================================================
    scen_c_dir = base_path / "scenario_c"
    dl_time_c = now - datetime.timedelta(minutes=5)
    exec_time_c = dl_time_c + datetime.timedelta(milliseconds=800)
    
    dl_c = [{
        "current_path": "C:\\Users\\Victim\\Downloads\\script.ps1",
        "target_path": "C:\\Users\\Victim\\Downloads\\script.ps1",
        "start_time": dl_time_c - datetime.timedelta(seconds=2),
        "end_time": dl_time_c,
        "referrer_url": "https://malicious-cdn.net/payload/script.ps1",
        "mime_type": "text/plain"
    }]
    create_sqlite_history(str(scen_c_dir / "History"), dl_c)
    
    create_mock_prefetch_binary(
        str(scen_c_dir / "Prefetch" / "POWERSHELL.EXE-A1B2C3D4.pf"),
        "POWERSHELL.EXE", 3, exec_time_c,
        [
            "\\DEVICE\\HARDDISKVOLUME1\\WINDOWS\\SYSTEM32\\WINDOWSPOWERSHELL\\V1.0\\POWERSHELL.EXE",
            "\\DEVICE\\HARDDISKVOLUME1\\USERS\\VICTIM\\DOWNLOADS\\SCRIPT.PS1"
        ]
    )

    print(f"Synthetic dataset generated successfully at '{base_dir}'")

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "dummy_artifacts")
    generate_all_scenarios(out_dir)
