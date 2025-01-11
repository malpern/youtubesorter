# YouTube Playlist Organizer

A powerful command-line tool for organizing YouTube playlists using AI-powered filtering. Efficiently manage your YouTube playlists with intelligent video sorting, deduplication, and batch operations.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)]()
[![Code Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen)]()
[![Code Quality](https://img.shields.io/badge/pylint-9.21%2F10-brightgreen)]()

## Features

🤖 **AI-Powered Sorting**
- Intelligent video classification using GPT
- Semantic matching of video content
- Customizable classification rules

🚀 **Efficient Operations**
- Batch processing for better performance
- Smart caching to reduce API calls
- Quota management to prevent limits
- Parallel playlist processing

💪 **Robust & Reliable**
- 91% test coverage
- Automatic error recovery
- Resume interrupted operations
- Undo support for all operations

## Quick Start

1. **Install the package**
```bash
python -m pip install uv  # if you don't have uv installed
uv venv
source .venv/bin/activate  # or `.venv/Scripts/activate` on Windows
uv pip install -r requirements.txt
```

2. **Set up YouTube API credentials**
```bash
# Create a .env file with your credentials
echo "YOUTUBE_API_KEY=your_api_key" > .env
echo "OPENAI_API_KEY=your_openai_key" >> .env
```

3. **Start organizing!**
```bash
# Consolidate videos about keyboards from multiple playlists
youtubeconsolidate playlist1 playlist2 -t target_playlist -p "Videos about mechanical keyboards"

# Distribute videos to themed playlists
youtubedistribute source_playlist -t "gaming:Gaming videos,music:Music videos"

# Remove duplicates from a playlist
youtubededuplicate playlist_id
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Usage Guide](docs/USAGE.md) - Complete command reference
- [Architecture](docs/ARCHITECTURE.md) - Technical implementation details
- [Changelog](docs/CHANGELOG.md) - Version history

## Key Commands

### Consolidate
Gather matching videos from multiple source playlists into one:
```bash
youtubeconsolidate [source_playlists...] -t TARGET_PLAYLIST -p "filter prompt"
```

### Distribute
Send videos from one playlist to many based on content:
```bash
youtubedistribute SOURCE_PLAYLIST -t "playlist1:prompt1,playlist2:prompt2"
```

### Deduplicate
Remove duplicate videos from a playlist:
```bash
youtubededuplicate PLAYLIST_ID [options]
```

### Common Options
- `-m, --move`: Move videos instead of copying
- `-v, --verbose`: Show detailed progress
- `-d, --debug`: Enable debug logging
- `-l, --limit N`: Process only N videos
- `-r, --resume`: Resume interrupted operation
- `--dry-run`: Preview changes without modifying

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## Acknowledgments

- Built with [google-api-python-client](https://github.com/googleapis/google-api-python-client)
- Powered by [OpenAI GPT](https://openai.com/gpt-4)