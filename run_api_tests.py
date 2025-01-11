#!/usr/bin/env python3
"""Script to run YouTube API tests with quota checking."""

import sys
import subprocess
import click
from src.youtubesorter.quota import check_quota


@click.command()
@click.option("--skip-quota-check", is_flag=True, help="Skip quota check before running tests")
@click.option("--min-quota", default=1000, help="Minimum quota required to run tests")
def run_api_tests(skip_quota_check, min_quota):
    """Run YouTube API tests with quota checking."""
    if not skip_quota_check:
        used, remaining = check_quota()
        click.echo("\nCurrent YouTube API Quota Status:")
        click.echo(f"Used: {used}")
        click.echo(f"Remaining: {remaining}")

        if remaining < min_quota:
            msg = (
                f"\nError: Insufficient quota remaining to run API tests. "
                f"Need at least {min_quota} units, but only {remaining} "
                "remaining."
            )
            click.echo(msg)
            sys.exit(1)

        click.echo("\nSufficient quota available. Proceeding with tests...")

    # Run pytest with API tests enabled
    result = subprocess.run(["pytest", "-v", "-m", "api or performance", "--run-api"])

    sys.exit(result.returncode)


if __name__ == "__main__":
    run_api_tests()
