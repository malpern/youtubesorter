"""Video classification using OpenAI API."""

import logging
import os
from typing import Any, Dict, List

import openai

from .errors import YouTubeError


logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def classify_videos(videos: List[Dict[str, Any]], filter_prompt: str) -> List[bool]:
    """Classify videos based on filter prompt.

    Args:
        videos: List of video dictionaries with titles and descriptions
        filter_prompt: Filter prompt to match against

    Returns:
        List of booleans indicating whether each video matches

    Raises:
        YouTubeError: If classification fails
    """
    try:
        # Prepare video info for classification
        video_info = []
        for video in videos:
            description = video.get("description", "")
            if description is None:
                description = "(No description)"
            info = f"Title: {video['title']}\nDescription: {description}"
            video_info.append(info)

        # Create system prompt
        system_prompt = (
            "You are a video classifier. You will be given video titles and descriptions "
            "and need to determine if they match the given criteria. Respond with only "
            "'yes' or 'no' for each video."
        )

        # Create user prompt
        user_prompt = (
            f"Filter criteria: {filter_prompt}\n\n"
            "For each video, respond with 'yes' if it matches the criteria, "
            "or 'no' if it doesn't:\n\n" + "\n---\n".join(video_info)
        )

        # Get classification from OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )

        # Parse response
        results = response.choices[0].message.content.lower().split("\n")
        matches = [r.strip().startswith("yes") for r in results if r.strip()]

        # Ensure we have a result for each video
        if len(matches) != len(videos):
            raise YouTubeError(
                f"Classification returned {len(matches)} results for {len(videos)} videos"
            )

        return matches

    except Exception as e:
        raise YouTubeError(f"Classification failed: {str(e)}")


def classify_video_titles(videos: List[Dict[str, Any]], filter_prompt: str) -> List[bool]:
    """Classify videos based on titles only.

    Args:
        videos: List of video dictionaries with titles
        filter_prompt: Filter prompt to match against

    Returns:
        List of booleans indicating whether each video matches

    Raises:
        YouTubeError: If classification fails
    """
    # Create videos with empty descriptions
    videos_with_empty_desc = []
    for video in videos:
        video_copy = video.copy()
        video_copy["description"] = "(No description)"
        videos_with_empty_desc.append(video_copy)

    return classify_videos(videos_with_empty_desc, filter_prompt)
