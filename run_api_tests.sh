#!/bin/bash

# Script to run YouTube API tests with quota checking

# Check if --skip-quota-check flag is provided
if [[ "$*" == *"--skip-quota-check"* ]]; then
    echo "Skipping quota check..."
    pytest -v -m "api or performance"
    exit $?
fi

# Run quota check
echo "Checking YouTube API quota..."
python3 -c "
from src.youtubesorter.quota import check_quota
used, remaining = check_quota()
print(f'\nCurrent YouTube API Quota Status:')
print(f'Used: {used}')
print(f'Remaining: {remaining}')

if remaining < 1000:
    print('\nError: Insufficient quota remaining to run API tests.')
    print(f'Need at least 1000 units, but only {remaining} remaining.')
    exit(1)

print('\nSufficient quota available. Proceeding with tests...\n')
"

# If quota check passed, run the tests
if [ $? -eq 0 ]; then
    pytest -v -m "api or performance"
fi 