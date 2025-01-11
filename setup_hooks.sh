#!/bin/bash

# Backup existing hook if it exists
if [ -f .git/hooks/pre-commit ]; then
    echo "Backing up existing pre-commit hook to .git/hooks/pre-commit.bak"
    cp .git/hooks/pre-commit .git/hooks/pre-commit.bak
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

echo "Running pre-commit checks..."

# Format code with black
echo "Running black formatter..."
black . || exit 1

# Run all unit tests (including command inheritance)
echo "Running tests..."
pytest -v -m "unit" || exit 1

# Run linting (warnings only)
echo "Running linting checks (warnings only)..."
flake8 src tests --exit-zero

# Run full pylint check (non-blocking)
echo "Running full pylint check (warnings only)..."
PYTHONPATH=. pylint --rcfile=.pylintrc src tests --exit-zero

# Run pylint with command checker (only check for command inheritance, blocking)
echo "Running command structure checks..."
PYTHONPATH=. pylint --disable=all --enable=invalid-command-inheritance,new-command-base-class --rcfile=.pylintrc src/youtubesorter/commands/*.py || exit 1

echo "All checks passed!"
EOF

# Make the hook executable
chmod +x .git/hooks/pre-commit

echo "Git hooks installed successfully!"
echo "Note: Your previous pre-commit hook was backed up to .git/hooks/pre-commit.bak"

# Fix trailing whitespace and missing newlines
find . -type f -name "*.py" -exec sed -i '' -e 's/[[:space:]]*$//' {} +
find . -type f -name "*.py" -exec sh -c '
  if [ -n "$(tail -c1 "{}")" ]; then
    echo >> "{}"
  fi
' \; 