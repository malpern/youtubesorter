"""YouTube playlist management tool."""

__version__ = "0.1.0"

# Import all public components
from .api import YouTubeAPI
from .auth import get_youtube_service
from .cache import PlaylistCache
from .classifier import classify_video_titles
from .cli import main
from .commands import YouTubeCommand
from .commands.filter import FilterCommand
from .commands.move import MoveCommand
from .commands.quota import QuotaCommand
from .consolidate import consolidate_playlists
from .core import YouTubeBase
from .deduplicate import deduplicate_playlist
from .distribute import distribute_videos
from .errors import YouTubeError
from .logging_config import configure_logging, get_logger
from .quota import with_quota_check
from .recovery import RecoveryManager
from .undo import UndoManager
from .utils import find_latest_state

# Import config variables
from .config import (  # noqa: F401
    YOUTUBE_SCOPES,
    CLIENT_SECRETS_FILE,
    CREDENTIALS_DIR,
    TOKEN_FILE,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    BATCH_SIZE,
)

# Configure logging
configure_logging()

# Get logger for this module
logger = get_logger(__name__)
