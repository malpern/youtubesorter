"""Logging configuration for the application."""

import logging
import sys
from typing import Optional

# Create logger
logger: logging.Logger = logging.getLogger("youtubesorter")
logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Add formatter to console handler
console_handler.setFormatter(formatter)

# Add console handler to logger
logger.addHandler(console_handler)

# Prevent propagation to root logger
logger.propagate = False


def enable_debug() -> None:
    """Enable debug logging.

    Sets both the logger and console handler to DEBUG level.
    """
    logger.setLevel(logging.DEBUG)
    console_handler.setLevel(logging.DEBUG)


def disable_debug() -> None:
    """Disable debug logging.

    Sets both the logger and console handler back to INFO level.
    """
    logger.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Name of the logger. If None, returns the root logger.

    Returns:
        A Logger instance configured with the application's settings.
    """
    if name:
        return logging.getLogger(f"youtubesorter.{name}")
    return logger
