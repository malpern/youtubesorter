import pytest
from src.youtubesorter.quota import check_quota


def pytest_addoption(parser):
    parser.addoption(
        "--run-api", action="store_true", default=False, help="run tests that hit the YouTube API"
    )
    parser.addoption(
        "--check-quota",
        action="store_true",
        default=False,
        help="check quota before running API tests",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-api"):
        skip_api = pytest.mark.skip(reason="need --run-api option to run")
        for item in items:
            if "api" in item.keywords or "performance" in item.keywords:
                item.add_marker(skip_api)


def pytest_sessionstart(session):
    """Check quota before running API tests if --check-quota is specified."""
    if session.config.getoption("--check-quota"):
        used, remaining = check_quota()
        print("\nCurrent YouTube API Quota Status:")
        print(f"Used: {used}")
        print(f"Remaining: {remaining}")

        if remaining < 1000:  # Minimum required quota for running tests
            pytest.exit("Insufficient quota remaining to run API tests")
