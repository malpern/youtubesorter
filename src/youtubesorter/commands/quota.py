"""Quota command for YouTube playlists."""

from . import YouTubeCommand
from ..logging_config import get_logger
from ..api import YouTubeAPI

logger = get_logger(__name__)


class QuotaCommand(YouTubeCommand):
    """Command to check YouTube API quota usage."""

    def __init__(self, youtube: YouTubeAPI) -> None:
        super().__init__(youtube)
        self.name = "quota"
        self.help = "Check YouTube API quota usage"

    def _run(self) -> bool:
        """Run the quota command.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            quota_info = self.youtube.get_quota_info()
            logger.info("Quota usage: %s", quota_info)
            return True
        except Exception as e:
            logger.error("Failed to get quota information: %s", str(e))
            return False
