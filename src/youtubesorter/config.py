"""Configuration and environment settings."""

import os
from dotenv import load_dotenv

# Force reload of environment variables
load_dotenv(override=True)

# YouTube API Settings
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
CREDENTIALS_DIR = os.getenv("CREDENTIALS_DIR", "data/credentials")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.pickle")

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo"
BATCH_SIZE = 10  # Number of videos to process in one LLM call
