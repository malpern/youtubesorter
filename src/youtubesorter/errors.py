"""Error handling utilities."""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def log_error(error: Exception, context: Optional[str] = None) -> None:
    """Log an error with optional context.

    Args:
        error: The exception to log
        context: Optional context about where/why the error occurred
    """
    if context:
        logger.error(f"{context}: {str(error)}")
    else:
        logger.error(str(error))


class YouTubeError(Exception):
    """Base class for YouTube API errors."""

    pass


class PlaylistNotFoundError(YouTubeError):
    """Error raised when a playlist is not found."""

    pass


class RateLimitError(YouTubeError):
    """Error raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = None):
        """Initialize error.

        Args:
            retry_after: Number of seconds to wait before retrying
        """
        self.retry_after = retry_after
        if retry_after:
            super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")
        else:
            super().__init__("Rate limit exceeded")


class VideoNotFoundError(YouTubeError):
    """Error raised when a video is not found (private/deleted)."""

    pass


class ClassifierError(YouTubeError):
    """Error raised when video classification fails."""

    pass


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Optional[tuple] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry a function on failure.

    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function
    """
    if retryable_exceptions is None:
        retryable_exceptions = (RateLimitError,)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "Error in %s: %s. Retrying in %s seconds... (attempt %d/%d)",
                            func.__name__,
                            str(e),
                            delay,
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            "Error in %s: %s. Max retries (%d) exceeded.",
                            func.__name__,
                            str(e),
                            max_retries,
                        )
                        raise

            raise last_exception

        return wrapper

    return decorator
