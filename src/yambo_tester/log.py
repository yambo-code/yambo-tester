# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import logging
import sys
from pathlib import Path


def setup_logging(logfile: Path = None, level=logging.INFO, console=True):
    """
    Configure logging to output both to a log file and to the console.
    
    :param logfile: Path to the log file. If ``None``, a default file named
        ``yambo_tester.log`` will be created in the current working directory.
    :type logfile: Path, optional
    :param level: Logging level (e.g., ``logging.INFO``, ``logging.DEBUG``). Default is ``INFO``.
    :type level: int, optional
    
    :return: The configured root logger instance.
    :rtype: logging.Logger
    """
    # Default log file if none provided
    if logfile is None:
        logfile = Path("yambo_tester.log")

    # Get the root logger (common for the entire application)
    logger = logging.getLogger()
    logger.setLevel(level)

    # Clear any existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        fmt="%(levelname)-8s | %(message)s"
    )
    console_handler.setFormatter(console_format)

    # --- File Handler ---
    # mode="w" overwrites the log file at each run; use "a" to append instead
    file_handler = logging.FileHandler(logfile, mode="w")
    file_handler.setLevel(level)
    file_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    # Attach both handlers to the root logger
    if console: logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Log the initialization message
    logger.info(f"Logging initialized. Log file: {logfile.resolve()}")

    return logger


if __name__ == '__main__':
    logger = setup_logging()
    logger.info("A message")
    logger.warning("A message")
    logger.error("A message")
