"""Base command class for YouTube operations."""

from typing import Optional

from ..core import YouTubeBase
from ..errors import YouTubeError
from ..logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class YouTubeCommand:
    """Base class for YouTube commands."""

    def __init__(self, youtube: YouTubeBase):
        """Initialize command.

        Args:
            youtube: YouTube API client
        """
        self.youtube = youtube
        self._logger = logger
        self._validated = False
        self.dry_run = False
        self.verbose = False
        self._total_items = 0
        self._current_item = 0

    def validate(self) -> None:
        """Validate command parameters.

        Raises:
            ValueError: If parameters are invalid
        """
        if not self.youtube:
            raise ValueError("YouTube API client is required")
        self._validated = True

    def run(self) -> bool:
        """Run the command.

        Returns:
            bool: True if successful, False otherwise

        Raises:
            YouTubeError: If command fails
        """
        try:
            self.validate()
            return self._run()
        except Exception as e:
            raise YouTubeError(str(e)) from e

    def _run(self) -> bool:
        """Internal run implementation.

        Returns:
            bool: True if successful, False otherwise
        """
        return False

    def set_total_items(self, total: int) -> None:
        """Set total number of items to process.

        Args:
            total: Total number of items
        """
        self._total_items = total
        self._current_item = 0

    def update_progress(self, current: Optional[int] = None) -> None:
        """Update progress indicator.

        Args:
            current: Optional current item number. If not provided, increments by 1.
        """
        if current is not None:
            self._current_item = current
        else:
            self._current_item += 1
