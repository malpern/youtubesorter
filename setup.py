"""Setup script for YouTube Playlist Filter & Mover."""

from setuptools import setup, find_namespace_packages

setup(
    name="youtubesorter",
    version="0.1.0",
    description="Filter and move videos between YouTube playlists",
    author="Micah Alpern",
    author_email="malpern@gmail.com",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    install_requires=[
        "google-api-python-client>=2.0.0",
        "google-auth-oauthlib>=0.4.0",
        "openai>=1.0.0",
        "tqdm>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "youtubesorter=youtubesorter.cli:main",
            "youtubeconsolidate=youtubesorter.consolidate:main",
            "youtubedistribute=youtubesorter.distribute:main",
        ]
    },
)
