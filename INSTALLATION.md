# Installation Guide

This guide provides detailed instructions for setting up the YouTube Playlist Organizer on your system.

## Prerequisites

- Python 3.7 or higher
- A Google Cloud project with YouTube Data API v3 enabled
- An OpenAI API key for GPT-powered video classification

## Step 1: Install Python Dependencies

1. Install `uv` if you haven't already:
```bash
python -m pip install uv
```

2. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: `.venv/Scripts/activate`
```

3. Install project dependencies:
```bash
uv pip install -r requirements.txt
```

## Step 2: Set Up YouTube API Access

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Download the client configuration file
   - Rename it to `credentials.json` and place it in the `data/credentials` directory

## Step 3: Get an OpenAI API Key

1. Visit [OpenAI's website](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to the API section
4. Create a new API key

## Step 4: Configure Environment Variables

Create a `.env` file in the project root with your API keys:

```bash
# Create .env file
echo "YOUTUBE_API_KEY=your_youtube_api_key" > .env
echo "OPENAI_API_KEY=your_openai_api_key" >> .env
```

## Step 5: Verify Installation

Run the following commands to verify your installation:

```bash
# Test YouTube API access
youtubeconsolidate --help

# Test a small operation
youtubeconsolidate SOURCE_PLAYLIST -t TARGET_PLAYLIST -p "test" --dry-run
```

## Common Issues and Solutions

### YouTube API Quota Limits

The YouTube Data API has a daily quota limit of 10,000 units. Operations consume quota as follows:
- Reading playlist items: 1 unit per request
- Adding/removing videos: 50 units per operation
- Batch operations can combine up to 50 requests

To avoid quota issues:
- Use `--dry-run` to preview changes
- Start with small playlists while testing
- Monitor your quota usage in the Google Cloud Console

### Authentication Errors

If you encounter authentication errors:
1. Ensure your credentials file is correctly placed
2. Check that the API is enabled in your Google Cloud project
3. Verify your OAuth consent screen is configured
4. Try deleting the token file in `data/credentials` to force reauthentication

### Rate Limiting

The tool automatically handles rate limiting with exponential backoff. If you encounter persistent rate limit errors:
- Reduce batch sizes using `-b` option
- Add delays between operations
- Check your API quotas and limits

## Advanced Configuration

### Custom Cache Directory

Set `CACHE_DIR` in your `.env` file to change the cache location:
```bash
CACHE_DIR=/path/to/cache
```

### Debug Logging

Enable debug logging for troubleshooting:
```bash
youtubeconsolidate SOURCE_PLAYLIST -t TARGET_PLAYLIST -p "test" -d
```

### Multiple Projects

To manage multiple YouTube projects:
1. Create separate credential files
2. Use environment files (e.g., `.env.project1`, `.env.project2`)
3. Switch between them using:
```bash
source switch_project.sh project1
```

## Updating

To update to the latest version:

```bash
git pull
uv pip install -r requirements.txt
```

## Uninstallation

To remove the tool:

1. Deactivate the virtual environment:
```bash
deactivate
```

2. Delete the project directory:
```bash
rm -rf youtubesorter2
```

3. Optionally, revoke API access:
   - Go to Google Cloud Console > APIs & Services > Credentials
   - Delete the OAuth client
   - Go to OpenAI's website and revoke your API key 