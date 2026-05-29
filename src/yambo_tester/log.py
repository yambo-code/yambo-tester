# Copyright (c) 2025 Nicola Spallanzani
# Licensed under the MIT License. See LICENSE file for details.

import logging
import sys
from pathlib import Path


MAIN_LOGGER_NAME = "yambo_tester"
TEST_LOGGER_PREFIX = "yambo_tester.test"


def _logger_name_for_path(logfile: Path, prefix: str = TEST_LOGGER_PREFIX) -> str:
    resolved = Path(logfile).resolve()
    safe_path = resolved.as_posix().lstrip("/").replace("/", ".").replace(" ", "_")
    return f"{prefix}.{safe_path}"


def _reset_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def setup_logging(logfile: Path = None, level=logging.INFO, console=True, name=MAIN_LOGGER_NAME):
    """
    Configure logging for a named logger.

    :param logfile: Path to the log file. If ``None``, a default file named
        ``yambo_tester.log`` will be created in the current working directory.
    :type logfile: Path, optional
    :param level: Logging level (e.g., ``logging.INFO``, ``logging.DEBUG``). Default is ``INFO``.
    :type level: int, optional
    :param console: Whether to attach a console handler.
    :type console: bool, optional
    :param name: Logger name to configure.
    :type name: str, optional

    :return: The configured logger instance.
    :rtype: logging.Logger
    """
    if logfile is None:
        logfile = Path("yambo_tester.log")
    else:
        logfile = Path(logfile)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    _reset_handlers(logger)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(fmt="%(levelname)-8s | %(message)s"))
        logger.addHandler(console_handler)

    logfile.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(logfile, mode="w")
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {logfile.resolve()}")
    return logger


def setup_test_logger(run_dir: Path, level=logging.INFO):
    """
    Configure a dedicated logger for one test run directory.

    :param run_dir: The test run directory containing ``tester.log``.
    :type run_dir: Path
    :param level: Logging level for the test logger.
    :type level: int, optional

    :return: The configured per-test logger instance.
    :rtype: logging.Logger
    """
    run_dir = Path(run_dir)
    logfile = run_dir / "tester.log"
    return setup_logging(logfile=logfile, level=level, console=False, name=_logger_name_for_path(logfile))


if __name__ == '__main__':
    logger = setup_logging()
    logger.info("A message")
    logger.warning("A message")
    logger.error("A message")
