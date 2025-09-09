#!/bin/bash

# Investment Strategies App Launcher
# Simple, reliable launcher that works from any location

# Change to this script's directory (robust against moved Dropbox paths)
script_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$script_dir"
echo "Working directory: $(pwd)"

# Kill any existing process on port 8092
echo "Checking if port 8092 is in use..."
pid=$(lsof -ti :8092 2>/dev/null)
if [ -n "$pid" ]; then
    echo "Port 8092 is in use by PID $pid. Stopping the process..."
    kill -9 $pid
    sleep 1
fi

# Launch the application
echo "Starting Investment Strategies app..."
echo "----------------------------------"
python3 app.py &
APP_PID=$!

# Wait for the app to start
echo "Waiting for app to start..."
sleep 5

# Open browser
echo "Opening browser..."
open "http://localhost:8092"

# Tell the user what's happening
echo ""
echo "Application is running. You can close this window, but the app will continue running."
echo "To stop the app, use: kill -9 $(lsof -ti :8092)"
echo ""