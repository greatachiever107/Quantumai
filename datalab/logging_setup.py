"""Logging setup.

LEARNING NOTES
--------------
``logging`` is Python's standard way to record what a program does. Each message has a
level (INFO, WARNING, ERROR). We write to the console AND a rotating file: when the file
reaches ~1 MB it is rolled over, so logs can never fill your disk.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(logs_dir: Path, name: str = "datalab") -> logging.Logger:
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Avoid adding duplicate handlers if this function is called twice.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    file_handler = RotatingFileHandler(
        logs_dir / "datalab.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console)
    logger.propagate = False
    return logger
