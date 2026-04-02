"""
logger.py – Shared logging setup.
Call get_logger(__name__) in every module to obtain a pre-configured logger.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "gateway.log"
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def _setup_root_logger() -> None:
    """Configure the root logger once (idempotent)."""
    global _initialized
    if _initialized:
        return

    _LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # handlers can filter further

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    # ---- Console handler (INFO and above) ----
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # ---- Rotating file handler (DEBUG and above, max 5 MB × 3 files) ----
    file_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root.addHandler(console)
    root.addHandler(file_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, initialising the root logger if needed."""
    _setup_root_logger()
    return logging.getLogger(name)
