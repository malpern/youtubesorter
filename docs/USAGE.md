# Usage Guide

This guide provides detailed information about using the YouTube Playlist Organizer's commands and features.

## Command Overview

The tool provides three main commands:
- `youtubeconsolidate`: Gather matching videos from multiple playlists into one
- `youtubedistribute`: Send videos from one playlist to many based on content
- `youtubededuplicate`: Remove duplicate videos from a playlist

## Common Options

All commands support these options:
```
-v, --verbose       Show detailed progress
-d, --debug        Enable debug logging
-l, --limit N      Process only N videos
-r, --resume       Resume interrupted operation
--dry-run          Preview changes without modifying
```

## Consolidate Command

Gather matching videos from multiple source playlists into a single target playlist.

### Syntax
```bash
youtubeconsolidate [source_playlists...] -t TARGET_PLAYLIST -p "filter prompt" [options]
```

### Arguments
- `source_playlists`: One or more playlist IDs to search through
- `-t, --target`: Target playlist ID to receive matching videos
- `-p, --prompt`: GPT prompt to identify matching videos
- `-m, --move`: Move videos instead of copying them
- `-b, --batch-size`: Number of videos to process at once (default: 50)

### Examples

1. Gather keyboard videos from multiple playlists:
```bash
youtubeconsolidate PL123 PL456 PL789 \
  -t TARGET_PL \
  -p "Videos about mechanical keyboards, typing, or keyboard reviews" \
  -v
```

2. Move (instead of copy) gaming videos:
```bash
youtubeconsolidate PL123 PL456 \
  -t GAMING_PL \
  -p "Gaming videos, let's plays, or game reviews" \
  -m
```

3. Test with a small batch first:
```bash
youtubeconsolidate PL123 \
  -t TEST_PL \
  -p "Test videos" \
  -l 10 \
  --dry-run
```

## Distribute Command

Send videos from one source playlist to multiple target playlists based on content.

### Syntax
```bash
youtubedistribute SOURCE_PLAYLIST -t "playlist1:prompt1,playlist2:prompt2" [options]
```

### Arguments
- `SOURCE_PLAYLIST`: Playlist ID to distribute videos from
- `-t, --targets`: Target playlists and their filter prompts
- `-m, --move`: Move videos instead of copying them
- `-b, --batch-size`: Number of videos to process at once (default: 50)

### Examples

1. Distribute videos to themed playlists:
```bash
youtubedistribute SOURCE_PL -t "
  TECH_PL:Technology reviews and tutorials,
  GAMING_PL:Gaming content and let's plays,
  MUSIC_PL:Music videos and performances"
```

2. Move videos to categories:
```bash
youtubedistribute UNSORTED_PL -t "
  TUTORIALS_PL:Educational or tutorial content,
  VLOGS_PL:Personal vlogs or daily life content" \
  -m
```

3. Test distribution with limits:
```bash
youtubedistribute SOURCE_PL -t "
  TEST1_PL:Test category 1,
  TEST2_PL:Test category 2" \
  -l 5 \
  --dry-run
```

## Deduplicate Command

Remove duplicate videos from a playlist, keeping only the first occurrence.

### Syntax
```bash
youtubededuplicate PLAYLIST_ID [options]
```

### Arguments
- `PLAYLIST_ID`: The playlist to remove duplicates from
- `-b, --batch-size`: Number of videos to process at once (default: 50)

### Examples

1. Basic deduplication:
```bash
youtubededuplicate PL123
```

2. Deduplicate with progress info:
```bash
youtubededuplicate PL123 -v
```

3. Test deduplication:
```bash
youtubededuplicate PL123 --dry-run
```

## Undo Operations

All commands support undoing the last operation.

### Syntax
```bash
youtubeconsolidate undo [options]
youtubedistribute undo [options]
youtubededuplicate undo [options]
```

### Examples

1. Undo last consolidate:
```bash
youtubeconsolidate undo -v
```

2. Preview undo operation:
```bash
youtubedistribute undo --dry-run
```

## Advanced Features

### Resume Interrupted Operations

If an operation is interrupted, you can resume it:
```bash
youtubeconsolidate PL123 -t TARGET_PL -p "prompt" -r
```

### Batch Processing

Control batch size for better performance:
```bash
youtubeconsolidate PL123 -t TARGET_PL -p "prompt" -b 25
```

### Debug Output

Enable detailed logging for troubleshooting:
```bash
youtubeconsolidate PL123 -t TARGET_PL -p "prompt" -d
```

## Best Practices

1. **Start Small**
   - Use `--dry-run` to preview changes
   - Start with small playlists
   - Use `-l` to limit initial operations

2. **Monitor Progress**
   - Use `-v` for detailed progress
   - Check operation statistics
   - Monitor quota usage

3. **Handle Interruptions**
   - Use `-r` to resume operations
   - Keep track of operation state
   - Review changes after completion

4. **Optimize Performance**
   - Adjust batch size with `-b`
   - Use move instead of copy when appropriate
   - Enable caching for repeated operations

## Error Handling

The tool automatically handles common issues:
- Network errors: Automatic retry with backoff
- Rate limits: Smart quota management
- API errors: Detailed error messages
- Interruptions: State recovery

If you encounter persistent errors:
1. Enable debug logging (`-d`)
2. Check quota usage
3. Verify playlist permissions
4. Review error messages
5. Try smaller batch sizes

## Examples for Common Tasks

### Organizing Music Videos
```bash
# Create genre-specific playlists
youtubedistribute MUSIC_PL -t "
  ROCK_PL:Rock music videos and performances,
  JAZZ_PL:Jazz music videos and performances,
  CLASSICAL_PL:Classical music performances"
```

### Managing Tutorial Content
```bash
# Consolidate programming tutorials
youtubeconsolidate PL1 PL2 PL3 \
  -t CODING_PL \
  -p "Programming tutorials, coding lessons, or development guides"
```

### Cleaning Up Playlists
```bash
# Remove duplicates and organize
youtubededuplicate MESSY_PL
youtubedistribute MESSY_PL -t "
  KEEP_PL:High quality content worth keeping,
  ARCHIVE_PL:Content to archive for later"
``` 