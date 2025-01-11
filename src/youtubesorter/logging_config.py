"""Logging configuration for the youtubesorter package."""

import logging


def configure_logging():
    """Configure logging for the package."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration to avoid duplicates
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Name for the logger, typically __name__

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
