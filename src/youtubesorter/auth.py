"""YouTube API authentication handling."""

import os
import pickle
from typing import Optional
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from . import config


def get_youtube_service() -> Optional[object]:
    """
    Get an authenticated YouTube service object.
    Returns None if authentication fails.
    """
    # Check for client secrets file first
    if not config.CLIENT_SECRETS_FILE:
        print("GOOGLE_CLIENT_SECRETS_FILE environment variable not set")
        return None

    creds = None

    # Load existing credentials if available
    if os.path.exists(config.TOKEN_FILE):
        with open(config.TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.CLIENT_SECRETS_FILE, config.YOUTUBE_SCOPES
                )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Authentication failed: {str(e)}")
                return None

        # Save the credentials for the next run
        os.makedirs(os.path.dirname(config.TOKEN_FILE), exist_ok=True)
        with open(config.TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    try:
        # Build the YouTube service
        youtube = build("youtube", "v3", credentials=creds)
        return youtube
    except Exception as e:
        print(f"Failed to build YouTube service: {str(e)}")
        return None
