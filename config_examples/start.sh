# ============================================================================
# start.sh - Production Start Script
# ============================================================================
#!/bin/bash

# Exit on error
set -e

echo "Starting PDF Tagger application..."

# Create necessary directories
mkdir -p uploads outputs tmp

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | xargs)
fi

# Start gunicorn
echo "Starting Gunicorn..."
gunicorn --config gunicorn_config.py app:app