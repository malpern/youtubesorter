# Contributing to YouTube Playlist Organizer

First off, thank you for considering contributing to YouTube Playlist Organizer! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps to reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed after following the steps
* Explain which behavior you expected to see instead and why
* Include any error messages or logs
* Note your Python version and operating system

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* A clear and descriptive title
* A detailed description of the proposed functionality
* Any possible drawbacks or limitations
* Mock-ups or examples of how the feature would work

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Run the test suite
5. Submit a pull request

## Development Setup

1. Clone your fork:
```bash
git clone https://github.com/your-username/youtubesorter2.git
cd youtubesorter2
```

2. Create a virtual environment:
```bash
python -m pip install uv
uv venv
source .venv/bin/activate  # or `.venv/Scripts/activate` on Windows
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Set up pre-commit hooks:
```bash
pre-commit install
```

## Development Process

### Code Style

* Follow PEP 8 guidelines
* Use type hints for all function arguments and return values
* Write docstrings for all public functions and classes
* Keep functions focused and small
* Use descriptive variable names

### Testing

* Write tests for all new functionality
* Maintain or improve test coverage
* Run the full test suite before submitting:
```bash
pytest tests/
```

* Run with coverage:
```bash
pytest --cov=src/youtubesorter tests/
```

### Documentation

* Update docstrings for any modified functions
* Update README.md if adding new features
* Add examples for new functionality
* Keep the documentation up to date with changes

## Project Structure

```
.
├── src/                    # Source code
│   └── youtubesorter/     # Main package
│       ├── api.py         # YouTube API wrapper
│       ├── auth.py        # Authentication
│       ├── cli.py         # Command line interface
│       ├── commands/      # Command implementations
│       └── utils/         # Utility functions
├── tests/                 # Test suite
│   ├── test_api.py       # API tests
│   ├── test_auth.py      # Auth tests
│   └── ...               # Other test modules
└── docs/                 # Documentation
```

## Command Pattern

New commands should follow the existing command pattern:

```python
from youtubesorter.commands.base import YouTubeCommand

class NewCommand(YouTubeCommand):
    """Command description."""
    
    def __init__(self, arg1: str, arg2: int):
        super().__init__()
        self.arg1 = arg1
        self.arg2 = arg2
        
    def validate(self) -> None:
        """Validate command arguments."""
        if not self.arg1:
            raise ValueError("arg1 is required")
            
    def run(self) -> None:
        """Execute the command."""
        # Implementation here
```

## Error Handling

* Use custom exception classes for specific errors
* Handle YouTube API errors appropriately
* Implement proper cleanup in error cases
* Add error cases to test suite

## Performance Considerations

* Use batch operations where possible
* Implement caching for expensive operations
* Monitor and optimize API quota usage
* Test with large playlists (1000+ videos)

## Git Workflow

1. Create a feature branch:
```bash
git checkout -b feature-name
```

2. Make your changes:
* Write code
* Add tests
* Update documentation

3. Commit your changes:
```bash
git add .
git commit -m "Description of changes"
```

4. Push to your fork:
```bash
git push origin feature-name
```

5. Create a Pull Request

## Release Process

1. Update version number in `setup.py`
2. Update CHANGELOG.md
3. Create a new release on GitHub
4. Tag the release

## Getting Help

* Check the documentation
* Look through existing issues
* Join our community discussions
* Reach out to maintainers

Thank you for contributing to YouTube Playlist Organizer! 