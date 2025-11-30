#!/bin/bash
#
# Veritas News Database Setup Script
# Run this to set up a fresh database for development/testing
#
# Usage:
#   ./scripts/setup_dev_db.sh         # Fresh database with 15 articles
#   ./scripts/setup_dev_db.sh 30      # Fresh database with 30 articles
#

set -e

cd "$(dirname "$0")/.."

LIMIT=${1:-15}

echo "🗞️  Veritas News - Database Setup"
echo "=================================="
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Copy .env.example to .env and add your GEMINI_API_KEY"
    echo ""
fi

echo "📦 Setting up fresh database with $LIMIT articles..."
echo ""

# Run the full refresh
uv run python scripts/refresh_database.py --full --limit "$LIMIT"

echo ""
echo "✅ Database setup complete!"
echo ""

# Show status
uv run python scripts/refresh_database.py --status
