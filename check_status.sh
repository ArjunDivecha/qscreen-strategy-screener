#!/bin/bash

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Checking application status..."

# Check process
if pgrep -fl app.py > /dev/null; then
    echo "✅ Application process is running"
else
    echo "❌ Application process is NOT running"
fi

# Check log file
LOG_FILE="logs/app.log"
if [ -f "$LOG_FILE" ]; then
    echo "Log file exists"
    # Show last 10 lines of log
    echo "Last 10 log entries:"
    tail -n 10 "$LOG_FILE"
else
    echo "❌ Log file does not exist"
fi

# Check port binding
if lsof -i :8091 > /dev/null; then
    echo "✅ Application is listening on port 8091"
else
    echo "❌ Application is NOT listening on port 8091"
fi 