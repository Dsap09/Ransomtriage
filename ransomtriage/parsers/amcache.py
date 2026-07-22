import os
import json
import logging
import datetime
from typing import List, Dict, Any
from .base import BaseParser

logger = logging.getLogger("ransomtriage.parsers.amcache")

class AmcacheParser(BaseParser):
    """
    Parses Amcache.hve Registry Hive or Amcache JSON export files
    to extract program SHA-1 hashes, file paths, and execution timestamps.
    """

    def validate(self) -> bool:
        if not os.path.exists(self.artifact_path) or not os.path.isfile(self.artifact_path):
            return False
        # Check for JSON mock file or Windows Registry Hive header ('regf')
        try:
            with open(self.artifact_path, "rb") as f:
                header = f.read(4)
                if header == b"regf" or header.startswith(b"{") or header.startswith(b"["):
                    return True
                return False
        except Exception as e:
            logger.warning(f"Error checking Amcache file {self.artifact_path}: {e}")
            return False

    def parse(self) -> List[Dict[str, Any]]:
        if not self.validate():
            logger.warning(f"File {self.artifact_path} is not a valid Amcache registry or JSON file.")
            return []

        records = []
        try:
            # 1. Try parsing JSON format (e.g. from dummy generator or pre-parsed reg export)
            if self.artifact_path.endswith(".json"):
                with open(self.artifact_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        records.append({
                            "artifact_type": "amcache",
                            "executable_name": self.safe_basename(item.get("path") or item.get("name", "")),
                            "full_path": item.get("path", ""),
                            "sha1": item.get("sha1", "").lower(),
                            "execution_time": datetime.datetime.fromisoformat(item["first_execution"]) if "first_execution" in item else datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
                        })
                return records

            # 2. Try parsing Windows Registry hive 'Amcache.hve' using python-registry
            try:
                from Registry import Registry
                reg = Registry.Registry(self.artifact_path)
                # Attempt to traverse Root\Root\File or Root\InventoryApplicationFile
                file_key = None
                try:
                    file_key = reg.open("Root\\File")
                except Exception:
                    try:
                        file_key = reg.open("Root\\InventoryApplicationFile")
                    except Exception:
                        pass

                if file_key:
                    for subkey in file_key.subkeys():
                        path = ""
                        sha1 = ""
                        exec_time = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
                        
                        for val in subkey.values():
                            val_name = val.name().lower()
                            if val_name in ("15", "lowercasehash", "filehash"):
                                sha1 = str(val.value()).lower()
                            elif val_name in ("15", "fullpath", "path"):
                                path = str(val.value())
                            elif val_name in ("17", "lastwritetime"):
                                if isinstance(val.value(), datetime.datetime):
                                    exec_time = val.value().replace(tzinfo=datetime.timezone.utc)

                        if path or sha1:
                            records.append({
                                "artifact_type": "amcache",
                                "executable_name": self.safe_basename(path),
                                "full_path": path,
                                "sha1": sha1,
                                "execution_time": exec_time
                            })
            except ImportError:
                logger.info("python-registry is not installed. Amcache .hve parsing skipped.")
            except Exception as e:
                logger.warning(f"Failed to parse registry hive {self.artifact_path}: {e}")

        except Exception as e:
            logger.error(f"Error parsing Amcache {self.artifact_path}: {e}")

        return records
