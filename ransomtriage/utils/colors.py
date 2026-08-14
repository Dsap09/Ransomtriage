# File: ransomtriage/utils/colors.py
"""
Kode warna ANSI untuk terminal.
Kompatibel dengan Linux/macOS dan Windows 10+ (CMD/PowerShell).
"""

import os
import sys


def _enable_windows_ansi():
    """Aktifkan dukungan ANSI escape sequences di Windows CMD/PowerShell."""
    if sys.platform == "win32":
        os.system("")  # Trick sederhana untuk enable virtual terminal processing


# Auto-enable saat modul di-import
_enable_windows_ansi()


class Colors:
    """Kode warna ANSI untuk terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    NC = '\033[0m'  # No Color / Reset

    @staticmethod
    def green(text):
        return f"{Colors.GREEN}{text}{Colors.NC}"

    @staticmethod
    def red(text):
        return f"{Colors.RED}{text}{Colors.NC}"

    @staticmethod
    def cyan(text):
        return f"{Colors.CYAN}{text}{Colors.NC}"

    @staticmethod
    def yellow(text):
        return f"{Colors.YELLOW}{text}{Colors.NC}"

    @staticmethod
    def blue(text):
        return f"{Colors.BLUE}{text}{Colors.NC}"

    @staticmethod
    def bold(text):
        return f"{Colors.BOLD}{text}{Colors.NC}"

    @staticmethod
    def header(text):
        return f"{Colors.HEADER}{text}{Colors.NC}"
