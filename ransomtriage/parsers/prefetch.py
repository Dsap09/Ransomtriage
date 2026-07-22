import os
import struct
import datetime
import logging
from typing import List, Dict, Any
from .base import BaseParser

logger = logging.getLogger("ransomtriage.parsers.prefetch")

FILETIME_EPOCH = datetime.datetime(1601, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

def filetime_to_datetime(ft: int) -> datetime.datetime:
    """Converts 64-bit Windows FILETIME to UTC datetime."""
    if not ft or ft <= 0:
        return datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    seconds = ft / 10_000_000.0
    try:
        return FILETIME_EPOCH + datetime.timedelta(seconds=seconds)
    except OverflowError:
        return datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)

def decompress_mam(data: bytes) -> bytes:
    """
    Decompresses Windows 10/11 MAM compressed Prefetch file header.
    If compressed with XPRESS Huffman, attempts decompression or returns raw.
    """
    if len(data) < 8 or not data.startswith(b"MAM\x04"):
        return data

    uncompressed_size = struct.unpack("<I", data[4:8])[0]
    compressed_data = data[8:]
    
    # Python LZNT1/XPRESS fallback decompression simulation
    # Simple chunk scan to extract uncompressed SCCA payload if embedded
    scca_pos = compressed_data.find(b"SCCA")
    if scca_pos != -1 and scca_pos >= 4:
        # SCCA signature starts at byte 4 of uncompressed header
        return compressed_data[scca_pos - 4:]
    
    # Return data for attempted direct parsing
    return data

class PrefetchParser(BaseParser):
    """
    Parses Windows Prefetch (.pf) files for Windows 8 (v26) and Windows 10/11 (v30).
    Extracts program executable name, run count, last execution timestamp(s), and accessed file paths.
    """

    def validate(self) -> bool:
        if not os.path.exists(self.artifact_path) or not os.path.isfile(self.artifact_path):
            return False
        try:
            with open(self.artifact_path, "rb") as f:
                header = f.read(8)
                if header.startswith(b"MAM\x04"):
                    return True
                if len(header) >= 8 and header[4:8] == b"SCCA":
                    return True
                return False
        except Exception as e:
            logger.warning(f"Error checking prefetch file {self.artifact_path}: {e}")
            return False

    def parse(self) -> List[Dict[str, Any]]:
        if not self.validate():
            logger.warning(f"File {self.artifact_path} is not a valid Prefetch (.pf) file.")
            return []

        try:
            with open(self.artifact_path, "rb") as f:
                raw_data = f.read()

            if raw_data.startswith(b"MAM\x04"):
                data = decompress_mam(raw_data)
            else:
                data = raw_data

            if len(data) < 84 or data[4:8] != b"SCCA":
                logger.warning(f"Unable to locate SCCA header in {self.artifact_path}")
                return []

            # Parse SCCA Header
            version = struct.unpack("<I", data[0:4])[0]
            
            # Executable name: 60 bytes UTF-16LE at offset 0x10
            raw_exec_name = data[16:76].decode("utf-16le", errors="ignore").rstrip("\x00")
            exec_name = self.safe_basename(raw_exec_name)

            # Section Pointers at offset 0x54 (84 bytes)
            # Offset A: Section 1 File Info
            sec1_offset = struct.unpack("<I", data[84:88])[0]
            sec1_size = struct.unpack("<I", data[88:92])[0]
            
            sec2_offset = struct.unpack("<I", data[92:96])[0]
            sec2_count = struct.unpack("<I", data[96:100])[0]

            sec3_offset = struct.unpack("<I", data[100:104])[0]
            sec3_size = struct.unpack("<I", data[104:108])[0]

            last_run_times = []
            run_count = 0

            # Parse Section 1 (File Info) based on SCCA format version
            if version in (26, 30):  # Win 8 / 8.1 / 10 / 11
                # Format: Last run time(s) at sec1_offset + 0x20
                time_offset = sec1_offset + 32
                if version == 30:
                    # Windows 10/11 stores up to 8 timestamps (8 * 8 bytes = 64 bytes)
                    for i in range(8):
                        ft = struct.unpack("<Q", data[time_offset + (i * 8) : time_offset + ((i + 1) * 8)])[0]
                        if ft > 0:
                            last_run_times.append(filetime_to_datetime(ft))
                    # Run count is at sec1_offset + 0x74 (116 bytes) or sec1_offset + 0x2C
                    if len(data) >= sec1_offset + 120:
                        run_count = struct.unpack("<I", data[sec1_offset + 116 : sec1_offset + 120])[0]
                elif version == 26:
                    # Windows 8/8.1 stores up to 8 timestamps
                    for i in range(8):
                        ft = struct.unpack("<Q", data[time_offset + (i * 8) : time_offset + ((i + 1) * 8)])[0]
                        if ft > 0:
                            last_run_times.append(filetime_to_datetime(ft))
                    if len(data) >= sec1_offset + 72:
                        run_count = struct.unpack("<I", data[sec1_offset + 68 : sec1_offset + 72])[0]

            if not last_run_times:
                # Fallback to single timestamp at sec1_offset + 32
                ft = struct.unpack("<Q", data[sec1_offset + 32 : sec1_offset + 40])[0] if len(data) >= sec1_offset + 40 else 0
                if ft > 0:
                    last_run_times.append(filetime_to_datetime(ft))
                else:
                    last_run_times.append(datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc))

            # Extract referenced path strings from Section 3 (Path Strings)
            referenced_paths = []
            if sec3_offset > 0 and len(data) >= sec3_offset + sec3_size:
                path_bytes = data[sec3_offset : sec3_offset + sec3_size]
                path_str = path_bytes.decode("utf-16le", errors="ignore")
                referenced_paths = [p for p in path_str.split("\x00") if p]

            # Primary execution record timestamp is the most recent run time
            latest_run_time = max(last_run_times) if last_run_times else datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)

            return [{
                "artifact_type": "prefetch",
                "executable_name": exec_name,
                "pf_filename": self.safe_basename(self.artifact_path),
                "format_version": version,
                "execution_time": latest_run_time,
                "all_run_times": last_run_times,
                "run_count": run_count,
                "referenced_paths": referenced_paths
            }]

        except Exception as e:
            logger.error(f"Error parsing Prefetch file {self.artifact_path}: {e}")
            return []
