"""Tests for the logging configuration."""

import logging

from src.youtubesorter.logging import enable_debug, disable_debug, get_logger, logger


def test_default_logger_configuration():
    """Test the default logger configuration."""
    assert logger.name == "youtubesorter"
    assert logger.level == logging.INFO
    assert not logger.propagate

    # Check handler configuration
    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.level == logging.INFO

    # Check formatter configuration
    formatter = handler.formatter
    assert formatter._fmt == "%(asctime)s - %(levelname)s - %(message)s"
    assert formatter.datefmt == "%Y-%m-%d %H:%M:%S"


def test_enable_debug():
    """Test enabling debug logging."""
    # Start with default levels
    logger.setLevel(logging.INFO)
    logger.handlers[0].setLevel(logging.INFO)

    enable_debug()

    assert logger.level == logging.DEBUG
    assert logger.handlers[0].level == logging.DEBUG


def test_disable_debug():
    """Test disabling debug logging."""
    # Start with debug levels
    logger.setLevel(logging.DEBUG)
    logger.handlers[0].setLevel(logging.DEBUG)

    disable_debug()

    assert logger.level == logging.INFO
    assert logger.handlers[0].level == logging.INFO


def test_get_logger_no_name():
    """Test getting the root logger."""
    log = get_logger()
    assert log is logger


def test_get_logger_with_name():
    """Test getting a named logger."""
    log = get_logger("test")
    assert log.name == "youtubesorter.test"
    assert log.parent is logger


def test_logger_output():
    """Test that logger output is formatted correctly."""
    # Create a test formatter without timestamps
    test_formatter = logging.Formatter("%(levelname)s - %(message)s")
    original_formatter = logger.handlers[0].formatter

    try:
        # Replace the formatter
        logger.handlers[0].setFormatter(test_formatter)

        test_logger = get_logger("test")
        test_logger.info("Test message")

        # Get the last log record
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "Test message", (), None)
        formatted = logger.handlers[0].formatter.format(record)
        assert formatted == "INFO - Test message"
    finally:
        # Restore the original formatter
        logger.handlers[0].setFormatter(original_formatter)


def test_debug_output_disabled():
    """Test that debug messages are not logged when debug is disabled."""
    # Create a test formatter without timestamps
    test_formatter = logging.Formatter("%(levelname)s - %(message)s")
    original_formatter = logger.handlers[0].formatter

    try:
        # Replace the formatter
        logger.handlers[0].setFormatter(test_formatter)

        disable_debug()
        test_logger = get_logger("test")

        # Verify debug logging is disabled
        assert not test_logger.isEnabledFor(logging.DEBUG)
    finally:
        # Restore the original formatter
        logger.handlers[0].setFormatter(original_formatter)


def test_debug_output_enabled():
    """Test that debug messages are logged when debug is enabled."""
    # Create a test formatter without timestamps
    test_formatter = logging.Formatter("%(levelname)s - %(message)s")
    original_formatter = logger.handlers[0].formatter

    try:
        # Replace the formatter
        logger.handlers[0].setFormatter(test_formatter)

        enable_debug()
        test_logger = get_logger("test")

        # Create a debug record
        record = logging.LogRecord("test", logging.DEBUG, "test.py", 1, "Debug message", (), None)

        # Should be logged at DEBUG level
        assert test_logger.isEnabledFor(logging.DEBUG)
        formatted = logger.handlers[0].formatter.format(record)
        assert formatted == "DEBUG - Debug message"
    finally:
        # Restore the original formatter
        logger.handlers[0].setFormatter(original_formatter)
