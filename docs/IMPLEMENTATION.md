# Technical Implementation Details

## Project Structure

```
.
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md     # System architecture
│   ├── CHANGELOG.md        # Version history
│   ├── IMPLEMENTATION.md   # Technical details
│   ├── INSTALLATION.md     # Setup guide
│   └── USAGE.md           # Usage instructions
├── src/                    # Source code
│   ├── __init__.py
│   ├── api.py               # YouTube API interactions
│   ├── auth.py              # Authentication handling
│   ├── cache.py             # Response caching
│   ├── classifier.py        # Video classification logic
│   ├── clear_playlist.py    # Playlist clearing utility
│   ├── cli.py               # Command-line interface
│   ├── command.py           # Base command class
│   ├── commands/            # Command implementations
│   ├── common.py            # Shared utilities
│   ├── config.py            # Configuration management
│   ├── consolidate.py       # Playlist consolidation
│   ├── deduplicate.py       # Playlist deduplication
│   ├── distribute.py        # Playlist distribution
│   ├── errors.py            # Error handling
│   ├── logging.py           # Logging utilities
│   ├── quota.py            # Quota management
│   ├── recovery.py          # State recovery
│   ├── undo.py             # Undo operations
│   └── utils.py             # Utility functions
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── run_api_tests.py    # API test runner
│   ├── run_api_tests.sh    # API test shell script
│   ├── test_api.py         # API tests
│   ├── test_auth.py        # Authentication tests
│   ├── test_cache.py       # Cache tests
│   ├── test_classifier.py  # Classification tests
│   ├── test_cli.py         # CLI tests
│   ├── test_commands.py    # Command tests
│   ├── test_common.py      # Utility tests
│   ├── test_consolidate.py # Consolidation tests
│   ├── test_deduplicate.py # Deduplication tests
│   ├── test_distribute.py  # Distribution tests
│   ├── test_errors.py      # Error handling tests
│   ├── test_integration.py # Integration tests
│   ├── test_performance.py # Performance tests
│   ├── test_quota.py       # Quota management tests
│   ├── test_recovery.py    # Recovery tests
│   └── test_utils.py       # Utility tests
├── data/                   # Data directory
│   ├── credentials/         # API credentials
│   └── recovery/           # Recovery state files
├── README.md              # Project overview
├── pyproject.toml         # Project configuration
└── ...                    # (other config files)
```

## Architecture Documentation

### System Components
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Command Line   │     │   Commands   │     │   YouTube   │
│   Interface    ├─────►│   Layer     ├─────►│    API     │
└─────────────────┘     └──────────────┘     └─────────────┘
                              │
                        ┌─────┴─────┐
                        │           │
                   ┌────▼───┐  ┌────▼────┐
                   │ Cache  │  │  Quota  │
                   │ Layer  │  │ Manager │
                   └────────┘  └─────────┘
```

### Component Responsibilities

1. **Command Line Interface**
   - Parses user input
   - Validates arguments
   - Creates appropriate command objects
   - Displays progress and results

2. **Commands Layer**
   - Implements Command Pattern
   - Handles business logic
   - Manages state and recovery
   - Reports progress
   - Implements undo operations

3. **Cache Layer**
   - Caches API responses
   - Manages TTL (Time To Live)
   - Handles cache invalidation
   - Provides batch operations
   - Tracks cache statistics

4. **Quota Manager**
   - Tracks API quota usage
   - Implements rate limiting
   - Manages quota reset
   - Provides usage statistics
   - Prevents quota exhaustion

### Data Flow
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Parse   │    │ Validate │    │  Check   │    │  Execute │
│  Input   ├───►│ Command  ├───►│  Cache   ├───►│   API    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │                │
                                     │                │
                                     ▼                ▼
                               ┌──────────┐    ┌──────────┐
                               │ Update   │    │  Update  │
                               │  Cache   │◄───┤  State   │
                               └──────────┘    └──────────┘
```

## Design Decisions

1. **Command Pattern**
   - Why: Standardize operations, enable undo
   - Trade-off: More boilerplate but better maintainability
   - Benefit: Easy to add new commands

2. **Caching Strategy**
   - Why: Reduce API calls, improve performance
   - Trade-off: Memory usage vs API quota
   - Implementation: File-based with TTL

3. **Batch Operations**
   - Why: Optimize API quota usage
   - Trade-off: Complexity vs performance
   - Benefit: Process more videos within quota limits

4. **Progress Reporting**
   - Why: Better user experience
   - Trade-off: Slight overhead
   - Benefit: Users know what's happening

## Error Recovery

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Operation│    │  Error   │    │ Recovery │
│  Fails   ├───►│ Handler  ├───►│  State   │
└──────────┘    └──────────┘    └──────────┘
                     │               │
                     ▼               ▼
                ┌──────────┐    ┌──────────┐
                │  Retry   │    │  Resume  │
                │ Strategy │◄───┤Operation │
                └──────────┘    └──────────┘
```

## State Management
- Operations are atomic where possible
- State is persisted after each batch
- Recovery files store operation progress
- Undo information is preserved
- Automatic cleanup of old state files

## Performance Considerations
- Batch operations reduce API calls
- Caching minimizes redundant requests
- Progress tracking has minimal overhead
- Memory usage is optimized
- Network retries prevent data loss

## API Documentation

### YouTube API Responses

#### Playlist Items Response
```json
{
    "items": [
        {
            "id": "playlist_item_id",
            "snippet": {
                "resourceId": {
                    "videoId": "video123"
                },
                "title": "Video Title",
                "description": "Video Description",
                "thumbnails": {
                    "default": {
                        "url": "http://example.com/thumb.jpg"
                    }
                }
            },
            "status": {
                "privacyStatus": "public"
            }
        }
    ],
    "nextPageToken": "token123"
}
```

### Rate Limits and Quotas
The YouTube Data API v3 has the following quota limits:
- Daily quota: 10,000 units
- Quota costs per operation:
  - `playlistItems.list`: 1 unit
  - `playlistItems.insert`: 50 units
  - `playlistItems.delete`: 50 units
  - Batch operations can combine up to 50 requests

### Error Handling
Common API errors and their handling:
```python
try:
    # API operation
except errors.QuotaExceededError:
    # Daily quota exceeded, retry tomorrow
except errors.RateLimitError:
    # Too many requests, implement backoff
except errors.PlaylistNotFoundError:
    # Invalid playlist ID
except errors.VideoNotFoundError:
    # Video was deleted or made private
except errors.AuthenticationError:
    # Token expired or invalid
``` 

# Implementation Details

## Command Pattern

The project uses the Command pattern for all operations, with a central base class `YouTubeCommand` in `src/commands/__init__.py`.

### Base Command Class

All commands MUST inherit from `YouTubeCommand` which provides:
- Template method pattern for standardized execution
- Progress tracking and reporting
- Error handling and recovery
- Dry run support
- Cleanup hooks
- Logging configuration

Example:
```python
from src.youtubesorter.commands import YouTubeCommand

class MyCommand(YouTubeCommand):
    def validate(self):
        # Validate arguments
        pass

    def run(self):
        # Implement command logic
        return True
```

### Command Flow
1. `execute()` - Template method that orchestrates execution
2. `setup()` - Initialize resources (e.g., YouTube client)
3. `validate()` - Check command arguments
4. `run()` - Execute command logic
5. `cleanup()` - Clean up resources

### Features
- Progress tracking via `set_total_items()` and `update_progress()`
- Dry run support via `dry_run` flag
- Error handling via `handle_error()`
- Logging via `self._logger`
- State management via recovery system

### Important Note
DO NOT create new base command classes. The `YouTubeCommand` class in `src/commands/__init__.py` 
is the single source of truth for command implementation patterns. 

## YouTube API Field Patterns

### Video ID Access
We consistently use `snippet.resourceId.videoId` for accessing video IDs from playlist items. This is the preferred method as it:
- Provides more complete metadata about the video
- Is more stable across API versions
- Matches current YouTube API best practices

### Parameter Ordering Standards
For consistency across the codebase, methods follow these parameter ordering rules:
1. `playlist_id` always comes first for playlist-related operations
2. `video_ids` follows as a list (never a set) to maintain order
3. Optional parameters follow required parameters
4. Boolean flags (e.g., `copy`, `verbose`) come last

Example:
```python
def batch_move_videos_to_playlist(
    playlist_id: str,           # Required, comes first
    video_ids: List[str],       # Required list, comes second
    remove_from_source: bool = True,  # Optional boolean flag
) -> List[str]:
    """Move multiple videos to a playlist."""
```

### Error Handling Pattern
To prevent error message duplication and maintain clear stack traces:
1. Low-level functions raise specific exceptions (PlaylistNotFoundError, YouTubeError)
2. Mid-level functions may catch and re-raise with additional context
3. Top-level functions (CLI, API endpoints) catch and format user-friendly messages

### State Management in Tests
Each test should:
1. Set up its own clean state
2. Clean up any persistent state after completion
3. Not rely on state from other tests

## Codebase Stability Guidelines

### Stable Implementation Decisions
1. **Video ID Field**: We consistently use `snippet.resourceId.videoId` for accessing video IDs from playlist items
2. **Parameter Order**: Methods follow the standard order: `(playlist_id, video_ids, source_playlist_id, remove_from_source)`
3. **Error Handling**: Standardized error handling with specific error types and clear error messages
4. **Command Pattern**: All operations use the Command pattern through `YouTubeCommand` base class

### Refactoring Guidelines
1. **DO NOT start significant refactors without team discussion and explicit approval**
2. **DO NOT change core API interfaces** - they are stable and have test coverage
3. **DO NOT modify the Command pattern implementation** - it's a core architectural decision
4. **DO NOT change error handling patterns** - they are standardized across the codebase

### Acceptable Changes
1. Bug fixes that maintain existing interfaces
2. Performance optimizations that don't change APIs
3. Documentation improvements
4. New features that follow existing patterns
5. Test coverage improvements

### Required Approvals
1. **Major Refactoring**: Requires team discussion and explicit approval
2. **API Changes**: Must be discussed and approved by team
3. **Architectural Changes**: Need thorough review and team consensus
4. **Core Pattern Changes**: Require detailed proposal and approval

### When Proposing Changes
1. Document the current behavior
2. Explain why the change is needed
3. Provide test coverage metrics
4. Include migration plan
5. Consider backward compatibility
6. Assess impact on existing features