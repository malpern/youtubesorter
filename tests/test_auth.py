"""Tests for the auth module."""

import os
import pickle
from unittest.mock import MagicMock, patch, mock_open

import pytest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.youtubesorter.auth import get_youtube_service
from src.youtubesorter import config


@pytest.fixture
def mock_credentials():
    """Create mock credentials."""
    creds = MagicMock(spec=Credentials)
    creds.valid = True
    creds.expired = False
    creds.refresh_token = True
    return creds


def test_get_youtube_service_no_secrets_file():
    """Test service creation when client secrets file is not set."""
    with patch.object(config, "CLIENT_SECRETS_FILE", None):
        assert get_youtube_service() is None


@patch("src.youtubesorter.auth.build")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("pickle.load")
def test_get_youtube_service_existing_valid_creds(
    mock_pickle_load, mock_file, mock_exists, mock_build, mock_credentials
):
    """Test service creation with existing valid credentials."""
    # Mock existing valid credentials
    mock_exists.return_value = True
    mock_pickle_load.return_value = mock_credentials
    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube

    # Call function
    service = get_youtube_service()

    # Verify results
    assert service == mock_youtube
    mock_build.assert_called_once_with("youtube", "v3", credentials=mock_credentials)


@patch("src.youtubesorter.auth.build")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("pickle.load")
@patch("pickle.dump")
def test_get_youtube_service_refresh_expired_creds(
    mock_pickle_dump, mock_pickle_load, mock_file, mock_exists, mock_build, mock_credentials
):
    """Test service creation with expired credentials that can be refreshed."""
    # Mock expired credentials that can be refreshed
    mock_credentials.valid = False
    mock_credentials.expired = True
    mock_exists.return_value = True
    mock_pickle_load.return_value = mock_credentials
    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube

    # Call function
    service = get_youtube_service()

    # Verify results
    assert service == mock_youtube
    mock_credentials.refresh.assert_called_once()
    mock_build.assert_called_once_with("youtube", "v3", credentials=mock_credentials)
    mock_pickle_dump.assert_called_once()


@patch("src.youtubesorter.auth.build")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("pickle.load")
@patch("pickle.dump")
@patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
def test_get_youtube_service_new_auth_flow(
    mock_flow,
    mock_pickle_dump,
    mock_pickle_load,
    mock_file,
    mock_exists,
    mock_build,
    mock_credentials,
):
    """Test service creation with new authentication flow."""
    # Mock new auth flow
    mock_exists.return_value = True
    mock_pickle_load.return_value = None
    mock_flow.return_value.run_local_server.return_value = mock_credentials
    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube

    # Call function
    service = get_youtube_service()

    # Verify results
    assert service == mock_youtube
    mock_flow.assert_called_once_with(config.CLIENT_SECRETS_FILE, config.YOUTUBE_SCOPES)
    mock_build.assert_called_once_with("youtube", "v3", credentials=mock_credentials)
    mock_pickle_dump.assert_called_once()


@patch("src.youtubesorter.auth.build")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("pickle.load")
@patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
def test_get_youtube_service_auth_flow_error(
    mock_flow, mock_pickle_load, mock_file, mock_exists, mock_build
):
    """Test service creation when authentication flow fails."""
    # Mock auth flow error
    mock_exists.return_value = True
    mock_pickle_load.return_value = None
    mock_flow.side_effect = Exception("Auth failed")

    # Call function
    service = get_youtube_service()

    # Verify results
    assert service is None
    mock_flow.assert_called_once_with(config.CLIENT_SECRETS_FILE, config.YOUTUBE_SCOPES)


@patch("src.youtubesorter.auth.build")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("pickle.load")
@patch("pickle.dump")
def test_get_youtube_service_build_error(
    mock_pickle_dump, mock_pickle_load, mock_file, mock_exists, mock_build, mock_credentials
):
    """Test service creation when build fails."""
    # Mock build error
    mock_exists.return_value = True
    mock_pickle_load.return_value = mock_credentials
    mock_build.side_effect = Exception("Build failed")

    # Call function
    service = get_youtube_service()

    # Verify results
    assert service is None
    mock_build.assert_called_once_with("youtube", "v3", credentials=mock_credentials)


@patch("src.youtubesorter.auth.build")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open)
@patch("pickle.load")
@patch("os.makedirs")
@patch("pickle.dump")
def test_get_youtube_service_create_token_dir(
    mock_pickle_dump,
    mock_makedirs,
    mock_pickle_load,
    mock_file,
    mock_exists,
    mock_build,
    mock_credentials,
):
    """Test service creation creates token directory if needed."""
    # Mock directory creation
    mock_exists.side_effect = lambda path: path != config.TOKEN_FILE  # Token file doesn't exist
    mock_pickle_load.return_value = None  # No existing credentials
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_credentials
    with patch(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
        return_value=mock_flow,
    ):
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        # Call function
        service = get_youtube_service()

        # Verify results
        assert service == mock_youtube
        mock_makedirs.assert_called_once_with(os.path.dirname(config.TOKEN_FILE), exist_ok=True)
        mock_pickle_dump.assert_called_once()
