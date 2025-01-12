"""Command implementations for YouTube playlist operations.

# YouTube API Field Patterns
When accessing video IDs from YouTube API responses, we use `snippet.resourceId.videoId` 
consistently across the codebase. This field is preferred over `contentDetails.videoId` because:
- It's the modern, more stable approach
- It provides additional context via the snippet object
- It's consistent with YouTube Data API v3 documentation

# Parameter Ordering Standards
Methods that operate on playlists follow this parameter order:
1. playlist_id: The target playlist ID (str)
2. video_ids: List of video IDs to process (List[str])
3. Optional parameters (e.g., copy=False, limit=None)

Example:
```python
def batch_move_videos_to_playlist(
    playlist_id: str,
    video_ids: List[str],
    source_playlist: Optional[str] = None,
    remove_from_source: bool = True
) -> List[str]:
    pass
```

# Error Handling Pattern
To avoid double-wrapped errors, we follow these rules:
1. Low-level functions raise specific exceptions without wrapping
2. Mid-level functions may catch and re-raise with context if needed
3. Top-level command handlers provide final error context and logging
4. Error messages should not repeat the error chain

# State Management in Tests
Tests should:
1. Start with a clean state (no cached data)
2. Clean up any state after completion
3. Use fixtures for common setup/teardown
4. Not rely on state from previous tests

This ensures test isolation and reproducibility.
""" 