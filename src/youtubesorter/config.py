"""Configuration and environment settings."""

import os
from dotenv import load_dotenv

# Force reload of environment variables
load_dotenv(override=True)

# Directory Settings
DATA_DIR = os.getenv("DATA_DIR", "data")
CREDENTIALS_DIR = os.getenv("CREDENTIALS_DIR", os.path.join(DATA_DIR, "credentials"))
CACHE_DIR = os.getenv("CACHE_DIR", os.path.join(DATA_DIR, "cache"))
STATE_DIR = os.getenv("STATE_DIR", os.path.join(DATA_DIR, "state"))
RECOVERY_DIR = os.getenv("RECOVERY_DIR", os.path.join(DATA_DIR, "recovery"))

# YouTube API Settings
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.pickle")

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-3.5-turbo"
BATCH_SIZE = 10  # Number of videos to process in one LLM call
