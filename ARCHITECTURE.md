# Technical Architecture

This document describes the technical implementation details of the YouTube Playlist Organizer.

## System Overview

The system is built around three core operations:
1. Consolidating videos from multiple playlists into one
2. Distributing videos from one playlist to many
3. Removing duplicate videos from playlists

### High-Level Architecture

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

## Core Components

### 1. Command Line Interface (`cli.py`)

The CLI module handles:
- Command-line argument parsing
- Input validation
- Command instantiation
- Progress reporting
- Error display

```python
def main():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    # Add command parsers
    add_consolidate_parser(subparsers)
    add_distribute_parser(subparsers)
    add_deduplicate_parser(subparsers)
    
    args = parser.parse_args()
    command = create_command(args)
    command.execute()
```

### 2. Command Layer

Uses the Command pattern to standardize operations:

```python
class YouTubeCommand:
    """Base class for all commands."""
    
    def execute(self):
        """Template method defining command flow."""
        try:
            self.setup()
            self.validate()
            if not self.dry_run:
                self.run()
            self.cleanup()
        except Exception as e:
            self.handle_error(e)
            
    def setup(self):
        """Initialize resources."""
        self.api = YouTubeAPI()
        self.cache = Cache()
        
    def validate(self):
        """Validate command arguments."""
        raise NotImplementedError
        
    def run(self):
        """Execute command logic."""
        raise NotImplementedError
        
    def cleanup(self):
        """Clean up resources."""
        self.cache.save()
```

### 3. YouTube API Layer (`api.py`)

Wraps the YouTube Data API with:
- Batch operations
- Error handling
- Rate limiting
- Quota management

```python
class YouTubeAPI:
    """YouTube API wrapper."""
    
    def batch_move_videos(self, videos, source, target):
        """Move videos between playlists in batches."""
        for batch in chunks(videos, self.batch_size):
            try:
                self.add_videos_to_playlist(batch, target)
                self.remove_videos_from_playlist(batch, source)
            except YouTubeError as e:
                self.handle_api_error(e)
```

### 4. Cache System

Implements a TTL-based cache for API responses:

```python
class Cache:
    """TTL-based cache for API responses."""
    
    def __init__(self, ttl=3600):
        self.ttl = ttl
        self.data = {}
        self.timestamps = {}
        
    def get(self, key):
        """Get cached value if not expired."""
        if key in self.data:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.data[key]
            del self.data[key]
        return None
        
    def set(self, key, value):
        """Cache value with timestamp."""
        self.data[key] = value
        self.timestamps[key] = time.time()
```

### 5. Quota Management

Tracks and manages API quota usage:

```python
class QuotaManager:
    """Manages YouTube API quota usage."""
    
    def __init__(self, daily_limit=10000):
        self.daily_limit = daily_limit
        self.used = 0
        self.reset_time = None
        
    def check_quota(self, cost):
        """Check if operation can proceed."""
        if self.should_reset():
            self.reset_quota()
        if self.used + cost > self.daily_limit:
            raise QuotaExceededError()
            
    def track_usage(self, cost):
        """Record quota usage."""
        self.used += cost
```

## Key Features

### 1. Error Recovery

The system implements robust error recovery:

```python
class RecoveryManager:
    """Manages operation state and recovery."""
    
    def save_state(self, operation):
        """Save operation state to file."""
        state = {
            'command': operation.__class__.__name__,
            'args': operation.__dict__,
            'progress': operation.progress,
            'timestamp': time.time()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f)
            
    def load_state(self):
        """Load saved operation state."""
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                return json.load(f)
        return None
```

### 2. Batch Processing

Implements efficient batch operations:

```python
def batch_process(items, operation, batch_size=50):
    """Process items in batches."""
    results = []
    for batch in chunks(items, batch_size):
        try:
            result = operation(batch)
            results.extend(result)
        except Exception as e:
            handle_batch_error(e, batch)
    return results
```

### 3. Progress Reporting

Provides detailed operation progress:

```python
class ProgressTracker:
    """Tracks operation progress."""
    
    def update(self, completed, total):
        """Update progress state."""
        self.completed = completed
        self.total = total
        self.percentage = (completed / total) * 100
        if self.verbose:
            self.display_progress()
            
    def display_progress(self):
        """Show progress bar and stats."""
        bar = self.create_progress_bar()
        stats = self.get_statistics()
        print(f"\r{bar} {stats}", end="")
```

## Performance Optimizations

### 1. Smart Caching

- Cache playlist metadata with TTL
- Batch cache updates
- Partial cache utilization
- Cache invalidation on modifications

### 2. Quota Optimization

- Batch operations to reduce quota usage
- Smart request bundling
- Cache utilization to avoid redundant calls
- Quota usage tracking and limits

### 3. Network Efficiency

- Retry with exponential backoff
- Connection pooling
- Request compression
- Parallel operations where possible

## Testing Strategy

### 1. Unit Tests

Test individual components in isolation:

```python
def test_cache_expiration():
    """Test cache TTL behavior."""
    cache = Cache(ttl=1)
    cache.set("key", "value")
    assert cache.get("key") == "value"
    time.sleep(2)
    assert cache.get("key") is None
```

### 2. Integration Tests

Test component interactions:

```python
def test_command_execution():
    """Test full command execution flow."""
    cmd = ConsolidateCommand(source="PL123", target="PL456")
    cmd.execute()
    assert cmd.api.get_playlist_items("PL456")
```

### 3. Error Handling Tests

Verify error recovery:

```python
def test_quota_exceeded_recovery():
    """Test recovery from quota exceeded."""
    cmd = ConsolidateCommand(source="PL123", target="PL456")
    cmd.quota_manager.used = cmd.quota_manager.daily_limit
    with pytest.raises(QuotaExceededError):
        cmd.execute()
    assert cmd.recovery_manager.load_state() is not None
```

## Security Considerations

### 1. API Authentication

- OAuth 2.0 for user authentication
- Secure credential storage
- Token refresh handling
- Scope limitations

### 2. Data Protection

- No permanent storage of video data
- Secure file permissions
- Clean directory structure:
  ```
  data/
  ├── credentials/  # API credentials and tokens
  ├── cache/       # Cached API responses
  ├── state/       # Operation state files
  └── recovery/    # Recovery files
  ```
- Sanitized error messages

### 3. File Management

The system uses a structured approach to file management:

1. **Credentials Directory** (`data/credentials/`)
   - OAuth2 tokens
   - API credentials
   - Secure permissions

2. **Cache Directory** (`data/cache/`)
   - TTL-based caching
   - Playlist metadata
   - Video information
   - Auto-cleanup after 7 days

3. **State Directory** (`data/state/`)
   - Operation state files
   - Undo operation history
   - Command progress tracking

4. **Recovery Directory** (`data/recovery/`)
   - Interrupted operation state
   - Progress tracking
   - Auto-cleanup of old files

All directories are configurable via environment variables:
```bash
DATA_DIR=/path/to/data
CREDENTIALS_DIR=/path/to/credentials
CACHE_DIR=/path/to/cache
STATE_DIR=/path/to/state
RECOVERY_DIR=/path/to/recovery
```

## Future Enhancements

1. **Performance Improvements**
   - Parallel playlist processing
   - Improved caching strategies
   - Better quota utilization

2. **Feature Additions**
   - Playlist analytics
   - Custom classification rules
   - Backup/restore functionality

3. **User Experience**
   - Interactive mode
   - Better progress visualization
   - Configuration profiles 