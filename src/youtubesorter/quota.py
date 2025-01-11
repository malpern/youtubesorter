"""YouTube API quota management."""

import functools
from typing import Callable, Tuple, TypeVar

from . import auth
from .errors import YouTubeError
from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def check_quota() -> Tuple[int, int]:
    """Check current quota usage.

    Returns:
        Tuple of (used quota, remaining quota)

    Raises:
        YouTubeError: If quota information cannot be retrieved
    """
    youtube = auth.get_youtube_service()
    if not youtube:
        raise YouTubeError("Failed to get YouTube service")

    try:
        # pylint: disable=no-member
        request = youtube.channels().list(part="snippet", mine=True, maxResults=1)
        # pylint: enable=no-member
        response = request.execute()

        quota_used = int(response["responseDetails"]["quotaUsed"])
        quota_limit = int(response["responseDetails"]["quotaLimit"])
        remaining = quota_limit - quota_used

        return quota_used, remaining

    except Exception as e:
        raise YouTubeError(f"Failed to get quota information: {str(e)}")


def with_quota_check(min_required: int = 100) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to check quota before executing a function.

    Args:
        min_required: Minimum quota required to execute function

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: any, **kwargs: any) -> T:
            _, remaining = check_quota()
            if remaining < min_required:
                raise YouTubeError(
                    "Insufficient quota remaining. " f"Need {min_required}, have {remaining}"
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
