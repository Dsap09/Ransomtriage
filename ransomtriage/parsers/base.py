import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any

logger = logging.getLogger("ransomtriage.parsers")

class BaseParser(ABC):
    """Abstract Base Class for all forensic artifact parsers."""

    def __init__(self, artifact_path: str):
        self.artifact_path = artifact_path

    @abstractmethod
    def validate(self) -> bool:
        """Validates if the target artifact exists and has correct format."""
        pass

    @abstractmethod
    def parse(self) -> List[Dict[str, Any]]:
        """
        Parses the artifact and returns a list of normalized records.
        Returns empty list if invalid or corrupted.
        """
        pass

    def safe_basename(self, file_path: str) -> str:
        """Safely extracts filename from Windows or POSIX path string."""
        if not file_path:
            return ""
        # Handle both Windows \ and Unix / separators
        normalized = file_path.replace("\\", "/")
        return os.path.basename(normalized)
