"""Command-line interface for YouTube playlist operations."""

import argparse
import logging
import sys

from . import auth, commands, quota, utils, common
from .errors import YouTubeError
from .recovery import RecoveryManager


logger = logging.getLogger(__name__)


def list_recovery_destinations(playlist_id: str, operation_type: str) -> None:
    """List destinations in recovery state.

    Args:
        playlist_id (str): The playlist ID to check
        operation_type (str): The operation type (move or filter)
    """
    state_file = utils.find_latest_state(playlist_id)
    if not state_file:
        logger.info("No recovery state found for playlist %s", playlist_id)
        return

    manager = RecoveryManager(playlist_id, operation_type, state_file)

    if manager.operation_type != operation_type:
        raise ValueError(f"Operation type mismatch: {manager.operation_type} != {operation_type}")

    logger.info("Available destinations in recovery state:")
    for dest_id in sorted(manager.destination_metadata.keys()):
        metadata = manager.destination_metadata[dest_id]
        progress = manager.get_destination_progress(dest_id)
        title = metadata.get("title", dest_id)
        success_count = progress.get("success_count", 0)
        failure_count = progress.get("failure_count", 0)
        status = "completed" if progress.get("completed", False) else "in progress"
        logger.info(
            "  %s (%s): %d successful, %d failed - %s",
            title,
            dest_id,
            success_count,
            failure_count,
            status,
        )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(description="YouTube playlist management tool")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Move command
    move_parser = subparsers.add_parser("move", help="Move videos between playlists")
    move_parser.add_argument("source", help="Source playlist ID or URL")
    move_parser.add_argument("target", help="Target playlist ID or URL")
    move_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    move_parser.add_argument(
        "-r", "--resume", action="store_true", help="Resume previous operation"
    )
    move_parser.add_argument(
        "--resume-destination", help="Resume from specific destination playlist"
    )
    move_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate operations without making changes"
    )
    move_parser.add_argument(
        "--retry-failed", action="store_true", help="Retry previously failed operations"
    )
    move_parser.add_argument("--limit", type=int, help="Limit number of videos to process")

    # Filter command
    filter_parser = subparsers.add_parser("filter", help="Filter videos into playlists")
    filter_parser.add_argument("source", help="Source playlist ID or URL")
    filter_parser.add_argument("target", help="Target playlist ID or URL")
    filter_parser.add_argument("prompt", help="Filter prompt")
    filter_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    filter_parser.add_argument(
        "-r", "--resume", action="store_true", help="Resume previous operation"
    )
    filter_parser.add_argument(
        "--resume-destination", help="Resume from specific destination playlist"
    )
    filter_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate operations without making changes"
    )
    filter_parser.add_argument(
        "--retry-failed", action="store_true", help="Retry previously failed operations"
    )
    filter_parser.add_argument("--limit", type=int, help="Limit number of videos to process")

    # Quota command
    quota_parser = subparsers.add_parser("quota", help="Check API quota usage")
    quota_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    # Undo command
    undo_parser = subparsers.add_parser("undo", help="Undo last operation")
    undo_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    # List destinations command
    list_parser = subparsers.add_parser(
        "list-destinations", help="List destinations in recovery state"
    )
    list_parser.add_argument("playlist", help="Source playlist ID or URL")
    list_parser.add_argument(
        "--operation", choices=["move", "filter"], required=True, help="Operation type"
    )

    return parser


def main() -> int:
    """Main entry point.

    Returns:
        int: Exit code
    """
    parser = create_parser()
    try:
        args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
    except SystemExit as e:
        return 1 if e.code == 2 else e.code

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Get YouTube service
    youtube = auth.get_youtube_service()
    if not youtube:
        logger.error("Command failed: %s", "Failed to get YouTube service")
        return 1

    # Check quota
    quota_used, quota_limit = quota.check_quota(youtube)
    if quota_used >= quota_limit:
        logger.error("Quota limit reached: %d/%d", quota_used, quota_limit)
        return 1

    # Execute command
    try:
        if args.command == "move":
            command = commands.MoveCommand(
                youtube=youtube,
                source_playlist=args.source,
                target_playlist=args.target,
                filter_pattern=None,  # Move command doesn't use filter pattern
                dry_run=getattr(args, "dry_run", False),
                resume=getattr(args, "resume", False),
                resume_destination=getattr(args, "resume_destination", None),
                retry_failed=getattr(args, "retry_failed", False),
                verbose=getattr(args, "verbose", False),
                limit=getattr(args, "limit", None),
            )
            try:
                command.validate()
                if not command.run():
                    logger.error("Command failed to run successfully")
                    return 1
                return 0
            except YouTubeError as e:
                logger.error("Command failed: %s", str(e))
                return 1
            except Exception as e:
                logger.error("Command failed: %s", str(e))
                return 1
        elif args.command == "filter":
            command = commands.FilterCommand(
                youtube=youtube,
                source_playlist=args.source,
                target_playlist=args.target,
                filter_pattern=args.prompt,
                dry_run=getattr(args, "dry_run", False),
                resume=getattr(args, "resume", False),
                resume_destination=getattr(args, "resume_destination", None),
                retry_failed=getattr(args, "retry_failed", False),
                verbose=getattr(args, "verbose", False),
                limit=getattr(args, "limit", None),
            )
            try:
                command.validate()
                if not command.run():
                    logger.error("Command failed to run successfully")
                    return 1
                return 0
            except YouTubeError as e:
                logger.error("Command failed: %s", str(e))
                return 1
            except Exception as e:
                logger.error("Command failed: %s", str(e))
                return 1
        elif args.command == "list-destinations":
            try:
                list_recovery_destinations(args.playlist, args.operation)
                return 0
            except (argparse.ArgumentError, ValueError) as e:
                logger.error("Failed to list destinations: %s", str(e))
                return 1
            except SystemExit as e:
                return 1 if e.code == 2 else e.code
        elif args.command == "undo":
            success = common.undo_operation(youtube, args.verbose)
            return 0 if success else 1
        elif args.command == "quota":
            return 0
        else:
            parser.print_help()
            return 1

    except SystemExit as e:
        return 1 if e.code == 2 else e.code
    except Exception as e:
        logger.error("Command failed: %s", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
