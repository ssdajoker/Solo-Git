#!/bin/bash
# Setup script for pre-commit hooks

set -e

echo "🔧 Setting up Solo-Git development hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install the hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install --install-hooks

# Install commit-msg hook
echo "💬 Installing commit-msg hook..."
pre-commit install --hook-type commit-msg

# Run hooks against all files to check everything is working
echo "✅ Running hooks against all files..."
pre-commit run --all-files || {
    echo "⚠️  Some hooks failed, but that's okay! They've been installed."
    echo "   Fix the issues and commit again."
}

echo ""
echo "✨ Pre-commit hooks installed successfully!"
echo ""
echo "Available manual hooks:"
echo "  - pytest-preflight:   pre-commit run pytest-preflight --all-files"
echo "  - coverage-check:     pre-commit run coverage-check --all-files"
echo "  - no-print-statements: pre-commit run no-print-statements --all-files"
echo ""
echo "To skip hooks temporarily:"
echo "  git commit --no-verify"
echo ""
echo "To update hooks:"
echo "  pre-commit autoupdate"
echo ""
