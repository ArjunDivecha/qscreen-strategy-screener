#!/bin/bash

# Investment Strategies Launcher
# This script launches the Quantpedia Strategy Screener application

# Navigate to this script's directory (robust to Dropbox path changes)
script_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$script_dir"

# Check if Python environment needs to be activated
# If you're using base Conda environment, it might already be activated
# Uncomment the following line if you need to activate a specific environment
# conda activate base

# Launch the Flask application
python3 app.py

# Keep the terminal window open after the app exits
echo "Press Enter to close this window..."
read