import logging
import sys


def logger_setup(logger_name: str, level=logging.INFO) -> logging.Logger:
    """Configures and returns a logger that outputs to both a file and the console."""

    # Logger instance
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Prevent duplicate logs if the logger is configured multiple times
    if logger.hasHandlers():
        return logger

    # Formatting
    # Example: 2026-05-24 15:30:00,123 | INFO     | Logger Name | Logger massage.
    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (streams logs to terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger
