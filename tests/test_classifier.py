"""Test cases for video classification."""

from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from src.youtubesorter import classifier


class TestClassifier(TestCase):
    """Test cases for video classification."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_videos = [
            {
                "video_id": "video1",
                "title": "Python Tutorial",
                "description": "Learn Python programming basics",
            },
            {
                "video_id": "video2",
                "title": "Cat Video",
                "description": "Funny cats playing with yarn",
            },
            {
                "video_id": "video3",
                "title": "Programming Tips",
                "description": "",
            },
        ]
        self.filter_prompt = "Videos about programming"

    @patch("src.youtubesorter.classifier.client")
    def test_classification_with_descriptions(self, mock_client):
        """Test that classification uses both title and description."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="yes\nno\nyes"))]
        mock_client.chat.completions.create.return_value = mock_response

        results = classifier.classify_videos(self.test_videos, self.filter_prompt)

        # Verify the prompt includes descriptions
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        self.assertIn("Learn Python programming basics", prompt)
        self.assertIn("Funny cats playing with yarn", prompt)
        self.assertIn("Description: ", prompt)

        # Verify classification results
        self.assertEqual(results, [True, False, True])

    @patch("src.youtubesorter.classifier.client")
    def test_classification_with_empty_descriptions(self, mock_client):
        """Test classification with empty descriptions."""
        videos = [
            {"title": "Python Tutorial", "description": "", "video_id": "123"},
            {"title": "Cat Video", "description": None, "video_id": "456"},
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="yes\nno"))]
        mock_client.chat.completions.create.return_value = mock_response

        results = classifier.classify_video_titles(videos, self.filter_prompt)

        # Verify both empty and None descriptions are handled
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        self.assertIn("(No description)", prompt)
        self.assertEqual(results, [True, False])

    @patch("src.youtubesorter.classifier.client")
    def test_description_affects_classification(self, mock_client):
        """Test that descriptions can affect classification results."""
        videos = [
            {
                "title": "Fun Video",  # Ambiguous title
                "description": "A detailed Python programming tutorial",
                "video_id": "123",
            },
            {
                "title": "Programming Video",  # Related title
                "description": "Just cats playing with computers",
                "video_id": "456",
            },
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="yes\nno"))]
        mock_client.chat.completions.create.return_value = mock_response

        results = classifier.classify_video_titles(videos, self.filter_prompt)

        # Verify the prompt emphasizes using both title and description
        call_args = mock_client.chat.completions.create.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        self.assertIn("titles and descriptions", system_prompt)
        self.assertEqual(results, [True, False])


if __name__ == "__main__":
    main()
