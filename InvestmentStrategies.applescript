-- Investment Strategies Launcher
-- This script launches the Quantpedia Strategy Screener application

try
    -- First, kill any process running on port 8092
    do shell script "lsof -ti:8092 | xargs kill -9 2>/dev/null || true"
    
    -- Wait a moment to ensure the port is released
    delay 1
    
    -- Dynamically determine the directory of this script and run the app from there
    set scriptPosix to POSIX path of (path to me)
    set appDir to do shell script "dirname " & quoted form of scriptPosix
    
    -- Launch a Terminal window to run the app (this ensures it stays running)
    tell application "Terminal"
        activate
        do script ("cd " & quoted form of appDir & " && python3 app.py")
    end tell
    
    -- Wait a moment to ensure the app has started
    delay 3
    
    -- Open the browser to the application
    do shell script "open 'http://localhost:8092'"
on error errMsg
    display dialog "Error launching Investment Strategies: " & errMsg buttons {"OK"} with icon stop
end try