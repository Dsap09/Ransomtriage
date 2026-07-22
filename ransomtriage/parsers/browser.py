import os
import sqlite3
import datetime
import logging
import shutil
import tempfile
from typing import List, Dict, Any
from .base import BaseParser

logger = logging.getLogger("ransomtriage.parsers.browser")

# Webkit Epoch: January 1, 1601 UTC
WEBKIT_EPOCH = datetime.datetime(1601, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

def webkit_to_datetime(webkit_timestamp: int) -> datetime.datetime:
    """Converts Webkit microsecond timestamp to Python datetime in UTC."""
    if not webkit_timestamp or webkit_timestamp <= 0:
        return datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    seconds = webkit_timestamp / 1_000_000.0
    return WEBKIT_EPOCH + datetime.timedelta(seconds=seconds)

class BrowserParser(BaseParser):
    """Parses Chrome/Edge SQLite 'History' artifacts to extract download logs."""

    def validate(self) -> bool:
        if not os.path.exists(self.artifact_path) or not os.path.isfile(self.artifact_path):
            return False
        # Basic check for SQLite header
        try:
            with open(self.artifact_path, "rb") as f:
                header = f.read(16)
                return header.startswith(b"SQLite format 3")
        except Exception as e:
            logger.warning(f"Failed to read file header for {self.artifact_path}: {e}")
            return False

    def parse(self) -> List[Dict[str, Any]]:
        if not self.validate():
            logger.warning(f"File {self.artifact_path} is corrupt or not a valid SQLite database.")
            return []

        records = []
        temp_dir = tempfile.mkdtemp()
        temp_db = os.path.join(temp_dir, "temp_history.sqlite")

        try:
            # Copy to temp file to prevent lock issues if browser database is locked
            shutil.copy2(self.artifact_path, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()

            # Execute parameterized SELECT query
            query = """
                SELECT 
                    d.id, d.target_path, d.current_path, d.start_time, d.end_time,
                    d.received_bytes, d.total_bytes, d.referrer, d.tab_url, d.mime_type
                FROM downloads d
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                dl_id, target_path, current_path, start_time_raw, end_time_raw, rec_bytes, tot_bytes, referrer, tab_url, mime_type = row
                
                final_path = target_path or current_path or ""
                filename = self.safe_basename(final_path)
                
                start_dt = webkit_to_datetime(start_time_raw)
                end_dt = webkit_to_datetime(end_time_raw) if end_time_raw else start_dt

                records.append({
                    "artifact_type": "browser_download",
                    "download_id": dl_id,
                    "filename": filename,
                    "full_path": final_path,
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "received_bytes": rec_bytes or 0,
                    "total_bytes": tot_bytes or 0,
                    "referrer_url": referrer or "",
                    "tab_url": tab_url or "",
                    "mime_type": mime_type or ""
                })

            conn.close()
        except sqlite3.Error as e:
            logger.error(f"SQLite error while parsing {self.artifact_path}: {e}. File tidak valid.")
        except Exception as e:
            logger.error(f"Unexpected error parsing browser history {self.artifact_path}: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return records
